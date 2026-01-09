"""
Django用户管理API端点 - 直接查询数据库
"""
from fastapi import APIRouter, HTTPException, Query, Depends
from typing import Dict, List, Optional
from sqlalchemy import select, func, or_, and_, text
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime
import logging

from ...core.db import get_async_db
from ...core.auth import get_current_user
from ...core.logging import logger

router = APIRouter(prefix="/django-users", tags=["Django用户管理"])


@router.get("/list")
async def get_django_users(
    page: int = Query(1, ge=1, description="页码"),
    limit: int = Query(20, ge=1, le=100, description="每页数量"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    db: AsyncSession = Depends(get_async_db)
) -> Dict:
    """从数据库获取用户列表"""
    try:
        from ...users.models.user import User
        
        query = select(User)
        
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.username.ilike(search_pattern),
                    User.email.ilike(search_pattern),
                    User.first_name.ilike(search_pattern),
                    User.last_name.ilike(search_pattern)
                )
            )
        
        query = query.order_by(User.id)
        
        total_result = await db.execute(
            select(func.count()).select_from(query.subquery())
        )
        total = total_result.scalar()
        
        offset = (page - 1) * limit
        paginated_query = query.offset(offset).limit(limit)
        
        result = await db.execute(paginated_query)
        users = result.scalars().all()
        
        items = []
        for user in users:
            items.append({
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined.isoformat() if user.date_joined else "",
                "last_login": user.last_login.isoformat() if user.last_login else ""
            })
        
        return {
            "status": 0,
            "msg": "",
            "data": {
                "items": items,
                "total": total,
                "page": page,
                "limit": limit
            }
        }
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}", exc_info=True)
        return {
            "status": 1,
            "msg": f"获取用户列表失败: {str(e)}",
            "data": {"items": [], "total": 0}
        }


@router.get("/detail/{user_id}")
async def get_django_user_detail(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
) -> Dict:
    """获取用户详情"""
    try:
        from ...users.models.user import User
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {
                "status": 1,
                "msg": f"用户不存在: {user_id}",
                "data": {}
            }
        
        user_data = {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "phone": user.phone or "",
            "department": user.department or "",
            "avatar": user.avatar or "",
            "employee_id": user.employee_id or "",
            "job_title": user.job_title or "",
            "hire_date": user.hire_date.isoformat() if user.hire_date else "",
            "termination_date": user.termination_date.isoformat() if user.termination_date else "",
            "manager_id": user.manager_id,
            "employment_status": user.employment_status,
            "is_active": user.is_active,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "date_joined": user.date_joined.isoformat() if user.date_joined else "",
            "last_login": user.last_login.isoformat() if user.last_login else ""
        }
        
        return {
            "status": 0,
            "msg": "",
            "data": user_data
        }
    except Exception as e:
        logger.error(f"获取用户详情失败: {str(e)}", exc_info=True)
        return {
            "status": 1,
            "msg": f"获取用户详情失败: {str(e)}",
            "data": {}
        }


