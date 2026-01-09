from typing import List, Optional
from fastapi import Request
try:
    from fastapi_amis_admin import admin
    from fastapi_amis_admin.models.fields import Field
    from fastapi_amis_admin.amis import PageSchema, ActionType, Action
    from fastapi_amis_admin.crud.schema import ItemListSchema, BaseApiOut
except ImportError:
    # 如果是相对路径导入失败，尝试从上级目录导入
    import sys
    import os
    # 添加 fastapi-amis-admin-master 目录到路径
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
    from fastapi_amis_admin import admin
    from fastapi_amis_admin.models.fields import Field
    from fastapi_amis_admin.amis import PageSchema, ActionType, Action
    from fastapi_amis_admin.crud.schema import ItemListSchema, BaseApiOut
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from jose import jwt

from .models.user import User, Role, Permission, UserActivityLog, UserLoginHistory, UserRoleLink
from ..core.db import get_async_db
from ..utils.clipboard_copy_action import add_clipboard_copy_actions, ClipboardCopyAction, QuickClipboardCopyAction
from ..utils.copy_config import get_copy_config
from ..utils.clipboard_integration import ClipboardCopyMixin
from ..core.config import settings


async def get_user_from_request(request: Request) -> Optional[dict]:
    """从请求中获取当前用户信息"""
    try:
        if hasattr(request.state, 'user') and request.state.user:
            return request.state.user
        return None
    except:
        return None


