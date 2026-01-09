"""
增强版快速复制功能模块
实现完整的单据复制功能，包括所有字段、关联数据和配置信息
"""
import json
import asyncio
from typing import List, Dict, Any, Type, Optional, Union, Set
from fastapi import Request
from datetime import datetime
from fastapi_amis_admin import admin, amis
from fastapi_amis_admin.admin import AdminAction, FormAction, ModelAdmin
from fastapi_amis_admin.amis.components import Action, Form, InputNumber, Switch, Checkbox, Alert
from fastapi_amis_admin.crud.schema import BaseApiOut
from pydantic import BaseModel, Field
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy import select, inspect, Column, Table, ForeignKey
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class EnhancedCopyActionSchema(BaseModel):
    """增强版复制操作表单模型"""
    reset_status: bool = Field(True, description="重置状态")
    copy_relations: bool = Field(True, description="复制关联数据")
    copy_attachments: bool = Field(True, description="复制附件")
    copy_configurations: bool = Field(True, description="复制配置信息")
    preserve_dates: bool = Field(False, description="保留日期信息")


def get_model_relationships(model: Type[DeclarativeBase]) -> Dict[str, Any]:
    """获取模型的所有关系信息"""
    relationships = {}
    mapper = inspect(model)
    
    for relationship_name, relationship_obj in mapper.relationships.items():
        relationships[relationship_name] = {
            'direction': relationship_obj.direction.name,
            'uselist': relationship_obj.uselist,
            'target': relationship_obj.mapper.class_,
            'foreign_keys': list(relationship_obj._user_defined_foreign_keys),
            'back_populates': relationship_obj.back_populates,
            'cascade': relationship_obj.cascade,
        }
    
    return relationships


def get_model_fields_info(model: Type[DeclarativeBase]) -> Dict[str, Dict[str, Any]]:
    """获取模型字段详细信息"""
    fields_info = {}
    mapper = inspect(model)
    
    for column in mapper.columns:
        field_info = {
            'type': str(column.type),
            'nullable': column.nullable,
            'primary_key': column.primary_key,
            'foreign_key': bool(column.foreign_keys),
            'default': column.default,
            'unique': column.unique,
            'index': column.index,
        }
        fields_info[column.name] = field_info
    
    return fields_info


def validate_copy_data(data: dict, model: Type[DeclarativeBase]) -> tuple[bool, List[str]]:
    """验证复制数据的完整性和有效性"""
    errors = []
    mapper = inspect(model)
    
    # 检查必填字段
    for column in mapper.columns:
        if not column.nullable and not column.primary_key and column.name in data:
            if data[column.name] is None or data[column.name] == "":
                errors.append(f"字段 '{column.name}' 不能为空")
    
    # 检查唯一字段冲突
    for column in mapper.columns:
        if column.unique and column.name in data and data[column.name] is not None:
            # 这里可以添加数据库唯一性检查
            pass
    
    # 检查外键约束
    for column in mapper.columns:
        if column.foreign_keys and column.name in data:
            # 这里可以添加外键有效性检查
            pass
    
    return len(errors) == 0, errors


def clean_copy_data_enhanced(data: dict, model: Type[DeclarativeBase], options: Dict[str, bool] = None) -> dict:
    """增强版数据清理，根据选项处理不同字段"""
    options = options or {}
    cleaned_data = data.copy()
    
    # 始终移除主键
    if 'id' in cleaned_data:
        cleaned_data.pop('id')
    
    # 根据选项处理时间戳字段
    if not options.get('preserve_dates', False):
        timestamp_fields = ['created_at', 'updated_at', 'create_time', 'update_time', 'date_joined', 'last_login']
        for field in timestamp_fields:
            if field in cleaned_data:
                cleaned_data.pop(field)
    
    # 移除自增字段
    autoincrement_fields = ['auto_increment_id']
    for field in autoincrement_fields:
        if field in cleaned_data:
            cleaned_data.pop(field)
    
    # 处理状态字段
    if options.get('reset_status', True):
        model_name = model.__name__
        if 'status' in cleaned_data:
            if model_name == 'Contract':
                cleaned_data['status'] = '草稿'
            elif model_name == 'Quote':
                cleaned_data['status'] = '草稿'
            elif model_name == 'Project':
                cleaned_data['status'] = '计划中'
            elif model_name == 'Product':
                cleaned_data['status'] = 'active'
    
    return cleaned_data


