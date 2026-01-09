#!/usr/bin/env python3
"""
FastAPI-Amis-Admin 复制功能演示示例
展示如何在实际应用中使用复制新增功能
"""

import datetime
from typing import List, Optional, Dict, Any

import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

from fastapi import Request
from pydantic import BaseModel
from sqlmodel import SQLModel, Field, Session, select
from sqlalchemy.exc import IntegrityError

from fastapi_amis_admin import admin
from fastapi_amis_admin.admin import AdminAction, ModelAction
from fastapi_amis_admin.admin.site import AdminSite
from fastapi_amis_admin.admin.admin import BaseApiOut
from fastapi_amis_admin.amis.components import Dialog, ActionType, Action
from fastapi_amis_admin.crud.schema import BaseApiOut
from fastapi_amis_admin.admin.settings import Settings


# 创建AdminSite实例
site = AdminSite(settings=Settings(database_url_async="postgresql+asyncpg://postgres:pwd123456@localhost:5432/amisadmin", site_path="/admin"))


# 示例模型：合同模型
class Contract(SQLModel, table=True):
    __tablename__ = "contracts_original"
    
    id: int = Field(default=None, primary_key=True, nullable=False)
    contract_no: str = Field(title="合同编号", unique=True, min_length=1, max_length=50)
    name: str = Field(title="合同名称", min_length=1, max_length=200)
    type: str = Field(title="合同类型", max_length=50)
    signing_date: datetime.date = Field(title="签订日期")
    expiry_date: datetime.date = Field(title="到期日期")
    party_a: str = Field(title="甲方", max_length=100)
    party_b: str = Field(title="乙方", max_length=100)
    amount: float = Field(title="合同金额", ge=0)
    status: str = Field(title="合同状态", default="draft", description="草稿、待审核、已生效、已过期、已终止")
    department: str = Field(title="所属部门", max_length=50)
    creator: str = Field(title="创建人", max_length=50)
    create_time: datetime.datetime = Field(default_factory=datetime.datetime.now, title="创建时间")
    update_time: datetime.datetime = Field(default_factory=datetime.datetime.now, title="更新时间")
    description: str = Field(default="", title="合同描述")


# 示例模型：报价模型
class Quote(SQLModel, table=True):
    __tablename__ = "quotes_original"
    
    id: int = Field(default=None, primary_key=True, nullable=False)
    customer_name: str = Field(title="客户名称", min_length=1, max_length=100)
    customer_email: str = Field(title="客户邮箱", max_length=100)
    customer_phone: str = Field(title="客户电话", max_length=20)
    products: str = Field(title="产品列表", description="JSON格式的产品列表")
    total_price: float = Field(title="总价", ge=0)
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.now, title="创建时间")
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.now, title="更新时间")
    status: str = Field(default="draft", title="状态", description="draft: 草稿, sent: 已发送, accepted: 已接受, rejected: 已拒绝")


# 示例模型：项目模型
class Project(SQLModel, table=True):
    __tablename__ = "projects_original"
    
    id: int = Field(default=None, primary_key=True, nullable=False)
    name: str = Field(title="项目名称", min_length=1, max_length=200)
    description: str = Field(title="项目描述", default="")
    planned_start_time: datetime.datetime = Field(title="计划开始时间")
    planned_end_time: datetime.datetime = Field(title="计划结束时间")
    actual_start_time: Optional[datetime.datetime] = Field(title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime.datetime] = Field(title="实际结束时间", nullable=True)
    project_manager: Optional[int] = Field(title="项目负责人", nullable=True)
    amount: float = Field(title="项目金额", ge=0)
    status: str = Field(title="项目状态", default="pending", description="待开始、进行中、已完成、已暂停、已终止")
    contract_id: Optional[int] = Field(title="关联合同ID", foreign_key="contracts_original.id", nullable=True)
    create_time: datetime.datetime = Field(default_factory=datetime.datetime.now, title="创建时间")
    update_time: datetime.datetime = Field(default_factory=datetime.datetime.now, title="更新时间")


# 工具函数：清理复制数据
def clean_copy_data(item_dict: Dict[str, Any], pk_name: str) -> Dict[str, Any]:
    """
    清除复制数据中的主键和时间戳
    
    Args:
        item_dict: 原始数据字典
        pk_name: 主键字段名
        
    Returns:
        清理后的数据字典
    """
    # 创建副本，避免修改原始数据
    cleaned_data = item_dict.copy()
    
    # 移除主键字段
    cleaned_data.pop(pk_name, None)
    
    # 移除常见时间戳字段
    timestamp_fields = ['create_time', 'update_time', 'created_at', 'updated_at']
    for field in timestamp_fields:
        cleaned_data.pop(field, None)
    
    return cleaned_data


