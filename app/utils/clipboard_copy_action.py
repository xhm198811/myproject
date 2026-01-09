"""
剪贴板复制动作模块
实现用于复制记录数据到剪贴板的功能
"""
import json
from typing import List, Dict, Any, Type, Optional, Union, Callable
from fastapi import Request
from fastapi_amis_admin import amis
from fastapi_amis_admin.admin import AdminAction, ModelAdmin
from fastapi_amis_admin.amis.components import Action, Form, Button
from fastapi_amis_admin.crud.schema import BaseApiOut
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import logging

logger = logging.getLogger(__name__)


class ClipboardCopyAction(AdminAction):
    """
    剪贴板复制动作类
    提供完整的复制功能，支持多种复制格式
    """
    
    def __init__(
        self,
        admin: ModelAdmin,
        name: str = "clipboard_copy",
        label: str = "详情复制",
        copy_format: str = "text",
        field_formatters: Optional[Dict[str, Callable]] = None,
        **kwargs
    ):
        self.admin = admin
        self.model = admin.model
        self.name = name
        self.label = label
        self.copy_format = copy_format
        self.field_formatters = field_formatters or {}
        
        super().__init__(admin=admin, **kwargs)
    
    def _build_action(self) -> Action:
        """构建Action配置"""
        return Action(
            label=self.label,
            icon="fa fa-copy",
            actionType="drawer",
            tooltip="打开复制对话框",
            level="link",
            drawer=self._build_drawer()
        )
    
    def _build_drawer(self) -> Dict[str, Any]:
        """构建抽屉配置"""
        return {
            "title": f"{self.label}",
            "size": "md",
            "body": {
                "type": "form",
                "body": [
                    {
                        "type": "radios",
                        "name": "copyFormat",
                        "label": "复制格式",
                        "value": self.copy_format,
                        "options": [
                            {"label": "文本", "value": "text"},
                            {"label": "JSON", "value": "json"},
                            {"label": "表格", "value": "table"}
                        ]
                    }
                ],
                "actions": [
                    {
                        "type": "button",
                        "label": "复制到剪贴板",
                        "icon": "fa fa-copy",
                        "level": "primary",
                        "actionType": "copy",
                        "closeParent": True,
                        "onEvent": {
                            "click": {
                                "script": ""
                            }
                        }
                    },
                    {
                        "type": "button",
                        "label": "关闭",
                        "actionType": "close"
                    }
                ]
            }
        }
    
    async def handle_request(self, request: Request, item_id: int, **kwargs) -> BaseApiOut:
        """处理复制请求"""
        try:
            async with self.admin.adapter.async_session() as session:
                stmt = select(self.model).where(self.model.id == item_id)
                result = await session.execute(stmt)
                item = result.scalar_one_or_none()
                
                if not item:
                    return BaseApiOut(status=404, msg=f"ID为 {item_id} 的记录不存在")
                
                return BaseApiOut(
                    status=200,
                    data=self._prepare_copy_data(item),
                    msg="复制成功"
                )
        except Exception as e:
            logger.error(f"复制记录失败: {str(e)}", exc_info=True)
            return BaseApiOut(status=500, msg=f"复制失败: {str(e)}")
    
    def _prepare_copy_data(self, item: Any) -> Dict[str, Any]:
        """准备复制数据"""
        data = {}
        for column in item.__table__.columns:
            value = getattr(item, column.name)
            if hasattr(value, 'isoformat'):
                value = value.isoformat()
            data[column.name] = value
        return data


class QuickClipboardCopyAction(AdminAction):
    """
    快速复制动作类
    提供一键复制功能，不显示对话框
    """
    
    def __init__(
        self,
        admin: ModelAdmin,
        name: str = "quick_copy",
        label: str = "复制",
        copy_fields: Optional[List[str]] = None,
        field_formatters: Optional[Dict[str, Callable]] = None,
        **kwargs
    ):
        self.admin = admin
        self.model = admin.model
        self.name = name
        self.label = label
        self.copy_fields = copy_fields or ["id", "name"]
        self.field_formatters = field_formatters or {}
        
        super().__init__(admin=admin, **kwargs)
    
    def _build_action(self) -> Action:
        """构建Action配置"""
        return Button(
            label=self.label,
            icon="fa fa-copy",
            level="link",
            tooltip="点击复制信息到剪贴板",
            actionType="copy",
            copyFormat="text",
            onEvent={
                "click": {
                    "script": ""
                }
            }
        )
    
    async def handle_request(self, request: Request, item_id: int, **kwargs) -> BaseApiOut:
        """处理快速复制请求"""
        try:
            async with self.admin.adapter.async_session() as session:
                stmt = select(self.model).where(self.model.id == item_id)
                result = await session.execute(stmt)
                item = result.scalar_one_or_none()
                
                if not item:
                    return BaseApiOut(status=404, msg=f"ID为 {item_id} 的记录不存在")
                
                copy_content = self._prepare_copy_content(item)
                
                return BaseApiOut(
                    status=200,
                    data={"copy_content": copy_content},
                    msg="复制成功"
                )
        except Exception as e:
            logger.error(f"快速复制失败: {str(e)}", exc_info=True)
            return BaseApiOut(status=500, msg=f"复制失败: {str(e)}")
    
    def _prepare_copy_content(self, item: Any) -> str:
        """准备复制内容"""
        lines = []
        for field in self.copy_fields:
            if hasattr(item, field):
                value = getattr(item, field)
                if field in self.field_formatters:
                    value = self.field_formatters[field](value)
                elif hasattr(value, 'isoformat'):
                    value = value.isoformat()
                else:
                    value = str(value) if value is not None else ""
                lines.append(f"{field}: {value}")
        return "\n".join(lines)


def add_clipboard_copy_actions(
    admin: ModelAdmin,
    quick_copy_fields: Optional[List[str]] = None,
    field_formatters: Optional[Dict[str, Callable]] = None,
    include_detail_copy: bool = True
) -> None:
    """
    为管理类添加复制功能
    
    Args:
        admin: 管理类实例
        quick_copy_fields: 快速复制字段列表
        field_formatters: 字段格式化函数字典
        include_detail_copy: 是否包含详情复制功能
    """
    if not hasattr(admin, 'custom_actions'):
        admin.custom_actions = []
    
    # 添加快速复制
    admin.custom_actions.append(
        QuickClipboardCopyAction(
            admin=admin,
            name="quick_copy",
            label="复制",
            copy_fields=quick_copy_fields,
            field_formatters=field_formatters
        )
    )
    
    # 添加详情复制
    if include_detail_copy:
        admin.custom_actions.append(
            ClipboardCopyAction(
                admin=admin,
                name="clipboard_copy",
                label="详情复制",
                field_formatters=field_formatters
            )
        )