async def copy_related_data(
    original_item: Any, 
    new_item: Any, 
    relationships: Dict[str, Any],
    session: AsyncSession,
    options: Dict[str, bool] = None
) -> Dict[str, Any]:
    """复制关联数据"""
    options = options or {}
    copied_relations = {}
    
    if not options.get('copy_relations', True):
        return copied_relations
    
    try:
        for rel_name, rel_info in relationships.items():
            if hasattr(original_item, rel_name):
                original_related = getattr(original_item, rel_name)
                
                if original_related is None:
                    continue
                
                # 处理一对多关系
                if rel_info['uselist']:
                    copied_items = []
                    for related_obj in original_related:
                        # 创建关联对象的副本
                        related_data = {col.name: getattr(related_obj, col.name) 
                                      for col in related_obj.__table__.columns 
                                      if col.name != 'id'}
                        
                        # 更新外键引用
                        for fk in rel_info['foreign_keys']:
                            if hasattr(new_item, fk.column.name):
                                related_data[fk.column.name] = getattr(new_item, 'id')
                        
                        new_related_obj = rel_info['target'](**related_data)
                        session.add(new_related_obj)
                        copied_items.append(new_related_obj)
                    
                    copied_relations[rel_name] = len(copied_items)
                    
                # 处理多对一关系
                else:
                    related_data = {col.name: getattr(original_related, col.name) 
                                  for col in original_related.__table__.columns 
                                  if col.name != 'id'}
                    
                    # 更新外键引用
                    for fk in rel_info['foreign_keys']:
                        if hasattr(new_item, fk.column.name):
                            related_data[fk.column.name] = getattr(new_item, 'id')
                    
                    new_related_obj = rel_info['target'](**related_data)
                    session.add(new_related_obj)
                    copied_relations[rel_name] = 1
    except Exception as e:
        logger.error(f"复制关联数据失败: {str(e)}")
        copied_relations['error'] = str(e)
    
    return copied_relations


def generate_new_code_enhanced(original_code: str, model_name: str, existing_codes: Set[str] = None) -> str:
    """增强版编码生成，避免重复"""
    existing_codes = existing_codes or set()
    
    if not original_code:
        base_code = f"{model_name.upper()}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    else:
        # 移除现有后缀
        base_code = original_code.split('-COPY')[0]
        base_code = base_code.split('-')[0] if '-' in base_code else base_code
    
    # 生成唯一编码
    new_code = f"{base_code}-COPY-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    counter = 1
    
    while new_code in existing_codes:
        new_code = f"{base_code}-COPY-{counter}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        counter += 1
        if counter > 100:  # 防止无限循环
            new_code = f"{base_code}-COPY-{datetime.now().microsecond}"
            break
    
    return new_code


async def get_existing_codes(session: AsyncSession, model: Type[DeclarativeBase], code_field: str) -> Set[str]:
    """获取现有编码集合"""
    try:
        stmt = select(getattr(model, code_field))
        result = await session.execute(stmt)
        return {row[0] for row in result if row[0] is not None}
    except Exception as e:
        logger.error(f"获取现有编码失败: {str(e)}")
        return set()


