from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status, Depends, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

from .config import settings
from .db import get_async_db
from .logging import logger


# 密码加密上下文
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")

# OAuth2 密码承载令牌
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/token")


class TokenData(BaseModel):
    """JWT 载荷数据模型"""
    sub: Optional[str] = None  # 用户 ID（字符串形式）
    token_type: Optional[str] = None


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证密码（使用 Django 的 check_password 函数）"""
    try:
        import os
        import sys
        import django
        
        sys.path.insert(0, 'E:\\HSdigitalportal\\enterprise_portal')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_portal.settings')
        django.setup()
        
        from django.contrib.auth.hashers import check_password
        return check_password(plain_password, hashed_password)
    except Exception as e:
        logger.error(f"密码验证失败: {e}")
        return False


def get_password_hash(password: str) -> str:
    """生成密码哈希（使用 Django 的 make_password 函数）"""
    try:
        import os
        import sys
        import django
        
        sys.path.insert(0, 'E:\\HSdigitalportal\\enterprise_portal')
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_portal.settings')
        django.setup()
        
        from django.contrib.auth.hashers import make_password
        return make_password(password)
    except Exception as e:
        logger.error(f"密码哈希生成失败: {e}")
        return ""


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """创建访问令牌（access token）"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "token_type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(data: Dict[str, Any]) -> str:
    """创建刷新令牌（refresh token）"""
    expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode = data.copy()
    to_encode.update({"exp": expire, "token_type": "refresh"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


async def get_user_from_db(db: AsyncSession, username: str) -> Optional[Dict[str, Any]]:
    """从数据库获取用户信息（通过用户名）"""
    try:
        from app.users.models.user import User
        from sqlalchemy import select
        
        logger.info(f"尝试获取用户: {username}")
        result = await db.execute(select(User).where(User.username == username))
        user = result.scalar_one_or_none()
        if user:
            logger.info(f"找到用户: {user.username}")
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "department": user.department,
                "avatar": user.avatar,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
                "password": user.password
            }
        logger.info(f"未找到用户: {username}")
        return None
    except Exception as e:
        logger.error(f"从数据库获取用户失败: {e}", exc_info=True)
        return None


async def get_user_by_id_from_db(db: AsyncSession, user_id: int) -> Optional[Dict[str, Any]]:
    """从数据库获取用户信息（通过 ID）"""
    try:
        from app.users.models.user import User
        from sqlalchemy import select
        result = await db.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if user:
            return {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "phone": user.phone,
                "department": user.department,
                "avatar": user.avatar,
                "is_active": user.is_active,
                "is_staff": user.is_staff,
                "is_superuser": user.is_superuser,
                "date_joined": user.date_joined,
                "last_login": user.last_login,
                "password": user.password
            }
        return None
    except Exception as e:
        logger.error(f"通过 ID 获取用户失败: {e}", exc_info=True)
        return None


async def authenticate_user(db: AsyncSession, username: str, password: str) -> Optional[Dict[str, Any]]:
    """认证用户凭据"""
    user = await get_user_from_db(db, username)
    if not user:
        return None
    if not verify_password(password, user["password"]):
        return None
    return user


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_async_db)
) -> Dict[str, Any]:
    """从 JWT 获取当前用户"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id_str: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("token_type")

        if user_id_str is None:
            raise credentials_exception

        # 可选：校验 token_type（如只允许 access token 用于此依赖）
        # if token_type != "access":
        #     raise credentials_exception

        user_id = int(user_id_str)
    except (JWTError, ValueError, TypeError) as e:
        logger.warning(f"JWT 解码失败: {e}")
        raise credentials_exception

    user = await get_user_by_id_from_db(db, user_id)
    if user is None:
        raise credentials_exception
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    return user


async def get_current_active_user(
    current_user: Dict[str, Any] = Depends(get_current_user)
) -> Dict[str, Any]:
    """获取当前活跃用户（已由 get_current_user 保证活跃）"""
    return current_user


async def get_current_superuser(
    current_user: Dict[str, Any] = Depends(get_current_active_user)
) -> Dict[str, Any]:
    """获取当前超级用户"""
    if not current_user.get("is_superuser", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要超级用户权限"
        )
    return current_user


async def record_login_history(
    db: AsyncSession,
    user_id: int,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
    login_status: str = "success",
    failure_reason: Optional[str] = None
) -> bool:
    """记录用户登录历史"""
    try:
        from app.users.models.user import UserLoginHistory
        from sqlalchemy import insert
        
        # 使用独立的数据库会话来避免事务冲突
        from .db import get_async_db_session
        db_session = get_async_db_session()
        
        async with db_session() as session:
            await session.execute(
                insert(UserLoginHistory).values(
                    user_id=user_id,
                    login_time=datetime.utcnow(),
                    ip_address=ip_address,
                    user_agent=user_agent,
                    login_status=login_status,
                    failure_reason=failure_reason
                )
            )
            await session.commit()
        
        logger.info(f"记录登录历史成功: user_id={user_id}, status={login_status}")
        return True
    except Exception as e:
        logger.error(f"记录登录历史失败: {e}", exc_info=True)
        return False


async def record_logout_history(
    db: AsyncSession,
    user_id: int
) -> bool:
    """记录用户登出时间"""
    try:
        from app.users.models.user import UserLoginHistory
        from sqlalchemy import select, update
        
        # 使用独立的数据库会话来避免事务冲突
        from .db import get_async_db_session
        db_session = get_async_db_session()
        
        async with db_session() as session:
            result = await session.execute(
                select(UserLoginHistory)
                .where(UserLoginHistory.user_id == user_id)
                .where(UserLoginHistory.logout_time.is_(None))
                .order_by(UserLoginHistory.login_time.desc())
                .limit(1)
            )
            login_history = result.scalar_one_or_none()
            
            if login_history:
                await session.execute(
                    update(UserLoginHistory)
                    .where(UserLoginHistory.id == login_history.id)
                    .values(logout_time=datetime.utcnow())
                )
                await session.commit()
                logger.info(f"记录登出时间成功: user_id={user_id}")
                return True
        return False
    except Exception as e:
        logger.error(f"记录登出时间失败: {e}", exc_info=True)
        return False


async def get_client_info(request: Request) -> tuple:
    """获取客户端IP和User-Agent信息"""
    ip_address = None
    
    x_forwarded_for = request.headers.get("X-Forwarded-For")
    if x_forwarded_for:
        ip_address = x_forwarded_for.split(",")[0].strip()
    else:
        ip_address = request.client.host if request.client else None
    
    user_agent = request.headers.get("User-Agent", "")
    
    return ip_address, user_agent


async def check_login_attempts(
    db: AsyncSession,
    username: str,
    ip_address: Optional[str] = None
) -> tuple:
    """
    检查登录尝试次数
    
    返回: (是否允许登录, 剩余尝试次数, 锁定时间)
    """
    try:
        from app.users.models.user import UserLoginHistory
        from sqlalchemy import select, func
        from .db import get_async_db_session
        
        # 使用独立的数据库会话来避免事务冲突
        db_session = get_async_db_session()
        
        max_attempts = settings.MAX_LOGIN_ATTEMPTS if hasattr(settings, 'MAX_LOGIN_ATTEMPTS') else 5
        lockout_minutes = settings.LOCKOUT_MINUTES if hasattr(settings, 'LOCKOUT_MINUTES') else 30
        
        time_threshold = datetime.utcnow() - timedelta(minutes=lockout_minutes)
        
        async with db_session() as session:
            result = await session.execute(
                select(func.count(UserLoginHistory.id))
                .where(UserLoginHistory.login_status == "failure")
                .where(UserLoginHistory.login_time >= time_threshold)
            )
            failure_count = result.scalar() or 0
            
            if failure_count >= max_attempts:
                lockout_until = time_threshold + timedelta(minutes=lockout_minutes)
                remaining_time = lockout_until - datetime.utcnow()
                return False, 0, remaining_time
            
            remaining_attempts = max_attempts - failure_count
            return True, remaining_attempts, None
    except Exception as e:
        logger.error(f"检查登录尝试次数失败: {e}", exc_info=True)
        return True, 5, None


def validate_password_strength(password: str) -> tuple:
    """
    验证密码强度
    
    返回: (是否有效, 错误消息)
    """
    if len(password) < 8:
        return False, "密码长度至少为8个字符"
    
    if len(password) > 128:
        return False, "密码长度不能超过128个字符"
    
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_special = any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password)
    
    strength_count = sum([has_upper, has_lower, has_digit, has_special])
    
    if strength_count < 3:
        return False, "密码必须包含大写字母、小写字母、数字和特殊字符中的至少三种"
    
    return True, None