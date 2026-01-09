"""
通用复制Action组件模块
为FastAPI-Amis-Admin提供完整的复制按钮和功能
"""
import json
import logging
from typing import Any, Dict, List, Optional, Union, Callable
from fastapi import Request
from fastapi_amis_admin import admin, amis
from fastapi_amis_admin.admin import AdminAction, ModelAdmin
from fastapi_amis_admin.amis.components import Action, Button, TableColumn, Form, Alert, Tpl
from fastapi_amis_admin.crud.schema import BaseApiOut
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from enum import Enum

logger = logging.getLogger(__name__)


class CopyFormat(str, Enum):
    """复制格式枚举"""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    TABLE = "table"


class CopyPosition(str, Enum):
    """复制按钮位置枚举"""
    HEADER_TOOLBAR = "headerToolbar"
    ITEM_ACTION = "itemAction"
    BULK_ACTION = "bulkAction"
    ROW_CELL = "rowCell"


class CopyTarget(str, Enum):
    """复制目标类型枚举"""
    CURRENT_ROW = "currentRow"
    SPECIFIED_FIELDS = "specifiedFields"
    ALL_FIELDS = "allFields"
    CUSTOM_DATA = "customData"


class CopyFeedbackType(str, Enum):
    """反馈类型枚举"""
    TOAST = "toast"
    ALERT = "alert"
    NOTIFICATION = "notification"


class CopyActionSchema(BaseModel):
    """复制操作配置模型"""
    copy_format: CopyFormat = CopyFormat.TEXT
    copy_target: CopyTarget = CopyTarget.CURRENT_ROW
    include_fields: Optional[str] = Field("", description="指定字段,逗号分隔")
    exclude_fields: Optional[str] = Field("id,created_at,updated_at", description="排除字段")
    custom_title: Optional[str] = Field("记录信息", description="自定义标题")
    show_preview: bool = True
    feedback_type: CopyFeedbackType = CopyFeedbackType.TOAST
    success_message: str = "复制成功"
    fail_message: str = "复制失败，请重试"