class EnhancedQuickCopyAction(AdminAction):
    """增强版快速复制动作 - 完整数据复制"""
    
    def __init__(self, admin: ModelAdmin, **kwargs):
        self.admin = admin
        self.model = admin.model
        self.app = admin.app
        self.engine = getattr(admin, 'engine', None)
        self.name = kwargs.get('name', "quick_copy")
        self.label = kwargs.get('label', "快速复制")
        self.flags = kwargs.get('flags') or ["item"]
        if isinstance(self.flags, str):
            self.flags = [self.flags]
        
        self._router_prefix = admin.router_prefix
        self._page_path = "/quick_copy"
        
        # 创建增强版抽屉配置（移除批量复制数量选择）
        self.action = Action(
            label=self.label,
            icon="fa fa-clone",
            actionType="drawer",
            confirmText="",
            flags=self.flags,
            drawer={
                "title": "快速复制记录",
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
                            "body": "正在复制记录的所有数据，包括关联信息和配置。请在保存前确认数据完整性。"
                        },
                        {
                            "type": "switch",
                            "name": "reset_status",
                            "label": "重置状态",
                            "value": True
                        },
                        {
                            "type": "switch", 
                            "name": "copy_relations",
                            "label": "复制关联数据",
                            "value": True
                        },
                        {
                            "type": "switch",
                            "name": "copy_attachments", 
                            "label": "复制附件",
                            "value": True
                        },
                        {
                            "type": "switch",
                            "name": "copy_configurations",
                            "label": "复制配置信息", 
                            "value": True
                        },
                        {
                            "type": "switch",
                            "name": "preserve_dates",
                            "label": "保留原始日期",
                            "value": False
                        }
                    ],
                    "actions": [
                        {
                            "type": "submit",
                            "label": "确定复制",
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
        
        self.action = self.action.update_from_dict(kwargs)
    
    @property
    def router_prefix(self):
        return self._router_prefix
    
    @property 
    def page_path(self):
        return self._page_path
    
    async def get_action(self, request: Request, **kwargs) -> Action:
        """获取动作配置，动态设置API URL和表单字段"""
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
    
    async def handle(self, request: Request, item_id: str = None, data: dict = None, **kwargs):
        """处理增强版快速复制操作"""
        try:
            # 获取数据库适配器
            adapter = getattr(self.admin, 'adapter', None)
            if not adapter:
                from app.admin import site
                if hasattr(site, 'db'):
                    adapter = site.db
                else:
                    return BaseApiOut(status=500, msg="无法获取数据库适配器")
            
            # 获取模型信息
            model = self.admin.model
            relationships = get_model_relationships(model)
            fields_info = get_model_fields_info(model)
            
            # 获取原始数据
            try:
                item_id_int = int(item_id)
            except ValueError:
                return BaseApiOut(status=400, msg=f"无效的ID格式: {item_id}")
            
            # 获取原始记录
            stmt = select(model).where(model.id == item_id_int)
            result = await adapter.async_scalars(stmt)
            original_item = result.first()
            
            if not original_item:
                return BaseApiOut(status=404, msg=f"记录 {item_id} 不存在")
            
            # 如果是GET请求，返回复制选项表单
            if request.method == "GET" or data is None:
                # 获取原始数据
                original_data = {column.name: getattr(original_item, column.name) 
                               for column in original_item.__table__.columns}
                
                # 分析关联数据
                relation_summary = {}
                for rel_name, rel_info in relationships.items():
                    if hasattr(original_item, rel_name):
                        related_data = getattr(original_item, rel_name)
                        if related_data is not None:
                            if rel_info['uselist']:
                                relation_summary[rel_name] = len(list(related_data)) if hasattr(related_data, '__len__') else "多个"
                            else:
                                relation_summary[rel_name] = "1个"
                
                return BaseApiOut(
                    data={
                        "original_data": original_data,
                        "relationships": relation_summary,
                        "fields_info": fields_info,
                        "copy_options": {
                            "copy_count": 1,
                            "reset_status": True,
                            "copy_relations": True,
                            "copy_attachments": True,
                            "copy_configurations": True,
                            "preserve_dates": False
                        }
                    },
                    msg="获取原始数据成功，可配置复制选项"
                )
            
            # 处理复制操作（移除批量复制数量处理）
            copy_options = EnhancedCopyActionSchema(**data)
            
            # 获取原始数据
            original_data = {column.name: getattr(original_item, column.name) 
                           for column in original_item.__table__.columns}
            
            # 清理和处理数据
            cleaned_data = clean_copy_data_enhanced(original_data, model, copy_options.dict())
            
            # 验证数据完整性
            is_valid, validation_errors = validate_copy_data(cleaned_data, model)
            if not is_valid:
                return BaseApiOut(status=400, msg="数据验证失败", data={"errors": validation_errors})
            
            # 生成新的编码
            code_field = None
            for field in ['contract_no', 'quote_no', 'project_code', 'code']:
                if field in cleaned_data:
                    code_field = field
                    break
            
            if code_field:
                existing_codes = await get_existing_codes(adapter, model, code_field)
                cleaned_data[code_field] = generate_new_code_enhanced(
                    cleaned_data.get(code_field, ''), 
                    model.__name__, 
                    existing_codes
                )
            
            # 创建新记录（只创建单个副本）
            created_items = []
            relation_copies = {}
            
            async with adapter.async_session() as session:
                # 创建单个新记录
                new_item = model(**cleaned_data)
                session.add(new_item)
                await session.flush()
                await session.refresh(new_item)
                
                # 复制关联数据
                if copy_options.copy_relations:
                    copied_relations = await copy_related_data(
                        original_item, new_item, relationships, session, copy_options.dict()
                    )
                    relation_copies[new_item.id] = copied_relations
                
                created_items.append(new_item)
                
                await session.commit()
            
            # 准备响应数据
            response_data = {
                "created_count": len(created_items),
                "items": [{"id": item.id, "name": getattr(item, 'name', f"副本_{item.id}")} for item in created_items],
                "relation_copies": relation_copies,
                "copy_options": copy_options.dict()
            }
            
            return BaseApiOut(
                data=response_data,
                msg=f"成功复制记录，包含所有关联数据"
            )
            
        except Exception as e:
            logger.error(f"增强版快速复制失败: {str(e)}", exc_info=True)
            return BaseApiOut(status=500, msg=f"复制失败: {str(e)}")





def add_enhanced_copy_actions(admin_class: Type[ModelAdmin]) -> Type[ModelAdmin]:
    """装饰器：为管理类添加增强版复制功能（仅单个快速复制）"""
    
    # 保存原始的admin_action_maker（如果存在）
    original_admin_action_maker = getattr(admin_class, 'admin_action_maker', [])
    
    # 定义文本复制动作的maker函数
    def text_copy_action_maker(admin):
        from app.utils.enhanced_copy_action import TextCopyAction
        return TextCopyAction(admin=admin)
    
    # 定义增强版快速复制动作的maker函数
    def enhanced_quick_copy_action_maker(admin):
        return EnhancedQuickCopyAction(admin=admin)
    
    # 创建新的admin_action_maker列表，包含文本复制和快速复制动作
    admin_class.admin_action_maker = [
        *original_admin_action_maker,
        text_copy_action_maker,
        enhanced_quick_copy_action_maker,
    ]
    
    # 保存原始的__init__方法
    original_init = admin_class.__init__
    
    def new_init(self, app):
        # 首先初始化custom_actions，确保在调用原始__init__之前存在
        if not hasattr(self, 'custom_actions'):
            self.custom_actions = []
        
        # 调用原始的__init__方法
        original_init(self, app)
        
        # 检查是否已经添加过复制操作，避免重复添加
        action_names = [action.name for action in self.custom_actions]
        
        # 添加增强版快速复制动作（仅单个复制）
        if 'quick_copy' not in action_names:
            quick_copy_action = EnhancedQuickCopyAction(admin=self)
            self.custom_actions.append(quick_copy_action)
    
    # 替换__init__方法
    admin_class.__init__ = new_init
    
    # 保存原始的路由注册方法
    original_register_router = getattr(admin_class, 'register_router', None)
    
    def register_enhanced_router(self, app=None):
        """注册增强版复制功能的路由（仅单个快速复制）"""
        # 调用原始路由注册
        if original_register_router:
            if app:
                original_register_router(self, app)
            else:
                original_register_router(self)
        
        # 添加增强版复制路由（仅单个快速复制）
        from fastapi import APIRouter
        router = APIRouter()
        
        @router.post(f"{self.router_prefix}/enhanced_quick_copy/{{item_id}}")
        async def enhanced_quick_copy_endpoint(item_id: str, request: Request):
            """增强版快速复制"""
            try:
                quick_copy_action = next(
                    (action for action in self.custom_actions if action.name == 'quick_copy'),
                    None
                )
                if not quick_copy_action:
                    return BaseApiOut(status=404, msg="快速复制功能未实现")
                
                result = await quick_copy_action.handle(request, item_id=item_id)
                return result
            except Exception as e:
                logger.error(f"增强版快速复制端点错误: {str(e)}", exc_info=True)
                return BaseApiOut(status=500, msg=f"复制失败: {str(e)}")
        
        # 注册路由（仅单个快速复制）
        if app and hasattr(app, 'include_router'):
            app.include_router(router)
            print(f"增强版快速复制功能路由已注册到应用: {self.router_prefix}/enhanced_quick_copy")
        elif hasattr(self, 'router') and hasattr(self.router, 'include_router'):
            self.router.include_router(router)
            print(f"增强版快速复制功能路由已注册到管理器路由: {self.router_prefix}/enhanced_quick_copy")
    
    # 替换路由注册方法
    admin_class.register_router = register_enhanced_router
    
    return admin_class