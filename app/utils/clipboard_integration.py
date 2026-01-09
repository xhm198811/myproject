"""
剪贴板集成模块
为管理类提供复制功能
"""
import json
import logging
from typing import List, Dict, Any, Optional, Callable, Type, Union
from datetime import datetime
from fastapi import Request, Depends, HTTPException
from fastapi_amis_admin.admin import ModelAdmin, ModelAction
from fastapi_amis_admin.amis.components import Action, ActionType
from fastapi_amis_admin.crud.schema import BaseApiOut
from fastapi_amis_admin.amis.constants import LevelEnum
from fastapi_amis_admin.utils.pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import Field

# 配置日志
logger = logging.getLogger(__name__)

# --------------------------- 自定义异常（优化错误处理） ---------------------------
class ClipboardCopyError(Exception):
    """剪贴板复制功能基础异常"""
    def __init__(self, msg: str, error_code: str, status_code: int = 400):
        self.msg = msg
        self.error_code = error_code
        self.status_code = status_code
        super().__init__(self.msg)

# --------------------------- 配置模型（优化配置管理） ---------------------------
class ClipboardCopyConfig(BaseModel):
    """复制功能配置项"""
    copy_fields: List[str] = Field(default_factory=list, description="要复制的字段列表")
    copy_button_label: str = Field("复制", description="复制按钮显示文本")
    copy_success_message: str = Field("信息已复制到剪贴板", description="复制成功提示语")
    copy_format: str = Field("text", description="复制内容格式: text/json/markdown")
    copy_field_formatters: Optional[Dict[str, Callable[[Any], str]]] = Field(None, description="字段自定义格式化函数")
    allow_batch_copy: bool = Field(False, description="是否允许批量复制")
    max_content_size: int = Field(1024 * 1024, description="复制内容最大字节数（默认1MB）")
    confirm_text: str = Field("确定要复制此记录吗？", description="复制确认提示语")

# --------------------------- 混合类（核心格式化逻辑） ---------------------------
class ClipboardCopyMixin:
    """
    剪贴板复制功能混合类
    为ModelAdmin提供复制记录到剪贴板的核心逻辑
    """
    # 复制功能配置
    copy_config: ClipboardCopyConfig = Field(default_factory=ClipboardCopyConfig)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(** kwargs)
        # 兼容旧的配置方式（向下兼容）
        if hasattr(cls, 'copy_fields') and not getattr(cls, 'copy_config', None):
            cls.copy_config = ClipboardCopyConfig(
                copy_fields=cls.copy_fields,
                copy_button_label=getattr(cls, 'copy_button_label', "复制"),
                copy_success_message=getattr(cls, 'copy_success_message', "信息已复制到剪贴板"),
                copy_format=getattr(cls, 'copy_format', "text"),
                copy_field_formatters=getattr(cls, 'copy_field_formatters', None)
            )

    def _format_field_value(self, field_name: str, value: Any) -> str:
        """
        格式化单个字段值（统一格式化逻辑）
        :param field_name: 字段名
        :param value: 字段值
        :return: 格式化后的字符串
        """
        if value is None:
            return "(空)"

        # 优先使用自定义格式化函数
        if self.copy_config.copy_field_formatters and field_name in self.copy_config.copy_field_formatters:
            return self.copy_config.copy_field_formatters[field_name](value)

        # 内置类型格式化
        if isinstance(value, datetime):
            return value.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(value, bool):
            return "是" if value else "否"
        elif isinstance(value, (list, dict)):
            return json.dumps(value, ensure_ascii=False, default=str)
        else:
            return str(value)

    def _format_as_text(self, item_data: Dict[str, Any]) -> str:
        """格式化为纯文本（键值对）"""
        lines = []
        for field in self.copy_config.copy_fields:
            if field in item_data:
                value = self._format_field_value(field, item_data[field])
                lines.append(f"{field}: {value}")
        return "\n".join(lines)

    def _format_as_json(self, item_data: Dict[str, Any]) -> str:
        """格式化为JSON字符串"""
        filtered_data = {
            field: item_data[field]
            for field in self.copy_config.copy_fields
            if field in item_data
        }
        return json.dumps(filtered_data, ensure_ascii=False, indent=2, default=str)

    def _format_as_markdown(self, item_data: Dict[str, Any]) -> str:
        """格式化为Markdown表格"""
        lines = ["| 字段 | 值 |", "|------|-----|"]
        for field in self.copy_config.copy_fields:
            if field in item_data:
                value = self._format_field_value(field, item_data[field])
                lines.append(f"| {field} | {value} |")
        return "\n".join(lines)

    def get_copy_content(self, item_data: Dict[str, Any]) -> str:
        """
        获取格式化后的复制内容（对外暴露的核心方法）
        :param item_data: 模型记录的字典数据
        :return: 格式化后的字符串
        """
        format_map = {
            "text": self._format_as_text,
            "json": self._format_as_json,
            "markdown": self._format_as_markdown
        }
        formatter = format_map.get(self.copy_config.copy_format, self._format_as_text)
        return formatter(item_data)