class UniversalCopyAction(AdminAction):
    """
    通用复制Action组件
    
    特性:
    - 支持多种复制格式: 文本、JSON、Markdown、表格
    - 支持多种复制目标: 当前行、指定字段、所有字段、自定义数据
    - 内置用户反馈机制: Toast提示、Alert提示、通知
    - 响应式设计: 适配不同屏幕尺寸
    - 良好的用户体验: 加载状态、错误处理、成功反馈
    """

    def __init__(
        self,
        admin: ModelAdmin,
        name: str = "universal_copy",
        label: str = "复制",
        icon: str = "fa fa-copy",
        position: Union[CopyPosition, List[str]] = CopyPosition.ITEM_ACTION,
        copy_config: Optional[CopyActionSchema] = None,
        field_formatters: Optional[Dict[str, Callable]] = None,
        **kwargs
    ):
        self.admin = admin
        self.model = admin.model
        self.name = name
        self.label = label
        self.icon = icon
        self.position = position if isinstance(position, list) else [position]
        self.copy_config = copy_config or CopyActionSchema()
        self.field_formatters = field_formatters or {}
        
        self._router_prefix = admin.router_prefix
        self._page_path = "/universal_copy"

        super().__init__(admin=admin, action=self._build_action(), flags=self._get_flags(), **kwargs)

    def _get_flags(self) -> List[str]:
        """获取操作标志"""
        flags = []
        if CopyPosition.HEADER_TOOLBAR in self.position:
            flags.append("headerToolbar")
        if CopyPosition.ITEM_ACTION in self.position:
            flags.append("item")
        if CopyPosition.BULK_ACTION in self.position:
            flags.append("bulk")
        return flags if flags else ["item"]

    def _build_action(self) -> Action:
        """构建Action配置"""
        return Action(
            label=self.label,
            icon=self.icon,
            actionType="drawer",
            tooltip="点击复制数据到剪贴板",
            className="universal-copy-action",
            level="link",
            flags=self._get_flags(),
            drawer=self._build_drawer()
        )

    def _build_drawer(self) -> Dict[str, Any]:
        """构建抽屉配置"""
        return {
            "title": f"{self.label} - 选择复制选项",
            "size": "md",
            "body": {
                "type": "form",
                "api": {
                    "method": "post",
                    "url": ""
                },
                "body": [
                    {
                        "type": "alert",
                        "level": "info",
                        "body": f"请选择复制格式和选项，然后点击下方按钮将{self.label}的数据复制到剪贴板"
                    },
                    {
                        "type": "select",
                        "name": "copy_format",
                        "label": "复制格式",
                        "options": [
                            {"label": "📝 文本格式", "value": "text"},
                            {"label": "{ } JSON格式", "value": "json"},
                            {"label": "📋 Markdown表格", "value": "markdown"}
                        ],
                        "value": self.copy_config.copy_format.value,
                        "required": True
                    },
                    {
                        "type": "radios",
                        "name": "copy_target",
                        "label": "复制内容",
                        "options": [
                            {"label": "当前行数据", "value": "currentRow"},
                            {"label": "指定字段", "value": "specifiedFields"},
                            {"label": "所有字段", "value": "allFields"}
                        ],
                        "value": self.copy_config.copy_target.value
                    },
                    {
                        "type": "input-text",
                        "name": "include_fields",
                        "label": "指定字段(可选)",
                        "placeholder": "例如: name,code,status (留空则复制所有)",
                        "visibleOn": "data.copy_target === 'specifiedFields'",
                        "description": "输入要复制的字段名,用逗号分隔"
                    },
                    {
                        "type": "switch",
                        "name": "show_preview",
                        "label": "显示预览",
                        "value": True,
                        "description": "是否显示复制内容预览"
                    },
                    {
                        "type": "divider"
                    },
                    {
                        "type": "tpl",
                        "tpl": "📋 预览内容:",
                        "visibleOn": "data.show_preview",
                        "className": "mb-2"
                    },
                    {
                        "type": "static",
                        "name": "preview_content",
                        "label": "",
                        "visibleOn": "data.show_preview",
                        "value": "加载预览数据中..."
                    }
                ],
                "actions": [
                    {
                        "type": "submit",
                        "label": "📋 复制到剪贴板",
                        "icon": "fa fa-clipboard",
                        "level": "primary",
                        "className": "copy-submit-btn"
                    },
                    {
                        "type": "button",
                        "label": "关闭",
                        "actionType": "close"
                    }
                ],
                "onEvent": {
                    "submitSucc": {
                        "eventType": "submitSucc",
                        "script": """
                            const data = event.response?.data || event.detail?.response?.data;
                            if (data?.copy_content) {
                                const handler = window.clipboardHandler;
                                if (handler) {
                                    handler.copyToClipboard(data.copy_content).then(success => {
                                        if (success) {
                                            handler.showToast('复制成功', 'success');
                                        } else {
                                            handler.showToast('复制失败，请重试', 'error');
                                        }
                                    });
                                }
                            }
                        """
                    }
                }
            }
        }

    def _format_field_value(self, field_name: str, value: Any) -> str:
        """格式化字段值"""
        if value is None:
            return "(空)"

        if field_name in self.field_formatters:
            return self.field_formatters[field_name](value)

        from datetime import datetime
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, bool):
            return "是" if value else "否"
        else:
            return str(value)

    def _format_as_text(self, item_data: Dict[str, Any], include_fields: List[str] = None) -> str:
        """格式化为文本"""
        lines = []
        lines.append("=" * 50)
        lines.append(f"{self.copy_config.custom_title} (ID: {item_data.get('id', 'N/A')})")
        lines.append("=" * 50)

        target_fields = include_fields or list(item_data.keys())
        for field in target_fields:
            if field in item_data:
                value = self._format_field_value(field, item_data[field])
                lines.append(f"{field}: {value}")

        lines.append("=" * 50)
        return "\n".join(lines)

    def _format_as_json(self, item_data: Dict[str, Any], include_fields: List[str] = None) -> str:
        """格式化为JSON"""
        target_fields = include_fields or list(item_data.keys())
        filtered_data = {k: item_data[k] for k in target_fields if k in item_data}
        return json.dumps(filtered_data, ensure_ascii=False, indent=2, default=str)

    def _format_as_markdown(self, item_data: Dict[str, Any], include_fields: List[str] = None) -> str:
        """格式化为Markdown表格"""
        lines = []
        lines.append(f"## {self.copy_config.custom_title} (ID: {item_data.get('id', 'N/A')})")
        lines.append("")

        target_fields = include_fields or list(item_data.keys())
        lines.append("| 字段 | 值 |")
        lines.append("|------|-----|")

        for field in target_fields:
            if field in item_data:
                value = self._format_field_value(field, item_data[field])
                escaped_value = str(value).replace("|", "\\|").replace("\n", "<br>")
                lines.append(f"| {field} | {escaped_value} |")

        lines.append("")
        return "\n".join(lines)

    @property
    def router_prefix(self):
        return self._router_prefix

    @property
    def page_path(self):
        return self._page_path

    async def get_action(self, request: Request, **kwargs) -> Action:
        """获取Action配置"""
        action = self.action.copy() if self.action else Action()

        router_prefix = self.router_prefix
        if not router_prefix.startswith('/admin'):
            router_prefix = f"/admin{router_prefix}"

        page_path = self.page_path.lstrip('/')
        api_url = f"{router_prefix}/{page_path}/${{id}}"

        if hasattr(action, 'drawer') and hasattr(action.drawer, 'body'):
            action.drawer.body.api.url = api_url
            if hasattr(action.drawer.body, 'actions'):
                for btn_action in action.drawer.body.actions:
                    if hasattr(btn_action, 'api'):
                        btn_action.api.url = api_url

        return action

    async def handle(self, request: Request, item_id: str = None, data: dict = None, **kwargs):
        """处理复制操作"""
        try:
            adapter = getattr(self.admin, 'adapter', None)
            if not adapter:
                from app.admin import site
                if hasattr(site, 'db'):
                    adapter = site.db
                else:
                    return BaseApiOut(status=500, msg="无法获取数据库适配器")

            if not item_id:
                return BaseApiOut(status=400, msg="缺少记录ID")

            try:
                item_id_int = int(item_id)
            except ValueError:
                return BaseApiOut(status=400, msg=f"无效的ID格式: {item_id}")

            model = self.admin.model
            stmt = select(model).where(model.id == item_id_int)
            result = await adapter.async_scalars(stmt)
            item = result.first()

            if not item:
                return BaseApiOut(status=404, msg=f"记录 {item_id} 不存在")

            item_data = {}
            for column in item.__table__.columns:
                value = getattr(item, column.name, None)
                item_data[column.name] = value

            if not data:
                preview = self._format_as_text(item_data)
                return BaseApiOut(
                    data={
                        "original_data": item_data,
                        "preview_content": preview[:500] + "..." if len(preview) > 500 else preview
                    },
                    msg="获取数据成功"
                )

            copy_format = data.get('copy_format', 'text')
            copy_target = data.get('copy_target', 'currentRow')
            include_fields_str = data.get('include_fields', '')
            exclude_fields = [f.strip() for f in self.copy_config.exclude_fields.split(',') if f.strip()]

            include_fields = None
            if include_fields_str.strip():
                include_fields = [f.strip() for f in include_fields_str.split(',') if f.strip()]

            if copy_target == 'allFields' and include_fields is None:
                include_fields = [k for k in item_data.keys() if k not in exclude_fields]
            elif copy_target == 'currentRow':
                include_fields = include_fields or [k for k in item_data.keys() if k not in exclude_fields]

            if copy_format == 'json':
                copy_content = self._format_as_json(item_data, include_fields)
            elif copy_format == 'markdown':
                copy_content = self._format_as_markdown(item_data, include_fields)
            else:
                copy_content = self._format_as_text(item_data, include_fields)

            return BaseApiOut(
                data={
                    "copy_content": copy_content,
                    "copy_format": copy_format,
                    "item_id": item_id_int
                },
                msg=self.copy_config.success_message
            )

        except Exception as e:
            logger.error(f"复制操作失败: {str(e)}", exc_info=True)
            return BaseApiOut(status=500, msg=f"{self.copy_config.fail_message}: {str(e)}")


