from typing import List, Dict, Any
import logging
from fastapi_amis_admin import admin, amis
from fastapi_amis_admin.models.fields import Field
from fastapi_amis_admin.admin import AdminAction
from fastapi_amis_admin.amis.components import Action, ActionType
from fastapi_amis_admin.admin.admin import FormAdmin
from fastapi_amis_admin.crud.schema import BaseApiOut
from fastapi_amis_admin.utils.translation import i18n as _

# 假设你的工具模块路径正确，保留原有导入
from ..utils.clipboard_copy_action import add_clipboard_copy_actions, ClipboardCopyAction, QuickClipboardCopyAction
from ..utils.copy_config import get_copy_config

# 配置日志格式，方便排查问题
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 导入数据模型和Schema（保持原有导入）
from .models import Product, ProductModel, MaterialConfig, BoardType, QuotationRecord, AluminumPrice
from .schemas import (
    ProductCreate, ProductUpdate, ProductRead,
    MaterialConfigCreate, MaterialConfigUpdate, MaterialConfigRead,
    BoardTypeCreate, BoardTypeUpdate, BoardTypeRead
)

# 产品Admin
class ProductAdmin(admin.ModelAdmin):
    """产品管理"""
    page_schema = amis.PageSchema(label="产品管理", icon="fa fa-product-hunt")  # 补充图标更直观
    model = Product
    # 补充常用搜索字段，提升后台搜索体验
    search_fields = [Product.name, Product.thickness]
    list_filter = [Product.thickness, Product.final_price]  # 补充过滤字段
    list_display = [
        Product.id,
        Product.name,  # 产品名称
        Product.thickness,  # 厚度
        Product.final_price,  # 最终价格
        Product.created_at  # 创建时间
    ]
    # 默认按创建时间降序排列
    list_order = [-Product.created_at]
    update_exclude = {"created_at"}
    create_exclude = {"created_at", "updated_at"}

# 材料配置Admin
class MaterialConfigAdmin(admin.ModelAdmin):
    """材料配置管理"""
    page_schema = amis.PageSchema(label="材料配置管理", icon="fa fa-cogs")
    model = MaterialConfig
    search_fields = [MaterialConfig.name]  # 按名称搜索
    list_filter = [MaterialConfig.coefficient]  # 按系数过滤
    list_display = [
        MaterialConfig.id,
        MaterialConfig.name,  # 配置名称
        MaterialConfig.coefficient,  # 系数
        MaterialConfig.thickness_choices  # 厚度选项
    ]
    list_order = [-MaterialConfig.id]
    update_exclude = set()
    create_exclude = set()

# 板型配置Admin
class BoardTypeAdmin(admin.ModelAdmin):
    """背衬类型管理"""
    page_schema = amis.PageSchema(label="背衬类型管理", icon="fa fa-th")
    model = BoardType
    search_fields = [BoardType.name]  # 按名称搜索
    list_filter = [BoardType.min_thickness, BoardType.max_thickness]  # 按厚度范围过滤
    list_display = [
        BoardType.id,
        BoardType.name,  # 板型名称
        BoardType.min_thickness,  # 最小厚度
        BoardType.max_thickness  # 最大厚度
    ]
    list_order = [-BoardType.id]
    update_exclude = set()
    create_exclude = set()

# 产品型号Admin
class ProductModelAdmin(admin.ModelAdmin):
    """产品模型管理"""
    page_schema = amis.PageSchema(label="产品模型管理", icon="fa fa-cube")
    model = ProductModel
    search_fields = [ProductModel.name, ProductModel.product_id]  # 按名称/产品ID搜索
    list_filter = [ProductModel.product_id]  # 按产品过滤
    list_display = [
        ProductModel.id,
        ProductModel.name,  # 型号名称
        ProductModel.product_id,  # 关联产品ID
        ProductModel.model_file,  # 模型文件
        ProductModel.created_at  # 创建时间
    ]
    list_order = [-ProductModel.created_at]
    update_exclude = {"created_at"}
    create_exclude = {"created_at"}

