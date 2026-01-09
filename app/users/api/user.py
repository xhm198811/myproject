from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List
from datetime import datetime, timedelta

from ..models.user import User, Role, Permission, UserRoleLink, RolePermissionLink
from ...core.db import get_async_db
from ...core.auth import (
    verify_password,
    get_password_hash,
    get_current_user,
    get_user_from_db
)

from .schemas import (
    UserCreate,
    UserResponse,
    UserUpdate,
    ChangePasswordRequest
)

router = APIRouter(prefix="/users", tags=["users"])


async def get_current_user_roles(db: AsyncSession, user_id: int) -> List[str]:
    result = await db.execute(
        select(Role.name)
        .join(UserRoleLink, Role.id == UserRoleLink.role_id)
        .where(UserRoleLink.user_id == user_id)
    )
    return [row[0] for row in result.all()]








@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_async_db)
):
    try:
        existing_user = await get_user_from_db(db, user_data.username)
        if existing_user:
            raise HTTPException(status_code=400, detail="用户名已存在")
        
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_email = result.scalar_one_or_none()
        if existing_email:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        
        hashed_password = get_password_hash(user_data.password)
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            phone=user_data.phone,
            department=user_data.department,
            date_joined=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        return UserResponse.model_validate(new_user)
    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=400, detail=f"创建用户失败: {str(e)}")


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(User).where(User.id == current_user["id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    return UserResponse.model_validate(user)


@router.put("/me", response_model=UserResponse)
async def update_current_user(
    user_update: UserUpdate,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(User).where(User.id == current_user["id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if user_update.email is not None:
        result = await db.execute(select(User).where(User.email == user_update.email))
        existing_email = result.scalar_one_or_none()
        if existing_email and existing_email.id != user.id:
            raise HTTPException(status_code=400, detail="邮箱已被使用")
        user.email = user_update.email
    
    if user_update.first_name is not None:
        user.first_name = user_update.first_name
    if user_update.last_name is not None:
        user.last_name = user_update.last_name
    if user_update.phone is not None:
        user.phone = user_update.phone
    if user_update.department is not None:
        user.department = user_update.department
    
    await db.commit()
    await db.refresh(user)
    
    return UserResponse.model_validate(user)


@router.post("/change-password")
async def change_password(
    password_data: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(select(User).where(User.id == current_user["id"]))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    if not verify_password(password_data.old_password, user.password):
        raise HTTPException(status_code=400, detail="原密码错误")
    
    user.password = get_password_hash(password_data.new_password)
    await db.commit()
    
    return {"status": 0, "msg": "密码修改成功"}


@router.get("/me/roles")
async def get_my_roles(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    roles = await get_current_user_roles(db, current_user["id"])
    return {
        "status": 0,
        "data": {
            "roles": roles
        }
    }


@router.get("/me/permissions")
async def get_my_permissions(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_async_db)
):
    result = await db.execute(
        select(Permission.codename)
        .join(RolePermissionLink, Permission.id == RolePermissionLink.permission_id)
        .join(UserRoleLink, RolePermissionLink.role_id == UserRoleLink.role_id)
        .where(UserRoleLink.user_id == current_user["id"])
    )
    permissions = [row[0] for row in result.all()]
    
    return {
        "status": 0,
        "data": {
            "permissions": permissions
        }
    }