# 工具函数：生成新合同编号
def generate_contract_no(old_no: str, index: int = 1) -> str:
    """
    生成新合同编号
    
    Args:
        old_no: 原始合同编号
        index: 复制索引，用于生成多个副本
        
    Returns:
        新的合同编号
    """
    # 尝试匹配标准合同编号格式: CONYYYYNNN
    import re
    match = re.match(r"(CON\d{4})(\d{3})", old_no)
    if match:
        prefix = match.group(1)
        num = int(match.group(2)) + index
        return f"{prefix}{num:03d}"
    
    # 如果不匹配标准格式，添加后缀
    return f"{old_no}_copy_{index}"


# 工具函数：根据模型类型处理复制数据
def process_model_data(item_dict: Dict[str, Any], model_name: str, index: int = 1, reset_status: bool = True) -> Dict[str, Any]:
    """
    根据模型类型处理复制数据
    
    Args:
        item_dict: 原始数据字典
        model_name: 模型名称
        index: 复制索引
        reset_status: 是否重置状态
        
    Returns:
        处理后的数据字典
    """
    # 创建副本，避免修改原始数据
    processed_data = item_dict.copy()
    
    if model_name == 'Contract':
        # 生成新的合同编号
        old_contract_no = processed_data.get('contract_no', '')
        if old_contract_no:
            processed_data['contract_no'] = generate_contract_no(old_contract_no, index)
        
        # 重置状态为草稿
        if reset_status:
            processed_data['status'] = 'draft'
    
    elif model_name == 'Quote':
        # 重置状态为草稿
        if reset_status:
            processed_data['status'] = 'draft'
    
    elif model_name == 'Project':
        # 重置状态为待开始
        if reset_status:
            processed_data['status'] = 'pending'
        
        # 清空实际时间字段
        processed_data['actual_start_time'] = None
        processed_data['actual_end_time'] = None
    
    # 添加复制标记（仅当复制多个时）
    if index > 1:
        name = processed_data.get('name', '')
        processed_data['name'] = f"{name} (副本{index})"
    
    return processed_data