# 报价记录Admin
class QuotationRecordAdmin(admin.ModelAdmin):
    """报价记录管理"""
    page_schema = amis.PageSchema(label="报价记录管理", icon="fa fa-file-text-o")
    model = QuotationRecord
    # 按产品ID/用户ID/价格搜索
    search_fields = [QuotationRecord.product_id, QuotationRecord.user_id, QuotationRecord.final_price]
    list_filter = [QuotationRecord.product_id, QuotationRecord.user_id, QuotationRecord.created_at]
    list_display = [
        QuotationRecord.id,
        QuotationRecord.product_id,  # 产品ID
        QuotationRecord.user_id,  # 用户ID
        QuotationRecord.thickness,  # 厚度
        QuotationRecord.final_price,  # 最终报价
        QuotationRecord.created_at  # 报价时间
    ]
    list_order = [-QuotationRecord.created_at]  # 按报价时间降序
    update_exclude = {"created_at"}
    create_exclude = {"created_at"}

# 铝价记录Admin
class AluminumPriceAdmin(admin.ModelAdmin):
    """铝锭价格管理"""
    page_schema = amis.PageSchema(label="铝锭价格管理", icon="fa fa-line-chart")
    model = AluminumPrice
    search_fields = [AluminumPrice.date, AluminumPrice.price]  # 按日期/价格搜索
    list_filter = [AluminumPrice.date]  # 按日期过滤
    list_display = [
        AluminumPrice.id,
        AluminumPrice.date,  # 价格日期
        AluminumPrice.price,  # 铝锭价格
        AluminumPrice.created_at  # 记录创建时间
    ]
    list_order = [-AluminumPrice.date]  # 按日期降序
    update_exclude = {"created_at"}
    create_exclude = {"created_at", "updated_at"}


# 暂时注释掉复制功能装饰器，先让服务器能正常启动
# 注意：启用前需确保 get_copy_config 函数能正确返回配置，否则会导致启动失败
# 使用装饰器为所有Admin类添加复制功能
# ProductAdmin = add_clipboard_copy_actions(
#     ProductAdmin,
#     quick_copy_fields=get_copy_config('ProductAdmin').get('quick_copy_fields', []),
#     field_formatters=get_copy_config('ProductAdmin').get('field_formatters', {})
# )
#
# MaterialConfigAdmin = add_clipboard_copy_actions(
#     MaterialConfigAdmin,
#     quick_copy_fields=get_copy_config('MaterialConfigAdmin').get('quick_copy_fields', []),
#     field_formatters=get_copy_config('MaterialConfigAdmin').get('field_formatters', {})
# )
#
# BoardTypeAdmin = add_clipboard_copy_actions(
#     BoardTypeAdmin,
#     quick_copy_fields=get_copy_config('BoardTypeAdmin').get('quick_copy_fields', []),
#     field_formatters=get_copy_config('BoardTypeAdmin').get('field_formatters', {})
# )
#
# ProductModelAdmin = add_clipboard_copy_actions(
#     ProductModelAdmin,
#     quick_copy_fields=get_copy_config('ProductModelAdmin').get('quick_copy_fields', []),
#     field_formatters=get_copy_config('ProductModelAdmin').get('field_formatters', {})
# )
#
# QuotationRecordAdmin = add_clipboard_copy_actions(
#     QuotationRecordAdmin,
#     quick_copy_fields=get_copy_config('QuotationRecordAdmin').get('quick_copy_fields', []),
#     field_formatters=get_copy_config('QuotationRecordAdmin').get('field_formatters', {})
# )
#
# AluminumPriceAdmin = add_clipboard_copy_actions(
#     AluminumPriceAdmin,
#     quick_copy_fields=get_copy_config('AluminumPriceAdmin').get('quick_copy_fields', []),
#     field_formatters=get_copy_config('AluminumPriceAdmin').get('field_formatters', {})
# )