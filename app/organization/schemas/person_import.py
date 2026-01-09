from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, validator
from datetime import date, datetime


class PersonImportItem(BaseModel):
    """人员导入项"""
    name: str = Field(..., description="姓名", max_length=100)
    code: str = Field(..., description="人员编码", max_length=50)
    organization_id: Optional[int] = Field(None, description="所属组织ID")
    position: Optional[str] = Field(None, description="职位", max_length=100)
    job_level: Optional[str] = Field(None, description="职级", max_length=50)
    gender: Optional[str] = Field(None, description="性别: male, female, other", max_length=10)
    birth_date: Optional[str] = Field(None, description="出生日期 YYYY-MM-DD")
    id_card: Optional[str] = Field(None, description="身份证号", max_length=18)
    phone: Optional[str] = Field(None, description="手机号码", max_length=20)
    email: Optional[str] = Field(None, description="邮箱", max_length=100)
    address: Optional[str] = Field(None, description="住址", max_length=255)
    emergency_contact: Optional[str] = Field(None, description="紧急联系人", max_length=100)
    emergency_phone: Optional[str] = Field(None, description="紧急联系电话", max_length=20)
    hire_date: Optional[str] = Field(None, description="入职日期 YYYY-MM-DD")
    probation_end_date: Optional[str] = Field(None, description="试用期结束日期 YYYY-MM-DD")
    contract_start_date: Optional[str] = Field(None, description="合同开始日期 YYYY-MM-DD")
    contract_end_date: Optional[str] = Field(None, description="合同结束日期 YYYY-MM-DD")
    employment_status: Optional[str] = Field("active", description="在职状态", max_length=20)
    work_location: Optional[str] = Field(None, description="工作地点", max_length=100)
    education: Optional[str] = Field(None, description="学历", max_length=50)
    major: Optional[str] = Field(None, description="专业", max_length=100)
    school: Optional[str] = Field(None, description="毕业院校", max_length=100)
    skills: Optional[str] = Field(None, description="技能", max_length=500)
    experience: Optional[str] = Field(None, description="工作经历", max_length=1000)
    
    @validator('code')
    def validate_code(cls, v):
        if not v or not v.strip():
            raise ValueError('人员编码不能为空')
        return v.strip()
    
    @validator('name')
    def validate_name(cls, v):
        if not v or not v.strip():
            raise ValueError('姓名不能为空')
        return v.strip()
    
    @validator('phone')
    def validate_phone(cls, v):
        if v and v.strip():
            phone = v.strip()
            if not phone.isdigit() or len(phone) != 11:
                raise ValueError('手机号码必须是11位数字')
            return phone
        return v
    
    @validator('email')
    def validate_email(cls, v):
        if v and v.strip():
            email = v.strip()
            if '@' not in email:
                raise ValueError('邮箱格式不正确')
            return email
        return v
    
    @validator('id_card')
    def validate_id_card(cls, v):
        if v and v.strip():
            id_card = v.strip()
            if len(id_card) not in [15, 18]:
                raise ValueError('身份证号必须是15位或18位')
            return id_card
        return v
    
    @validator('gender')
    def validate_gender(cls, v):
        if v and v not in ['male', 'female', 'other']:
            raise ValueError('性别必须是 male, female 或 other')
        return v
    
    @validator('employment_status')
    def validate_employment_status(cls, v):
        if v and v not in ['active', 'probation', 'leave', 'retired', 'resigned']:
            raise ValueError('在职状态必须是 active, probation, leave, retired 或 resigned')
        return v


class PersonBatchImportRequest(BaseModel):
    """批量导入请求"""
    data: List[PersonImportItem] = Field(..., description="人员数据列表")
    import_mode: str = Field("append", description="导入模式: append(追加), update(更新), skip(跳过)")
    skip_duplicates: bool = Field(True, description="是否跳过重复数据")
    
    @validator('import_mode')
    def validate_import_mode(cls, v):
        if v not in ['append', 'update', 'skip']:
            raise ValueError('导入模式必须是 append, update 或 skip')
        return v


class PersonBatchImportResult(BaseModel):
    """批量导入结果"""
    total_count: int = Field(..., description="总记录数")
    success_count: int = Field(..., description="成功导入数")
    failed_count: int = Field(..., description="失败数")
    skipped_count: int = Field(..., description="跳过数")
    success_rate: float = Field(..., description="成功率")
    errors: List[Dict[str, Any]] = Field(default_factory=list, description="错误列表")
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_count": 100,
                "success_count": 95,
                "failed_count": 3,
                "skipped_count": 2,
                "success_rate": 95.0,
                "errors": [
                    {
                        "row_index": 5,
                        "field": "phone",
                        "error_message": "手机号码必须是11位数字",
                        "data": {"name": "张三", "phone": "123"}
                    }
                ]
            }
        }


class PersonImportError(BaseModel):
    """导入错误信息"""
    row_index: int = Field(..., description="行号")
    field: Optional[str] = Field(None, description="错误字段")
    error_message: str = Field(..., description="错误信息")
    data: Dict[str, Any] = Field(..., description="原始数据")