class QuickCopyAction(AdminAction):
    """
    快速复制Action - 一键复制当前行数据
    适用于列表页操作列
    """

    def __init__(
        self,
        admin: ModelAdmin,
        name: str = "quick_copy",
        label: str = "复制",
        icon: str = "fa fa-copy",
        copy_format: str = "text",
        copy_fields: Optional[List[str]] = None,
        **kwargs
    ):
        self.admin = admin
        self.model = admin.model
        self.name = name
        self.label = label
        self.icon = icon
        self.copy_format = copy_format
        self.copy_fields = copy_fields or []

        self._router_prefix = admin.router_prefix
        self._page_path = "/quick_copy"

        super().__init__(admin=admin, action=self._build_action(), flags=["item"], **kwargs)

    def _build_action(self) -> Action:
        """构建Action配置"""
        return Action(
            label=self.label,
            icon=self.icon,
            actionType="ajax",
            confirmText="确定要复制这条记录吗？",
            tooltip="一键复制当前行数据",
            className="quick-copy-action",
            level="link",
            api={
                "method": "post",
                "url": ""
            }
        )

    @property
    def router_prefix(self):
        return self._router_prefix

    @property
    def page_path(self):
        return self._page_path

    def _format_field_value(self, value: Any) -> str:
        """格式化字段值"""
        if value is None:
            return ""
        from datetime import datetime
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M')
        elif isinstance(value, bool):
            return "是" if value else "否"
        else:
            return str(value)

    def _format_content(self, item_data: Dict[str, Any]) -> str:
        """格式化复制内容"""
        if self.copy_format == 'json':
            if self.copy_fields:
                filtered_data = {k: item_data[k] for k in self.copy_fields if k in item_data}
            else:
                filtered_data = item_data
            return json.dumps(filtered_data, ensure_ascii=False, default=str)

        values = []
        target_fields = self.copy_fields or list(item_data.keys())
        for field in target_fields:
            if field in item_data:
                value = self._format_field_value(item_data[field])
                if value:
                    values.append(value)
        return " | ".join(values)

    async def get_action(self, request: Request, **kwargs) -> Action:
        """获取Action配置"""
        action = self.action.copy() if self.action else Action()

        router_prefix = self.router_prefix
        if not router_prefix.startswith('/admin'):
            router_prefix = f"/admin{router_prefix}"

        page_path = self.page_path.lstrip('/')
        api_url = f"{router_prefix}/{page_path}/${{id}}"

        if hasattr(action, 'api'):
            action.api.url = api_url

        return action

    async def handle(self, request: Request, item_id: str = None, data: dict = None, **kwargs):
        """处理快速复制操作"""
        try:
            adapter = getattr(self.admin, 'adapter', None)
            if not adapter:
                from app.admin import site
                if hasattr(site, 'db'):
                    adapter = site.db
                else:
                    return BaseApiOut(status=500, msg="无法获取数据库适配器")

            if not item_id:
                return BaseApiOut(status=400, msg="缺少记录ID")

            try:
                item_id_int = int(item_id)
            except ValueError:
                return BaseApiOut(status=400, msg=f"无效的ID格式: {item_id}")

            model = self.admin.model
            stmt = select(model).where(model.id == item_id_int)
            result = await adapter.async_scalars(stmt)
            item = result.first()

            if not item:
                return BaseApiOut(status=404, msg=f"记录 {item_id} 不存在")

            item_data = {}
            for column in item.__table__.columns:
                value = getattr(item, column.name, None)
                item_data[column.name] = value

            copy_content = self._format_content(item_data)
            display_content = copy_content[:100] + '...' if len(copy_content) > 100 else copy_content

            return BaseApiOut(
                data={
                    "copy_content": copy_content,
                    "item_id": item_id_int
                },
                msg=f"已复制: {display_content}"
            )

        except Exception as e:
            logger.error(f"快速复制操作失败: {str(e)}", exc_info=True)
            return BaseApiOut(status=500, msg=f"复制失败: {str(e)}")


