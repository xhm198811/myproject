from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import remote
from typing import Optional, List, TYPE_CHECKING
from datetime import datetime

if TYPE_CHECKING:
    from .person import Person


class Organization(SQLModel, table=True):
    __tablename__ = "organizations"
    
    id: Optional[int] = Field(default=None, primary_key=True, title="ID")
    name: str = Field(max_length=200, index=True, title="组织名称")
    code: str = Field(max_length=50, unique=True, index=True, title="组织编码")
    type: str = Field(max_length=50, default="department", title="组织类型")
    
    parent_id: Optional[int] = Field(
        default=None,
        foreign_key="organizations.id",
        title="上级组织ID"
    )
    
    level: int = Field(default=1, title="组织层级")
    sort_order: int = Field(default=0, title="排序")
    
    leader_id: Optional[int] = Field(
        default=None,
        title="负责人ID"
    )
    
    description: Optional[str] = Field(default=None, max_length=500, title="组织描述")
    address: Optional[str] = Field(default=None, max_length=255, title="地址")
    phone: Optional[str] = Field(default=None, max_length=20, title="联系电话")
    email: Optional[str] = Field(default=None, max_length=100, title="联系邮箱")
    
    is_active: bool = Field(default=True, title="是否启用")
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        title="创建时间"
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        title="更新时间"
    )
    
    children: List["Organization"] = Relationship(
        back_populates="parent",
        sa_relationship_kwargs={
            "primaryjoin": "Organization.id == remote(Organization.parent_id)",
            "order_by": "Organization.sort_order"
        }
    )
    
    parent: Optional["Organization"] = Relationship(
        back_populates="children",
        sa_relationship_kwargs={
            "primaryjoin": "Organization.parent_id == remote(Organization.id)"
        }
    )
    
    persons: List["Person"] = Relationship(
        back_populates="organization",
        sa_relationship_kwargs={
            "primaryjoin": "Organization.id == Person.organization_id"
        }
    )


class OrganizationRole(SQLModel, table=True):
    __tablename__ = "organization_roles"
    
    id: Optional[int] = Field(default=None, primary_key=True, title="ID")
    name: str = Field(max_length=100, index=True, title="角色名称")
    code: str = Field(max_length=50, unique=True, index=True, title="角色编码")
    description: Optional[str] = Field(default=None, max_length=500, title="角色描述")
    
    permissions: Optional[dict] = Field(
        default=None,
        sa_column=Column(JSON),
        title="角色权限配置"
    )
    
    is_active: bool = Field(default=True, title="是否启用")
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now()),
        title="创建时间"
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now()),
        title="更新时间"
    )
