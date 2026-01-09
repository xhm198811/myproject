from datetime import datetime, timedelta
from typing import Dict, Set, Optional
from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from .config import settings
from .logging import logger


class OnlineUserManager:
    """在线用户管理器"""
    
    def __init__(self):
        # 存储在线用户信息: {user_id: {'last_activity': datetime, 'ip_address': str, 'user_agent': str}}
        self.online_users: Dict[int, dict] = {}
    
    def add_online_user(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        添加在线用户
        
        user_id: 用户ID
        ip_address: IP地址
        user_agent: User-Agent信息
        """
        self.online_users[user_id] = {
            'last_activity': datetime.utcnow(),
            'ip_address': ip_address,
            'user_agent': user_agent
        }
        logger.info(f"用户上线: user_id={user_id}, ip={ip_address}")
    
    def update_user_activity(
        self,
        user_id: int,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        更新用户活动时间
        
        user_id: 用户ID
        ip_address: IP地址
        user_agent: User-Agent信息
        """
        if user_id in self.online_users:
            self.online_users[user_id]['last_activity'] = datetime.utcnow()
            if ip_address:
                self.online_users[user_id]['ip_address'] = ip_address
            if user_agent:
                self.online_users[user_id]['user_agent'] = user_agent
    
    def remove_online_user(self, user_id: int):
        """
        移除在线用户
        
        user_id: 用户ID
        """
        if user_id in self.online_users:
            del self.online_users[user_id]
            logger.info(f"用户下线: user_id={user_id}")
    
    def is_user_online(self, user_id: int) -> bool:
        """
        检查用户是否在线
        
        user_id: 用户ID
        
        返回: 是否在线
        """
        if user_id not in self.online_users:
            return False
        
        # 检查是否超时
        last_activity = self.online_users[user_id]['last_activity']
        timeout = timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES)
        
        if datetime.utcnow() - last_activity > timeout:
            # 超时，移除用户
            self.remove_online_user(user_id)
            return False
        
        return True
    
    def get_online_user_count(self) -> int:
        """
        获取在线用户数量
        
        返回: 在线用户数
        """
        self.clean_inactive_users()
        return len(self.online_users)
    
    def get_online_users(self) -> Dict[int, dict]:
        """
        获取所有在线用户
        
        返回: 在线用户字典
        """
        self.clean_inactive_users()
        return self.online_users.copy()
    
    def get_online_user_ids(self) -> Set[int]:
        """
        获取所有在线用户ID
        
        返回: 在线用户ID集合
        """
        self.clean_inactive_users()
        return set(self.online_users.keys())
    
    def clean_inactive_users(self):
        """清理不活跃的用户"""
        current_time = datetime.utcnow()
        timeout = timedelta(minutes=settings.SESSION_TIMEOUT_MINUTES)
        
        inactive_users = [
            user_id for user_id, data in self.online_users.items()
            if current_time - data['last_activity'] > timeout
        ]
        
        for user_id in inactive_users:
            self.remove_online_user(user_id)
    
    def get_user_info(self, user_id: int) -> Optional[dict]:
        """
        获取用户在线信息
        
        user_id: 用户ID
        
        返回: 用户在线信息，如果用户不在线则返回None
        """
        if self.is_user_online(user_id):
            return self.online_users[user_id].copy()
        return None


# 全局在线用户管理器实例
online_user_manager = OnlineUserManager()


async def get_online_users_with_details(db: AsyncSession) -> list:
    """
    获取在线用户详细信息
    
    返回: 包含用户详细信息的列表
    """
    from app.users.models.user import User
    
    online_user_ids = online_user_manager.get_online_user_ids()
    
    if not online_user_ids:
        return []
    
    # 查询用户详细信息
    result = await db.execute(
        select(User).where(User.id.in_(online_user_ids))
    )
    users = result.scalars().all()
    
    # 组合在线状态和用户信息
    online_users = []
    for user in users:
        online_info = online_user_manager.get_user_info(user.id)
        if online_info:
            online_users.append({
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'department': user.department,
                'avatar': user.avatar,
                'is_staff': user.is_staff,
                'is_superuser': user.is_superuser,
                'last_activity': online_info['last_activity'].isoformat(),
                'ip_address': online_info['ip_address'],
                'user_agent': online_info['user_agent']
            })
    
    return online_users


async def track_user_activity(
    user_id: int,
    request: Request,
    db: AsyncSession
):
    """
    跟踪用户活动
    
    user_id: 用户ID
    request: FastAPI请求对象
    db: 数据库会话
    """
    # 获取客户端信息
    from .auth import get_client_info
    ip_address, user_agent = await get_client_info(request)
    
    # 更新用户在线状态
    online_user_manager.update_user_activity(user_id, ip_address, user_agent)
    
    # 记录活动日志（可选）
    await record_user_activity(db, user_id, request, ip_address, user_agent)


async def record_user_activity(
    db: AsyncSession,
    user_id: int,
    request: Request,
    ip_address: Optional[str],
    user_agent: Optional[str]
):
    """
    记录用户活动到数据库
    
    user_id: 用户ID
    request: FastAPI请求对象
    ip_address: IP地址
    user_agent: User-Agent信息
    """
    try:
        from app.users.models.user import UserActivityLog
        from sqlalchemy import insert
        
        # 获取请求路径和方法
        path = request.url.path
        method = request.method
        
        # 记录活动日志
        await db.execute(
            insert(UserActivityLog).values(
                user_id=user_id,
                action=f"{method} {path}",
                description=f"用户访问 {path}",
                ip_address=ip_address,
                user_agent=user_agent,
                meta_data={
                    'method': method,
                    'path': path,
                    'query_params': str(request.query_params)
                }
            )
        )
        await db.commit()
    except Exception as e:
        logger.error(f"记录用户活动失败: {e}", exc_info=True)
        await db.rollback()


async def get_user_activity_stats(
    db: AsyncSession,
    user_id: Optional[int] = None,
    days: int = 7
) -> dict:
    """
    获取用户活动统计
    
    user_id: 用户ID，如果为None则统计所有用户
    days: 统计天数
    
    返回: 统计信息
    """
    from app.users.models.user import UserActivityLog
    from sqlalchemy import select, func, and_
    
    time_threshold = datetime.utcnow() - timedelta(days=days)
    
    query = select(UserActivityLog).where(UserActivityLog.created_at >= time_threshold)
    
    if user_id:
        query = query.where(UserActivityLog.user_id == user_id)
    
    result = await db.execute(query)
    activities = result.scalars().all()
    
    # 统计信息
    total_activities = len(activities)
    unique_users = len(set(activity.user_id for activity in activities))
    
    # 按日期分组统计
    daily_stats = {}
    for activity in activities:
        date = activity.created_at.date().isoformat()
        if date not in daily_stats:
            daily_stats[date] = 0
        daily_stats[date] += 1
    
    return {
        'total_activities': total_activities,
        'unique_users': unique_users,
        'daily_stats': daily_stats,
        'period_days': days
    }
