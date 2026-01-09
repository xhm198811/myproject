from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Any
from datetime import datetime, timedelta
from jose import JWTError, jwt

from ...core.db import get_async_db
from ...core.auth import (
    authenticate_user, 
    create_access_token, 
    create_refresh_token, 
    get_user_from_db,
    record_login_history,
    record_logout_history,
    get_client_info,
    check_login_attempts,
    validate_password_strength,
    get_current_active_user
)
from ...core.config import settings
from .schemas import (
    TokenResponse, 
    RefreshTokenRequest, 
    LoginRequest, 
    LoginResponse, 
    LogoutResponse,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest
)

router = APIRouter()


@router.post("/token", response_model=TokenResponse, summary="用户登录获取令牌")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    用户通过用户名和密码登录，获取访问令牌（access_token）和刷新令牌（refresh_token）。
    
    - 支持标准 OAuth2 密码模式
    - 返回包含用户信息的 token 响应
    """
    user_dict = await authenticate_user(db, form_data.username, form_data.password)
    if not user_dict:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user_dict.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    
    # 从数据库获取完整用户信息
    from ..models.user import User
    from sqlalchemy.future import select
    result = await db.execute(select(User).where(User.id == user_dict["id"]))
    user = result.scalar_one_or_none()
    
    if user:
        # 更新用户最后登录时间
        user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
    
    # 创建令牌
    access_token = create_access_token(data={"sub": str(user_dict["id"]), "user_id": user_dict["id"]})
    refresh_token = create_refresh_token(data={"sub": str(user_dict["id"])})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        username=user.username,
        user_id=user.id,
        is_superuser=user.is_superuser
    )


@router.post("/login", response_model=LoginResponse, summary="用户登录（增强版）")
async def login(
    login_data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    用户登录接口（增强版）
    
    - 支持登录历史记录
    - 支持登录失败次数限制
    - 支持记住我功能
    - 支持验证码验证（如果启用）
    """
    # 获取客户端信息
    ip_address, user_agent = await get_client_info(request)
    
    # 检查登录尝试次数
    can_login, remaining_attempts, lockout_time = await check_login_attempts(
        db, login_data.username, ip_address
    )
    
    if not can_login:
        lockout_minutes = int(lockout_time.total_seconds() / 60) if lockout_time else 0
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"登录失败次数过多，账户已被锁定 {lockout_minutes} 分钟"
        )
    
    # 验证码验证（如果启用）
    if settings.ENABLE_CAPTCHA and login_data.captcha_code and login_data.captcha_key:
        from ...utils.captcha import verify_captcha
        if not await verify_captcha(login_data.captcha_key, login_data.captcha_code):
            await record_login_history(
                db, 
                user_id=0, 
                ip_address=ip_address, 
                user_agent=user_agent,
                login_status="failure",
                failure_reason="验证码错误"
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="验证码错误"
            )
    
    # 验证用户凭据
    user_dict = await authenticate_user(db, login_data.username, login_data.password)
    
    if not user_dict:
        # 记录登录失败
        from ..models.user import User
        from sqlalchemy.future import select
        
        try:
            # 查询用户信息
            result = await db.execute(select(User).where(User.username == login_data.username))
            user = result.scalar_one_or_none()
            
            user_id = user.id if user else 0
            await record_login_history(
                db,
                user_id=user_id,
                ip_address=ip_address,
                user_agent=user_agent,
                login_status="failure",
                failure_reason="用户名或密码错误"
            )
        except Exception as e:
            pass
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"用户名或密码错误，剩余尝试次数: {remaining_attempts - 1}"
        )
    
    if not user_dict.get("is_active", True):
        await record_login_history(
            db,
            user_id=user_dict["id"],
            ip_address=ip_address,
            user_agent=user_agent,
            login_status="failure",
            failure_reason="用户账户已被禁用"
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    
    # 从数据库获取完整用户信息
    from ..models.user import User
    from sqlalchemy.future import select
    result = await db.execute(select(User).where(User.id == user_dict["id"]))
    user = result.scalar_one_or_none()
    
    if user:
        # 更新用户最后登录时间
        user.last_login = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
    
    # 根据记住我设置令牌过期时间
    if login_data.remember_me:
        access_expire_minutes = settings.REMEMBER_ME_DAYS * 24 * 60
    else:
        access_expire_minutes = settings.ACCESS_TOKEN_EXPIRE_MINUTES
    
    # 创建令牌
    access_token = create_access_token(
        data={"sub": str(user_dict["id"]), "user_id": user_dict["id"]},
        expires_delta=timedelta(minutes=access_expire_minutes)
    )
    refresh_token = create_refresh_token(data={"sub": str(user_dict["id"])})
    
    # 记录登录成功
    await record_login_history(
        db,
        user_id=user_dict["id"],
        ip_address=ip_address,
        user_agent=user_agent,
        login_status="success"
    )
    
    # 添加用户到在线列表
    from ...core.online_users import online_user_manager
    online_user_manager.add_online_user(user_dict["id"], ip_address, user_agent)
    
    return LoginResponse(
        access_token=access_token,
        token_type="bearer",
        refresh_token=refresh_token,
        expires_in=access_expire_minutes * 60,
        user={
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "phone": user.phone,
            "department": user.department,
            "avatar": user.avatar,
            "is_staff": user.is_staff,
            "is_superuser": user.is_superuser,
            "date_joined": user.date_joined.isoformat() if user.date_joined else None,
            "last_login": user.last_login.isoformat() if user.last_login else None
        }
    )


@router.post("/logout", response_model=LogoutResponse, summary="用户登出")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    用户登出接口
    
    - 记录登出时间
    - 从在线用户列表中移除
    - 清除客户端令牌（需要客户端配合）
    """
    # 获取当前用户
    from ...core.auth import get_current_user
    from ...core.online_users import online_user_manager
    try:
        current_user = await get_current_user(request.headers.get("Authorization"), db)
        
        # 记录登出时间
        await record_logout_history(db, current_user["id"])
        
        # 从在线用户列表中移除
        online_user_manager.remove_online_user(current_user["id"])
    except:
        pass
    
    return LogoutResponse(message="登出成功")


@router.post("/token/refresh")
async def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: AsyncSession = Depends(get_async_db)
):
    
    try:
        payload = jwt.decode(
            refresh_data.refresh_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM]
        )
    except JWTError:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    
    if payload.get("token_type") != "refresh":
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="无效的刷新令牌")
    
    user = await get_user_from_db(db, username)
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")
    
    if not user.get("is_active", True):
        raise HTTPException(status_code=400, detail="用户账户已被禁用")
    
    new_access_token = create_access_token(data={"sub": user["username"], "user_id": user["id"]})
    
    return {
        "status": 0,
        "msg": "令牌刷新成功",
        "data": {
            "access_token": new_access_token,
            "token_type": "bearer"
        }
    }


@router.get("/captcha", summary="获取验证码")
async def get_captcha():
    """
    获取验证码
    
    - 返回验证码密钥和图片
    - 验证码有效期为配置的 CAPTCHA_EXPIRE_SECONDS 秒
    """
    from ...utils.captcha import create_captcha
    return await create_captcha()


@router.post("/forgot-password", summary="请求密码重置")
async def forgot_password(
    request_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    请求密码重置
    
    - 发送密码重置链接到用户邮箱
    - 重置链接有效期为1小时
    """
    from ...core.password_reset import request_password_reset
    return await request_password_reset(db, request_data.email)


@router.post("/reset-password", summary="重置密码")
async def reset_password(
    request_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_async_db)
) -> Any:
    """
    重置密码
    
    - 使用重置令牌设置新密码
    - 令牌验证成功后会自动失效
    """
    from ...core.password_reset import reset_password
    return await reset_password(db, request_data.token, request_data.new_password)


@router.post("/change-password", summary="修改密码")
async def change_password(
    request_data: ChangePasswordRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    修改当前用户密码
    
    - 需要提供旧密码进行验证
    - 新密码必须符合密码强度要求
    """
    from ...core.password_reset import change_password
    return await change_password(
        db, 
        current_user["id"], 
        request_data.old_password, 
        request_data.new_password
    )


@router.get("/online-users", summary="获取在线用户列表")
async def get_online_users(
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    获取在线用户列表
    
    - 返回当前所有在线用户的详细信息
    - 需要用户登录
    """
    from ...core.online_users import get_online_users_with_details
    return {
        "status": "success",
        "data": await get_online_users_with_details(db),
        "count": len(await get_online_users_with_details(db))
    }


@router.get("/activity-stats", summary="获取用户活动统计")
async def get_activity_stats(
    days: int = 7,
    db: AsyncSession = Depends(get_async_db),
    current_user: dict = Depends(get_current_active_user)
) -> Any:
    """
    获取用户活动统计
    
    - 返回指定天数内的用户活动统计信息
    - 需要用户登录
    """
    from ...core.online_users import get_user_activity_stats
    return {
        "status": "success",
        "data": await get_user_activity_stats(db, days=days)
    }
