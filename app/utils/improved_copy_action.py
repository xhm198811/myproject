"""
改进版复制动作类
集成统一错误处理、智能重试和增强用户体验
"""
import asyncio
from typing import List, Dict, Any, Type, Optional, Union
from datetime import datetime
from fastapi import Request
from fastapi_amis_admin import admin, amis
from fastapi_amis_admin.admin import AdminAction, ModelAdmin
from fastapi_amis_admin.amis.components import Action, Alert, Progress, Spinner
from fastapi_amis_admin.crud.schema import BaseApiOut
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .copy_error_handler import (
    handle_copy_exception, 
    CopyErrorContext, 
    CopyErrorCode
)
from .enhanced_copy_utils import (
    enhanced_copy_records_batch,
    enhanced_copy_record,
    copy_with_validation,
    RetryConfig,
    ValidationResult
)


class ImprovedCopyActionSchema(BaseModel):
    """改进版复制操作表单模型"""
    copy_count: int = Field(1, title="复制数量", ge=1, le=10, description="每条记录的复制数量")
    reset_status: bool = Field(True, title="重置状态", description="是否重置记录状态为初始值")
    copy_relations: bool = Field(True, title="复制关联数据", description="是否同时复制关联的子表数据")
    copy_attachments: bool = Field(True, title="复制附件", description="是否复制附件文件")
    preserve_dates: bool = Field(False, title="保留日期", description="是否保留原始创建和更新日期")
    validate_before_copy: bool = Field(True, title="复制前验证", description="是否在复制前进行业务规则验证")
    continue_on_error: bool = Field(True, title="错误时继续", description="遇到错误时是否继续处理其他记录")
    max_retries: int = Field(3, title="最大重试次数", ge=1, le=10, description="失败时的最大重试次数")


