from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from ..models.quote import QuoteStatus

class QuoteBase(BaseModel):
    """报价单基础模型"""
    quote_no: str = Field(..., description="报价单编号")
    customer_name: str = Field(..., description="客户名称")
    project_name: Optional[str] = Field(None, description="项目名称")
    total_amount: float = Field(0, description="总金额")
    status: str = Field(QuoteStatus.DRAFT, description="状态")
    validity_days: int = Field(30, description="有效期天数")
    description: Optional[str] = Field(None, description="描述")
    created_by: Optional[str] = Field("admin", description="创建人")

class QuoteCreate(QuoteBase):
    """创建报价单"""
    pass

class QuoteUpdate(BaseModel):
    """更新报价单"""
    customer_name: Optional[str] = Field(None, description="客户名称")
    project_name: Optional[str] = Field(None, description="项目名称")
    total_amount: Optional[float] = Field(None, description="总金额")
    status: Optional[str] = Field(None, description="状态")
    validity_days: Optional[int] = Field(None, description="有效期天数")
    description: Optional[str] = Field(None, description="描述")

class QuoteRead(QuoteBase):
    """报价单详情"""
    id: int = Field(..., description="报价单ID")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: Optional[datetime] = Field(None, description="更新时间")
    
    class Config:
        from_attributes = True

class QuoteBatchCreate(BaseModel):
    """批量创建报价单"""
    quotes: List[QuoteCreate] = Field(..., description="报价单列表")

class QuoteBatchResult(BaseModel):
    """批量操作结果"""
    success_count: int = Field(0, description="成功数量")
    failed_count: int = Field(0, description="失败数量")
    failed_items: List[dict] = Field(default_factory=list, description="失败项目")
    errors: List[str] = Field(default_factory=list, description="错误信息")

class QuoteItemBase(BaseModel):
    """报价单项基础模型"""
    quote_id: int = Field(..., description="报价单ID")
    product_name: str = Field(..., description="产品名称")
    quantity: int = Field(1, description="数量")
    unit_price: float = Field(0, description="单价")
    total_price: float = Field(0, description="总价")
    remark: Optional[str] = Field(None, description="备注")

class QuoteItemCreate(QuoteItemBase):
    """创建报价单项"""
    pass

class QuoteItemUpdate(BaseModel):
    """更新报价单项"""
    product_name: Optional[str] = Field(None, description="产品名称")
    quantity: Optional[int] = Field(None, description="数量")
    unit_price: Optional[float] = Field(None, description="单价")
    total_price: Optional[float] = Field(None, description="总价")
    remark: Optional[str] = Field(None, description="备注")

class QuoteItemRead(QuoteItemBase):
    """报价单项详情"""
    id: int = Field(..., description="报价单项ID")
    
    class Config:
        from_attributes = True

class QuoteItemBatchCreate(BaseModel):
    """批量创建报价单项"""
    items: List[QuoteItemCreate] = Field(..., description="报价单项列表")

class QuoteItemBatchResult(BaseModel):
    """批量操作结果"""
    success_count: int = Field(0, description="成功数量")
    failed_count: int = Field(0, description="失败数量")
    failed_items: List[dict] = Field(default_factory=list, description="失败项目")
    errors: List[str] = Field(default_factory=list, description="错误信息")