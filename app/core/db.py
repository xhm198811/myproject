from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime
from fastapi import HTTPException
from .config import settings
from .db_pool import db_manager
from .logging import logger

# 使用数据库连接管理器初始化引擎
async def get_engine():
    """获取数据库引擎"""
    return await db_manager.get_engine()

# 创建异步数据库引擎（向后兼容）
engine = None

async def init_engine():
    """初始化数据库引擎"""
    global engine
    engine = await get_engine()
    return engine

# 创建异步会话工厂
async def get_async_session_factory():
    """获取异步会话工厂"""
    eng = await get_engine()
    return sessionmaker(
        eng,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

# 初始化会话工厂
async_session_factory = None

async def init_db():
    """初始化数据库表并创建默认用户"""
    global async_session_factory, engine
    
    try:
        logger.info("开始初始化数据库...")
        
        # 初始化引擎
        engine = await init_engine()
        
        # 初始化会话工厂
        async_session_factory = await get_async_session_factory()
        
        # 创建所有模型表（如果不存在）
        async with engine.begin() as conn:
            # 检查表是否已存在，避免重复创建
            from sqlalchemy import inspect
            
            def check_existing_tables(sync_conn):
                inspector = inspect(sync_conn)
                return inspector.get_table_names()
            
            existing_tables = await conn.run_sync(check_existing_tables)
            
            # 获取所有需要创建的表
            tables_to_create = []
            for table_name, table in SQLModel.metadata.tables.items():
                if table_name not in existing_tables:
                    tables_to_create.append(table)
            
            if tables_to_create:
                # 只创建不存在的表
                for table in tables_to_create:
                    await conn.run_sync(table.create)
                logger.info(f"创建了 {len(tables_to_create)} 个新表")
            else:
                logger.info("所有表已存在，跳过创建")
        
        logger.info("数据库表创建完成")
        
        # 导入组织人员模型以确保表被创建
        try:
            from app.organization.models import Organization, OrganizationRole, Person, PersonRoleLink, PersonDepartmentHistory
            logger.info("组织人员模型导入成功")
        except Exception as e:
            logger.warning(f"导入组织人员模型失败: {e}")
        
        # 创建默认超级用户
        async with async_session_factory() as session:
            try:
                from app.users.models.user import User
                from sqlmodel import select
                from passlib.context import CryptContext
                
                # 检查默认用户是否已存在
                result = await session.execute(select(User).where(User.username == "admin"))
                existing_user = result.scalar_one_or_none()
                
                from app.core.auth import get_password_hash
                
                if not existing_user:
                    # 创建新用户
                    new_user = User(
                        username="admin",
                        password=get_password_hash("admin123"),
                        email="admin@example.com",
                        is_superuser=True,
                        is_staff=True,
                        is_active=True,
                        date_joined=datetime.now(),
                        created_at=datetime.now(),
                        updated_at=datetime.now()
                    )
                    
                    session.add(new_user)
                    await session.commit()
                    await session.refresh(new_user)
                    
                    logger.info(f"创建默认超级用户: {new_user.username} (ID: {new_user.id})")
                else:
                    # 重置密码为admin123
                    existing_user.password = get_password_hash("admin123")
                    session.add(existing_user)
                    await session.commit()
                    await session.refresh(existing_user)
                    logger.info(f"默认超级用户已存在，重置密码: {existing_user.username}")
                    
            except Exception as e:
                logger.error(f"创建默认用户时出错: {e}")
                raise
        
        # 执行数据库健康检查
        health_status = await db_manager.health_check()
        if health_status["status"] == "healthy":
            logger.info("数据库健康检查通过")
        else:
            logger.warning(f"数据库健康检查警告: {health_status}")
        
        logger.info("数据库初始化完成")
        
    except Exception as e:
        logger.error(f"数据库初始化失败: {e}")
        raise

async def get_async_db():
    """获取异步数据库会话"""
    global async_session_factory
    
    if async_session_factory is None:
        raise RuntimeError("数据库尚未初始化。请确保应用已经启动并完成了数据库初始化。")
    
    async with async_session_factory() as session:
        try:
            yield session
        except HTTPException:
            raise
        except Exception as e:
            await session.rollback()
            import traceback
            error_trace = traceback.format_exc()
            logger.error(f"数据库会话异常: {type(e).__name__}: {e}\n{error_trace}")
            raise e
        finally:
            await session.close()

# 别名函数，符合更简洁的命名习惯
get_db = get_async_db

def get_async_db_session():
    """获取异步数据库会话上下文管理器"""
    return async_session_factory
