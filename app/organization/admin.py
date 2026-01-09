from typing import List, Optional
from fastapi import Request, Depends
try:
    from fastapi_amis_admin.admin import ModelAdmin, AdminAction
    from fastapi_amis_admin.models.fields import Field
    from fastapi_amis_admin.amis import PageSchema
    from fastapi_amis_admin.crud.schema import ItemListSchema
    from fastapi_amis_admin.amis.components import Action, ActionType, Dialog, Form
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from fastapi_amis_admin.admin import ModelAdmin, AdminAction
    from fastapi_amis_admin.models.fields import Field
    from fastapi_amis_admin.amis import PageSchema
    from fastapi_amis_admin.crud.schema import ItemListSchema
    from fastapi_amis_admin.amis.components import Action, ActionType, Dialog, Form

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from .models.organization import Organization, OrganizationRole
from .models.person import Person, PersonRoleLink, PersonDepartmentHistory
from ..core.db import get_async_db
from ..utils.clipboard_integration import ClipboardCopyMixin
from .schemas.person_import import PersonBatchImportRequest, PersonBatchImportResult
from .services.person_import_service import PersonImportService


async def get_user_from_request(request: Request) -> Optional[dict]:
    """从请求中获取当前用户信息"""
    try:
        if hasattr(request.state, 'user') and request.state.user:
            return request.state.user
        return None
    except:
        return None


class OrganizationAdmin(ClipboardCopyMixin, ModelAdmin):
    page_schema = PageSchema(label="组织管理", icon="fa fa-sitemap")
    model = Organization

    copy_fields = ["name", "code", "type", "description", "phone", "email"]
    copy_button_label = "复制组织"
    copy_success_message = "组织信息已复制到剪贴板"

    list_display = [
        Organization.id,
        Organization.name,
        Organization.code,
        Organization.type,
        Organization.level,
        "parent_name",
        "leader_name",
        Organization.phone,
        Organization.email,
        Organization.is_active,
        Organization.created_at,
    ]
    
    async def get_list(self, request):
        """获取列表数据，关联上级组织和负责人信息"""
        from sqlalchemy.orm import selectinload
        
        stmt = select(self.model).options(
            selectinload(self.model.parent),
            selectinload(self.model.leader)
        )
        return await self.schema_list_from_stmt(request, stmt)

    form_fields = [
        Organization.name,
        Organization.code,
        Organization.type,
        Organization.parent_id,
        Organization.leader_id,
        Organization.description,
        Organization.address,
        Organization.phone,
        Organization.email,
        Organization.is_active,
    ]

    async def has_create_permission(self, request: Request, data=None, **kwargs) -> bool:
        """只允许 admin 用户创建组织"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def has_delete_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许 admin 用户删除组织"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def has_list_permission(self, request: Request, paginator, filters=None, **kwargs) -> bool:
        """只允许 admin 或 staff 用户查看组织列表"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_staff", False) or current_user.get("is_superuser", False)

    async def has_read_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许 admin 或 staff 用户查看组织详情"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_staff", False) or current_user.get("is_superuser", False)

    async def has_update_permission(self, request: Request, item_id: List[str], data=None, **kwargs) -> bool:
        """只允许 admin 用户更新组织"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def on_list_after(self, request: Request, result, data: ItemListSchema, **kwargs):
        """列表查询后处理，添加子组织数量"""
        data = await super().on_list_after(request, result, data, **kwargs)
        async for db in get_async_db():
            for item in data.items:
                org_id = getattr(item, 'id', None)
                
                if org_id:
                    child_count_result = await db.execute(
                        select(func.count()).select_from(Organization).where(Organization.parent_id == org_id)
                    )
                    item.child_count = child_count_result.scalar() or 0
                
                if hasattr(item, 'leader') and item.leader:
                    leader_name = getattr(item.leader, 'name', '')
                    item.leader_name = leader_name
                else:
                    item.leader_name = ""
                
                if hasattr(item, 'parent') and item.parent:
                    parent_name = getattr(item.parent, 'name', '')
                    item.parent_name = parent_name
                else:
                    item.parent_name = ""
        return data

    async def on_create_before(self, request: Request, data: dict, **kwargs):
        """创建组织前处理，自动计算层级"""
        parent_id = data.get("parent_id")
        if parent_id:
            async for db in get_async_db():
                result = await db.execute(select(Organization).where(Organization.id == parent_id))
                parent_org = result.scalar_one_or_none()
                if parent_org:
                    data["level"] = parent_org.level + 1
                else:
                    data["level"] = 1
        else:
            data["level"] = 1
        return data

    async def on_update_before(self, request: Request, data: dict, **kwargs):
        """更新组织前处理，重新计算层级"""
        parent_id = data.get("parent_id")
        if parent_id:
            async for db in get_async_db():
                result = await db.execute(select(Organization).where(Organization.id == parent_id))
                parent_org = result.scalar_one_or_none()
                if parent_org:
                    data["level"] = parent_org.level + 1
                else:
                    data["level"] = 1
        else:
            data["level"] = 1
        return data


class OrganizationRoleAdmin(ClipboardCopyMixin, ModelAdmin):
    page_schema = PageSchema(label="组织角色", icon="fa fa-user-tag")
    model = OrganizationRole

    copy_fields = ["name", "code", "description", "is_active"]
    copy_button_label = "复制角色"
    copy_success_message = "角色信息已复制到剪贴板"

    list_display = [
        OrganizationRole.id,
        OrganizationRole.name,
        OrganizationRole.code,
        OrganizationRole.description,
        OrganizationRole.is_active,
        OrganizationRole.created_at,
    ]

    form_fields = [
        OrganizationRole.name,
        OrganizationRole.code,
        OrganizationRole.description,
        OrganizationRole.permissions,
        OrganizationRole.is_active,
    ]

    async def has_create_permission(self, request: Request, data=None, **kwargs) -> bool:
        """只允许 admin 用户创建角色"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def has_delete_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许 admin 用户删除角色"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def has_list_permission(self, request: Request, paginator, filters=None, **kwargs) -> bool:
        """只允许 admin 或 staff 用户查看角色列表"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_staff", False) or current_user.get("is_superuser", False)

    async def has_read_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许 admin 或 staff 用户查看角色详情"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_staff", False) or current_user.get("is_superuser", False)

    async def has_update_permission(self, request: Request, item_id: List[str], data=None, **kwargs) -> bool:
        """只允许 admin 用户更新角色"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)