class UserAdmin(ClipboardCopyMixin, admin.ModelAdmin):
    page_schema = PageSchema(label="用户管理", icon="fa fa-user")
    model = User

    copy_fields = ["username", "email", "first_name", "last_name", "phone", "department", "employee_id", "job_title"]
    copy_button_label = "复制用户"
    copy_success_message = "用户信息已复制到剪贴板"
    
    async def has_create_permission(self, request: Request, data=None, **kwargs) -> bool:
        """禁用创建用户功能"""
        return False
    
    async def has_delete_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """禁用删除用户功能"""
        return False
    
    async def has_list_permission(self, request: Request, paginator, filters=None, **kwargs) -> bool:
        """只允许 admin 用户查看用户列表"""
        current_user = await get_user_from_request(request)
        print(f"[DEBUG] has_list_permission: current_user = {current_user}")
        if not current_user:
            print(f"[DEBUG] has_list_permission: No current user, returning False")
            return False
        is_superuser = current_user.get("is_superuser", False)
        print(f"[DEBUG] has_list_permission: is_superuser = {is_superuser}")
        return is_superuser
    
    async def has_read_permission(self, request: Request, item_id: List[str], **kwargs) -> bool:
        """只允许查看自己的信息或 admin 用户"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        if current_user.get("is_superuser", False):
            return True
        return str(current_user.get("id")) in item_id
    
    async def has_update_permission(self, request: Request, item_id: List[str], data=None, **kwargs) -> bool:
        """只允许修改自己的密码或 admin 用户"""
        current_user = await get_user_from_request(request)
        if not current_user:
            return False
        if current_user.get("is_superuser", False):
            return True
        return str(current_user.get("id")) in item_id
  
    column_list = [
        User.id,
        User.employee_id,
        User.username,
        User.email,
        User.first_name,
        User.last_name,
        User.job_title,
        User.department,
        User.phone,
        User.employment_status,
        User.is_active,
        User.is_staff,
        User.is_superuser,
        User.date_joined,
        User.last_login,
    ]
    
    form_fields = [
        User.password,
    ]
    
    form_exclude_fields = [
        User.employee_id,
        User.username,
        User.email,
        User.first_name,
        User.last_name,
        User.phone,
        User.job_title,
        User.department,
        User.manager_id,
        User.hire_date,
        User.employment_status,
        User.avatar,
        User.is_active,
        User.is_staff,
        User.is_superuser,
        User.date_joined,
        User.last_login,
    ]
    
    # 暂时屏蔽复制功能 - 开始
    # async def copy_item(self, request: Request, item_id: str, data: Optional[dict] = None, **kwargs):
    #     from ..core.db import get_async_db
    #     
    #     if not item_id:
    #         return BaseApiOut(status=-1, msg="请选择要复制的用户")
    #     
    #     async for db in get_async_db():
    #         try:
    #             result = await db.execute(select(User).where(User.id == item_id))
    #             original_user = result.scalar_one_or_none()
    #             
    #             if not original_user:
    #                 return BaseApiOut(status=-1, msg="用户不存在")
    #             
    #             new_username = f"{original_user.username}_copy"
    #             
    #             existing_result = await db.execute(
    #                 select(User).where(User.username == new_username)
    #             )
    #             if existing_result.scalar_one_or_none():
    #                 return BaseApiOut(status=-1, msg=f"用户名 {new_username} 已存在")
    #             
    #             new_user = User(
    #                 username=new_username,
    #                 email=f"copy_{original_user.email}",
    #                 hashed_password=original_user.hashed_password,
    #                 first_name=original_user.first_name,
    #                 last_name=original_user.last_name,
    #                 phone=original_user.phone,
    #                 department=original_user.department,
    #                 avatar=original_user.avatar,
    #                 is_active=original_user.is_active,
    #                 is_staff=original_user.is_staff,
    #                 is_superuser=False
    #             )
    #             
    #             db.add(new_user)
    #             await db.commit()
    #             await db.refresh(new_user)
    #             
    #             return BaseApiOut(
    #                 status=0,
    #                 msg="用户复制成功",
    #                 data={
    #                     "id": new_user.id,
    #                     "username": new_user.username,
    #                     "email": new_user.email
    #                 }
    #             )
    #         except Exception as e:
    #             await db.rollback()
    #             return BaseApiOut(status=-1, msg=f"复制失败: {str(e)}")
    # 暂时屏蔽复制功能 - 结束
    
    async def on_list_after(self, request: Request, result, data: ItemListSchema, **kwargs):
        """列表查询后处理，根据权限过滤用户"""
        data = await super().on_list_after(request, result, data, **kwargs)
        
        current_user = await get_user_from_request(request)
            
        if current_user and current_user.get("is_superuser", False):
            pass
        elif current_user:
            current_user_id = str(current_user.get("id", ""))
            data.items = [item for item in data.items if str(item.id) == current_user_id]
        else:
            data.items = []
        
        for item in data.items:
            if hasattr(item, 'roles') and item.roles:
                role_names = [role.get("name", "") for role in item.roles]
                item.role_names = ", ".join(role_names)
            else:
                item.role_names = ""
        return data
    
    async def on_create_before(self, request: Request, data: dict, **kwargs):
        """创建用户前处理，使用 Django 方式哈希密码"""
        if "password" in data and data["password"]:
            import os
            import sys
            import django
            
            sys.path.insert(0, 'E:\\HSdigitalportal\\enterprise_portal')
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_portal.settings')
            django.setup()
            
            from django.contrib.auth.hashers import make_password
            data["password"] = make_password(data["password"])
        return data
    
    async def on_update_before(self, request: Request, data: dict, **kwargs):
        """更新用户前处理，使用 Django 方式哈希密码"""
        if "password" in data and data["password"]:
            import os
            import sys
            import django
            
            sys.path.insert(0, 'E:\\HSdigitalportal\\enterprise_portal')
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_portal.settings')
            django.setup()
            
            from django.contrib.auth.hashers import make_password
            data["password"] = make_password(data["password"])
        return data


class RoleAdmin(ClipboardCopyMixin, admin.ModelAdmin):
    page_schema = PageSchema(label="角色管理", icon="fa fa-users")
    model = Role

    copy_fields = ["name", "display_name", "description", "is_active"]
    copy_button_label = "复制角色"
    copy_success_message = "角色信息已复制到剪贴板"

    column_list = [
        Role.id,
        Role.name,
        Role.display_name,
        Role.description,
        Role.is_active,
        Role.is_system,
        Role.created_at,
    ]

    form_fields = [
        Role.name,
        Role.display_name,
        Role.description,
        Role.is_active,
        Role.is_system,
    ]

    async def on_list_after(self, request: Request, result, data: ItemListSchema, **kwargs):
        """列表查询后处理，添加权限和用户数量"""
        data = await super().on_list_after(request, result, data, **kwargs)
        async for db in get_async_db():
            for item in data.items:
                role_id = getattr(item, 'id', None)
                
                user_count_result = await db.execute(
                    select(func.count()).select_from(UserRoleLink).where(UserRoleLink.role_id == role_id)
                )
                item.user_count = user_count_result.scalar() or 0
                
                if hasattr(item, 'permissions') and item.permissions:
                    permission_names = [perm.get("name", "") for perm in item.permissions]
                    item.permission_names = ", ".join(permission_names)
                else:
                    item.permission_names = ""
        return data


class PermissionAdmin(ClipboardCopyMixin, admin.ModelAdmin):
    page_schema = PageSchema(label="权限管理", icon="fa fa-key")
    model = Permission

    copy_fields = ["name", "codename", "description", "module", "action"]
    copy_button_label = "复制权限"
    copy_success_message = "权限信息已复制到剪贴板"

    column_list = [
        Permission.id,
        Permission.name,
        Permission.codename,
        Permission.description,
        Permission.module,
        Permission.action,
        Permission.created_at,
    ]

    form_fields = [
        Permission.name,
        Permission.codename,
        Permission.description,
        Permission.module,
        Permission.action,
    ]


class UserActivityLogAdmin(admin.ModelAdmin):
    page_schema = PageSchema(label="用户活动日志", icon="fa fa-history")
    model = UserActivityLog

    column_list = [
        UserActivityLog.id,
        UserActivityLog.user_id,
        UserActivityLog.action,
        UserActivityLog.description,
        UserActivityLog.ip_address,
        UserActivityLog.created_at,
    ]

    form_fields = [
        UserActivityLog.user_id,
        UserActivityLog.action,
        UserActivityLog.description,
        UserActivityLog.ip_address,
        UserActivityLog.user_agent,
        UserActivityLog.meta_data,
    ]


class UserLoginHistoryAdmin(admin.ModelAdmin):
    page_schema = PageSchema(label="用户登录历史", icon="fa fa-sign-in")
    model = UserLoginHistory

    column_list = [
        UserLoginHistory.id,
        UserLoginHistory.user_id,
        UserLoginHistory.login_time,
        UserLoginHistory.logout_time,
        UserLoginHistory.ip_address,
        UserLoginHistory.login_status,
        UserLoginHistory.failure_reason,
    ]

    form_fields = [
        UserLoginHistory.user_id,
        UserLoginHistory.login_time,
        UserLoginHistory.logout_time,
        UserLoginHistory.ip_address,
        UserLoginHistory.user_agent,
        UserLoginHistory.login_status,
        UserLoginHistory.failure_reason,
    ]


# 暂时注释掉复制功能装饰器
# 使用装饰器为所有Admin类添加复制功能
# UserAdmin = add_clipboard_copy_actions(
#     UserAdmin,
#     quick_copy_fields=get_copy_config('UserAdmin').get('quick_copy_fields', []),
#     field_formatters=get_copy_config('UserAdmin').get('field_formatters', {})
# )
#
# RoleAdmin = add_clipboard_copy_actions(
#     RoleAdmin,
#     quick_copy_fields=['name', 'display_name', 'is_active'],
#     field_formatters={
#         'name': lambda x: f"角色:{x}" if x else "",
#         'display_name': lambda x: f"显示名:{x}" if x else "",
#         'is_active': lambda x: "启用" if x else "禁用",
#     }
# )
#
# PermissionAdmin = add_clipboard_copy_actions(
#     PermissionAdmin,
#     quick_copy_fields=['name', 'codename', 'module', 'action'],
#     field_formatters={
#         'name': lambda x: f"权限:{x}" if x else "",
#         'codename': lambda x: f"代码:{x}" if x else "",
#         'module': lambda x: f"模块:{x}" if x else "",
#         'action': lambda x: f"操作:{x}" if x else "",
#     }
# )
#
# UserActivityLogAdmin = add_clipboard_copy_actions(
#     UserActivityLogAdmin,
#     quick_copy_fields=['action', 'description', 'ip_address'],
#     field_formatters={
#         'action': lambda x: f"操作:{x}" if x else "",
#         'description': lambda x: x[:100] if x else "",
#         'ip_address': lambda x: f"IP:{x}" if x else "",
#     }
# )
#
# UserLoginHistoryAdmin = add_clipboard_copy_actions(
#     UserLoginHistoryAdmin,
#     quick_copy_fields=['login_time', 'ip_address', 'login_status'],
#     field_formatters={
#         'login_time': lambda x: x.strftime('%Y-%m-%d %H:%M:%S') if x else "",
#         'ip_address': lambda x: f"IP:{x}" if x else "",
#         'login_status': lambda x: "成功" if x else "失败",
#     }
# )
