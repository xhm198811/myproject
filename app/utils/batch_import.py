"""
通用批量导入工具类
支持Excel文件解析和数据验证
"""
from typing import List, Dict, Any, Optional, Callable, Type
import openpyxl
import xlrd
import io
import logging

logger = logging.getLogger(__name__)


class BatchImportConfig:
    """批量导入配置"""
    
    def __init__(
        self,
        model_name: str,
        fields: List[Dict[str, Any]],
        start_row: int = 2,
        max_rows: int = 100
    ):
        self.model_name = model_name
        self.fields = fields
        self.start_row = start_row
        self.max_rows = max_rows


class BatchImportResult:
    """批量导入结果"""
    
    def __init__(self):
        self.success_count = 0
        self.failed_count = 0
        self.errors = []
        self.imported_ids = []
    
    def add_success(self, item_id: Any):
        self.success_count += 1
        self.imported_ids.append(item_id)
    
    def add_error(self, message: str):
        self.failed_count += 1
        self.errors.append(message)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success_count": self.success_count,
            "failed_count": self.failed_count,
            "errors": self.errors,
            "imported_ids": self.imported_ids
        }


class ExcelParser:
    """Excel文件解析器"""
    
    @staticmethod
    def parse_file(
        file_content: bytes,
        file_extension: str,
        config: BatchImportConfig
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """
        解析Excel文件
        
        Args:
            file_content: 文件内容
            file_extension: 文件扩展名 (xlsx 或 xls)
            config: 导入配置
            
        Returns:
            (数据列表, 错误列表)
        """
        errors = []
        data_list = []
        
        try:
            if file_extension == 'xlsx':
                workbook = openpyxl.load_workbook(io.BytesIO(file_content))
                sheet = workbook.active
                rows = list(sheet.iter_rows(min_row=config.start_row, values_only=True))
            elif file_extension == 'xls':
                workbook = xlrd.open_workbook(file_contents=file_content, formatting_info=False, on_demand=True)
                sheet = workbook.sheet_by_index(0)
                rows = [sheet.row_values(i) for i in range(config.start_row - 1, sheet.nrows)]
            else:
                return [], ["不支持的文件格式"]
            
            for row_idx, row in enumerate(rows, config.start_row):
                if len(row) < len(config.fields):
                    errors.append(f"第{row_idx}行：数据不完整，需要{len(config.fields)}列")
                    continue
                
                item_data = {}
                row_errors = []
                
                for field_idx, field_config in enumerate(config.fields):
                    field_name = field_config['name']
                    field_type = field_config.get('type', 'string')
                    required = field_config.get('required', False)
                    value = row[field_idx]
                    
                    try:
                        parsed_value = ExcelParser._parse_value(value, field_type, required)
                        
                        if required and parsed_value is None:
                            row_errors.append(f"{field_name}不能为空")
                        elif parsed_value is not None:
                            item_data[field_name] = parsed_value
                            
                    except ValueError as e:
                        row_errors.append(f"{field_name}格式错误: {str(e)}")
                
                if row_errors:
                    errors.append(f"第{row_idx}行：{'; '.join(row_errors)}")
                else:
                    data_list.append(item_data)
                
                if len(data_list) >= config.max_rows:
                    break
            
            return data_list, errors
            
        except Exception as e:
            logger.error(f"解析Excel文件失败: {str(e)}", exc_info=True)
            return [], [f"解析文件失败: {str(e)}"]
    
    @staticmethod
    def _parse_value(value: Any, field_type: str, required: bool) -> Any:
        """解析字段值"""
        if value is None:
            if required:
                raise ValueError("字段不能为空")
            return None
        
        value_str = str(value).strip()
        if not value_str:
            if required:
                raise ValueError("字段不能为空")
            return None
        
        if field_type == 'string':
            return value_str
        elif field_type == 'int':
            return int(float(value_str))
        elif field_type == 'float':
            return float(value_str)
        elif field_type == 'bool':
            return value_str.lower() in ['true', '1', 'yes', '是']
        else:
            return value_str


class BatchImporter:
    """批量导入器"""
    
    def __init__(self, config: BatchImportConfig):
        self.config = config
        self.parser = ExcelParser()
    
    def import_from_file(
        self,
        file_content: bytes,
        file_extension: str,
        create_func: Callable[[Dict[str, Any]], Any]
    ) -> BatchImportResult:
        """
        从文件批量导入数据
        
        Args:
            file_content: 文件内容
            file_extension: 文件扩展名
            create_func: 创建记录的函数
            
        Returns:
            导入结果
        """
        result = BatchImportResult()
        
        data_list, parse_errors = self.parser.parse_file(
            file_content, file_extension, self.config
        )
        
        result.errors.extend(parse_errors)
        
        for item_data in data_list:
            try:
                created_item = create_func(item_data)
                if created_item:
                    item_id = getattr(created_item, 'id', None)
                    result.add_success(item_id)
                else:
                    result.add_error(f"创建记录失败: {item_data}")
            except Exception as e:
                logger.error(f"创建记录失败: {str(e)}", exc_info=True)
                result.add_error(f"创建记录失败: {str(e)}")
        
        return result
    
    def get_template(self) -> List[Dict[str, Any]]:
        """获取导入模板"""
        template = []
        for field in self.config.fields:
            template.append({
                "name": field['name'],
                "label": field.get('label', field['name']),
                "type": field.get('type', 'string'),
                "required": field.get('required', False),
                "description": field.get('description', '')
            })
        return template
