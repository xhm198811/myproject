"""
Django产品管理页面配置
使用amis从Django API获取产品数据
修复网络错误问题
"""

from fastapi_amis_admin.amis import Page, Table, Action, Dialog, Form, InputNumber, Select, InputText, Alert
from fastapi_amis_admin.amis.types import AmisAPI
from typing import Dict, Any

def create_django_product_admin() -> Dict[str, Any]:
    """创建Django产品管理页面配置"""
    
    # 产品表格配置
    product_table = {
        "type": "crud",
        "name": "products",
        "api": {
            "method": "get",
            "url": "/api/django-products/list",
            "data": {
                "page": "${page}",
                "limit": "${perPage}",
                "search": "${search}"
            },
            "headers": {
                "Content-Type": "application/json",
                "Accept": "application/json"
            }
        },
        "syncLocation": False,
        "columns": [
            {
                "name": "id",
                "label": "产品ID",
                "type": "text",
                "width": 80
            },
            {
                "name": "name",
                "label": "产品名称",
                "type": "text",
                "searchable": True
            },
            {
                "name": "thickness",
                "label": "厚度(mm)",
                "type": "text",
                "width": 100
            },
            {
                "name": "material_series",
                "label": "材质系列",
                "type": "text",
                "width": 120
            },
            {
                "name": "backing_type",
                "label": "背衬类型",
                "type": "text",
                "width": 120
            },
            {
                "name": "final_price",
                "label": "价格(元)",
                "type": "text",
                "width": 100,
                "tpl": "¥${final_price}"
            },
            {
                "name": "created_at",
                "label": "创建时间",
                "type": "datetime",
                "width": 150
            },
            {
                "type": "operation",
                "label": "操作",
                "width": 180,
                "buttons": [
                    {
                        "type": "button",
                        "label": "详情",
                        "level": "link",
                        "actionType": "drawer",
                        "drawer": {
                            "title": "产品详情",
                            "size": "md",
                            "body": {
                                "type": "form",
                                "initApi": {
                                    "method": "get",
                                    "url": "/api/django-products/detail/${id}",
                                    "headers": {
                                        "Content-Type": "application/json",
                                        "Accept": "application/json"
                                    }
                                },
                                "controls": [
                                    {
                                        "type": "static",
                                        "name": "id",
                                        "label": "产品ID"
                                    },
                                    {
                                        "type": "static",
                                        "name": "name",
                                        "label": "产品名称"
                                    },
                                    {
                                        "type": "static",
                                        "name": "thickness",
                                        "label": "厚度(mm)"
                                    },
                                    {
                                        "type": "static",
                                        "name": "material_series",
                                        "label": "材质系列"
                                    },
                                    {
                                        "type": "static",
                                        "name": "backing_type",
                                        "label": "背衬类型"
                                    },
                                    {
                                        "type": "static",
                                        "name": "final_price",
                                        "label": "价格(元)",
                                        "tpl": "¥${final_price}"
                                    },
                                    {
                                        "type": "divider"
                                    }
                                ]
                            }
                        }
                    }
                ]
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
        ],
        "messages": {
            "fetchFailed": "获取数据失败，请检查网络连接或联系管理员",
            "saveSuccess": "保存成功",
            "saveFailed": "保存失败"
        }
    }
    
    # 页面配置
    page = {
        "type": "page",
        "title": "Django产品管理",
        "data": {
            "isDjangoSource": True,
            "sourceInfo": "数据来源: Django API"
        },
        "body": [
            {
                "type": "alert",
                "level": "info",
                "body": "本产品管理页面数据来源于Django API后台，实时同步产品信息。",
                "showIcon": True
            },
            {
                "type": "form",
                "title": "搜索条件",
                "mode": "inline",
                "className": "m-b-md",
                "controls": [
                    {
                        "type": "text",
                        "name": "search",
                        "placeholder": "搜索产品名称",
                        "clearable": True
                    },
                    {
                        "type": "button",
                        "label": "搜索",
                        "level": "primary",
                        "actionType": "reload",
                        "target": "products"
                    },
                    {
                        "type": "button",
                        "label": "重置",
                        "actionType": "reset",
                        "onEvent": {
                            "click": {
                                "actions": [
                                    {
                                        "actionType": "clear",
                                        "componentId": "search"
                                    },
                                    {
                                        "actionType": "reload",
                                        "componentId": "products"
                                    }
                                ]
                            }
                        }
                    }
                ]
            },
            product_table
        ]
    }
    
    return page

def create_django_product_form() -> Dict[str, Any]:
    """创建Django产品表单配置"""
    
    form = {
        "type": "form",
        "title": "产品信息",
        "body": [
            {
                "type": "input-text",
                "name": "name",
                "label": "产品名称",
                "required": True,
                "placeholder": "请输入产品名称"
            },
            {
                "type": "input-number",
                "name": "thickness",
                "label": "厚度(mm)",
                "precision": 2,
                "min": 0.5,
                "max": 5.0,
                "step": 0.1,
                "required": True
            },
            {
                "type": "select",
                "name": "material_series",
                "label": "材质系列",
                "source": {
                    "method": "get",
                    "url": "/api/django-products/materials",
                    "headers": {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                },
                "required": True,
                "placeholder": "请选择材质系列"
            },
            {
                "type": "select",
                "name": "backing_type",
                "label": "背衬类型",
                "source": {
                    "method": "get",
                    "url": "/api/django-products/board-types",
                    "headers": {
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                },
                "placeholder": "请选择背衬类型"
            },
            {
                "type": "input-number",
                "name": "final_price",
                "label": "价格(元)",
                "precision": 2,
                "min": 0,
                "step": 0.01,
                "required": True
            }
        ]
    }
    
    return form