class PersonAdmin(ClipboardCopyMixin, ModelAdmin):
    page_schema = PageSchema(label="人员管理", icon="fa fa-users")
    model = Person

    copy_fields = ["name", "code", "position", "phone", "email", "job_level"]
    copy_button_label = "复制人员"
    copy_success_message = "人员信息已复制到剪贴板"

    list_display = [
        Person.id,
        Person.name,
        Person.code,
        "organization_name",
        Person.position,
        Person.job_level,
        Person.gender,
        Person.phone,
        Person.email,
        Person.employment_status,
        Person.is_active,
        Person.created_at,
    ]
    
    async def get_list(self, request):
        """获取列表数据，关联组织信息"""
        from sqlalchemy.orm import selectinload
        
        stmt = select(self.model).options(
            selectinload(self.model.organization)
        )
        return await self.schema_list_from_stmt(request, stmt)

    form_fields = [
        Person.name,
        Person.code,
        Person.user_id,
        Person.organization_id,
        Person.position,
        Person.job_level,
        Person.gender,
        Person.birth_date,
        Person.id_card,
        Person.phone,
        Person.email,
        Person.address,
        Person.emergency_contact,
        Person.emergency_phone,
        Person.hire_date,
        Person.probation_end_date,
        Person.contract_start_date,
        Person.contract_end_date,
        Person.employment_status,
        Person.work_location,
        Person.education,
        Person.major,
        Person.school,
        Person.skills,
        Person.experience,
        Person.avatar,
        Person.is_active,
    ]

    admin_action_maker = [
        lambda admin_obj: AdminAction(
            admin=admin_obj,
            name='batch_import',
            label='批量导入',
            icon='fa fa-file-import',
            action=Action(
                actionType='dialog',
                dialog={
                    "title": "批量导入人员",
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
                                "description": "请上传包含人员数据的Excel文件，支持.xlsx和.xls格式"
                            },
                            {
                                "type": "divider"
                            },
                            {
                                "type": "tpl",
                                "tpl": "<a href=\"/api/batch-import/download/person\" target=\"_blank\" style=\"color: #1890ff;\">下载导入模板</a>",
                                "className": "mb-2"
                            },
                            {
                                "type": "tpl",
                                "tpl": "<div style=\"background: #f5f5f5; padding: 10px; border-radius: 4px; margin-top: 10px;\"><strong>导入说明：</strong><br/>1. 第一行为表头，从第二行开始为数据<br/>2. 必填字段：姓名、人员编码<br/>3. 支持的最大导入数量：1000条<br/>4. 人员编码必须唯一，重复将根据导入模式处理</div>",
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
                                "url": "/api/batch-import/import/person/form",
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

    async def has_create_permission(self, request: Request, data=None, **kwargs) -> bool:
        """只允许 admin 用户创建人员"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def has_delete_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许 admin 用户删除人员"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def has_list_permission(self, request: Request, paginator, filters=None, **kwargs) -> bool:
        """只允许 admin 或 staff 用户查看人员列表"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_staff", False) or current_user.get("is_superuser", False)

    async def has_read_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许 admin 或 staff 用户查看人员详情"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_staff", False) or current_user.get("is_superuser", False)

    async def has_update_permission(self, request: Request, item_id: List[str], data=None, **kwargs) -> bool:
        """只允许 admin 用户更新人员"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def on_list_after(self, request: Request, result, data: ItemListSchema, **kwargs):
        """列表查询后处理，添加组织和用户信息"""
        data = await super().on_list_after(request, result, data, **kwargs)
        
        for item in data.items:
            if hasattr(item, 'organization') and item.organization:
                org_name = getattr(item.organization, 'name', '')
                item.organization_name = org_name
            else:
                item.organization_name = ""
            
            if hasattr(item, 'user') and item.user:
                username = getattr(item.user, 'username', '')
                item.username = username
            else:
                item.username = ""
        
        return data

    async def batch_import(self, request: Request):
        """批量导入人员"""
        try:
            from fastapi import UploadFile, File, Form
            import pandas as pd
            import io
            
            form = await request.form()
            file = form.get('file')
            import_mode = form.get('import_mode', 'append')
            skip_duplicates = form.get('skip_duplicates', 'true').lower() == 'true'
            
            if not file:
                return {
                    'status': 'error',
                    'message': '请上传Excel文件'
                }
            
            # 读取Excel文件
            content = await file.read()
            df = pd.read_excel(io.BytesIO(content))
            
            # 转换为字典列表
            data = df.to_dict('records')
            
            # 转换为导入格式
            from .schemas.person_import import PersonImportItem
            import_data = []
            for row in data:
                try:
                    import_item = PersonImportItem(**row)
                    import_data.append(import_item)
                except Exception as e:
                    continue
            
            # 执行导入
            async for db in get_async_db():
                service = PersonImportService(db)
                result = await service.import_persons(
                    data=import_data,
                    import_mode=import_mode,
                    skip_duplicates=skip_duplicates
                )
            
            return {
                'status': 'success',
                'message': f'导入完成，成功{result.success_count}条，失败{result.failed_count}条，跳过{result.skipped_count}条',
                'data': {
                    'total_count': result.total_count,
                    'success_count': result.success_count,
                    'failed_count': result.failed_count,
                    'skipped_count': result.skipped_count,
                    'success_rate': result.success_rate,
                    'errors': result.errors[:10]
                }
            }
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            return {
                'status': 'error',
                'message': f'导入失败: {str(e)}'
            }


class PersonDepartmentHistoryAdmin(ModelAdmin):
    page_schema = PageSchema(label="部门调动历史", icon="fa fa-exchange-alt")
    model = PersonDepartmentHistory

    list_display = [
        PersonDepartmentHistory.id,
        "person_name",
        "from_organization_name",
        "to_organization_name",
        PersonDepartmentHistory.change_date,
        PersonDepartmentHistory.reason,
        PersonDepartmentHistory.created_by,
    ]
    
    async def get_list(self, request):
        """获取列表数据，关联人员和组织信息"""
        from sqlalchemy.orm import selectinload
        
        stmt = select(self.model).options(
            selectinload(self.model.person),
            selectinload(self.model.from_organization),
            selectinload(self.model.to_organization)
        )
        return await self.schema_list_from_stmt(request, stmt)
    
    async def on_list_after(self, request: Request, result, data: ItemListSchema, **kwargs):
        """列表查询后处理，添加人员和组织名称"""
        data = await super().on_list_after(request, result, data, **kwargs)
        
        for item in data.items:
            if hasattr(item, 'person') and item.person:
                person_name = getattr(item.person, 'name', '')
                item.person_name = person_name
            else:
                item.person_name = ""
            
            if hasattr(item, 'from_organization') and item.from_organization:
                from_org_name = getattr(item.from_organization, 'name', '')
                item.from_organization_name = from_org_name
            else:
                item.from_organization_name = ""
            
            if hasattr(item, 'to_organization') and item.to_organization:
                to_org_name = getattr(item.to_organization, 'name', '')
                item.to_organization_name = to_org_name
            else:
                item.to_organization_name = ""
        
        return data

    form_fields = [
        PersonDepartmentHistory.person_id,
        PersonDepartmentHistory.from_organization_id,
        PersonDepartmentHistory.to_organization_id,
        PersonDepartmentHistory.change_date,
        PersonDepartmentHistory.reason,
        PersonDepartmentHistory.remark,
    ]

    async def has_create_permission(self, request: Request, data=None, **kwargs) -> bool:
        """只允许 admin 用户创建调动记录"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def has_delete_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许 admin 用户删除调动记录"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)

    async def has_list_permission(self, request: Request, paginator, filters=None, **kwargs) -> bool:
        """只允许 admin 或 staff 用户查看调动记录"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_staff", False) or current_user.get("is_superuser", False)

    async def has_read_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许 admin 或 staff 用户查看调动记录详情"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_staff", False) or current_user.get("is_superuser", False)

    async def has_update_permission(self, request: Request, item_id: List[str], data=None, **kwargs) -> bool:
        """只允许 admin 用户更新调动记录"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        return current_user.get("is_superuser", False)
