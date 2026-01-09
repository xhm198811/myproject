"""
报价记录管理后台配置 - Django API版本
"""

from typing import Any
from fastapi_amis_admin.amis import Page
from fastapi_amis_admin.admin import admin
from fastapi_amis_admin.admin.admin import AdminApp
from fastapi import Request
import json
from ..api.django_products import router as django_products_router
from .quotation_record_admin import create_quotation_record_admin

class QuotationRecordAdmin(admin.PageAdmin):
    """报价记录管理"""
    
    page_schema = admin.PageSchema(
        title="报价记录管理",
        icon="fa fa-file-invoice",
        sort=120
    )
    
    async def get_page(self, request: Request) -> Page:
        """获取报价记录管理页面"""
        # 创建报价记录管理页面配置
        page_config = create_quotation_record_admin()
        
        # 转换为amis页面
        return Page(**page_config)

# 创建管理实例
def create_quotation_record_admin_instance(app: AdminApp) -> QuotationRecordAdmin:
    """创建报价记录管理实例"""
    return QuotationRecordAdmin(app)