"""
下载模板功能模块
提供可重用的Excel模板下载功能组件
"""
from typing import List, Dict, Any, Type, Optional, Union
from fastapi import Request, Response
from fastapi_amis_admin import admin, amis
from fastapi_amis_admin.admin import AdminAction, ModelAdmin
from fastapi_amis_admin.amis.components import Action
from fastapi_amis_admin.crud.schema import BaseApiOut
from pydantic import BaseModel, Field
from sqlalchemy.orm import DeclarativeBase
import xlsxwriter
import io
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


def add_download_template_route(admin_class: Type[ModelAdmin]) -> Type[ModelAdmin]:
    """
    为Admin类添加下载模板路由注册功能
    
    Args:
        admin_class: 要增强的Admin类
        
    Returns:
        增强后的Admin类
    """
    
    # 保存原始的register_router方法
    original_register_router = getattr(admin_class, 'register_router', None)
    
    def register_router(self, app=None):
        """重写register_router方法，添加下载模板路由"""
        # 调用原始方法（如果存在）
        if original_register_router:
            if app:
                original_register_router(self, app)
            else:
                original_register_router(self)
        
        # 添加下载模板路由
        from fastapi import APIRouter
        router = APIRouter()
        
        @router.get(f"{self.router_prefix}/download_template")
        async def download_template_endpoint(request: Request):
            """下载Excel模板"""
            try:
                # 获取下载模板动作
                download_action = next(
                    (action for action in self.custom_actions 
                     if action.name == 'download_template'), 
                    None
                )
                
                if not download_action:
                    return BaseApiOut(status=404, msg="下载模板功能未实现")
                
                # 执行下载模板
                result = await download_action.handle(request)
                return result
                
            except Exception as e:
                logger.error(f"下载模板失败: {str(e)}")
                return BaseApiOut(status=500, msg=f"下载模板失败: {str(e)}")
        
        # 将路由添加到应用
        if app and hasattr(app, 'include_router'):
            app.include_router(router)
            logger.info(f"下载模板路由已注册到应用: {self.router_prefix}/download_template")
        elif hasattr(self, 'router') and hasattr(self.router, 'include_router'):
            self.router.include_router(router)
            logger.info(f"下载模板路由已注册到管理器路由: {self.router_prefix}/download_template")
    
    admin_class.register_router = register_router
    
    return admin_class


def create_excel_template(fields: List[Dict[str, Any]], filename: str) -> bytes:
    """
    创建Excel模板文件
    
    Args:
        fields: 字段定义列表，每个字段包含name, label, type等信息
        filename: 文件名
        
    Returns:
        Excel文件的字节数据
    """
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # 创建工作表
    worksheet = workbook.add_worksheet('模板数据')
    
    # 定义格式
    header_format = workbook.add_format({
        'bold': True,
        'font_size': 12,
        'bg_color': '#4472C4',
        'font_color': 'white',
        'align': 'center',
        'valign': 'vcenter',
        'border': 1,
        'border_color': '#D3D3D3'
    })
    
    # 写入表头
    for col, field in enumerate(fields):
        worksheet.write(0, col, field.get('label', field.get('name', '')), header_format)
        
        # 设置列宽
        worksheet.set_column(col, col, max(15, len(field.get('label', field.get('name', ''))) * 2))
    
    # 添加示例数据行
    example_format = workbook.add_format({
        'bg_color': '#F2F2F2',
        'border': 1,
        'border_color': '#D3D3D3'
    })
    
    for col, field in enumerate(fields):
        field_type = field.get('type', 'string')
        field_name = field.get('name', '')
        
        # 根据字段类型提供示例数据
        if field_type == 'number':
            worksheet.write(1, col, 123.45, example_format)
        elif field_type == 'integer':
            worksheet.write(1, col, 100, example_format)
        elif field_type == 'date':
            worksheet.write(1, col, datetime.now().strftime('%Y-%m-%d'), example_format)
        elif field_type == 'boolean':
            worksheet.write(1, col, '是/否', example_format)
        elif field_name.endswith('_id') or field_name.endswith('id'):
            worksheet.write(1, col, 1, example_format)
        else:
            worksheet.write(1, col, f"示例{field.get('label', field_name)}", example_format)
    
    # 创建说明工作表
    instruction_worksheet = workbook.add_worksheet('填写说明')
    instruction_format = workbook.add_format({
        'bold': True,
        'font_size': 14,
        'bg_color': '#E7F3FF',
        'align': 'center',
        'valign': 'vcenter'
    })
    
    instruction_worksheet.write(0, 0, 'Excel导入模板填写说明', instruction_format)
    instruction_worksheet.merge_range(0, 0, 0, 3, 'Excel导入模板填写说明', instruction_format)
    
    # 添加说明内容
    instructions = [
        '',
        '【填写须知】',
        '1. 请勿修改表头，确保数据从第2行开始填写',
        '2. 带*的字段为必填项',
        '3. 日期格式：YYYY-MM-DD（如：2024-01-01）',
        '4. 数字字段请填写数字，不要包含文字',
        '5. 布尔字段请填写"是"或"否"',
        '6. 外键ID字段请填写有效的ID数字',
        '',
        '【字段说明】'
    ]
    
    # 添加字段说明
    for i, instruction in enumerate(instructions):
        instruction_worksheet.write(i + 1, 0, instruction)
    
    # 添加每个字段的详细说明
    row = len(instructions) + 1
    for field in fields:
        field_label = field.get('label', field.get('name', ''))
        field_type = field.get('type', 'string')
        is_required = '是' if field.get('required', False) else '否'
        
        type_desc = {
            'string': '文本',
            'number': '数字',
            'integer': '整数',
            'date': '日期',
            'boolean': '布尔值'
        }.get(field_type, '文本')
        
        instruction_worksheet.write(row, 0, f'【{field_label}】')
        instruction_worksheet.write(row, 1, f'类型: {type_desc}')
        instruction_worksheet.write(row, 2, f'必填: {is_required}')
        
        row += 1
    
    # 设置列宽
    instruction_worksheet.set_column(0, 0, 20)
    instruction_worksheet.set_column(1, 1, 15)
    instruction_worksheet.set_column(2, 2, 10)
    
    workbook.close()
    
    # 获取文件数据
    output.seek(0)
    return output.read()


def get_model_fields(model: Type[DeclarativeBase]) -> List[Dict[str, Any]]:
    """
    获取模型的字段定义
    
    Args:
        model: SQLAlchemy模型类
        
    Returns:
        字段定义列表
    """
    fields = []
    
    for column in model.__table__.columns:
        field_info = {
            'name': column.name,
            'label': column.info.get('label', column.name),
            'type': str(column.type).lower(),
            'required': not column.nullable and column.default is None,
        }
        
        # 转换类型
        if 'int' in field_info['type']:
            field_info['type'] = 'integer'
        elif 'decimal' in field_info['type'] or 'float' in field_info['type']:
            field_info['type'] = 'number'
        elif 'date' in field_info['type']:
            field_info['type'] = 'date'
        elif 'bool' in field_info['type']:
            field_info['type'] = 'boolean'
        else:
            field_info['type'] = 'string'
            
        fields.append(field_info)
    
    return fields