class ImprovedCopyAction(AdminAction):
    """改进版复制动作类"""
    
    def __init__(self, admin: ModelAdmin, **kwargs):
        self.admin = admin
        self.model = admin.model
        self.name = kwargs.get('name', "improved_copy")
        self.label = kwargs.get('label', "智能复制")
        self.flags = kwargs.get('flags') or ["item", "batch"]
        if isinstance(self.flags, str):
            self.flags = [self.flags]
        
        self._router_prefix = admin.router_prefix
        self._page_path = "/improved_copy"
        
        # 创建增强版动作配置
        self.action = self._build_enhanced_action(**kwargs)
        self.schema = ImprovedCopyActionSchema
        
        super().__init__(admin=admin, **kwargs)
    
    def _build_enhanced_action(self, **kwargs) -> Action:
        """构建增强版动作配置"""
        return Action(
            label=self.label,
            icon="fa fa-clone",
            actionType="drawer",
            confirmText="",
            flags=self.flags,
            drawer={
                "title": "智能复制记录",
                "size": "lg",
                "body": {
                    "type": "form",
                    "api": {
                        "method": "post",
                        "url": "",
                    },
                    "body": [
                        {
                            "type": "alert",
                            "level": "info",
                            "body": """
                            <div>
                                <p><strong>智能复制功能特性：</strong></p>
                                <ul>
                                    <li>🔄 <strong>自动重试机制</strong> - 网络或数据库临时故障时自动重试</li>
                                    <li>🛡️ <strong>智能验证</strong> - 复制前检查业务规则，避免无效操作</li>
                                    <li>📊 <strong>部分成功处理</strong> - 批量操作时部分失败不影响其他记录</li>
                                    <li>🔍 <strong>详细错误信息</strong> - 提供具体的错误原因和解决建议</li>
                                    <li>⚡ <strong>性能优化</strong> - 并发复制提升大数据量处理速度</li>
                                </ul>
                            </div>
                            """
                        },
                        {
                            "type": "input-number",
                            "name": "copy_count",
                            "label": "复制数量",
                            "value": 1,
                            "min": 1,
                            "max": 10,
                            "required": True,
                            "description": "每条记录将创建的副本数量"
                        },
                        {
                            "type": "group",
                            "body": [
                                {
                                    "type": "switch",
                                    "name": "reset_status",
                                    "label": "重置状态",
                                    "value": True,
                                    "description": "将状态重置为初始值（如草稿、待开始等）"
                                },
                                {
                                    "type": "switch",
                                    "name": "copy_relations", 
                                    "label": "复制关联数据",
                                    "value": True,
                                    "description": "同时复制关联的子表数据（如合同的明细项目）"
                                }
                            ]
                        },
                        {
                            "type": "group", 
                            "body": [
                                {
                                    "type": "switch",
                                    "name": "copy_attachments",
                                    "label": "复制附件",
                                    "value": True,
                                    "description": "复制记录关联的附件文件"
                                },
                                {
                                    "type": "switch",
                                    "name": "preserve_dates",
                                    "label": "保留日期",
                                    "value": False,
                                    "description": "保留原始创建和更新时间戳"
                                }
                            ]
                        },
                        {
                            "type": "group",
                            "body": [
                                {
                                    "type": "switch",
                                    "name": "validate_before_copy",
                                    "label": "复制前验证",
                                    "value": True,
                                    "description": "在复制前检查业务规则和数据完整性"
                                },
                                {
                                    "type": "switch",
                                    "name": "continue_on_error",
                                    "label": "错误时继续",
                                    "value": True,
                                    "description": "遇到错误时继续处理其他记录"
                                }
                            ]
                        },
                        {
                            "type": "input-number",
                            "name": "max_retries",
                            "label": "最大重试次数",
                            "value": 3,
                            "min": 1,
                            "max": 10,
                            "description": "网络或数据库故障时的最大重试次数"
                        }
                    ],
                    "actions": [
                        {
                            "type": "submit",
                            "label": "开始复制",
                            "primary": True,
                            "api": {
                                "method": "post",
                                "url": "",
                            }
                        },
                        {
                            "type": "button",
                            "label": "取消",
                            "actionType": "close"
                        }
                    ]
                }
            }
        )
    
    @property
    def router_prefix(self):
        return self._router_prefix
    
    @property
    def page_path(self):
        return self._page_path
    
    async def get_action(self, request: Request, **kwargs) -> Action:
        """获取动作配置，动态设置API URL"""
        action = self.action.copy() if self.action else Action()
        
        router_prefix = self.router_prefix
        if not router_prefix.startswith('/admin'):
            router_prefix = f"/admin{router_prefix}"
        
        page_path = self.page_path.lstrip('/')
        api_url = f"{router_prefix}/{page_path}/${{id}}"
        
        if hasattr(action, 'api'):
            action.api.url = api_url
        if hasattr(action, 'drawer') and hasattr(action.drawer, 'body'):
            action.drawer.body.api.url = api_url
            if hasattr(action.drawer.body, 'actions'):
                for btn_action in action.drawer.body.actions:
                    if hasattr(btn_action, 'api'):
                        btn_action.api.url = api_url
        
        return action
    
    async def handle(self, request: Request, item_id: str = None, item_ids: List[str] = None, data: dict = None, **kwargs):
        """处理改进版复制操作"""
        try:
            # 获取数据库适配器
            adapter = getattr(self.admin, 'adapter', None)
            if not adapter:
                from app.admin import site
                if hasattr(site, 'db'):
                    adapter = site.db
                else:
                    return handle_copy_exception(
                        Exception("无法获取数据库适配器"),
                        self.model.__name__,
                        "get_adapter",
                        []
                    )
            
            # 确定操作类型和目标ID
            is_batch = item_ids is not None and len(item_ids) > 1
            operation_type = "batch_copy" if is_batch else "single_copy"
            target_ids = item_ids if is_batch else ([item_id] if item_id else [])
            
            # 创建错误上下文
            context = CopyErrorContext(
                model_name=self.model.__name__,
                operation_type=operation_type,
                item_ids=[int(id_) for id_ in target_ids if id_.isdigit()],
                user_id=getattr(request.state, 'user_id', None),
                request_id=getattr(request.state, 'request_id', None),
                additional_data={
                    "is_batch": is_batch,
                    "timestamp": datetime.now().isoformat()
                }
            )
            
            # 如果是GET请求或没有数据，返回预检查信息
            if request.method == "GET" or data is None:
                return await self._handle_preview_request(adapter, context)
            
            # 处理复制操作
            return await self._handle_copy_operation(adapter, context, data)
            
        except Exception as e:
            return handle_copy_exception(
                e,
                self.model.__name__,
                "handle_copy_action",
                target_ids if 'target_ids' in locals() else [],
                user_id=getattr(request.state, 'user_id', None)
            )
    
    async def _handle_preview_request(self, adapter, context: CopyErrorContext) -> BaseApiOut:
        """处理预检查请求"""
        try:
            # 获取要复制的记录信息
            records_info = []
            
            for item_id in context.item_ids:
                stmt = select(self.model).where(self.model.id == item_id)
                result = await adapter.async_scalars(stmt)
                record = result.first()
                
                if record:
                    record_data = {
                        "id": record.id,
                        "name": getattr(record, 'name', f"记录_{record.id}"),
                        "status": getattr(record, 'status', 'unknown'),
                        "created_at": getattr(record, 'created_at', None),
                        "summary": self._get_record_summary(record)
                    }
                    records_info.append(record_data)
            
            if not records_info:
                return BaseApiOut(
                    status=404,
                    msg="没有找到可复制的记录",
                    data={"found_count": 0, "total_requested": len(context.item_ids)}
                )
            
            return BaseApiOut(
                status=200,
                data={
                    "records": records_info,
                    "total_count": len(records_info),
                    "model_name": self.model.__name__,
                    "copy_options": {
                        "copy_count": 1,
                        "reset_status": True,
                        "copy_relations": True,
                        "copy_attachments": True,
                        "preserve_dates": False,
                        "validate_before_copy": True,
                        "continue_on_error": True,
                        "max_retries": 3
                    },
                    "preview": True
                },
                msg=f"找到{len(records_info)}条可复制的记录"
            )
            
        except Exception as e:
            return handle_copy_exception(
                e,
                self.model.__name__,
                "preview_copy",
                context.item_ids,
                user_id=context.user_id,
                request_id=context.request_id
            )
    
    async def _handle_copy_operation(self, adapter, context: CopyErrorContext, data: dict) -> BaseApiOut:
        """处理复制操作"""
        try:
            # 解析复制配置
            copy_config = ImprovedCopyActionSchema(**data)
            
            # 创建转换函数
            transform_func = self._create_transform_function(copy_config)
            
            # 创建重试配置
            retry_config = RetryConfig(
                max_attempts=copy_config.max_retries + 1,  # +1 因为第一次不算重试
                base_delay=1.0,
                max_delay=10.0,
                backoff_factor=2.0
            )
            
            async with adapter.async_session() as session:
                if len(context.item_ids) == 1:
                    # 单条记录复制
                    if copy_config.validate_before_copy:
                        result = await copy_with_validation(
                            session, self.model, context.item_ids[0], 
                            transform_func, context
                        )
                    else:
                        new_record, error = await enhanced_copy_record(
                            session, self.model, context.item_ids[0],
                            transform_func, context, retry_config
                        )
                        
                        if error:
                            return handle_copy_exception(
                                error,
                                self.model.__name__,
                                "single_copy",
                                context.item_ids,
                                user_id=context.user_id,
                                request_id=context.request_id
                            )
                        
                        await session.commit()
                        
                        result = BaseApiOut(
                            status=200,
                            msg="复制成功",
                            data={
                                "new_record_id": new_record.id,
                                "new_record_name": getattr(new_record, 'name', f"副本_{new_record.id}")
                            }
                        )
                else:
                    # 批量复制
                    result = await enhanced_copy_records_batch(
                        session=session,
                        model=self.model,
                        item_ids=context.item_ids,
                        transform=transform_func,
                        context=context,
                        copy_count=copy_config.copy_count,
                        continue_on_error=copy_config.continue_on_error,
                        max_concurrent=5
                    )
                
                return result
                
        except Exception as e:
            return handle_copy_exception(
                e,
                self.model.__name__,
                "copy_operation",
                context.item_ids,
                user_id=context.user_id,
                request_id=context.request_id
            )
    
    def _create_transform_function(self, config: ImprovedCopyActionSchema):
        """创建数据转换函数"""
        def transform(record_dict: Dict[str, Any], copy_index: int = 0) -> Dict[str, Any]:
            """根据配置转换记录数据"""
            transformed = record_dict.copy()
            
            # 始终移除主键和时间戳字段
            for field in ['id', 'created_at', 'updated_at', 'create_time', 'update_time']:
                if field in transformed:
                    del transformed[field]
            
            # 状态处理
            if config.reset_status and 'status' in transformed:
                model_name = self.model.__name__.lower()
                if 'contract' in model_name:
                    transformed['status'] = 'draft'
                elif 'quote' in model_name or 'quotation' in model_name:
                    transformed['status'] = 'draft'
                elif 'project' in model_name:
                    transformed['status'] = 'pending'
                elif 'user' in model_name:
                    transformed['is_active'] = True
            
            # 编码生成处理
            for field in ['contract_no', 'quote_no', 'project_code', 'code', 'serial_number']:
                if field in transformed and transformed[field]:
                    original_code = str(transformed[field])
                    # 添加复制后缀和索引
                    suffix = f"_COPY_{copy_index + 1}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
                    transformed[field] = original_code + suffix
                    break
            
            # 特定字段清理
            model_name = self.model.__name__.lower()
            if 'project' in model_name:
                # 项目特定字段
                if not config.preserve_dates:
                    for field in ['actual_start_date', 'actual_end_date', 'completion_date']:
                        if field in transformed:
                            transformed[field] = None
            
            elif 'user' in model_name:
                # 用户特定字段
                if 'username' in transformed:
                    transformed['username'] = f"{transformed['username']}_copy_{copy_index + 1}"
                if 'email' in transformed and '@' in transformed['email']:
                    email_parts = transformed['email'].split('@')
                    transformed['email'] = f"{email_parts[0]}_copy_{copy_index + 1}@{email_parts[1]}"
                
                # 清空登录相关字段
                for field in ['last_login', 'login_count', 'password_changed_at']:
                    if field in transformed:
                        transformed[field] = None
            
            return transformed
        
        return transform
    
    def _get_record_summary(self, record) -> str:
        """获取记录摘要信息"""
        summary_parts = []
        
        # 基本字段
        for field in ['name', 'title', 'subject', 'description']:
            if hasattr(record, field):
                value = getattr(record, field)
                if value:
                    summary_parts.append(f"{field}: {str(value)[:50]}")
                    break
        
        # 状态信息
        if hasattr(record, 'status'):
            summary_parts.append(f"状态: {record.status}")
        
        # 时间信息
        for field in ['created_at', 'create_time', 'date_joined']:
            if hasattr(record, field):
                value = getattr(record, field)
                if value:
                    summary_parts.append(f"创建: {value.strftime('%Y-%m-%d')}")
                    break
        
        return " | ".join(summary_parts) if summary_parts else f"记录 #{record.id}"


def add_improved_copy_action(admin_class: Type[ModelAdmin]) -> Type[ModelAdmin]:
    """装饰器：为管理类添加改进版复制功能"""
    
    # 保存原始的admin_action_maker
    original_admin_action_maker = getattr(admin_class, 'admin_action_maker', [])
    
    # 定义改进版复制动作的maker函数
    def improved_copy_action_maker(admin):
        return ImprovedCopyAction(admin=admin)
    
    # 更新admin_action_maker
    admin_class.admin_action_maker = [
        *original_admin_action_maker,
        improved_copy_action_maker,
    ]
    
    # 保存原始的__init__方法
    original_init = admin_class.__init__
    
    def new_init(self, app):
        # 初始化custom_actions
        if not hasattr(self, 'custom_actions'):
            self.custom_actions = []
        
        # 调用原始的__init__方法
        original_init(self, app)
        
        # 添加改进版复制动作
        action_names = [action.name for action in self.custom_actions]
        if 'improved_copy' not in action_names:
            improved_copy_action = ImprovedCopyAction(admin=self)
            self.custom_actions.append(improved_copy_action)
    
    # 替换__init__方法
    admin_class.__init__ = new_init
    
    return admin_class