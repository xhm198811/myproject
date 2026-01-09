from typing import Optional, List, Dict, Any
from urllib.parse import quote, urlparse, urlunparse

from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security.utils import get_authorization_scheme_param
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError

# 核心配置/工具导入（规范绝对导入，补充类型提示）
from app.core.config import settings
from app.core.db import get_async_db_session
from app.core.auth import get_user_from_db, get_user_by_id_from_db
from app.core.logging import logger

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    认证中间件：处理请求级别的JWT认证
    功能：
    1. 从请求头/Cookie获取JWT Token
    2. 验证Token并加载用户信息到request.state
    3. 对管理后台路径进行登录校验，未登录则重定向到登录页
    """
    # 管理后台路径（配置化，避免硬编码）
    ADMIN_PATHS: List[str] = getattr(settings, 'ADMIN_PATHS', [
        "/admin", "/ContractAdmin", "/ProjectAdmin", "/QuoteAdmin", "/ProductAdmin"
    ])
    # 无需认证的路径（白名单）
    WHITELIST_PATHS: List[str] = [
        "/login", "/api/login", "/api/captcha", "/api/health", 
        "/static", "/docs", "/redoc", "/openapi.json",
        "/swagger-ui", "/swagger-ui-bundle.js", "/swagger-ui-standalone-preset.js",
        "/swagger-ui.css", "/favicon.ico"
    ]

    async def dispatch(
        self, 
        request: Request, 
        call_next: RequestResponseEndpoint
    ) -> Response:
        """核心调度方法：处理认证逻辑并传递请求"""
        # 初始化请求状态（规范类型注解）
        request.state.user: Optional[Dict[str, Any]] = None
        request.state.token: Optional[str] = None
        request.state.is_authenticated: bool = False
        
        # 获取请求基础信息（便于日志追踪）
        client_ip = request.client.host if request.client else "unknown"
        request_path = request.url.path
        request_method = request.method
        request_id = request.headers.get("X-Request-ID", "unknown")

        try:
            # ======================
            # 1. 跳过白名单路径的认证（提升性能）
            # ======================
            if any(request_path.startswith(path) for path in self.WHITELIST_PATHS):
                logger.debug(
                    f"[AuthMiddleware-{request_id}] Skip auth for whitelist path: {request_path} "
                    f"(IP: {client_ip}, Method: {request_method})"
                )
                return await call_next(request)

            # ======================
            # 2. 获取并验证Token
            # ======================
            token = await self._extract_token(request)
            
            if token:
                request.state.token = token
                logger.debug(
                    f"[AuthMiddleware-{request_id}] Found token (IP: {client_ip}, Path: {request_path}) "
                    f"Token: {token[:20]}..."
                )
                
                # 验证Token并加载用户信息
                user = await self._validate_token_and_get_user(token)
                if user:
                    request.state.user = user
                    request.state.is_authenticated = True
                    logger.info(
                        f"[AuthMiddleware-{request_id}] User authenticated "
                        f"(IP: {client_ip}, User: {user.get('username')}, Path: {request_path})"
                    )

            # ======================
            # 3. 管理后台路径访问控制
            # ======================
            if self._is_admin_path(request_path):
                # 跳过登录页面本身（避免无限重定向）
                if request_path == "/login":
                    return await call_next(request)
                
                # 已登录用户直接放行
                if request.state.is_authenticated:
                    return await call_next(request)
                
                # 未登录处理逻辑
                logger.warning(
                    f"[AuthMiddleware-{request_id}] Unauthenticated access to admin path "
                    f"(IP: {client_ip}, Path: {request_path}, Method: {request_method})"
                )
                
                # 处理不同请求类型
                response = await self._handle_unauthenticated_admin_access(request)
                return response

            # ======================
            # 4. 非管理后台路径，正常放行
            # ======================
            return await call_next(request)

        except Exception as e:
            # 全局异常捕获，避免中间件崩溃
            logger.error(
                f"[AuthMiddleware-{request_id}] Unexpected error "
                f"(IP: {client_ip}, Path: {request_path}): {str(e)}",
                exc_info=True
            )
            # 非关键异常继续处理请求，避免阻断所有请求
            return await call_next(request)

    async def _extract_token(self, request: Request) -> Optional[str]:
        """
        提取Token：优先从请求头，其次从Cookie
        返回：有效Token | None
        """
        # 1. 从Authorization请求头提取
        authorization = request.headers.get("Authorization", "")
        scheme, token = get_authorization_scheme_param(authorization)
        
        if scheme.lower() == "bearer" and token:
            return token

        # 2. 从Cookie提取（兼容前端存储方式）
        token = request.cookies.get("access_token")
        if token:
            logger.debug(f"[AuthMiddleware] Token extracted from cookie: {token[:20]}...")
            return token

        # 3. Token不存在
        logger.debug(f"[AuthMiddleware] No valid token found (Headers: {bool(authorization)}, Cookie: {bool(request.cookies.get('access_token'))})")
        return None

    async def _validate_token_and_get_user(self, token: str) -> Optional[Dict[str, Any]]:
        """
        验证Token并获取用户信息
        返回：用户信息字典 | None
        """
        try:
            # 1. 解码JWT Token
            payload = jwt.decode(
                token,
                settings.SECRET_KEY,
                algorithms=[settings.ALGORITHM],
                options={"verify_exp": True}  # 强制验证过期时间
            )

            # 2. 提取用户标识
            username: Optional[str] = payload.get("sub")
            user_id: Optional[int] = payload.get("user_id")
            
            if not username and not user_id:
                logger.warning(f"[AuthMiddleware] Token payload missing user identifier (sub/user_id)")
                return None

            # 3. 获取数据库会话
            db_session_factory = get_async_db_session()
            async with db_session_factory() as db:  # 类型：AsyncSession
                # 4. 根据标识查询用户
                if user_id is not None:
                    user = await get_user_by_id_from_db(db, user_id)
                else:
                    user = await get_user_from_db(db, username)
                
                # 5. 验证用户状态
                if not user or not user.get("is_active", False):
                    logger.warning(f"[AuthMiddleware] User not found or inactive (username: {username}, user_id: {user_id})")
                    return None
                
                return user

        except JWTError as e:
            logger.warning(f"[AuthMiddleware] Invalid JWT token: {str(e)}")
            return None
        except SQLAlchemyError as e:
            logger.error(f"[AuthMiddleware] Database error when fetching user: {str(e)}", exc_info=True)
            return None
        except Exception as e:
            logger.error(f"[AuthMiddleware] Unexpected error when validating token: {str(e)}", exc_info=True)
            return None

    def _is_admin_path(self, path: str) -> bool:
        """判断是否为管理后台路径"""
        return any(path.startswith(admin_path) for admin_path in self.ADMIN_PATHS)

    async def _handle_unauthenticated_admin_access(self, request: Request) -> Response:
        """处理未登录用户访问管理后台的逻辑"""
        request_path = request.url.path
        request_method = request.method
        request_url = str(request.url)

        # 1. 非GET请求（POST/PUT/DELETE等）：直接返回401
        if request_method.upper() != "GET":
            raise HTTPException(
                status_code=401,
                detail="未登录或令牌已过期，请先登录"
            )

        # 3. API请求：返回401 JSON响应
        if request_path.endswith(('.json', '.api')) or '/api/' in request_path:
            raise HTTPException(
                status_code=401,
                detail={
                    "code": 401,
                    "message": "未登录或令牌已过期",
                    "data": {"redirect_url": "/login"}
                }
            )

        # 4. 普通页面请求：重定向到登录页（URL编码避免参数错误）
        # 构建安全的重定向URL（过滤恶意URL）
        parsed_url = urlparse(request_url)
        safe_redirect_url = urlunparse((
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            parsed_url.params,
            parsed_url.query,
            ""  # 移除fragment，避免XSS
        ))
        
        # URL编码重定向参数
        encoded_redirect = quote(safe_redirect_url, safe='')
        login_url = f"/login?redirect={encoded_redirect}"
        
        logger.info(f"[AuthMiddleware] Redirecting to login: {login_url} (Original: {safe_redirect_url})")
        
        return RedirectResponse(
            url=login_url,
            status_code=302,  # 临时重定向
            headers={"Cache-Control": "no-cache, no-store"}  # 禁用缓存
        )