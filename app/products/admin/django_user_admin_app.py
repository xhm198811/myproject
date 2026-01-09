"""
Django用户管理后台配置
"""
from typing import Any
from fastapi_amis_admin.amis import Page
from fastapi_amis_admin.admin import admin
from fastapi_amis_admin.admin.admin import AdminApp
from fastapi import Request
import json
from ..api.django_users import router as django_users_router

def create_django_user_admin() -> dict:
    """创建Django用户管理页面配置"""
    
    page_config = {
        "type": "page",
        "title": "Django用户管理",
        "body": [
            {
                "type": "crud",
                "api": {
                    "method": "get",
                    "url": "/api/django-users/list",
                    "data": {
                        "page": "${page}",
                        "limit": "${perPage}",
                        "search": "${search}"
                    },
                    "adaptor": "return {\"status\": 0, \"msg\": \"\", \"data\": payload.data};"
                },
                "columns": [
                    {
                        "name": "id",
                        "label": "ID",
                        "type": "text",
                        "sortable": True,
                        "width": 80
                    },
                    {
                        "name": "username",
                        "label": "用户名",
                        "type": "text",
                        "sortable": True,
                        "searchable": True
                    },
                    {
                        "name": "email",
                        "label": "邮箱",
                        "type": "text",
                        "searchable": True
                    },
                    {
                        "name": "first_name",
                        "label": "名",
                        "type": "text"
                    },
                    {
                        "name": "last_name",
                        "label": "姓",
                        "type": "text"
                    },
                    {
                        "name": "is_active",
                        "label": "是否激活",
                        "type": "status",
                        "map": {
                            "true": "是",
                            "false": "否"
                        }
                    },
                    {
                        "name": "is_staff",
                        "label": "是否管理员",
                        "type": "status",
                        "map": {
                            "true": "是",
                            "false": "否"
                        }
                    },
                    {
                        "name": "is_superuser",
                        "label": "是否超级管理员",
                        "type": "status",
                        "map": {
                            "true": "是",
                            "false": "否"
                        }
                    },
                    {
                        "name": "date_joined",
                        "label": "注册时间",
                        "type": "datetime",
                        "format": "YYYY-MM-DD HH:mm:ss"
                    },
                    {
                        "name": "last_login",
                        "label": "最后登录",
                        "type": "datetime",
                        "format": "YYYY-MM-DD HH:mm:ss"
                    }
                ],
                "filter": {
                    "title": "搜索",
                    "controls": [
                        {
                            "type": "text",
                            "name": "search",
                            "label": "搜索关键词",
                            "placeholder": "搜索用户名或邮箱"
                        }
                    ]
                },
                "headerToolbar": [
                    {
                        "type": "reload"
                    },
                    {
                        "type": "columns-toggler"
                    },
                    {
                        "type": "export-excel",
                        "label": "导出Excel"
                    }
                ],
                "perPage": 20,
                "pageField": "page",
                "perPageField": "limit",
                "interval": 3000,
                "silentPolling": True,
                "stopAutoRefreshWhen": "data.items.length > 0"
            }
        ]
    }
    
    return page_config


class DjangoUserAdmin(admin.PageAdmin):
    """Django用户管理"""
    
    page_schema = admin.PageSchema(
        title="Django用户管理",
        icon="fa fa-users",
        sort=100
    )
    
    async def get_page(self, request: Request) -> Page:
        """获取用户管理页面"""
        # 创建Django用户管理页面配置
        page_config = create_django_user_admin()
        
        # 转换为amis页面
        return Page(**page_config)

# 创建管理实例
def create_django_user_admin_instance(app: AdminApp) -> DjangoUserAdmin:
    """创建Django用户管理实例"""
    return DjangoUserAdmin(app)
