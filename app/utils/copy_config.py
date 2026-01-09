"""
复制功能配置模块
为各个Admin类提供复制功能的配置
"""

# 合同管理复制配置
contract_copy_fields = [
    'contract_no', 'name', 'type', 'status', 'signing_date',
    'expiry_date', 'party_a', 'party_b', 'amount'
]

contract_field_formatters = {
    'contract_no': lambda x: f"合同编号:{x}" if x else "",
    'name': lambda x: f"合同名称:{x}" if x else "",
    'type': lambda x: {"purchase": "采购合同", "sales": "销售合同"}.get(x, x),
    'status': lambda x: {
        'draft': '草稿', 'pending': '待签署', 'signed': '已签署',
        'executing': '执行中', 'completed': '已完成', 'cancelled': '已取消'
    }.get(x, x),
    'signing_date': lambda x: x.strftime('%Y-%m-%d') if x else "",
    'expiry_date': lambda x: x.strftime('%Y-%m-%d') if x else "",
    'amount': lambda x: f"¥{x:,.2f}" if x else "未填写",
}

# 产品管理复制配置
product_copy_fields = [
    'name', 'thickness', 'final_price'
]

product_field_formatters = {
    'name': lambda x: f"产品:{x}" if x else "",
    'thickness': lambda x: f"{x}mm" if x else "",
    'final_price': lambda x: f"¥{x:,.2f}" if x else "",
}

# 项目管理复制配置
project_copy_fields = [
    'name', 'status', 'project_manager', 'amount'
]

project_field_formatters = {
    'name': lambda x: f"项目:{x}" if x else "",
    'status': lambda x: {
        'pending': '待开始', 'in_progress': '进行中',
        'completed': '已完成', 'delayed': '延期', 'cancelled': '已取消'
    }.get(x, x),
    'project_manager': lambda x: f"负责人:{x}" if x else "",
    'amount': lambda x: f"¥{x:,.2f}" if x else "",
}

# 项目阶段复制配置
project_stage_copy_fields = [
    'name', 'status', 'planned_start_time', 'planned_end_time'
]

project_stage_field_formatters = {
    'name': lambda x: f"阶段:{x}" if x else "",
    'status': lambda x: {
        'pending': '未开始', 'in_progress': '进行中',
        'completed': '已完成', 'delayed': '延期'
    }.get(x, x),
    'planned_start_time': lambda x: x.strftime('%Y-%m-%d') if x else "",
    'planned_end_time': lambda x: x.strftime('%Y-%m-%d') if x else "",
}

# 项目任务复制配置
project_task_copy_fields = [
    'name', 'status', 'progress', 'priority', 'assignee'
]

project_task_field_formatters = {
    'name': lambda x: f"任务:{x}" if x else "",
    'status': lambda x: {
        'todo': '待处理', 'in_progress': '进行中',
        'review': '审核中', 'completed': '已完成'
    }.get(x, x),
    'progress': lambda x: f"进度:{x}%" if x is not None else "",
    'priority': lambda x: {
        'low': '低', 'medium': '中', 'high': '高', 'urgent': '紧急'
    }.get(x, x),
    'assignee': lambda x: f"执行人:{x}" if x else "",
}

# 项目成员复制配置
project_member_copy_fields = [
    'role', 'permissions'
]

project_member_field_formatters = {
    'role': lambda x: f"角色:{x}" if x else "",
    'permissions': lambda x: f"权限:{x}" if x else "",
}

# 项目文档复制配置
project_document_copy_fields = [
    'name', 'category', 'version', 'uploader'
]

project_document_field_formatters = {
    'name': lambda x: f"文档:{x}" if x else "",
    'category': lambda x: f"分类:{x}" if x else "",
    'version': lambda x: f"版本:{x}" if x else "",
    'uploader': lambda x: f"上传者:{x}" if x else "",
}



# 材料配置复制配置
material_config_copy_fields = [
    'name', 'coefficient', 'thickness_choices'
]

