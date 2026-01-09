"""
项目管理模块 - 优化版
提供项目的CRUD操作、快速复制等核心功能
"""
from typing import List, Dict, Any, Optional, Union
from datetime import datetime, date
import logging

from fastapi import HTTPException, Request, Depends
from fastapi_amis_admin.admin import ModelAdmin, AdminAction
from fastapi_amis_admin.amis.components import Action, ActionType, Button, Dialog, Form
from fastapi_amis_admin.amis import PageSchema
from fastapi_amis_admin.amis.constants import SizeEnum
from fastapi_amis_admin.crud.schema import BaseApiOut
from sqlmodel import select, func
from pydantic import BaseModel

from .models.project import (
    Project, ProjectStage, ProjectTask,
    ProjectDocument
)
from .schemas import (
    ProjectCreate,
    ProjectStageBatchCreate, ProjectStageBatchResult, ProjectStageCreate,
    ProjectTaskBatchCreate, ProjectTaskBatchResult, ProjectTaskCreate
)
from app.utils.clipboard_integration import ClipboardCopyMixin
from app.core.auth import get_current_active_user
from .services.project import project_service

# 配置日志
logger = logging.getLogger(__name__)

class ProjectAdmin(ClipboardCopyMixin, ModelAdmin):
    """项目管理（优化版）"""
    page_schema = PageSchema(label="项目管理", icon="fa fa-project-diagram")
    model = Project
    router_prefix = "/ProjectAdmin"

    copy_fields = ["name", "description", "project_manager", "amount", "status"]
    copy_button_label = "复制项目"
    copy_success_message = "项目信息已复制到剪贴板"
    copy_mode = "record"
    copy_success_feedback = "项目记录复制成功，新项目ID：${data.new_id}"

    admin_action_maker = [
        lambda admin: AdminAction(
            admin=admin,
            name='record_copy',
            label='复制记录',
            icon='fa fa-copy',
            action=Action(
                actionType='ajax',
                label='复制记录',
                icon='fa fa-copy',
                confirmText='确定要复制此记录吗？',
                api="post:/admin/ProjectAdmin/item/${id}/quick_copy"
            ),
            flags=['item', 'column']
        ),
        lambda admin: AdminAction(
            admin=admin,
            name='upload_attachment',
            label='上传附件',
            icon='fa fa-upload',
            action=Action(
                actionType='dialog',
                dialog={
                    "title": "上传项目附件",
                    "size": "lg",
                    "body": {
                        "type": "form",
                        "api": "post:/api/projects/${id}/attachments",
                        "body": [
                            {
                                "type": "input-file",
                                "name": "file",
                                "label": "选择文件",
                                "accept": ".pdf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.txt,.jpg,.jpeg,.png,.gif,.zip,.rar",
                                "maxSize": 20971520,
                                "required": "true",
                                "asBlob": "true",
                                "description": "支持PDF、Word、Excel、PPT、TXT、图片、压缩包等格式，文件大小不超过20MB"
                            },
                            {
                                "type": "select",
                                "name": "file_type",
                                "label": "附件类型",
                                "options": [
                                    {"label": "项目文档", "value": "document"},
                                    {"label": "技术文档", "value": "technical"},
                                    {"label": "设计文档", "value": "design"},
                                    {"label": "其他文件", "value": "other"}
                                ],
                                "value": "document",
                                "required": "true"
                            },
                            {
                                "type": "input-text",
                                "name": "remark",
                                "label": "备注",
                                "maxLength": 500,
                                "placeholder": "请输入附件备注信息"
                            }
                        ]
                    }
                }
            ),
            flags=['item']
        ),
        lambda admin: AdminAction(
            admin=admin,
            name='batch_import',
            label='批量导入',
            icon='fa fa-file-import',
            action=Action(
                actionType='dialog',
                dialog={
                    "title": "批量导入项目",
                    "size": "md",
                    "body": {
                        "type": "form",
                        "mode": "normal",
                        "controls": [
                            {
                                "type": "input-file",
                                "name": "file",
                                "label": "选择Excel文件",
                                "accept": ".xlsx,.xls",
                                "required": True,
                                "asBlob": True,
                                "description": "请上传包含项目数据的Excel文件，支持.xlsx和.xls格式"
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "tpl",
                                "tpl": "<a href=\"/api/batch-import/download/project\" target=\"_blank\" style=\"color: #1890ff;\">下载导入模板</a>",
                                "className": "mb-2"
                            },
                            {
                                "type": "tpl",
                                "tpl": "<div style=\"background: #f5f5f5; padding: 10px; border-radius: 4px; margin-top: 10px;\"><strong>导入说明：</strong><br/>1. 第一行为表头，从第二行开始为数据<br/>2. 必填字段：项目名称<br/>3. 支持的最大导入数量：100条</div>",
                                "className": "mb-2"
                            }
                        ]
                    },
                    "actions": [
                        {
                            "type": "button",
                            "actionType": "cancel",
                            "label": "取消"
                        },
                        {
                            "type": "submit",
                            "label": "开始导入",
                            "level": "primary",
                            "api": {
                                "method": "post",
                                "url": "/api/batch-import/import/project/form",
                                "data": {
                                    "file": "${file}"
                                }
                            }
                        }
                    ]
                }
            ),
            flags=['toolbar']
        )
    ]
    
    # 列表显示字段
    list_display = [
        Project.id,
        Project.name,
        Project.status,
        Project.planned_start_time,
        Project.planned_end_time,
        Project.actual_start_time,
        Project.actual_end_time,
        "manager_name",
        Project.amount,
        Project.contract_id,
        "_document_count",
        Project.create_time,
        Project.update_time
    ]

    # 列表自定义列配置
    list_columns = {
        "_document_count": {
            "type": "tpl",
            "tpl": "<span class='label label-info'>${data.document_count || 0} 个文件</span>",
            "label": "文档数量",
            "width": 100
        }
    }
    
    def get_list_column(self, request, col_name):
        """获取自定义列配置"""
        if col_name == "_document_count":
            return {
                "name": "_document_count",
                "label": "文档数量",
                "type": "tpl",
                "tpl": "<span class='label label-info'>${data.document_count || 0} 个文件</span>",
                "width": 100
            }
        elif col_name == "manager_name":
            return {
                "name": "manager_name",
                "label": "项目负责人",
                "type": "tpl",
                "tpl": "<a href='/admin/PersonAdmin/item/${data.project_manager}' target='_blank'>${data.manager_name || data.project_manager || '未指定'}</a>",
                "width": 150
            }
        return super().get_list_column(request, col_name)

    # 列表筛选字段 - 明确指定可筛选的字段，避免日期字段自动生成无效筛选器
    list_filter = [
        Project.name,
        Project.status,
        Project.project_manager,
        Project.amount,
        Project.contract_id
    ]

    async def get_list_table(self, request):
        """获取列表表格（已优化）"""
        table = await super().get_list_table(request)
        table.keepItemSelectionOnPageChange = True
        table.selectable = True
        table.multiple = True
        return table
    
    # 注册自定义路由
    def register_router(self):
        """注册自定义路由"""
        super().register_router()
        
        # 注册快速复制路由
        @self.router.post("/item/{item_id}/quick_copy")
        async def quick_copy_route(item_id: int, request: Request):
            """快速复制项目记录"""
            return await self.quick_copy(request, item_id)
    
    # 快速复制项目记录
    async def quick_copy(self, request: Request, item_id: int):
        """快速复制项目记录"""
        try:
            # 调用服务层进行复制
            from app.core.db import get_async_db
            from sqlalchemy.ext.asyncio import AsyncSession
            
            async for db in get_async_db():
                result = await project_service.quick_copy_project(db, item_id)
                
                if result and result.get("new_id"):
                    return BaseApiOut(
                        status=0,
                        msg="项目复制成功",
                        data={"new_id": result["new_id"]}
                    )
                else:
                    return BaseApiOut(
                        status=1,
                        msg="项目复制失败"
                    )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return BaseApiOut(
                status=1,
                msg=f"项目复制失败: {str(e)}"
            )

    async def on_delete_pre(self, request, item_id):
        """删除前处理 - 删除相关阶段、任务、成员、文档和活动"""
        try:
            # 获取异步会话
            async with self.get_async_session() as session:
                # 确保item_id是列表格式，支持批量删除
                if not isinstance(item_id, list):
                    item_id = [item_id]
                
                for id in item_id:
                    # 删除项目阶段
                    stage_stmt = select(ProjectStage).where(ProjectStage.project_id == id)
                    stage_result = await session.execute(stage_stmt)
                    stages = stage_result.scalars().all()
                    
                    for stage in stages:
                        # 删除阶段任务
                        task_stmt = select(ProjectTask).where(ProjectTask.stage_id == stage.id)
                        task_result = await session.execute(task_stmt)
                        tasks = task_result.scalars().all()
                        
                        for task in tasks:
                            await session.delete(task)
                        
                        await session.delete(stage)
                    
                    # 删除项目成员
                    member_stmt = select(ProjectMember).where(ProjectMember.project_id == id)
                    member_result = await session.execute(member_stmt)
                    members = member_result.scalars().all()
                    
                    for member in members:
                        await session.delete(member)
                    
                    # 删除项目文档
                    doc_stmt = select(ProjectDocument).where(ProjectDocument.project_id == id)
                    doc_result = await session.execute(doc_stmt)
                    documents = doc_result.scalars().all()
                    
                    for document in documents:
                        # 删除物理文件
                        import os
                        if document.file_path and os.path.exists(document.file_path):
                            try:
                                os.remove(document.file_path)
                            except Exception as e:
                                print(f"删除文件失败: {document.file_path}, 错误: {e}")
                        
                        # 删除数据库记录
                        await session.delete(document)
                    

                    
                    # 删除项目本身
                    project_stmt = select(Project).where(Project.id == id)
                    project_result = await session.execute(project_stmt)
                    project = project_result.scalar_one_or_none()
                    if project:
                        await session.delete(project)
                
                # 提交删除操作
                await session.commit()
                
        except Exception as e:
            print(f"删除前处理失败: {e}")
            import traceback
            traceback.print_exc()
            # 不阻止删除操作，只是记录错误
        
        # 返回None表示已经完全处理了删除操作
        return table

    def create_item(self, data: dict):
        """创建项目（已优化）"""
        return self.model(**data)

    # 项目详情和更新方法保持不变（已优化）
    def read_item(self, obj: Project) -> dict:
        """获取项目详情（已优化）"""
        try:
            # 获取文档数量
            from app.core.config import settings
            from sqlalchemy import create_engine
            from sqlalchemy.orm import sessionmaker
            import sqlmodel
            
            document_count = 0
            sync_engine = create_engine(settings.DATABASE_URL)
            SyncSession = sessionmaker(bind=sync_engine)
            
            with SyncSession() as session:
                stmt = sqlmodel.select(sqlmodel.func.count(ProjectDocument.id)).where(
                    ProjectDocument.project_id == obj.id
                )
                result = session.execute(stmt)
                document_count = result.scalar()
            
            # 直接返回成功，避免数据库查询
            return {
                "id": obj.id,
                "name": obj.name,
                "description": obj.description,
                "planned_start_time": obj.planned_start_time.isoformat() if obj.planned_start_time else None,
                "planned_end_time": obj.planned_end_time.isoformat() if obj.planned_end_time else None,
                "actual_start_time": obj.actual_start_time.isoformat() if obj.actual_start_time else None,
                "actual_end_time": obj.actual_end_time.isoformat() if obj.actual_end_time else None,
                "project_manager": obj.project_manager,
                "amount": obj.amount,
                "status": obj.status,
                "contract_id": obj.contract_id,
                "document_count": document_count,
                "create_time": obj.create_time.isoformat() if obj.create_time else None,
                "update_time": obj.update_time.isoformat() if obj.update_time else None
            }
        except Exception as e:
            logger.error(f"获取项目详情失败: {str(e)}", exc_info=True)
            raise

    def update_item(self, obj: Project, values: dict):
        """更新项目（已优化）"""
        try:
            # 处理合同ID关联
            contract_id = values.get('contract_id')
            if contract_id is not None:
                # 验证合同是否存在
                from app.contracts.models.contract import Contract
                from sqlmodel import select
                from app.core.config import settings
                from sqlalchemy import create_engine
                from sqlalchemy.orm import sessionmaker
                
                # 创建同步数据库引擎
                sync_engine = create_engine(settings.DATABASE_URL)
                SyncSession = sessionmaker(bind=sync_engine)
                
                # 使用同步会话验证合同
                with SyncSession() as session:
                    contract_stmt = select(Contract).where(Contract.id == contract_id)
                    contract_result = session.execute(contract_stmt)
                    contract = contract_result.scalar_one_or_none()
                    
                    if not contract:
                        raise ValueError(f"关联合同失败：ID为 {contract_id} 的合同不存在")
            
            # 更新项目字段
            for key, value in values.items():
                if hasattr(obj, key):
                    setattr(obj, key, value)
            
            # 返回更新后的对象
            return obj
        except Exception as e:
            logger.error(f"更新项目失败: {str(e)}", exc_info=True)
            raise HTTPException(status_code=500, detail=f"更新项目失败: {str(e)}")

    async def get_list(self, request):
        """获取列表数据，关联负责人信息"""
        from sqlalchemy.orm import selectinload
        
        stmt = select(self.model).options(
            selectinload(self.model.manager)
        )
        return await self.schema_list_from_stmt(request, stmt)
    
    async def on_list_after(self, request, result, data, **kwargs):
        """列表查询后处理，添加负责人名称"""
        data = await super().on_list_after(request, result, data, **kwargs)
        
        for item in data.items:
            if hasattr(item, 'manager') and item.manager:
                manager_name = getattr(item.manager, 'name', '')
                item.manager_name = manager_name
            else:
                item.manager_name = ""
        
        return data