# 复制新增动作类
class CopyCreateAction(admin.ModelAction):
    """
    复制新增动作类
    提供弹窗配置，允许用户选择复制数量、是否重置状态等选项
    """
    
    # 配置动作基本信息
    action = ActionType.Dialog(
        label="复制新增",  
        icon="fa fa-copy",
        dialog=Dialog(title="复制新增", size="lg")
    )
    
    # 定义复制时的自定义表单模型
    class schema(BaseModel):
        """复制参数表单模型"""
        copy_count: int = Field(1, title="复制数量", ge=1, le=10, description="最多复制10条")
        reset_status: bool = Field(True, title="重置状态", description="是否重置状态为初始值")
        copy_related: bool = Field(False, title="复制关联数据", description="是否同时复制关联数据")
    
    def __init__(self, admin: admin.ModelAdmin, **kwargs):
        """初始化复制动作"""
        super().__init__(admin, **kwargs)
        # 保存admin引用
        self.admin = admin
    
    async def get_action(self, request: Request, **kwargs) -> Action:
        """获取动作配置，自定义弹窗表单"""
        # 获取默认动作配置
        action = await super().get_action(request, **kwargs)
        
        # 获取模型管理员的路由路径
        admin = self.admin
        router_path = admin.router_path if hasattr(admin, 'router_path') else admin.router.prefix
        
        # 自定义弹窗表单
        action.dialog.body = {
            "type": "form",
            "title": "复制参数设置",
            "api": {
                "method": "post",
                "url": f"{router_path}{self.page_path}",
                "data": {
                    "copy_count": "${copy_count}",
                    "reset_status": "${reset_status}",
                    "copy_related": "${copy_related}",
                    "item_id": "${ids}"
                }
            },
            "body": [
                {
                    "type": "input-number",
                    "name": "copy_count",
                    "label": "复制数量",
                    "value": 1,
                    "min": 1,
                    "max": 10,
                    "description": "最多复制10条记录"
                },
                {
                    "type": "switch",
                    "name": "reset_status",
                    "label": "重置状态",
                    "value": True,
                    "description": "是否重置状态为初始值"
                },
                {
                    "type": "switch",
                    "name": "copy_related",
                    "label": "复制关联数据",
                    "value": False,
                    "description": "是否同时复制关联数据"
                }
            ],
            "actions": [
                {
                    "type": "submit",
                    "label": "确认复制",
                    "primary": True
                },
                {
                    "type": "button",
                    "label": "取消",
                    "actionType": "cancel"
                }
            ]
        }
        
        return action
    
    async def handle(self, request: Request, data: Optional[dict], item_id: List[str], **kwargs):
        """处理复制逻辑"""
        try:
            # 获取表单参数
            copy_count = int(data.get('copy_count', 1)) if data else 1
            reset_status = data.get('reset_status', True) if data else True
            copy_related = data.get('copy_related', False) if data else False
            
            # 添加调试日志
            logger.debug(f"复制参数: copy_count={copy_count}, reset_status={reset_status}, copy_related={copy_related}")
            
            # 验证参数
            if copy_count < 1 or copy_count > 10:
                return {"status": -1, "msg": "复制数量必须在1-10之间"}
            
            # 获取模型类
            model = self.get_model(request)
            
            # 获取主键名称
            pk_name = model.__table__.primary_key.columns.keys()[0]
            logger.debug(f"模型: {model.__name__}, 主键字段: {pk_name}")
            
            # 获取原始数据
            if item_id and len(item_id) > 0:
                # 从数据库获取原始数据
                logger.debug(f"从数据库获取原始数据，ID列表: {item_id}")
                original_items = await request.state.session.execute(
                    select(model).where(model.id.in_(item_id))
                )
                original_items = original_items.scalars().all()
            else:
                # 如果没有item_id，从data中获取
                if not data or 'id' not in data:
                    return {"status": -1, "msg": "缺少要复制的数据ID"}
                logger.debug(f"从data中获取原始数据，ID: {data['id']}")
                original_item = await request.state.session.get(model, data['id'])
                original_items = [original_item] if original_item else []
            
            if not original_items:
                return {"status": -1, "msg": "未找到要复制的数据"}
            
            logger.debug(f"找到 {len(original_items)} 条原始数据")
            
            # 复制数据
            result = []
            for original_item in original_items:
                # 转换为字典
                item_dict = self.model_to_dict(original_item, request=request)
                logger.debug(f"原始数据字典: {item_dict}")
                
                # 清理数据（移除主键和时间戳）
                cleaned_data = clean_copy_data(item_dict, pk_name)
                logger.debug(f"清理后数据: {cleaned_data}")
                
                # 复制指定次数
                for i in range(copy_count):
                    # 处理复制数据
                    processed_data = process_model_data(
                        cleaned_data, 
                        self.model_name, 
                        i + 1,  # 从1开始计数
                        reset_status
                    )
                    logger.debug(f"处理后的数据 (副本{i+1}): {processed_data}")
                    
                    # 创建新记录
                    new_item = model(**processed_data)
                    request.state.session.add(new_item)
                    await request.state.session.flush()  # 获取新ID
                    logger.debug(f"创建新记录，ID: {new_item.id}")
                    
                    result.append({
                        "id": new_item.id,
                        "name": getattr(new_item, 'name', ''),
                        "contract_no": getattr(new_item, 'contract_no', ''),
                        "status": getattr(new_item, 'status', '')
                    })
            
            # 提交事务
            await request.state.session.commit()
            logger.debug(f"事务已提交，总共创建了 {len(result)} 条记录")
            
            return {
                "status": 0,
                "msg": f"成功复制{len(result)}条数据",
                "data": result
            }
            
        except Exception as e:
            # 回滚事务
            await request.state.session.rollback()
            logger.error(f"复制失败: {str(e)}")
            return {
                "status": -1,
                "msg": f"复制失败: {str(e)}"
            }


