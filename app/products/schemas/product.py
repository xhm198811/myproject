from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel, Field
from sqlmodel import SQLModel

# 产品相关Schema
class ProductBase(SQLModel):
    name: str = Field(title="产品名称", min_length=1, max_length=200)
    code: str = Field(title="产品编码", max_length=50)
    category: str = Field(title="产品类别", max_length=50)
    description: str = Field(title="产品描述", default="")
    thickness: float = Field(title="板材厚度(mm)", ge=0.5, le=5.0)
    material_series: str = Field(title="材料系列", max_length=50)
    backing_type: str = Field(title="背衬类型", max_length=50)
    final_price: float = Field(title="最终价格", ge=0.01)
    unit: str = Field(title="单位", default="件", max_length=20)
    status: str = Field(title="产品状态", default="active")

class ProductCreate(ProductBase):
    pass

class ProductUpdate(SQLModel):
    name: Optional[str] = Field(title="产品名称", min_length=1, max_length=200, default=None)
    code: Optional[str] = Field(title="产品编码", max_length=50, default=None)
    category: Optional[str] = Field(title="产品类别", max_length=50, default=None)
    description: Optional[str] = Field(title="产品描述", default=None)
    thickness: Optional[float] = Field(title="板材厚度(mm)", ge=0.5, le=5.0, default=None)
    material_series: Optional[str] = Field(title="材料系列", max_length=50, default=None)
    backing_type: Optional[str] = Field(title="背衬类型", max_length=50, default=None)
    final_price: Optional[float] = Field(title="最终价格", ge=0.01, default=None)
    unit: Optional[str] = Field(title="单位", max_length=20, default="件")
    status: Optional[str] = Field(title="产品状态", default=None)

class ProductRead(ProductBase):
    id: int
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None

# 产品模型相关Schema
class ProductModelBase(SQLModel):
    name: str = Field(title="模型名称", max_length=200)
    product_id: int = Field(title="产品ID")
    model_file: str = Field(title="模型文件路径", max_length=500)
    file_size: int = Field(title="文件大小")
    version: str = Field(title="版本号", default="1.0.0")

class ProductModelCreate(ProductModelBase):
    pass

class ProductModelUpdate(SQLModel):
    name: Optional[str] = Field(title="模型名称", max_length=200, default=None)
    product_id: Optional[int] = Field(title="产品ID", default=None)
    model_file: Optional[str] = Field(title="模型文件路径", max_length=500, default=None)
    file_size: Optional[int] = Field(title="文件大小", default=None)
    version: Optional[str] = Field(title="版本号", default=None)

class ProductModelRead(ProductModelBase):
    id: int
    created_at: datetime
    created_by: Optional[int] = None

# 材料配置相关Schema
class MaterialConfigBase(SQLModel):
    name: str = Field(title="材质名称", max_length=50)
    coefficient: float = Field(title="材质系数", ge=0.1, le=2.0)
    thickness_choices: str = Field(title="厚度选项(mm)", default="2.0,2.5,3.0", max_length=100)

class MaterialConfigCreate(MaterialConfigBase):
    pass

class MaterialConfigUpdate(SQLModel):
    name: Optional[str] = Field(title="材质名称", max_length=50, default=None)
    coefficient: Optional[float] = Field(title="材质系数", ge=0.1, le=2.0, default=None)
    thickness_choices: Optional[str] = Field(title="厚度选项(mm)", default=None, max_length=100)

class MaterialConfigRead(MaterialConfigBase):
    id: int
    created_at: datetime
    updated_at: datetime

# 背衬类型相关Schema
class BoardTypeBase(SQLModel):
    name: str = Field(title="背衬名称", max_length=50)
    min_thickness: float = Field(title="最小厚度(mm)", ge=0.5)
    max_thickness: float = Field(title="最大厚度(mm)", le=5.0)

class BoardTypeCreate(BoardTypeBase):
    pass

class BoardTypeUpdate(SQLModel):
    name: Optional[str] = Field(title="背衬名称", max_length=50, default=None)
    min_thickness: Optional[float] = Field(title="最小厚度(mm)", ge=0.5, default=None)
    max_thickness: Optional[float] = Field(title="最大厚度(mm)", le=5.0, default=None)

