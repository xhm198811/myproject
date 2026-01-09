"""
报价记录管理页面配置
使用amis从Django API获取报价记录数据
"""

from fastapi_amis_admin.amis import Page, Table, Action, Dialog, Form, InputNumber, Select, InputText, Alert
from fastapi_amis_admin.amis.types import AmisAPI
from typing import Dict, Any

def create_quotation_record_admin() -> Dict[str, Any]:
    """创建报价记录管理页面配置"""
    
    # 报价记录表格配置
    quotation_table = {
        "type": "crud",
        "name": "quotation_records",
        "api": {
            "method": "get",
            "url": "/api/django-products/quotation-history",
            "data": {
                "page": "${page}",
                "limit": "${perPage}"
            }
        },
        "syncLocation": False,
        "columns": [
            {
                "name": "id",
                "label": "记录ID",
                "type": "text",
                "width": 80
            },
            {
                "name": "product_id",
                "label": "产品ID",
                "type": "text",
                "width": 80
            },
            {
                "name": "user_id",
                "label": "用户ID",
                "type": "text",
                "width": 80
            },
            {
                "name": "final_price",
                "label": "最终价格(元)",
                "type": "text",
                "width": 120,
                "tpl": "¥${final_price}"
            },
            {
                "name": "thickness",
                "label": "厚度(mm)",
                "type": "text",
                "width": 100
            },
            {
                "name": "width",
                "label": "宽度(mm)",
                "type": "text",
                "width": 100
            },
            {
                "name": "coating_process",
                "label": "表面处理工艺",
                "type": "text",
                "width": 120
            },
            {
                "name": "perforation_rate",
                "label": "穿孔率(%)",
                "type": "text",
                "width": 100
            },
            {
                "name": "created_at",
                "label": "创建时间",
                "type": "datetime",
                "width": 150
            }
        ],
        "headerToolbar": [
            {
                "type": "columns-toggler",
                "align": "left"
            },
            {
                "type": "pagination",
                "align": "right"
            }
        ],
        "footerToolbar": [
            {
                "type": "pagination",
                "align": "right"
            },
            {
                "type": "statistics",
                "align": "left"
            }
        ]
    }
    
    # 页面配置
    page = {
        "type": "page",
        "title": "报价记录管理",
        "data": {
            "sourceInfo": "数据来源: Django API"
        },
        "body": [
            {
                "type": "alert",
                "level": "info",
                "body": "本报价记录管理页面数据来源于Django API后台，实时同步报价记录信息。",
                "showIcon": True
            },
            quotation_table
        ]
    }
    
    return page