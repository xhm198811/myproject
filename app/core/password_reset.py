import secrets
import string
from datetime import datetime, timedelta
from typing import Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
import hashlib

from .config import settings
from .auth import validate_password_strength
from .logging import logger


class PasswordResetManager:
    """密码重置管理器"""
    
    def __init__(self):
        self.reset_tokens = {}
    
    def generate_reset_token(self, user_id: int) -> str:
        """
        生成密码重置令牌
        
        返回: 重置令牌
        """
        timestamp = datetime.utcnow().timestamp()
        random_str = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))
        
        token_data = f"{user_id}:{timestamp}:{random_str}"
        token_hash = hashlib.sha256(token_data.encode()).hexdigest()
        
        # 存储令牌信息
        expire_time = datetime.utcnow() + timedelta(hours=1)  # 令牌有效期1小时
        self.reset_tokens[token_hash] = {
            'user_id': user_id,
            'expire_time': expire_time
        }
        
        # 清理过期令牌
        self.clean_expired_tokens()
        
        return token_hash
    
    def verify_reset_token(self, token: str) -> Optional[int]:
        """
        验证密码重置令牌
        
        返回: 用户ID，如果令牌无效则返回None
        """
        if token not in self.reset_tokens:
            return None
        
        token_data = self.reset_tokens[token]
        
        # 检查是否过期
        if datetime.utcnow() > token_data['expire_time']:
            del self.reset_tokens[token]
            return None
        
        return token_data['user_id']
    
    def invalidate_token(self, token: str):
        """使令牌失效"""
        if token in self.reset_tokens:
            del self.reset_tokens[token]
    
    def clean_expired_tokens(self):
        """清理过期令牌"""
        current_time = datetime.utcnow()
        expired_tokens = [
            token for token, data in self.reset_tokens.items()
            if current_time > data['expire_time']
        ]
        
        for token in expired_tokens:
            del self.reset_tokens[token]


# 全局密码重置管理器实例
password_reset_manager = PasswordResetManager()


async def request_password_reset(
    db: AsyncSession,
    email: str
) -> dict:
    """
    请求密码重置
    
    返回: 包含重置令牌的字典（实际应用中应该发送邮件）
    """
    from app.users.models.user import User
    
    # 查找用户
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    if not user:
        # 为了安全，不透露用户是否存在
        logger.warning(f"密码重置请求: 邮箱 {email} 未找到用户")
        return {
            "message": "如果该邮箱已注册，您将收到密码重置链接",
            "status": "success"
        }
    
    if not user.is_active:
        logger.warning(f"密码重置请求: 用户 {user.username} 账户已被禁用")
        return {
            "message": "如果该邮箱已注册，您将收到密码重置链接",
            "status": "success"
        }
    
    # 生成重置令牌
    reset_token = password_reset_manager.generate_reset_token(user.id)
    
    # 在实际应用中，这里应该发送邮件
    # 示例邮件内容：
    # reset_link = f"http://yourdomain.com/reset-password?token={reset_token}"
    # send_email(email, "密码重置", f"请点击以下链接重置密码: {reset_link}")
    
    logger.info(f"密码重置令牌已生成: user_id={user.id}, email={email}")
    
    # 开发环境直接返回令牌
    return {
        "message": "密码重置链接已发送到您的邮箱",
        "status": "success",
        "reset_token": reset_token  # 仅用于开发环境
    }


async def reset_password(
    db: AsyncSession,
    token: str,
    new_password: str
) -> dict:
    """
    重置密码
    
    返回: 操作结果
    """
    from app.users.models.user import User
    from .auth import get_password_hash
    
    # 验证令牌
    user_id = password_reset_manager.verify_reset_token(token)
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="重置令牌无效或已过期"
        )
    
    # 验证密码强度
    is_valid, error_message = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户账户已被禁用"
        )
    
    # 更新密码
    user.password = get_password_hash(new_password)
    await db.commit()
    
    # 使令牌失效
    password_reset_manager.invalidate_token(token)
    
    logger.info(f"密码重置成功: user_id={user_id}, username={user.username}")
    
    return {
        "message": "密码重置成功",
        "status": "success"
    }


async def change_password(
    db: AsyncSession,
    user_id: int,
    old_password: str,
    new_password: str
) -> dict:
    """
    修改密码
    
    返回: 操作结果
    """
    from app.users.models.user import User
    from .auth import verify_password, get_password_hash
    
    # 获取用户
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="用户不存在"
        )
    
    # 验证旧密码
    if not verify_password(old_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="旧密码错误"
        )
    
    # 验证新密码强度
    is_valid, error_message = validate_password_strength(new_password)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_message
        )
    
    # 检查新旧密码是否相同
    if verify_password(new_password, user.password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="新密码不能与旧密码相同"
        )
    
    # 更新密码
    user.password = get_password_hash(new_password)
    await db.commit()
    
    logger.info(f"密码修改成功: user_id={user_id}, username={user.username}")
    
    return {
        "message": "密码修改成功",
        "status": "success"
    }
