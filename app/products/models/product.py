from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime

# 产品模型 - 使用Django的products_product表
class Product(SQLModel, table=True):
    """产品模型"""
    __tablename__ = "products_product"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    name: str = Field(title="产品名称", min_length=1, max_length=200)
    thickness: float = Field(title="板材厚度(mm)", ge=0.5, le=5.0)
    final_price: float = Field(title="最终价格", ge=0.01)
    created_at: datetime = Field(title="创建时间")
    updated_at: datetime = Field(title="更新时间")
    backing_type_id: Optional[int] = Field(title="背衬类型ID", foreign_key="products_boardtype.id", nullable=True)
    material_series_id: Optional[int] = Field(title="材料系列ID", foreign_key="products_materialseries.id", nullable=True)
    
    # 关系
    models: List["ProductModel"] = Relationship(back_populates="product")
    quotations: List["QuotationRecord"] = Relationship(back_populates="product")
    backing_type: "BoardType" = Relationship()
    material_series: "MaterialSeries" = Relationship()

# 产品模型 - 使用Django的products_productmodel表
class ProductModel(SQLModel, table=True):
    """产品模型文件"""
    __tablename__ = "products_productmodel"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    name: str = Field(title="模型名称", max_length=200)
    product_id: int = Field(title="产品ID", foreign_key="products_product.id")
    model_file: str = Field(title="模型文件路径", max_length=100)
    created_at: datetime = Field(title="创建时间")
    
    # 关系
    product: Product = Relationship(back_populates="models")

# 材料系列 - 使用Django的products_materialseries表
class MaterialSeries(SQLModel, table=True):
    """材料系列"""
    __tablename__ = "products_materialseries"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    name: str = Field(title="材料系列名称", max_length=50, unique=True)

# 材料配置 - 使用Django的products_materialconfig表
class MaterialConfig(SQLModel, table=True):
    """材料配置"""
    __tablename__ = "products_materialconfig"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    name: str = Field(title="材质名称", max_length=50, unique=True)
    coefficient: float = Field(title="材质系数", ge=0.1, le=2.0)
    thickness_choices: str = Field(title="厚度选项(mm)", default="2.0,2.5,3.0", max_length=100)

# 背衬类型 - 使用Django的products_boardtype表
class BoardType(SQLModel, table=True):
    """背衬类型"""
    __tablename__ = "products_boardtype"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    name: str = Field(title="背衬名称", max_length=50, unique=True)
    min_thickness: float = Field(title="最小厚度(mm)", ge=0.5)
    max_thickness: float = Field(title="最大厚度(mm)", le=5.0)

# 报价记录 - 使用Django的products_quotationrecord表
class QuotationRecord(SQLModel, table=True):
    """报价记录"""
    __tablename__ = "products_quotationrecord"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    product_id: int = Field(title="产品ID", foreign_key="products_product.id")
    user_id: int = Field(title="用户ID", foreign_key="auth_user.id")
    aluminum_ingot_price: float = Field(title="铝锭价格(元/吨)", ge=0)
    thickness: float = Field(title="板材厚度(mm)", ge=0.5, le=5.0)
    backing_type_id: Optional[int] = Field(title="背衬类型ID", foreign_key="products_boardtype.id", nullable=True)
    material_config_id: int = Field(title="材质配置ID", foreign_key="products_materialconfig.id")
    width: Optional[float] = Field(title="宽度(mm)", nullable=True)
    coating_process: str = Field(title="表面处理工艺", max_length=50)
    perforation_rate: float = Field(title="穿孔率(%)", ge=0, le=100)
    board_structure: str = Field(title="板型结构", max_length=20, default="standard")
    accessories: bool = Field(title="是否需要配件", default=False)
    final_price: float = Field(title="最终价格", ge=0.01)
    created_at: datetime = Field(default_factory=datetime.now, title="创建时间")
    
    # 关系
    product: Product = Relationship(back_populates="quotations")
    user: "User" = Relationship()
    backing_type: Optional[BoardType] = Relationship()
    material_config: MaterialConfig = Relationship()

# 铝锭价格
class AluminumPrice(SQLModel, table=True):
    """铝锭价格"""
    __tablename__ = "aluminum_prices"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    date: datetime = Field(title="日期")
    price: float = Field(title="价格", ge=0)
    created_at: datetime = Field(default_factory=datetime.now, title="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, title="更新时间")