@router.post("/create")
async def create_django_user(
    user_data: Dict,
    db: AsyncSession = Depends(get_async_db)
) -> Dict:
    """创建新用户"""
    try:
        from ...users.models.user import User
        from ...core.auth import get_password_hash
        
        username = user_data.get("username")
        email = user_data.get("email")
        password = user_data.get("password")
        
        if not username or not email or not password:
            return {
                "status": 1,
                "msg": "用户名、邮箱和密码不能为空",
                "data": {}
            }
        
        existing_user = await db.execute(
            select(User).where(or_(User.username == username, User.email == email))
        )
        if existing_user.scalar_one_or_none():
            return {
                "status": 1,
                "msg": "用户名或邮箱已存在",
                "data": {}
            }
        
        hashed_password = get_password_hash(password)
        
        new_user = User(
            username=username,
            email=email,
            password=hashed_password,
            first_name=user_data.get("first_name", ""),
            last_name=user_data.get("last_name", ""),
            phone=user_data.get("phone"),
            department=user_data.get("department"),
            avatar=user_data.get("avatar"),
            employee_id=user_data.get("employee_id"),
            job_title=user_data.get("job_title"),
            hire_date=user_data.get("hire_date"),
            employment_status=user_data.get("employment_status", "active"),
            is_active=user_data.get("is_active", True),
            is_staff=user_data.get("is_staff", False),
            is_superuser=user_data.get("is_superuser", False),
            date_joined=datetime.utcnow(),
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)
        
        logger.info(f"创建用户成功: {username}")
        
        return {
            "status": 0,
            "msg": "用户创建成功",
            "data": {
                "id": new_user.id,
                "username": new_user.username,
                "email": new_user.email
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"创建用户失败: {str(e)}", exc_info=True)
        return {
            "status": 1,
            "msg": f"创建用户失败: {str(e)}",
            "data": {}
        }


@router.put("/update/{user_id}")
async def update_django_user(
    user_id: int,
    user_data: Dict,
    db: AsyncSession = Depends(get_async_db)
) -> Dict:
    """更新用户信息"""
    try:
        from ...users.models.user import User
        from ...core.auth import get_password_hash
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {
                "status": 1,
                "msg": f"用户不存在: {user_id}",
                "data": {}
            }
        
        if "username" in user_data:
            existing_user = await db.execute(
                select(User).where(
                    and_(User.username == user_data["username"], User.id != user_id)
                )
            )
            if existing_user.scalar_one_or_none():
                return {
                    "status": 1,
                    "msg": "用户名已存在",
                    "data": {}
                }
            user.username = user_data["username"]
        
        if "email" in user_data:
            existing_email = await db.execute(
                select(User).where(
                    and_(User.email == user_data["email"], User.id != user_id)
                )
            )
            if existing_email.scalar_one_or_none():
                return {
                    "status": 1,
                    "msg": "邮箱已存在",
                    "data": {}
                }
            user.email = user_data["email"]
        
        if "password" in user_data and user_data["password"]:
            user.password = get_password_hash(user_data["password"])
        
        if "first_name" in user_data:
            user.first_name = user_data["first_name"]
        if "last_name" in user_data:
            user.last_name = user_data["last_name"]
        if "phone" in user_data:
            user.phone = user_data["phone"]
        if "department" in user_data:
            user.department = user_data["department"]
        if "avatar" in user_data:
            user.avatar = user_data["avatar"]
        if "employee_id" in user_data:
            user.employee_id = user_data["employee_id"]
        if "job_title" in user_data:
            user.job_title = user_data["job_title"]
        if "hire_date" in user_data:
            user.hire_date = user_data["hire_date"]
        if "employment_status" in user_data:
            user.employment_status = user_data["employment_status"]
        if "is_active" in user_data:
            user.is_active = user_data["is_active"]
        if "is_staff" in user_data:
            user.is_staff = user_data["is_staff"]
        if "is_superuser" in user_data:
            user.is_superuser = user_data["is_superuser"]
        
        await db.commit()
        await db.refresh(user)
        
        logger.info(f"更新用户成功: {user.username}")
        
        return {
            "status": 0,
            "msg": "用户更新成功",
            "data": {
                "id": user.id,
                "username": user.username,
                "email": user.email
            }
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"更新用户失败: {str(e)}", exc_info=True)
        return {
            "status": 1,
            "msg": f"更新用户失败: {str(e)}",
            "data": {}
        }


@router.delete("/delete/{user_id}")
async def delete_django_user(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
) -> Dict:
    """删除用户"""
    try:
        from ...users.models.user import User
        
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        
        if not user:
            return {
                "status": 1,
                "msg": f"用户不存在: {user_id}",
                "data": {}
            }
        
        # 先删除 django_admin_log 表中的相关记录，避免外键约束错误
        try:
            await db.execute(
                text("DELETE FROM django_admin_log WHERE user_id = :user_id"),
                {"user_id": user_id}
            )
            logger.info(f"删除 django_admin_log 表中用户 {user.username} 的记录")
        except Exception as e:
            logger.warning(f"删除 django_admin_log 记录失败（表可能不存在）: {str(e)}")
        
        # 删除用户
        await db.delete(user)
        await db.commit()
        
        logger.info(f"删除用户成功: {user.username}")
        
        return {
            "status": 0,
            "msg": "用户删除成功",
            "data": {"id": user_id}
        }
    except Exception as e:
        await db.rollback()
        logger.error(f"删除用户失败: {str(e)}", exc_info=True)
        return {
            "status": 1,
            "msg": f"删除用户失败: {str(e)}",
            "data": {}
        }