material_config_field_formatters = {
    'name': lambda x: f"材料:{x}" if x else "",
    'coefficient': lambda x: f"系数:{x}" if x is not None else "",
    'thickness_choices': lambda x: f"厚度:{x}" if x else "",
}

# 背衬类型复制配置
board_type_copy_fields = [
    'name', 'min_thickness', 'max_thickness'
]

board_type_field_formatters = {
    'name': lambda x: f"类型:{x}" if x else "",
    'min_thickness': lambda x: f"最小:{x}mm" if x else "",
    'max_thickness': lambda x: f"最大:{x}mm" if x else "",
}

# 产品型号复制配置
product_model_copy_fields = [
    'name', 'version'
]

product_model_field_formatters = {
    'name': lambda x: f"型号:{x}" if x else "",
    'version': lambda x: f"版本:{x}" if x else "",
}

# 报价记录复制配置
quotation_record_copy_fields = [
    'product_name', 'thickness', 'final_price'
]

quotation_record_field_formatters = {
    'product_name': lambda x: f"产品:{x}" if x else "",
    'thickness': lambda x: f"{x}mm" if x else "",
    'final_price': lambda x: f"¥{x:,.2f}" if x else "",
}

# 铝锭价格复制配置
aluminum_price_copy_fields = [
    'date', 'price'
]

aluminum_price_field_formatters = {
    'date': lambda x: x.strftime('%Y-%m-%d') if x else "",
    'price': lambda x: f"¥{x:,.2f}/吨" if x else "",
}

# 用户复制配置
user_copy_fields = [
    'username', 'email', 'is_active'
]

user_field_formatters = {
    'username': lambda x: f"用户:{x}" if x else "",
    'email': lambda x: f"邮箱:{x}" if x else "",
    'is_active': lambda x: "状态:启用" if x else "状态:禁用",
}

# 获取复制配置的辅助函数
def get_copy_config(admin_name: str):
    """根据Admin名称获取复制配置"""
    configs = {
        'ContractAdmin': {
            'quick_copy_fields': contract_copy_fields,
            'field_formatters': contract_field_formatters,
        },
        'ProductAdmin': {
            'quick_copy_fields': product_copy_fields,
            'field_formatters': product_field_formatters,
        },
        'ProjectAdmin': {
            'quick_copy_fields': project_copy_fields,
            'field_formatters': project_field_formatters,
        },
        'ProjectStageAdmin': {
            'quick_copy_fields': project_stage_copy_fields,
            'field_formatters': project_stage_field_formatters,
        },
        'ProjectTaskAdmin': {
            'quick_copy_fields': project_task_copy_fields,
            'field_formatters': project_task_field_formatters,
        },
        'ProjectMemberAdmin': {
            'quick_copy_fields': project_member_copy_fields,
            'field_formatters': project_member_field_formatters,
        },
        'ProjectDocumentAdmin': {
            'quick_copy_fields': project_document_copy_fields,
            'field_formatters': project_document_field_formatters,
        },
        'MaterialConfigAdmin': {
            'quick_copy_fields': material_config_copy_fields,
            'field_formatters': material_config_field_formatters,
        },
        'BoardTypeAdmin': {
            'quick_copy_fields': board_type_copy_fields,
            'field_formatters': board_type_field_formatters,
        },
        'ProductModelAdmin': {
            'quick_copy_fields': product_model_copy_fields,
            'field_formatters': product_model_field_formatters,
        },
        'QuotationRecordAdmin': {
            'quick_copy_fields': quotation_record_copy_fields,
            'field_formatters': quotation_record_field_formatters,
        },
        'AluminumPriceAdmin': {
            'quick_copy_fields': aluminum_price_copy_fields,
            'field_formatters': aluminum_price_field_formatters,
        },
        'UserAdmin': {
            'quick_copy_fields': user_copy_fields,
            'field_formatters': user_field_formatters,
        },
    }
    return configs.get(admin_name, {})