class CopyActionButtonBuilder:
    """复制按钮构建器"""

    @staticmethod
    def create_table_copy_column(
        field_name: str,
        label: str = None,
        width: int = 60,
        align: str = "center"
    ) -> TableColumn:
        """创建表格复制列"""
        return TableColumn(
            name=field_name,
            label=label or "复制",
            width=width,
            align=align,
            type="button",
            copyable=True,
            buttons=[
                {
                    "type": "button",
                    "icon": "fa fa-copy",
                    "tooltip": "复制",
                    "onEvent": {
                        "click": {
                            "eventType": "click",
                            "script": """
                                const handler = window.clipboardHandler;
                                if (handler) {
                                    const value = event.data.""" + field_name + """;
                                    handler.copyToClipboard(String(value || ''));
                                }
                            """
                        }
                    }
                }
            ]
        )

    @staticmethod
    def create_row_copy_button(
        label: str = "复制",
        icon: str = "fa fa-copy",
        copy_fields: List[str] = None,
        copy_format: str = "text"
    ) -> dict:
        """创建整行复制按钮配置"""
        return {
            "type": "button",
            "icon": icon,
            "label": label,
            "tooltip": "复制整行数据",
            "level": "link",
            "className": "row-copy-btn",
            "onEvent": {
                "click": {
                    "eventType": "click",
                    "script": f"""
                        const handler = window.clipboardHandler;
                        if (handler) {{
                            handler.setButtonLoading(event.target);
                            const data = event.data || {{}};
                            const rowData = {{}};
                            const fields = {json.dumps(copy_fields or [])};
                            
                            if (fields.length > 0) {{
                                fields.forEach(f => {{ rowData[f] = data[f]; }});
                            }} else {{
                                Object.keys(data).forEach(k => {{
                                    if (!k.startsWith('__') && !k.endsWith('_raw')) {{
                                        rowData[k] = data[k];
                                    }}
                                }});
                            }}
                            
                            const content = JSON.stringify(rowData, null, 2);
                            await handler.copyToClipboard(content);
                            handler.resetButton(event.target);
                        }}
                    """
                }
            }
        }