# --------------------------- 复制Action类（核心业务逻辑） ---------------------------
class ClipboardCopyAction(ModelAction, ClipboardCopyMixin):
    """
    剪贴板复制Action类
    整合配置、权限、数据库查询、格式化的完整复制功能
    """
    def __init__(self, admin: ModelAdmin, **kwargs):
        # 初始化父类
        ModelAction.__init__(self, admin=admin, label=admin.copy_config.copy_button_label, **kwargs)
        ClipboardCopyMixin.__init__(self)

        # 复用admin的配置
        self.copy_config = admin.copy_config

        # 构建前端Action（复用配置项）
        api_url = f"{self.admin.router_path}{self.page_path}"
        self.action = ActionType.Ajax(
            label=self.copy_config.copy_button_label,
            icon="fa fa-copy",
            tooltip=self.copy_config.copy_success_message,
            level=LevelEnum.link,
            confirmText=self.copy_config.confirm_text,
            api={
                "method": "post",
                "url": f"{api_url}?item_id=${{IF(ids, ids, id)}}",
            }
        )
        self.schema = BaseModel  # 空Schema，无需表单
        self.form_init = False

    @property
    def page_path(self) -> str:
        """Action路由路径"""
        return f"/{self.name or 'clipboard_copy'}"

    def register_router(self):
        """注册路由（优化路由注册逻辑）"""
        self.admin.router.add_api_route(
            self.page_path,
            self.route_submit,
            methods=["POST"],
            response_model=BaseApiOut,
            dependencies=[Depends(self.page_permission_depend)],
            name=f"{self.admin.__class__.__name__}_clipboard_copy",
        )
        return self

    @property
    def route_submit(self):
        """路由处理函数（封装依赖注入）"""
        async def route(
            request: Request,
            item_id: Union[List[str], str],  # 兼容单条/多条ID
            session: AsyncSession = Depends(self.admin.db.session_generator),  # 标准化获取数据库会话
        ):
            try:
                # 统一处理ID格式（兼容单字符串/列表）
                item_ids = [item_id] if isinstance(item_id, str) else item_id
                result = await self.handle(request, item_ids, session)
                return BaseApiOut(
                    status=200,
                    msg=self.copy_config.copy_success_message,
                    data=result
                )
            except ClipboardCopyError as e:
                logger.error(f"复制失败: {e.error_code} - {e.msg}")
                return BaseApiOut(
                    status=e.status_code,
                    msg=e.msg,
                    data={"error": e.error_code, "copy_success": False}
                )
            except Exception as e:
                logger.error(f"复制操作未预期异常", exc_info=True)
                return BaseApiOut(
                    status=500,
                    msg=f"复制失败：{str(e)}",
                    data={"error": "internal_error", "copy_success": False}
                )

        return route

    async def handle(self, request: Request, item_ids: List[str], session: AsyncSession) -> Dict[str, Any]:
        """
        核心处理逻辑（优化后）
        :param request: 请求对象
        :param item_ids: 要复制的记录ID列表
        :param session: 数据库会话
        :return: 包含复制内容的结果字典
        """
        logger.info(f"复制操作触发 - 管理员: {self.admin.__class__.__name__}, 记录ID: {item_ids}")

        # 1. 基础校验
        if not item_ids:
            raise ClipboardCopyError("缺少记录ID", "no_item_id")

        # 2. 批量复制校验
        if not self.copy_config.allow_batch_copy and len(item_ids) > 1:
            raise ClipboardCopyError(
                f"不支持批量复制（当前选择{len(item_ids)}条），请选择单条记录",
                "batch_not_supported"
            )

        # 3. 复制字段校验
        if not self.copy_config.copy_fields:
            raise ClipboardCopyError("未配置复制字段", "no_copy_fields")

        # 4. 查询记录并格式化内容
        copy_contents = []
        for item_id in item_ids:
            # ID格式转换（兼容整数/字符串ID）
            try:
                item_id_value = int(item_id)
            except (ValueError, TypeError):
                item_id_value = item_id  # 非整数ID（如UUID）直接使用

            # 查询数据库记录
            stmt = select(self.admin.model).where(self.admin.model.id == item_id_value)
            result = await session.scalars(stmt)
            item = result.first()

            if not item:
                raise ClipboardCopyError(f"记录 {item_id_value} 不存在或已被删除", "record_not_found", 404)

            # 转换为字典（优化字段提取）
            item_data = {col.name: getattr(item, col.name) for col in item.__table__.columns}

            # 获取格式化后的复制内容
            copy_content = self.get_copy_content(item_data)

            # 内容大小校验
            if len(copy_content.encode('utf-8')) > self.copy_config.max_content_size:
                raise ClipboardCopyError(
                    f"复制内容过大（{len(copy_content.encode('utf-8'))}字节），超过限制{self.copy_config.max_content_size}字节",
                    "content_too_large"
                )

            copy_contents.append({
                "item_id": item_id_value,
                "copy_content": copy_content
            })

        # 5. 结果整合（兼容单条/批量）
        return {
            "copy_success": True,
            "fields_count": len(self.copy_config.copy_fields),
            "copy_contents": copy_contents if self.copy_config.allow_batch_copy else copy_contents[0]["copy_content"],
            "item_count": len(copy_contents)
        }


# --------------------------- 记录复制Action类（数据库记录复制功能） ---------------------------
class RecordCopyAction(ModelAction):
    """
    记录复制Action类
    在数据库中创建当前记录的新副本
    """
    def __init__(
        self,
        admin: ModelAdmin,
        name: str = "record_copy",
        copy_fields: Optional[List[str]] = None,
        copy_api_url: str = "",
        success_message: str = "记录复制成功",
        flags: Optional[List[str]] = None,
        **kwargs
    ):
        self.admin = admin
        self.model = admin.model
        self.copy_fields = copy_fields or []
        self.copy_api_url = copy_api_url
        self.success_message = success_message
        self.flags = flags or ['item']
        
        ModelAction.__init__(self, admin=admin, name=name, label="复制记录", **kwargs)
        
        # 不注册路由，直接返回前端Action配置
        self.action = ActionType.Ajax(
            label="复制记录",
            icon="fa fa-copy",
            tooltip="复制此记录",
            level=LevelEnum.link,
            confirmText="确定要复制此记录吗？",
            api={
                "method": "post",
                "url": copy_api_url,
                "data": {"custom_data": {}}
            }
        )
        self.schema = BaseModel
        self.form_init = False