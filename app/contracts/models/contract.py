from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime, date
from typing import TYPE_CHECKING
import mimetypes
import os
if TYPE_CHECKING:
    from app.projects.models.project import Project

ALLOWED_FILE_TYPES = {
    'document': ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'rtf'],
    'image': ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp', 'svg'],
    'archive': ['zip', 'rar', '7z', 'tar', 'gz'],
    'all': []
}
ALLOWED_FILE_TYPES['all'] = (
    ALLOWED_FILE_TYPES['document'] + 
    ALLOWED_FILE_TYPES['image'] + 
    ALLOWED_FILE_TYPES['archive']
)

MAX_FILE_SIZE = 20 * 1024 * 1024

def validate_file_type(file_extension: str) -> bool:
    file_ext = file_extension.lower().lstrip('.')
    return file_ext in ALLOWED_FILE_TYPES['all']

def get_mime_type(file_name: str) -> str:
    mime_type, _ = mimetypes.guess_type(file_name)
    return mime_type or 'application/octet-stream'

def get_file_category(file_extension: str) -> str:
    file_ext = file_extension.lower().lstrip('.')
    for category, extensions in ALLOWED_FILE_TYPES.items():
        if category != 'all' and file_ext in extensions:
            return category
    return 'other'

class Contract(SQLModel, table=True):
    """合同模型"""
    __tablename__ = "contracts"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    contract_no: str = Field(title="合同编号", unique=True, min_length=1, max_length=50)
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
    create_time: datetime = Field(default_factory=datetime.now, title="创建时间")
    update_time: datetime = Field(default_factory=datetime.now, title="更新时间")
    description: str = Field(default="", title="合同描述")
    
    status_logs: List["ContractStatusLog"] = Relationship(back_populates="contract")
    attachments: List["ContractAttachment"] = Relationship(back_populates="contract")
    reminders: List["ContractReminder"] = Relationship(back_populates="contract")

# 合同状态变更记录模型
class ContractStatusLog(SQLModel, table=True):
    """合同状态变更记录模型"""
    __tablename__ = "contract_status_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    contract_id: int = Field(title="合同ID", foreign_key="contracts.id")
    old_status: str = Field(title="旧状态", max_length=50)
    new_status: str = Field(title="新状态", max_length=50)
    operator: str = Field(title="操作人", max_length=50)
    operate_time: datetime = Field(default_factory=datetime.now, title="操作时间")
    remark: str = Field(default="", title="备注")
    
    # 关系
    contract: Contract = Relationship(back_populates="status_logs")



# 合同提醒模型
class ContractReminder(SQLModel, table=True):
    """合同提醒模型"""
    __tablename__ = "contract_reminders"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    contract_id: int = Field(title="合同ID", foreign_key="contracts.id")
    reminder_type: str = Field(title="提醒类型", description="到期提醒、续签提醒")
    reminder_date: date = Field(title="提醒日期")
    is_sent: bool = Field(default=False, title="是否已发送")
    send_time: Optional[datetime] = Field(title="发送时间", nullable=True)
    recipient: str = Field(title="接收人", max_length=100)
    message: str = Field(title="提醒内容", max_length=500)
    remark: str = Field(default="", title="备注")
    
    # 关系
    contract: Contract = Relationship(back_populates="reminders")

# 合同附件模型 - 增强版
class ContractAttachment(SQLModel, table=True):
    """合同附件模型"""
    __tablename__ = "contract_attachments"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    contract_id: int = Field(title="合同ID", foreign_key="contracts.id")
    file_name: str = Field(title="原始文件名", max_length=200)
    file_path: str = Field(title="文件存储路径", max_length=500)
    file_size: int = Field(title="文件大小（字节）")
    file_extension: str = Field(title="文件扩展名", max_length=20)
    mime_type: str = Field(title="MIME类型", max_length=100)
    file_category: str = Field(title="文件类别", max_length=20, description="document/image/archive/other")
    file_type: str = Field(title="附件类型", max_length=50, description="content:合同内容文件, attachment:普通附件")
    uploader: str = Field(title="上传人", max_length=50)
    upload_time: datetime = Field(default_factory=datetime.now, title="上传时间")
    download_count: int = Field(default=0, title="下载次数")
    is_active: bool = Field(default=True, title="是否有效")
    remark: str = Field(default="", title="备注")
    
    contract: Contract = Relationship(back_populates="attachments")