# 快速复制动作类
class QuickCopyAction(admin.ModelAdmin, admin.RouterAdmin):
    """
    快速复制动作类
    一键复制，使用默认参数
    """
    
    # 配置动作基本信息
    action = ActionType.Ajax(
        label="快速复制",  
        icon="fa fa-files-o",
        confirmText="确定要复制这条记录吗？"
    )
    
    def __init__(self, admin: admin.ModelAdmin, **kwargs):
        """初始化快速复制动作"""
        # 保存admin引用
        self.admin = admin
        self.model = admin.model
        self.app = admin.app
        self.engine = admin.engine
        self.name = kwargs.get('name', "quick_copy")
        self.label = kwargs.get('label', "快速复制")
        self.flags = kwargs.get('flags') or ["item"]
        self.action = kwargs.get('action') or self.action
        
        # 设置路由 - 使用私有变量来存储属性值
        self._router_prefix = admin.router_prefix
        self._page_path = "/quick_copy"
        
        # 创建路由
        from fastapi import APIRouter
        self.router = APIRouter()
        self.register_router()
    
    @property
    def router_prefix(self):
        return self._router_prefix
    
    @property
    def page_path(self):
        return self._page_path
    
    async def get_action(self, request: Request, **kwargs) -> Action:
        """获取动作配置"""
        # 获取默认动作配置
        action = self.action.copy() if self.action else Action()
        
        # 确保URL正确，使用正确的参数名称
        action.api = {
            "method": "post",
            "url": f"{self.router_prefix}{self.page_path}",
            "data": {
                "item_id": "${id}"
            }
        }
        
        return action
    
    def register_router(self):
        """注册路由"""
        # 直接在admin的路由器上添加路由，而不是使用include_router
        self.admin.router.add_api_route(
            self.page_path,
            self.handle,
            methods=["POST"],
            response_model=BaseApiOut,
            name=f"{self.name}_route"
        )
        return self
    
    # 使用自定义路由处理函数
    async def handle(self, request: Request):
        """处理快速复制动作"""
        try:
            # 从请求中获取item_id参数
            request_data = await request.json()
            item_id = request_data.get('item_id')
            
            if not item_id:
                return BaseApiOut(status=1, msg="缺少必要参数: item_id")
            
            logger.debug(f"快速复制，ID: {item_id}")
            
            # 获取模型类 - 从admin对象获取
            model = self.admin.model
            
            # 获取主键名称
            pk_name = model.__table__.primary_key.columns.keys()[0]
            logger.debug(f"模型: {model.__name__}, 主键字段: {pk_name}")
            
            # 使用request.state.session获取数据库会话
            # 查询原始数据
            stmt = select(model).where(model.__table__.c[pk_name] == item_id)
            result = await request.state.session.execute(stmt)
            item = result.scalar_one_or_none()
            
            if not item:
                return BaseApiOut(status=1, msg="未找到要复制的数据")
            
            # 转换为字典
            item_dict = item.dict()
            logger.debug(f"原始数据: {item_dict}")
            
            # 清理数据（移除主键和时间戳）
            cleaned_data = clean_copy_data(item_dict, pk_name)
            logger.debug(f"清理后数据: {cleaned_data}")
            
            # 处理数据
            processed_data = process_model_data(
                cleaned_data, 
                model.__name__, 
                1,  # 快速复制只复制一条
                True  # 快速复制默认重置状态
            )
            logger.debug(f"处理后的数据: {processed_data}")
            
            # 创建新对象
            new_item = model(**processed_data)
            request.state.session.add(new_item)
            await request.state.session.commit()
            await request.state.session.refresh(new_item)
            logger.debug(f"快速复制成功，新记录ID: {new_item.id}")
            
            # 返回成功结果
            return BaseApiOut(
                status=0, 
                msg="复制成功",
                data={"id": new_item.id}
            )
                
        except IntegrityError as e:
            # 处理唯一约束冲突
            logger.error(f"快速复制失败：数据冲突，请检查唯一约束 - {str(e)}")
            return BaseApiOut(status=1, msg="复制失败：数据冲突，请检查唯一约束")
        except Exception as e:
            # 处理其他异常
            logger.error(f"快速复制失败：{str(e)}")
            return BaseApiOut(status=1, msg=f"复制失败：{str(e)}")


# 注册模型管理类
@site.register_admin
class ContractAdmin(admin.ModelAdmin):
    """合同管理类"""
    page_schema = "合同管理"
    model = Contract
    
    # 添加复制动作
    admin_action_maker = [
        lambda admin: CopyCreateAction(admin, name="copy_create", label="复制新增"),
        lambda admin: QuickCopyAction(admin, name="quick_copy", label="快速复制", flags=["item"])
    ]


@site.register_admin
class QuoteAdmin(admin.ModelAdmin):
    """报价管理类"""
    page_schema = "报价管理"
    model = Quote
    
    # 添加复制动作
    admin_action_maker = [
        lambda admin: CopyCreateAction(admin, name="copy_create", label="复制新增"),
        lambda admin: QuickCopyAction(admin, name="quick_copy", label="快速复制", flags=["item"])
    ]


@site.register_admin
class ProjectAdmin(admin.ModelAdmin):
    """项目管理类"""
    page_schema = "项目管理"
    model = Project
    
    # 添加复制动作
    admin_action_maker = [
        lambda admin: CopyCreateAction(admin, name="copy_create", label="复制新增"),
        lambda admin: QuickCopyAction(admin, name="quick_copy", label="快速复制", flags=["item"])
    ]


# 启动应用
if __name__ == "__main__":
    import uvicorn
    from fastapi import FastAPI
    
    print("启动FastAPI-Amis-Admin复制功能演示应用...")
    print("访问地址: http://127.0.0.1:8001/admin")
    print("用户名: admin")
    print("密码: admin")
    
    # 创建FastAPI应用
    app = FastAPI()
    
    # 挂载后台管理系统
    site.mount_app(app)
    
    uvicorn.run(app, host="127.0.0.1", port=8001)