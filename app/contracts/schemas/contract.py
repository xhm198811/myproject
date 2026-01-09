from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime, date
from pydantic import validator

# 合同基本信息模型
class ContractBase(SQLModel):
    """合同基础模型"""
    contract_no: str = Field(title="合同编号", min_length=1, max_length=50)
    name: str = Field(title="合同名称", min_length=1, max_length=200)
    type: str = Field(title="合同类型", max_length=50)
    signing_date: date = Field(title="签订日期")
    expiry_date: date = Field(title="到期日期")
    party_a: str = Field(title="甲方", max_length=100)
    party_b: str = Field(title="乙方", max_length=100)
    amount: float = Field(title="合同金额", ge=0)
    status: str = Field(title="合同状态", default="draft", description="草稿、待审核、已生效、已过期、已终止")
    department: str = Field(title="所属部门", max_length=50)
    creator: str = Field(title="创建人", max_length=50)
    description: str = Field(default="", title="合同描述")
    
    @validator('expiry_date')
    def expiry_date_after_signing_date(cls, v, values):
        if 'signing_date' in values and v <= values['signing_date']:
            raise ValueError('到期日期必须晚于签订日期')
        return v

class ContractCreate(ContractBase):
    """创建合同模型"""
    pass

class ContractUpdate(SQLModel):
    """更新合同模型"""
    contract_no: Optional[str] = Field(None, title="合同编号", min_length=1, max_length=50)
    name: Optional[str] = Field(None, title="合同名称", min_length=1, max_length=200)
    type: Optional[str] = Field(None, title="合同类型", max_length=50)
    signing_date: Optional[date] = Field(None, title="签订日期")
    expiry_date: Optional[date] = Field(None, title="到期日期")
    party_a: Optional[str] = Field(None, title="甲方", max_length=100)
    party_b: Optional[str] = Field(None, title="乙方", max_length=100)
    amount: Optional[float] = Field(None, title="合同金额", ge=0)
    status: Optional[str] = Field(None, title="合同状态", description="草稿、待审核、已生效、已过期、已终止")
    department: Optional[str] = Field(None, title="所属部门", max_length=50)
    creator: Optional[str] = Field(None, title="创建人", max_length=50)
    description: Optional[str] = Field(None, title="合同描述")

class ContractRead(ContractBase):
    """读取合同模型"""
    id: int
    create_time: datetime
    update_time: datetime

# 批量导入合同模型
class ContractBatchCreate(SQLModel):
    """批量创建合同模型"""
    contracts: List[ContractCreate] = Field(title="合同列表")

class ContractBatchResult(SQLModel):
    """批量创建结果模型"""
    success_count: int = Field(title="成功数量")
    error_count: int = Field(title="错误数量")
    errors: List[dict] = Field(title="错误信息", default_factory=list)

# 合同状态变更记录模型
class ContractStatusLogBase(SQLModel):
    """合同状态变更记录基础模型"""
    contract_id: int = Field(title="合同ID")
    old_status: str = Field(title="旧状态", max_length=50)
    new_status: str = Field(title="新状态", max_length=50)
    operator: str = Field(title="操作人", max_length=50)
    remark: str = Field(default="", title="备注")

class ContractStatusLogCreate(ContractStatusLogBase):
    """创建合同状态变更记录模型"""
    pass

class ContractStatusLogRead(ContractStatusLogBase):
    """读取合同状态变更记录模型"""
    id: int
    operate_time: datetime

# 合同附件模型
class ContractAttachmentBase(SQLModel):
    """合同附件基础模型"""
    contract_id: int = Field(title="合同ID")
    file_name: str = Field(title="文件名", max_length=200)
    file_path: str = Field(title="文件路径", max_length=500)
    file_size: int = Field(title="文件大小")
    uploader: str = Field(title="上传人", max_length=50)
    remark: str = Field(default="", title="备注")

class ContractAttachmentCreate(ContractAttachmentBase):
    """创建合同附件模型"""
    pass

class ContractAttachmentRead(ContractAttachmentBase):
    """读取合同附件模型"""
    id: int
    upload_time: datetime