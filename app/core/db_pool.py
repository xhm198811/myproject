from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy import text
from typing import Dict, Any, Optional
from datetime import datetime
from .config import settings
from .logging import logger
import asyncio


class DatabaseConnectionManager:
    """数据库连接池管理器"""
    
    def __init__(self, database_url: str):
        self.database_url = database_url
        self.engine: Optional[AsyncEngine] = None
        self._connection_stats = {
            "total_connections": 0,
            "active_connections": 0,
            "idle_connections": 0,
            "failed_connections": 0,
            "last_health_check": None,
            "is_healthy": True
        }
        self._lock = asyncio.Lock()
    
    async def initialize(self) -> AsyncEngine:
        """初始化数据库连接池"""
        try:
            logger.info("正在初始化数据库连接池...")
            
            self.engine = create_async_engine(
                self.database_url,
                echo=settings.DEBUG,
                future=True,
                pool_size=settings.DATABASE_POOL_SIZE,
                max_overflow=settings.DATABASE_MAX_OVERFLOW,
                pool_timeout=settings.DATABASE_POOL_TIMEOUT,
                pool_pre_ping=True,
                pool_recycle=3600,
                pool_use_lifo=True,
            )
            
            logger.info(f"数据库连接池初始化成功 - 连接池大小: {settings.DATABASE_POOL_SIZE}, 最大溢出: {settings.DATABASE_MAX_OVERFLOW}")
            return self.engine
            
        except Exception as e:
            logger.error(f"数据库连接池初始化失败: {e}")
            raise
    
    async def get_engine(self) -> AsyncEngine:
        """获取数据库引擎"""
        if self.engine is None:
            await self.initialize()
        return self.engine
    
    async def health_check(self) -> Dict[str, Any]:
        """数据库健康检查"""
        try:
            engine = await self.get_engine()
            
            async with engine.connect() as conn:
                result = await conn.execute(text("SELECT 1"))
                result.fetchone()
            
            async with self._lock:
                self._connection_stats["last_health_check"] = datetime.now()
                self._connection_stats["is_healthy"] = True
                
                pool = engine.pool
                if hasattr(pool, 'size'):
                    self._connection_stats["total_connections"] = pool.size()
                if hasattr(pool, 'checkedout'):
                    self._connection_stats["active_connections"] = pool.checkedout()
                if hasattr(pool, 'checkedin'):
                    self._connection_stats["idle_connections"] = pool.checkedin()
            
            logger.info("数据库健康检查通过")
            return {
                "status": "healthy",
                "timestamp": self._connection_stats["last_health_check"].isoformat(),
                "connection_stats": self._connection_stats.copy()
            }
            
        except Exception as e:
            async with self._lock:
                self._connection_stats["is_healthy"] = False
                self._connection_stats["failed_connections"] += 1
            
            logger.error(f"数据库健康检查失败: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "connection_stats": self._connection_stats.copy()
            }
    
    async def get_connection_stats(self) -> Dict[str, Any]:
        """获取连接池统计信息"""
        try:
            engine = await self.get_engine()
            pool = engine.pool
            
            stats = {
                "pool_size": settings.DATABASE_POOL_SIZE,
                "max_overflow": settings.DATABASE_MAX_OVERFLOW,
                "pool_timeout": settings.DATABASE_POOL_TIMEOUT,
                "last_health_check": self._connection_stats["last_health_check"].isoformat() if self._connection_stats["last_health_check"] else None,
                "is_healthy": self._connection_stats["is_healthy"],
                "failed_connections": self._connection_stats["failed_connections"]
            }
            
            if hasattr(pool, 'size'):
                stats["total_connections"] = pool.size()
            if hasattr(pool, 'checkedout'):
                stats["active_connections"] = pool.checkedout()
            if hasattr(pool, 'checkedin'):
                stats["idle_connections"] = pool.checkedin()
            if hasattr(pool, 'overflow'):
                stats["overflow_connections"] = pool.overflow()
            
            return stats
            
        except Exception as e:
            logger.error(f"获取连接池统计信息失败: {e}")
            return {
                "error": str(e),
                "is_healthy": False
            }
    
    async def close(self):
        """关闭数据库连接池"""
        try:
            if self.engine:
                logger.info("正在关闭数据库连接池...")
                await self.engine.dispose()
                self.engine = None
                logger.info("数据库连接池已关闭")
        except Exception as e:
            logger.error(f"关闭数据库连接池失败: {e}")


# 创建全局数据库连接管理器实例
db_manager = DatabaseConnectionManager(settings.DATABASE_URL_ASYNC)


async def get_db_manager() -> DatabaseConnectionManager:
    """获取数据库连接管理器实例"""
    return db_manager


async def check_database_health() -> Dict[str, Any]:
    """检查数据库健康状态"""
    return await db_manager.health_check()


async def get_database_stats() -> Dict[str, Any]:
    """获取数据库统计信息"""
    return await db_manager.get_connection_stats()