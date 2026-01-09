from sqlalchemy import Column, Integer, String, Float, DateTime, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlmodel import SQLModel, Field, Relationship
from datetime import datetime
from typing import Optional, List
import enum

class QuoteStatus(str, enum.Enum):
    """报价单状态"""
    DRAFT = "草稿"
    PENDING = "待审核"
    APPROVED = "已批准"
    REJECTED = "已拒绝"
    EXPIRED = "已过期"

class Quote(SQLModel, table=True):
    """报价单主表"""
    __tablename__ = "quotes"
    
    id: int = Field(default=None, primary_key=True, nullable=False)
    quote_no: str = Field(title="报价单编号", unique=True, min_length=1, max_length=50)
    customer_name: str = Field(title="客户名称", min_length=1, max_length=100)
    project_name: str = Field(default="", title="项目名称", max_length=200)
    total_amount: float = Field(default=0, title="总金额", ge=0)
    status: str = Field(default=QuoteStatus.DRAFT, title="状态", max_length=20)
    validity_days: int = Field(default=30, title="有效期天数")
    description: str = Field(default="", title="描述")
    created_by: str = Field(default="", title="创建人", max_length=50)
    created_at: datetime = Field(default_factory=datetime.now, title="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, title="更新时间")
    
    # 关联关系
    items: List["QuoteItem"] = Relationship(back_populates="quote")

class QuoteItem(SQLModel, table=True):
    """报价单项表"""
    __tablename__ = "quote_items"
    
    id: int = Field(default=None, primary_key=True, nullable=False)
    quote_id: int = Field(title="报价单ID", foreign_key="quotes.id")
    product_name: str = Field(title="产品名称", min_length=1, max_length=200)
    quantity: int = Field(default=1, title="数量", ge=1)
    unit_price: float = Field(default=0, title="单价", ge=0)
    total_price: float = Field(default=0, title="总价", ge=0)
    remark: str = Field(default="", title="备注")
    
    # 关联关系
    quote: Optional["Quote"] = Relationship(back_populates="items")