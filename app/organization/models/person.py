from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Date, JSON
from sqlalchemy.sql import func
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime, date

if TYPE_CHECKING:
    from .organization import Organization
    from ..users.models.user import User


class Person(SQLModel, table=True):
    __tablename__ = "persons"
    
    id: Optional[int] = Field(default=None, primary_key=True, title="ID")
    
    name: str = Field(max_length=100, title="姓名")
    code: str = Field(max_length=50, unique=True, index=True, title="人员编码")
    
    user_id: Optional[int] = Field(
        default=None,
        foreign_key="auth_user.id",
        title="关联的用户ID"
    )
    
    organization_id: Optional[int] = Field(
        default=None,
        foreign_key="organizations.id",
        title="所属组织ID"
    )
    
    position: Optional[str] = Field(default=None, max_length=100, title="职位")
    job_level: Optional[str] = Field(default=None, max_length=50, title="职级")
    
    gender: Optional[str] = Field(default=None, max_length=10, title="性别")
    birth_date: Optional[date] = Field(default=None, title="出生日期")
    
    id_card: Optional[str] = Field(default=None, max_length=18, title="身份证号")
    phone: Optional[str] = Field(default=None, max_length=20, title="手机号码")
    email: Optional[str] = Field(default=None, max_length=100, title="邮箱")
    
    address: Optional[str] = Field(default=None, max_length=255, title="住址")
    emergency_contact: Optional[str] = Field(default=None, max_length=100, title="紧急联系人")
    emergency_phone: Optional[str] = Field(default=None, max_length=20, title="紧急联系电话")
    
    hire_date: Optional[date] = Field(default=None, title="入职日期")
    probation_end_date: Optional[date] = Field(default=None, title="试用期结束日期")
    contract_start_date: Optional[date] = Field(default=None, title="合同开始日期")
    contract_end_date: Optional[date] = Field(default=None, title="合同结束日期")
    
    employment_status: str = Field(
        default="active",
        max_length=20,
        title="在职状态"
    )
    
    work_location: Optional[str] = Field(default=None, max_length=100, title="工作地点")
    
    education: Optional[str] = Field(default=None, max_length=50, title="学历")
    major: Optional[str] = Field(default=None, max_length=100, title="专业")
    school: Optional[str] = Field(default=None, max_length=100, title="毕业院校")
    
    skills: Optional[str] = Field(default=None, max_length=500, title="技能")
    experience: Optional[str] = Field(default=None, max_length=1000, title="工作经历")
    
    avatar: Optional[str] = Field(default=None, max_length=255, title="头像URL")
    
    is_active: bool = Field(default=True, title="是否启用")
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        title="创建时间"
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        title="更新时间"
    )
    
    user: Optional["User"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Person.user_id == User.id"
        }
    )
    
    organization: Optional["Organization"] = Relationship(
        back_populates="persons",
        sa_relationship_kwargs={
            "primaryjoin": "Person.organization_id == Organization.id"
        }
    )


class PersonRoleLink(SQLModel, table=True):
    __tablename__ = "person_roles"
    
    person_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            ForeignKey("persons.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    organization_role_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            ForeignKey("organization_roles.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: Optional[int] = Field(default=None, foreign_key="auth_user.id")


class PersonDepartmentHistory(SQLModel, table=True):
    __tablename__ = "person_department_history"
    
    id: Optional[int] = Field(default=None, primary_key=True, title="ID")
    person_id: Optional[int] = Field(
        sa_column=Column(Integer, ForeignKey("persons.id", ondelete="CASCADE")),
        title="人员ID"
    )
    from_organization_id: Optional[int] = Field(
        sa_column=Column(Integer, ForeignKey("organizations.id")),
        title="原部门ID"
    )
    to_organization_id: Optional[int] = Field(
        sa_column=Column(Integer, ForeignKey("organizations.id")),
        title="新部门ID"
    )
    
    change_date: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        title="调动日期"
    )
    reason: Optional[str] = Field(default=None, max_length=500, title="调动原因")
    remark: Optional[str] = Field(default=None, max_length=500, title="备注")
    
    created_by: Optional[int] = Field(default=None, foreign_key="auth_user.id", title="创建人")
    
    person: Optional["Person"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "PersonDepartmentHistory.person_id == Person.id"
        }
    )
    
    from_organization: Optional["Organization"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "PersonDepartmentHistory.from_organization_id == Organization.id"
        }
    )
    
    to_organization: Optional["Organization"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "PersonDepartmentHistory.to_organization_id == Organization.id"
        }
    )
