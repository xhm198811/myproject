"""
产品管理后台配置 - Django API版本
"""
from typing import Any
from fastapi_amis_admin.amis import Page
from fastapi_amis_admin.admin import admin
from fastapi_amis_admin.admin.admin import AdminApp
from fastapi import Request
import json
from ..api.django_products import router as django_products_router
from .django_product_admin import create_django_product_admin

class DjangoProductAdmin(admin.PageAdmin):
    """Django产品管理"""
    
    page_schema = admin.PageSchema(
        title="Django产品管理",
        icon="fa fa-cube",
        sort=110
    )
    
    async def get_page(self, request: Request) -> Page:
        """获取产品管理页面"""
        # 创建Django产品管理页面配置
        page_config = create_django_product_admin()
        
        # 转换为amis页面
        return Page(**page_config)

# 创建管理实例
def create_django_product_admin_instance(app: AdminApp) -> DjangoProductAdmin:
    """创建Django产品管理实例"""
    return DjangoProductAdmin(app)