# 项目阶段管理
class ProjectStageAdmin(ClipboardCopyMixin, ModelAdmin):
    """项目阶段管理"""
    page_schema = PageSchema(label="项目阶段管理", icon="fa fa-tasks")
    model = ProjectStage
    router_prefix = "/ProjectStageAdmin"

    copy_fields = ["project_id", "name", "status", "planned_start_time", "planned_end_time"]
    copy_button_label = "复制阶段"
    copy_success_message = "阶段信息已复制到剪贴板"
    list_display = [
        ProjectStage.id,
        ProjectStage.project_id,
        ProjectStage.name,
        ProjectStage.status,
        ProjectStage.planned_start_time,
        ProjectStage.planned_end_time,
        ProjectStage.actual_start_time,
        ProjectStage.actual_end_time,
        ProjectStage.create_time,
        ProjectStage.update_time
    ]

    # 列表筛选字段
    list_filter = []


# 项目任务管理
class ProjectTaskAdmin(ClipboardCopyMixin, ModelAdmin):
    """项目任务管理"""
    page_schema = PageSchema(label="项目任务管理", icon="fa fa-list-check")
    model = ProjectTask
    router_prefix = "/ProjectTaskAdmin"

    copy_fields = ["stage_id", "name", "assignee", "status", "priority", "progress"]
    copy_button_label = "复制任务"
    copy_success_message = "任务信息已复制到剪贴板"
    list_display = [
        ProjectTask.id,
        ProjectTask.stage_id,
        ProjectTask.name,
        ProjectTask.assignee,
        ProjectTask.status,
        ProjectTask.progress,
        ProjectTask.priority,
        ProjectTask.planned_start_time,
        ProjectTask.planned_end_time,
        ProjectTask.actual_start_time,
        ProjectTask.actual_end_time,
        ProjectTask.create_time,
        ProjectTask.update_time
    ]

    # 列表筛选字段
    list_filter = [    ]


# 项目文档管理
class ProjectDocumentAdmin(ModelAdmin):
    """项目文档管理"""
    page_schema = PageSchema(label="项目文档管理", icon="fa fa-file-alt")
    model = ProjectDocument
    router_prefix = "/ProjectDocumentAdmin"
    
    # 禁止修改
    readonly_fields = ["*"]
    
    # 自定义权限控制
    async def has_update_permission(self, request, item_id, data):
        """禁止修改"""
        return False
    
    list_display = [
        ProjectDocument.id,
        ProjectDocument.project_id,
        ProjectDocument.name,
        ProjectDocument.category,
        ProjectDocument.file_path,
        ProjectDocument.file_size,
        ProjectDocument.version,
        ProjectDocument.uploader,
        ProjectDocument.upload_time
    ]
    search_fields = []
    list_filter = []
    filter_fields = []