def add_universal_copy_actions(
    admin_class,
    copy_config: Optional[CopyActionSchema] = None,
    quick_copy_fields: Optional[List[str]] = None,
    enable_quick_copy: bool = True,
    enable_universal_copy: bool = True
):
    """
    为管理类添加复制功能
    
    Args:
        admin_class: 管理类
        copy_config: 通用复制配置
        quick_copy_fields: 快速复制字段列表
        enable_quick_copy: 是否启用快速复制
        enable_universal_copy: 是否启用通用复制
    """

    def universal_copy_action_maker(admin):
        return UniversalCopyAction(
            admin=admin,
            copy_config=copy_config
        )

    def quick_copy_action_maker(admin):
        return QuickCopyAction(
            admin=admin,
            copy_fields=quick_copy_fields
        )

    original_action_maker = getattr(admin_class, 'admin_action_maker', [])

    new_makers = []
    if enable_quick_copy:
        new_makers.append(quick_copy_action_maker)
    if enable_universal_copy:
        new_makers.append(universal_copy_action_maker)

    admin_class.admin_action_maker = [
        *original_action_maker,
        *new_makers
    ]

    original_init = admin_class.__init__

    def new_init(self, app):
        if not hasattr(self, 'custom_actions'):
            self.custom_actions = []

        original_init(self, app)

        action_names = [action.name for action in self.custom_actions]

        if enable_quick_copy and 'quick_copy' not in action_names:
            quick_copy = QuickCopyAction(admin=self, copy_fields=quick_copy_fields)
            self.custom_actions.append(quick_copy)

        if enable_universal_copy and 'universal_copy' not in action_names:
            universal_copy = UniversalCopyAction(admin=self, copy_config=copy_config)
            self.custom_actions.append(universal_copy)

    admin_class.__init__ = new_init

    return admin_class