class BoardTypeRead(BoardTypeBase):
    id: int
    created_at: datetime
    updated_at: datetime

# 报价记录相关Schema
class QuotationRecordBase(SQLModel):
    product_id: int = Field(title="产品ID")
    user_id: int = Field(title="用户ID")
    aluminum_ingot_price: float = Field(title="铝锭价格(元/吨)", ge=0)
    thickness: float = Field(title="板材厚度(mm)", ge=0.5, le=5.0)
    backing_type_id: Optional[int] = Field(title="背衬类型ID", default=None)
    material_config_id: int = Field(title="材质配置ID")
    width: Optional[float] = Field(title="宽度(mm)", default=None)
    coating_process: str = Field(title="表面处理工艺", max_length=50)
    perforation_rate: float = Field(title="穿孔率(%)", ge=0, le=100)
    board_structure: str = Field(title="板型结构", max_length=20, default="standard")
    accessories: bool = Field(title="是否需要配件", default=False)
    final_price: float = Field(title="最终价格", ge=0.01)

class QuotationRecordCreate(QuotationRecordBase):
    pass

class QuotationRecordUpdate(SQLModel):
    product_id: Optional[int] = Field(title="产品ID", default=None)
    user_id: Optional[int] = Field(title="用户ID", default=None)
    aluminum_ingot_price: Optional[float] = Field(title="铝锭价格(元/吨)", ge=0, default=None)
    thickness: Optional[float] = Field(title="板材厚度(mm)", ge=0.5, le=5.0, default=None)
    backing_type_id: Optional[int] = Field(title="背衬类型ID", default=None)
    material_config_id: Optional[int] = Field(title="材质配置ID", default=None)
    width: Optional[float] = Field(title="宽度(mm)", default=None)
    coating_process: Optional[str] = Field(title="表面处理工艺", max_length=50, default=None)
    perforation_rate: Optional[float] = Field(title="穿孔率(%)", ge=0, le=100, default=None)
    board_structure: Optional[str] = Field(title="板型结构", max_length=20, default=None)
    accessories: Optional[bool] = Field(title="是否需要配件", default=None)
    final_price: Optional[float] = Field(title="最终价格", ge=0.01, default=None)

class QuotationRecordRead(QuotationRecordBase):
    id: int
    created_at: datetime

# 铝锭价格相关Schema
class AluminumPriceBase(SQLModel):
    date: datetime = Field(title="日期")
    price: float = Field(title="价格", ge=0)

class AluminumPriceCreate(AluminumPriceBase):
    pass

class AluminumPriceUpdate(SQLModel):
    date: Optional[datetime] = Field(title="日期", default=None)
    price: Optional[float] = Field(title="价格", ge=0, default=None)

class AluminumPriceRead(AluminumPriceBase):
    id: int
    created_at: datetime
    updated_at: datetime

# 批量导入相关Schema
class ProductBatchCreate(BaseModel):
    products: List[ProductCreate] = Field(title="产品列表", min_items=1)

class ProductBatchResult(BaseModel):
    success_count: int = Field(title="成功数量")
    failed_count: int = Field(title="失败数量")
    failed_items: List[dict] = Field(title="失败项目", default=[])
    errors: List[str] = Field(title="错误信息", default=[])

class MaterialConfigBatchCreate(BaseModel):
    configs: List[MaterialConfigCreate] = Field(title="材料配置列表", min_items=1)

class MaterialConfigBatchResult(BaseModel):
    success_count: int = Field(title="成功数量")
    failed_count: int = Field(title="失败数量")
    failed_items: List[dict] = Field(title="失败项目", default=[])
    errors: List[str] = Field(title="错误信息", default=[])

class BoardTypeBatchCreate(BaseModel):
    board_types: List[BoardTypeCreate] = Field(title="背衬类型列表", min_items=1)

class BoardTypeBatchResult(BaseModel):
    success_count: int = Field(title="成功数量")
    failed_count: int = Field(title="失败数量")
    failed_items: List[dict] = Field(title="失败项目", default=[])
    errors: List[str] = Field(title="错误信息", default=[])