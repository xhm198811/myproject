from fastapi_amis_admin.admin import ModelAdmin, AdminAction, PageAdmin
from fastapi_amis_admin.admin.admin import AdminApp
from fastapi_amis_admin.amis.components import Action, ActionType, TableColumn, Dialog, Form, Page, Grid, Card, Chart, Button, Divider, Service, Property, CRUD, Table, Tpl, InputText, InputDate, Select
from fastapi_amis_admin.amis import PageSchema
from fastapi_amis_admin.amis.constants import SizeEnum
from fastapi_amis_admin.crud.schema import BaseApiOut
from fastapi import HTTPException, Request, UploadFile, Depends
from fastapi_amis_admin.amis.constants import LevelEnum
from fastapi.responses import JSONResponse
from typing import List, Dict, Any, Optional
from datetime import datetime, date
from .models.contract import Contract, ContractStatusLog, ContractAttachment, ContractReminder
from .schemas import ContractCreate
from .services.contract import contract_service
from sqlmodel import select, func, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from app.utils.clipboard_integration import ClipboardCopyMixin
from app.core.auth import get_current_active_user
from pydantic import BaseModel

class ContractAdmin(ClipboardCopyMixin, ModelAdmin):
    """合同管理"""
    page_schema = "合同管理"
    model = Contract
    router_prefix = "/ContractAdmin"

    copy_fields = ["contract_no", "name", "type", "party_a", "party_b", "amount", "signing_date", "expiry_date"]
    copy_button_label = "复制合同"
    copy_success_message = "合同信息已复制到剪贴板"
    copy_mode = "record"
    copy_success_feedback = "合同记录复制成功，新合同ID：${data.new_id}"

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
                api="post:/admin/ContractAdmin/item/${id}/quick_copy"
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
                    "title": "上传合同附件",
                    "size": "lg",
                    "body": {
                        "type": "form",
                        "api": "post:/api/contracts/${id}/attachments",
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
                                    {"label": "合同附件", "value": "attachment"},
                                    {"label": "补充协议", "value": "supplement"},
                                    {"label": "证明材料", "value": "evidence"},
                                    {"label": "其他文件", "value": "other"}
                                ],
                                "value": "attachment",
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
                    "title": "批量导入合同",
                    "size": "md",
                    "body": {
                        "type": "form",
                        "mode": "normal",
                        "controls": [
                            {
                                "type": "input-file",
                                "name": "import_file",
                                "label": "选择Excel文件",
                                "accept": ".xlsx,.xls",
                                "required": True,
                                "asBlob": True,
                                "description": "请上传包含合同数据的Excel文件，支持.xlsx和.xls格式"
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "tpl",
                                "tpl": "<a href=\"/api/batch-import/download/contract\" target=\"_blank\" style=\"color: #1890ff;\">下载导入模板</a>",
                                "className": "mb-2"
                            },
                            {
                                "type": "tpl",
                                "tpl": "<div style=\"background: #f5f5f5; padding: 10px; border-radius: 4px; margin-top: 10px;\"><strong>导入说明：</strong><br/>1. 第一行为表头，从第二行开始为数据<br/>2. 必填字段：合同编号、合同名称、甲方、乙方、合同金额<br/>3. 支持的最大导入数量：100条</div>",
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
                                "url": "/api/batch-import/import/contract",
                                "data": {
                                    "file": "${import_file}"
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
        Contract.id,
        Contract.contract_no,
        Contract.name,
        Contract.type,
        Contract.status,
        Contract.signing_date,
        Contract.expiry_date,
        Contract.party_a,
        Contract.party_b,
        Contract.amount,
        "_attachment_count"
    ]

    # 列表自定义列配置
    list_columns = {
        "_attachment_count": {
            "type": "tpl",
            "tpl": "<span class='label label-info'>${data.attachment_count || 0} 个文件</span>",
            "label": "附件数量",
            "width": 100
        }
    }
    
    def get_list_column(self, request, col_name):
        """获取自定义列配置"""
        if col_name == "_attachment_count":
            return {
                "name": "_attachment_count",
                "label": "附件数量",
                "type": "tpl",
                "tpl": "<span class='label label-info'>${data.attachment_count || 0} 个文件</span>",
                "width": 100
            }
        return super().get_list_column(request, col_name)

    # 列表筛选字段
    list_filter = []

    # 读取字段（用于获取单个合同详情）
    read_fields = [
        Contract.id,
        Contract.contract_no,
        Contract.name,
        Contract.type,
        Contract.signing_date,
        Contract.expiry_date,
        Contract.party_a,
        Contract.party_b,
        Contract.amount,
        Contract.status,
        Contract.department,
        Contract.creator,
        Contract.create_time,
        Contract.update_time,
        Contract.description,
        "_attachments"
    ]
    
    # 自定义创建前处理
    async def on_create_pre(self, request, obj):
        """创建前处理"""
        data = await super().on_create_pre(request, obj)
        return data
    
    # 自定义列表后处理 - 防止关系字段导致循环引用错误
    async def on_list_after(self, request, result, data, **kwargs):
        """解析数据库查询结果为schema_list，过滤掉关系字段防止循环引用"""
        from sqlalchemy.engine import Row
        
        data.items = self.parser.conv_row_to_dict(result.all())
        
        filtered_items = []
        for item in data.items:
            filtered_item = {k: v for k, v in item.items() if not k.startswith('_')}
            
            contract_id = item.get('id')
            if contract_id:
                filtered_item['attachment_count'] = await self.get_attachment_count(contract_id)
            
            filtered_items.append(filtered_item)
        
        data.items = filtered_items
        
        data.items = [self.list_item(item) for item in data.items]
        return data
    
    # 自定义更新前处理
    async def on_update_pre(self, request, obj, item_id):
        """更新前处理"""
        data = await super().on_update_pre(request, obj, item_id)
        return data
    
    # 自定义删除前处理
    async def on_delete_pre(self, request, item_id):
        """删除前处理 - 删除相关附件和状态日志"""
        try:
            # 获取异步会话
            async with self.get_async_session() as session:
                # 确保item_id是列表格式，支持批量删除
                if not isinstance(item_id, list):
                    item_id = [item_id]
                
                for id in item_id:
                    # 删除与合同相关的项目记录
                    from app.projects.models.project import Project
                    stmt = select(Project).where(Project.contract_id == id)
                    result = await session.execute(stmt)
                    projects = result.scalars().all()
                    
                    for project in projects:
                        # 删除项目的所有子记录
                        # 删除项目阶段
                        from app.projects.models.project import ProjectStage
                        stage_stmt = select(ProjectStage).where(ProjectStage.project_id == project.id)
                        stage_result = await session.execute(stage_stmt)
                        stages = stage_result.scalars().all()
                        
                        for stage in stages:
                            # 删除阶段任务
                            from app.projects.models.project import ProjectTask
                            task_stmt = select(ProjectTask).where(ProjectTask.stage_id == stage.id)
                            task_result = await session.execute(task_stmt)
                            tasks = task_result.scalars().all()
                            
                            for task in tasks:
                                await session.delete(task)
                            
                            await session.delete(stage)
                        
                        # 删除项目成员
                        from app.projects.models.project import ProjectMember
                        member_stmt = select(ProjectMember).where(ProjectMember.project_id == project.id)
                        member_result = await session.execute(member_stmt)
                        members = member_result.scalars().all()
                        
                        for member in members:
                            await session.delete(member)
                        
                        # 删除项目文档
                        from app.projects.models.project import ProjectDocument
                        doc_stmt = select(ProjectDocument).where(ProjectDocument.project_id == project.id)
                        doc_result = await session.execute(doc_stmt)
                        documents = doc_result.scalars().all()
                        
                        for document in documents:
                            await session.delete(document)
                        

                        
                        # 删除项目本身
                        await session.delete(project)
                    
                    # 删除合同附件
                    stmt = select(ContractAttachment).where(ContractAttachment.contract_id == id)
                    result = await session.execute(stmt)
                    attachments = result.scalars().all()
                    
                    for attachment in attachments:
                        # 删除物理文件
                        import os
                        from pathlib import Path
                        if attachment.file_path and os.path.exists(attachment.file_path):
                            try:
                                os.remove(attachment.file_path)
                            except Exception as e:
                                print(f"删除文件失败: {attachment.file_path}, 错误: {e}")
                        
                        # 删除数据库记录
                        await session.delete(attachment)
                    
                    # 删除合同状态日志
                    stmt = select(ContractStatusLog).where(ContractStatusLog.contract_id == id)
                    result = await session.execute(stmt)
                    status_logs = result.scalars().all()
                    
                    for status_log in status_logs:
                        await session.delete(status_log)
                    
                    # 删除合同提醒
                    stmt = select(ContractReminder).where(ContractReminder.contract_id == id)
                    result = await session.execute(stmt)
                    reminders = result.scalars().all()
                    
                    for reminder in reminders:
                        await session.delete(reminder)
                    
                    # 删除合同本身
                    contract_stmt = select(Contract).where(Contract.id == id)
                    contract_result = await session.execute(contract_stmt)
                    contract = contract_result.scalar_one_or_none()
                    if contract:
                        await session.delete(contract)
                
                # 提交删除操作
                await session.commit()
                
        except Exception as e:
            print(f"删除前处理失败: {e}")
            import traceback
            traceback.print_exc()
            # 不阻止删除操作，只是记录错误
        
        # 返回None表示已经完全处理了删除操作
        return None
    

    
    # 获取合同内容文件
    async def get_contract_content(self, contract_id: int) -> ContractAttachment:
        """获取合同内容文件"""
        async with self.get_async_session() as session:
            result = await session.execute(
                select(ContractAttachment).where(
                    ContractAttachment.contract_id == contract_id,
                    ContractAttachment.file_type == "content"
                ).order_by(ContractAttachment.upload_time.desc())
            )
            return result.scalar_one_or_none()
    
    # 上传合同内容文件
    async def upload_contract_content(self, contract_id: int, file: UploadFile, uploader: str) -> ContractAttachment:
        """上传合同内容文件"""
        import os
        from pathlib import Path
        
        # 创建上传目录
        upload_dir = Path("uploads/contracts")
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # 生成文件名
        file_extension = Path(file.filename).suffix
        file_name = f"contract_{contract_id}_content{file_extension}"
        file_path = upload_dir / file_name
        
        # 保存文件
        content = await file.read()
        with open(file_path, "wb") as f:
            f.write(content)
        
        # 创建附件记录
        attachment_data = {
            "contract_id": contract_id,
            "file_name": file.filename,
            "file_path": str(file_path),
            "file_size": len(content),
            "file_type": "content",
            "uploader": uploader,
            "remark": "合同内容文件"
        }
        
        async with self.get_async_session() as session:
            attachment = ContractAttachment(**attachment_data)
            session.add(attachment)
            await session.commit()
            await session.refresh(attachment)
            return attachment
    
    # 获取合同附件数量
    async def get_attachment_count(self, contract_id: int) -> int:
        """获取合同附件数量"""
        try:
            from app.core.db import async_session_factory
            async with async_session_factory() as session:
                stmt = select(ContractAttachment).where(
                    ContractAttachment.contract_id == contract_id,
                    ContractAttachment.is_active == True
                )
                result = await session.execute(stmt)
                return len(result.scalars().all())
        except Exception as e:
            print(f"获取附件数量失败: {e}")
            return 0
    
    # 获取合同附件列表
    async def get_attachment_list(self, contract_id: int) -> List[Dict]:
        """获取合同附件列表"""
        try:
            from app.core.db import async_session_factory
            async with async_session_factory() as session:
                stmt = select(ContractAttachment).where(
                    ContractAttachment.contract_id == contract_id,
                    ContractAttachment.is_active == True
                ).order_by(ContractAttachment.upload_time.desc())
                
                result = await session.execute(stmt)
                attachments = result.scalars().all()
                
                return [
                    {
                        "id": att.id,
                        "file_name": att.file_name,
                        "file_extension": att.file_extension,
                        "file_category": att.file_category,
                        "file_size": att.file_size,
                        "upload_time": att.upload_time.isoformat() if att.upload_time else None,
                        "uploader": att.uploader,
                        "download_count": att.download_count,
                        "remark": att.remark
                    }
                    for att in attachments
                ]
        except Exception as e:
            print(f"获取附件列表失败: {e}")
            return []
    
    # 自定义列表表格
    async def get_list_table(self, request):
        """获取列表表格"""
        table = await super().get_list_table(request)
        
        # 启用行选择功能，支持多选操作
        table.keepItemSelectionOnPageChange = True
        table.selectable = True
        table.multiple = True
        
        return table
    
    # 注册自定义路由
    def register_router(self):
        """注册自定义路由"""
        super().register_router()
        
        # 注册快速复制路由
        async def quick_copy_route(item_id: int, request: Request):
            """快速复制合同记录"""
            return await self.quick_copy(request, item_id)
        
        self.router.add_api_route(
            path="/item/{item_id}/quick_copy",
            endpoint=quick_copy_route,
            methods=["POST"],
            response_model=None,
            include_in_schema=True
        )
    
    # 快速复制合同记录
    async def quick_copy(self, request: Request, item_id: int):
        """快速复制合同记录"""
        try:
            # 调用服务层进行复制
            new_contract = await contract_service.copy_contract(item_id)
            
            if new_contract:
                return BaseApiOut(
                    status=0,
                    msg="合同复制成功",
                    data={"new_id": new_contract.id}
                )
            else:
                return BaseApiOut(
                    status=1,
                    msg="合同复制失败"
                )
        except Exception as e:
            import traceback
            traceback.print_exc()
            return BaseApiOut(
                status=1,
                msg=f"合同复制失败: {str(e)}"
            )
    
    # 获取amis JSON配置
    async def get_amis_json(self, request):
        """获取amis JSON配置"""
        config = await super().get_amis_json(request)
        return config
class ContractAnalysisAdmin(PageAdmin):
    """合同分析页面"""
    page_schema = "合同分析"
    router_prefix = "/ContractAnalysisAdmin"
    
    # 页面标题
    page = Page(
        title="合同数据分析",
        body=Grid(
            columns=[
                # 第一行：总体统计卡片
                Grid.Column(
                    span=12,
                    body=[Grid(
                        columns=[
                            Grid.Column(
                                span=3,
                                body=[Card(
                                    header=Card.Header(title="合同总数"),
                                    body=[Service(
                                        schema={
                                            "type": "tpl",
                                            "tpl": "${value}"
                                        },
                                        api="/api/contracts/analysis/total"
                                    )]
                                )]
                            ),
                            Grid.Column(
                                span=3,
                                body=[Card(
                                    header=Card.Header(title="生效合同"),
                                    body=[Service(
                                        schema={
                                            "type": "tpl",
                                            "tpl": "${value}"
                                        },
                                        api="/api/contracts/analysis/active"
                                    )]
                                )]
                            ),
                            Grid.Column(
                                span=3,
                                body=[Card(
                                    header=Card.Header(title="合同总金额"),
                                    body=[Service(
                                        schema={
                                            "type": "tpl",
                                            "tpl": "${value}"
                                        },
                                        api="/api/contracts/analysis/total_amount"
                                    )]
                                )]
                            ),
                            Grid.Column(
                                span=3,
                                body=[Card(
                                    header=Card.Header(title="平均合同金额"),
                                    body=[Service(
                                        schema={
                                            "type": "tpl",
                                            "tpl": "${value}"
                                        },
                                        api="/api/contracts/analysis/avg_amount"
                                    )]
                                )]
                            )
                        ]
                    )]
                ),
                # 第二行：合同状态分布和类型分布图表
                Grid.Column(
                    span=6,
                    body=[Card(
                        header=Card.Header(title="合同状态分布"),
                        body=[Chart(
                            config={
                                "title": {"text": "合同状态分布"},
                                "legend": {"orient": "right", "top": "center"},
                                "series": [
                                    {
                                        "type": "pie",
                                        "radius": ["50%", "70%"],
                                        "label": {"show": True}
                                    }
                                ]
                            },
                            api="/api/contracts/analysis/status_distribution",
                            height="300"
                        )]
                    )]
                ),
                Grid.Column(
                    span=6,
                    body=[Card(
                        header=Card.Header(title="合同类型分布"),
                        body=[Chart(
                            config={
                                "title": {"text": "合同类型分布"},
                                "xAxis": {"type": "category"},
                                "yAxis": {"type": "value"},
                                "series": [
                                    {
                                        "type": "bar",
                                        "label": {"show": True}
                                    }
                                ]
                            },
                            api="/api/contracts/analysis/type_distribution",
                            height="300"
                        )]
                    )]
                ),
                # 第三行：月度合同趋势和部门分布
                Grid.Column(
                    span=8,
                    body=[Card(
                        header=Card.Header(title="月度合同趋势"),
                        body=[Chart(
                            config={
                                "title": {"text": "月度合同趋势"},
                                "xAxis": {"type": "category"},
                                "yAxis": {"type": "value"},
                                "series": [
                                    {
                                        "type": "line",
                                        "smooth": True
                                    }
                                ]
                            },
                            api="/api/contracts/analysis/monthly_trend",
                            height="350"
                        )]
                    )]
                ),
                Grid.Column(
                    span=4,
                    body=[Card(
                        header=Card.Header(title="部门合同分布"),
                        body=[Chart(
                            config={
                                "title": {"text": "部门合同分布"},
                                "radar": {},
                                "series": [
                                    {
                                        "type": "radar"
                                    }
                                ]
                            },
                            api="/api/contracts/analysis/department_distribution",
                            height="350"
                        )]
                    )]
                ),
                # 第四行：即将到期合同和最近创建的合同
                Grid.Column(
                    span=6,
                    body=[Card(
                        header=Card.Header(title="即将到期合同（30天内）"),
                        body=[CRUD(
                            api="/api/contracts/analysis/expiring_contracts",
                            showHeader=False,
                            columns=[
                                TableColumn(name="contract_no", label="合同编号"),
                                TableColumn(name="name", label="合同名称"),
                                TableColumn(name="expiry_date", label="到期日期"),
                                TableColumn(name="party_b", label="乙方"),
                                TableColumn(name="amount", label="合同金额")
                            ]
                        )]
                    )]
                ),
                Grid.Column(
                    span=6,
                    body=[Card(
                        header=Card.Header(title="最近创建的合同"),
                        body=[CRUD(
                            api="/api/contracts/analysis/recent_contracts",
                            showHeader=False,
                            columns=[
                                TableColumn(name="contract_no", label="合同编号"),
                                TableColumn(name="name", label="合同名称"),
                                TableColumn(name="create_time", label="创建时间"),
                                TableColumn(name="status", label="状态"),
                                TableColumn(name="amount", label="合同金额")
                            ]
                        )]
                    )]
                )
            ]
        )
    )
    
    # 自定义路由处理分析数据
    def register_router(self):
        """注册自定义路由"""
        super().register_router()
        
        # 获取合同分析数据API
        async def get_total_contracts():
            """获取合同总数"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    result = await session.execute(select(func.count(Contract.id)))
                    total = result.scalar_one()
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "value": total,
                            "className": "text-primary"
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取合同总数失败: {str(e)}",
                    "data": None
                }
        
        async def get_active_contracts():
            """获取生效合同数"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(func.count(Contract.id)).where(Contract.status == "已生效")
                    )
                    active = result.scalar_one()
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "value": active,
                            "className": "text-success"
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取生效合同数失败: {str(e)}",
                    "data": None
                }
        
        async def get_total_amount():
            """获取合同总金额"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    result = await session.execute(select(func.sum(Contract.amount)))
                    total_amount = result.scalar() or 0
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "value": f"¥{total_amount:,.2f}",
                            "className": "text-warning"
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取合同总金额失败: {str(e)}",
                    "data": None
                }
        
        async def get_avg_amount():
            """获取平均合同金额"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    result = await session.execute(select(func.avg(Contract.amount)))
                    avg_amount = result.scalar() or 0
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "value": f"¥{avg_amount:,.2f}",
                            "className": "text-info"
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取平均合同金额失败: {str(e)}",
                    "data": None
                }
        
        async def get_status_distribution():
            """获取合同状态分布"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(Contract.status, func.count(Contract.id)).group_by(Contract.status)
                    )
                    data = result.all()
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "type": "pie",
                            "data": [
                                {
                                    "name": status,
                                    "value": count
                                }
                                for status, count in data
                            ]
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取合同状态分布失败: {str(e)}",
                    "data": None
                }
        
        async def get_type_distribution():
            """获取合同类型分布"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(Contract.type, func.count(Contract.id)).group_by(Contract.type)
                    )
                    data = result.all()
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "type": "bar",
                            "data": [
                                {
                                    "type": "类型",
                                    "value": count
                                }
                                for type_name, count in data
                            ]
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取合同类型分布失败: {str(e)}",
                    "data": None
                }
        
        async def get_monthly_trend():
            """获取月度合同趋势"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    from datetime import timedelta
                    from sqlalchemy import text
                    
                    # 获取过去12个月的数据
                    expiring_date = datetime.now() - timedelta(days=365)
                    result = await session.execute(
                        select(Contract)
                        .where(Contract.create_time >= expiring_date)
                        .order_by(Contract.create_time)
                    )
                    contracts = result.scalars().all()
                    
                    # 按月分组统计
                    monthly_data = {}
                    for contract in contracts:
                        month_key = contract.create_time.strftime('%Y-%m')
                        if month_key not in monthly_data:
                            monthly_data[month_key] = {"count": 0, "amount": 0}
                        monthly_data[month_key]["count"] += 1
                        monthly_data[month_key]["amount"] += contract.amount or 0
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "type": "line",
                            "data": {
                                "columns": ["月份", "合同数量", "合同金额"],
                                "rows": [
                                    [month, data["count"], data["amount"]]
                                    for month, data in sorted(monthly_data.items())
                                ]
                            }
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取月度合同趋势失败: {str(e)}",
                    "data": None
                }
        
        async def get_department_distribution():
            """获取部门合同分布"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(Contract.department, func.count(Contract.id)).group_by(Contract.department)
                    )
                    data = result.all()
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "type": "radar",
                            "data": {
                                "columns": ["部门", "合同数量"],
                                "rows": [
                                    [dept, count]
                                    for dept, count in data
                                ]
                            }
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取部门合同分布失败: {str(e)}",
                    "data": None
                }
        
        async def get_expiring_contracts():
            """获取即将到期的合同"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    from datetime import timedelta
                    
                    # 获取30天内到期的合同
                    expiring_date = datetime.now().date() + timedelta(days=30)
                    result = await session.execute(
                        select(Contract)
                        .where(
                            and_(
                                Contract.expiry_date <= expiring_date,
                                Contract.expiry_date >= datetime.now().date(),
                                Contract.status == "已生效"
                            )
                        )
                        .order_by(Contract.expiry_date)
                        .limit(10)
                    )
                    contracts = result.scalars().all()
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "items": [
                                {
                                    "id": contract.id,
                                    "contract_no": contract.contract_no,
                                    "name": contract.name,
                                    "expiry_date": contract.expiry_date.isoformat() if contract.expiry_date else None,
                                    "party_b": contract.party_b,
                                    "amount": contract.amount
                                }
                                for contract in contracts
                            ],
                            "total": len(contracts)
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取即将到期合同失败: {str(e)}",
                    "data": None
                }
        
        async def get_recent_contracts():
            """获取最近创建的合同"""
            try:
                from app.core.db import async_session_factory
                async with async_session_factory() as session:
                    result = await session.execute(
                        select(Contract)
                        .order_by(Contract.create_time.desc())
                        .limit(10)
                    )
                    contracts = result.scalars().all()
                    
                    return {
                        "status": 0,
                        "msg": "success",
                        "data": {
                            "items": [
                                {
                                    "id": contract.id,
                                    "contract_no": contract.contract_no,
                                    "name": contract.name,
                                    "create_time": contract.create_time.isoformat() if contract.create_time else None,
                                    "status": contract.status,
                                    "amount": contract.amount
                                }
                                for contract in contracts
                            ],
                            "total": len(contracts)
                        }
                    }
            except Exception as e:
                return {
                    "status": 500,
                    "msg": f"获取最近创建合同失败: {str(e)}",
                    "data": None
                }
        
        # 注册API路由
        self.router.add_api_route(
            "/api/contracts/analysis/total",
            get_total_contracts,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/active",
            get_active_contracts,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/total_amount",
            get_total_amount,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/avg_amount",
            get_avg_amount,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/status_distribution",
            get_status_distribution,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/type_distribution",
            get_type_distribution,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/monthly_trend",
            get_monthly_trend,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/department_distribution",
            get_department_distribution,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/expiring_contracts",
            get_expiring_contracts,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        self.router.add_api_route(
            "/api/contracts/analysis/recent_contracts",
            get_recent_contracts,
            methods=["GET"],
            response_model=None,
            include_in_schema=True
        )
        
        return self
class ContractStatusLogAdmin(ModelAdmin):
    """合同状态变更记录管理"""
    page_schema = "合同状态变更记录"
    model = ContractStatusLog
    router_prefix = "/ContractStatusLogAdmin"
    
    # 列表显示字段
    list_display = [
        ContractStatusLog.id,
        ContractStatusLog.contract_id,
        ContractStatusLog.old_status,
        ContractStatusLog.new_status,
        ContractStatusLog.operator,
        ContractStatusLog.operate_time,
        ContractStatusLog.remark
    ]
    
    # 列表筛选字段
    list_filter = []
    
    # 只读模型，禁止修改
    readonly_fields = ["*"]
    
    # 自定义权限控制
    async def has_change_permission(self, request, item_id):
        """禁止修改"""
        return False
    
    async def has_delete_permission(self, request, item_id):
        """禁止删除"""
        return False

class ContractAttachmentAdmin(ModelAdmin):
    """合同附件管理"""
    page_schema = "合同附件管理"
    model = ContractAttachment
    router_prefix = "/ContractAttachmentAdmin"
    
    # 禁止修改
    readonly_fields = ["*"]
    
    # 自定义权限控制
    async def has_update_permission(self, request, item_id, data):
        """禁止修改"""
        return False
    
    # 列表显示字段
    list_display = [
        ContractAttachment.id,
        "_contract_info",
        ContractAttachment.file_name,
        ContractAttachment.file_category,
        ContractAttachment.file_size,
        ContractAttachment.uploader,
        ContractAttachment.upload_time,
        ContractAttachment.remark
    ]
    
    # 自定义列配置
    def get_list_column(self, request, col_name):
        """获取自定义列配置"""
        if col_name == "_contract_info":
            return {
                "name": "_contract_info",
                "label": "所属合同",
                "type": "tpl",
                "tpl": "<span>合同 #${data.contract_id}</span>",
                "width": 120
            }
        return super().get_list_column(request, col_name)
    
    # 列表筛选字段
    list_filter = [
        ContractAttachment.file_category,
        ContractAttachment.file_type,
        ContractAttachment.uploader
    ]
    
    # 自定义创建前处理
    async def on_create_pre(self, request, obj):
        """创建前处理"""
        data = await super().on_create_pre(request, obj)
        return data
