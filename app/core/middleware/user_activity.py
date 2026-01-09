from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.ext.asyncio import AsyncSession

from .db import get_async_db_session
from .online_users import online_user_manager, track_user_activity
from .auth import get_current_user
from .logging import logger


class UserActivityMiddleware(BaseHTTPMiddleware):
    """用户活动跟踪中间件"""
    
    async def dispatch(self, request: Request, call_next):
        # 获取数据库会话
        db_session = get_async_db_session()
        
        # 尝试获取当前用户
        user_id = None
        try:
            authorization = request.headers.get("Authorization")
            if authorization:
                async with db_session() as db:
                    try:
                        current_user = await get_current_user(authorization, db)
                        user_id = current_user.get("id")
                        
                        # 跟踪用户活动
                        await track_user_activity(user_id, request, db)
                    except Exception as e:
                        logger.debug(f"跟踪用户活动失败: {e}")
        except Exception as e:
            logger.debug(f"获取用户信息失败: {e}")
        
        # 处理请求
        response = await call_next(request)
        
        return response
