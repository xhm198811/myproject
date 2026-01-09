from sqlmodel import SQLModel, Field, Relationship
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from typing import Optional, List
from datetime import datetime


class UserRoleLink(SQLModel, table=True):
    __tablename__ = "user_roles"
    
    user_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            ForeignKey("auth_user.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    role_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    assigned_by: Optional[int] = Field(default=None, foreign_key="auth_user.id")


class RolePermissionLink(SQLModel, table=True):
    __tablename__ = "role_permissions"
    
    role_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            ForeignKey("roles.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    permission_id: Optional[int] = Field(
        sa_column=Column(
            Integer,
            ForeignKey("permissions.id", ondelete="CASCADE"),
            primary_key=True
        )
    )
    granted_at: datetime = Field(default_factory=datetime.utcnow)
    granted_by: Optional[int] = Field(default=None, foreign_key="auth_user.id")


class User(SQLModel, table=True):
    __tablename__ = "auth_user"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(unique=True, index=True, max_length=150)
    email: str = Field(unique=True, index=True, max_length=254)
    password: str = Field(max_length=255)
    
    first_name: str = Field(default="", max_length=150)
    last_name: str = Field(default="", max_length=150)
    phone: Optional[str] = Field(default=None, max_length=20)
    department: Optional[str] = Field(default=None, max_length=100)
    avatar: Optional[str] = Field(default=None, max_length=255)
    
    employee_id: Optional[str] = Field(default=None, max_length=50, unique=True, index=True)
    job_title: Optional[str] = Field(default=None, max_length=100)
    hire_date: Optional[datetime] = Field(default=None)
    termination_date: Optional[datetime] = Field(default=None)
    manager_id: Optional[int] = Field(default=None, foreign_key="auth_user.id")
    employment_status: str = Field(default="active", max_length=20)
    
    is_active: bool = Field(default=True)
    is_staff: bool = Field(default=False)
    is_superuser: bool = Field(default=False)
    
    date_joined: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    last_login: Optional[datetime] = Field(default=None)
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
    
    roles: List["Role"] = Relationship(
        back_populates="users",
        link_model=UserRoleLink,
        sa_relationship_kwargs={
            "primaryjoin": "User.id == UserRoleLink.user_id",
            "secondaryjoin": "UserRoleLink.role_id == Role.id"
        }
    )
    
    activity_logs: List["UserActivityLog"] = Relationship(back_populates="user")
    login_history: List["UserLoginHistory"] = Relationship(back_populates="user")
    assigned_tasks: List["ProjectTask"] = Relationship(back_populates="assignee_user")
    
    managed_employees: List["User"] = Relationship(
        back_populates="manager",
        sa_relationship_kwargs={
            "primaryjoin": "User.id == remote(User.manager_id)"
        }
    )
    manager: Optional["User"] = Relationship(
        back_populates="managed_employees",
        sa_relationship_kwargs={
            "primaryjoin": "User.manager_id == remote(User.id)"
        }
    )


class Role(SQLModel, table=True):
    __tablename__ = "roles"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    display_name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=500)
    
    is_active: bool = Field(default=True)
    is_system: bool = Field(default=False)
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    updated_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    )
    
    users: List["User"] = Relationship(
        back_populates="roles",
        link_model=UserRoleLink,
        sa_relationship_kwargs={
            "primaryjoin": "Role.id == UserRoleLink.role_id",
            "secondaryjoin": "UserRoleLink.user_id == User.id"
        }
    )
    
    permissions: List["Permission"] = Relationship(
        back_populates="roles",
        link_model=RolePermissionLink,
        sa_relationship_kwargs={
            "primaryjoin": "Role.id == RolePermissionLink.role_id",
            "secondaryjoin": "RolePermissionLink.permission_id == Permission.id"
        }
    )


class Permission(SQLModel, table=True):
    __tablename__ = "permissions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, index=True, max_length=100)
    codename: str = Field(unique=True, index=True, max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    
    module: Optional[str] = Field(default=None, max_length=50)
    action: Optional[str] = Field(default=None, max_length=50)
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    roles: List["Role"] = Relationship(
        back_populates="permissions",
        link_model=RolePermissionLink,
        sa_relationship_kwargs={
            "primaryjoin": "Permission.id == RolePermissionLink.permission_id",
            "secondaryjoin": "RolePermissionLink.role_id == Role.id"
        }
    )


class UserActivityLog(SQLModel, table=True):
    __tablename__ = "user_activity_logs"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        sa_column=Column(Integer, ForeignKey("auth_user.id", ondelete="CASCADE"))
    )
    action: str = Field(max_length=100)
    description: Optional[str] = Field(default=None, max_length=500)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    
    meta_data: Optional[dict] = Field(default=None, sa_column=Column(Text))
    
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    
    user: "User" = Relationship(back_populates="activity_logs")


class UserLoginHistory(SQLModel, table=True):
    __tablename__ = "user_login_history"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: Optional[int] = Field(
        sa_column=Column(Integer, ForeignKey("auth_user.id", ondelete="CASCADE"))
    )
    login_time: datetime = Field(
        sa_column=Column(DateTime(timezone=True), server_default=func.now())
    )
    logout_time: Optional[datetime] = Field(default=None)
    ip_address: Optional[str] = Field(default=None, max_length=45)
    user_agent: Optional[str] = Field(default=None, max_length=500)
    login_status: str = Field(max_length=20, default="success")
    failure_reason: Optional[str] = Field(default=None, max_length=500)
    
    user: "User" = Relationship(back_populates="login_history")
