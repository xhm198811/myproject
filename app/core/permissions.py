from fastapi import Depends, HTTPException, status
from sqlmodel import Session, select
from typing import List, Optional
import logging

from app.core.db import get_db
from app.core.auth import get_current_user
from app.users.models import User, Role, Permission

logger = logging.getLogger(__name__)


async def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """获取当前激活的用户"""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="账户已被禁用"
        )
    return current_user


async def get_current_staff_user(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取当前员工用户"""
    if not current_user.is_staff:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要员工权限"
        )
    return current_user


async def get_current_superuser(
    current_user: User = Depends(get_current_active_user)
) -> User:
    """获取当前超级用户"""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级用户权限"
        )
    return current_user


class RequirePermission:
    """权限检查依赖"""
    
    def __init__(self, required_permission: str):
        self.required_permission = required_permission
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        # 超级用户拥有所有权限
        if current_user.is_superuser:
            return current_user
        
        # 获取用户的所有角色
        user_roles = db.exec(
            select(Role)
            .where(Role.id.in_([role.id for role in current_user.roles]))
            .where(Role.is_active == True)
        ).all()
        
        # 获取所有角色的权限
        permissions = set()
        for role in user_roles:
            for permission in role.permissions:
                if permission.is_active:
                    permissions.add(permission.code)
        
        # 检查是否拥有所需权限
        if self.required_permission not in permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要权限: {self.required_permission}"
            )
        
        return current_user


class RequireAnyPermission:
    """检查是否拥有任意一个权限"""
    
    def __init__(self, permissions: List[str]):
        self.permissions = permissions
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        # 超级用户拥有所有权限
        if current_user.is_superuser:
            return current_user
        
        # 获取用户的所有角色
        user_roles = db.exec(
            select(Role)
            .where(Role.id.in_([role.id for role in current_user.roles]))
            .where(Role.is_active == True)
        ).all()
        
        # 获取所有角色的权限
        user_permissions = set()
        for role in user_roles:
            for permission in role.permissions:
                if permission.is_active:
                    user_permissions.add(permission.code)
        
        # 检查是否拥有任意一个所需权限
        if not any(perm in user_permissions for perm in self.permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下权限之一: {', '.join(self.permissions)}"
            )
        
        return current_user


class RequireRole:
    """角色检查依赖"""
    
    def __init__(self, required_role: str):
        self.required_role = required_role
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        # 超级用户拥有所有角色
        if current_user.is_superuser:
            return current_user
        
        # 检查用户是否拥有所需角色
        user_roles = [role.code for role in current_user.roles if role.is_active]
        
        if self.required_role not in user_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要角色: {self.required_role}"
            )
        
        return current_user


class RequireAnyRole:
    """检查是否拥有任意一个角色"""
    
    def __init__(self, roles: List[str]):
        self.roles = roles
    
    async def __call__(
        self,
        current_user: User = Depends(get_current_active_user),
        db: Session = Depends(get_db)
    ) -> User:
        # 超级用户拥有所有角色
        if current_user.is_superuser:
            return current_user
        
        # 检查用户是否拥有任意一个所需角色
        user_roles = [role.code for role in current_user.roles if role.is_active]
        
        if not any(role in user_roles for role in self.roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"需要以下角色之一: {', '.join(self.roles)}"
            )
        
        return current_user


def has_permission(user: User, permission_code: str, db: Session) -> bool:
    """检查用户是否拥有指定权限"""
    # 超级用户拥有所有权限
    if user.is_superuser:
        return True
    
    # 获取用户的所有角色
    user_roles = db.exec(
        select(Role)
        .where(Role.id.in_([role.id for role in user.roles]))
        .where(Role.is_active == True)
    ).all()
    
    # 获取所有角色的权限
    permissions = set()
    for role in user_roles:
        for permission in role.permissions:
            if permission.is_active:
                permissions.add(permission.code)
    
    return permission_code in permissions


def has_role(user: User, role_code: str) -> bool:
    """检查用户是否拥有指定角色"""
    # 超级用户拥有所有角色
    if user.is_superuser:
        return True
    
    user_roles = [role.code for role in user.roles if role.is_active]
    return role_code in user_roles


def get_user_permissions(user: User, db: Session) -> List[str]:
    """获取用户的所有权限"""
    # 超级用户拥有所有权限
    if user.is_superuser:
        all_permissions = db.exec(select(Permission).where(Permission.is_active == True)).all()
        return [perm.code for perm in all_permissions]
    
    # 获取用户的所有角色
    user_roles = db.exec(
        select(Role)
        .where(Role.id.in_([role.id for role in user.roles]))
        .where(Role.is_active == True)
    ).all()
    
    # 获取所有角色的权限
    permissions = set()
    for role in user_roles:
        for permission in role.permissions:
            if permission.is_active:
                permissions.add(permission.code)
    
    return list(permissions)


def get_user_roles(user: User) -> List[str]:
    """获取用户的所有角色"""
    if user.is_superuser:
        return ["superuser"]
    
    return [role.code for role in user.roles if role.is_active]
