from .product import (
    ProductBase, ProductCreate, ProductUpdate, ProductRead,
    ProductModelBase, ProductModelCreate, ProductModelUpdate, ProductModelRead,
    MaterialConfigBase, MaterialConfigCreate, MaterialConfigUpdate, MaterialConfigRead,
    BoardTypeBase, BoardTypeCreate, BoardTypeUpdate, BoardTypeRead,
    QuotationRecordBase, QuotationRecordCreate, QuotationRecordUpdate, QuotationRecordRead,
    AluminumPriceBase, AluminumPriceCreate, AluminumPriceUpdate, AluminumPriceRead,
    ProductBatchCreate, ProductBatchResult,
    MaterialConfigBatchCreate, MaterialConfigBatchResult,
    BoardTypeBatchCreate, BoardTypeBatchResult
)

__all__ = [
    "ProductBase", "ProductCreate", "ProductUpdate", "ProductRead",
    "ProductModelBase", "ProductModelCreate", "ProductModelUpdate", "ProductModelRead",
    "MaterialConfigBase", "MaterialConfigCreate", "MaterialConfigUpdate", "MaterialConfigRead",
    "BoardTypeBase", "BoardTypeCreate", "BoardTypeUpdate", "BoardTypeRead",
    "QuotationRecordBase", "QuotationRecordCreate", "QuotationRecordUpdate", "QuotationRecordRead",
    "AluminumPriceBase", "AluminumPriceCreate", "AluminumPriceUpdate", "AluminumPriceRead",
    "ProductBatchCreate", "ProductBatchResult",
    "MaterialConfigBatchCreate", "MaterialConfigBatchResult",
    "BoardTypeBatchCreate", "BoardTypeBatchResult"
]