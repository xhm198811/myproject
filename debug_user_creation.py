"""
调试用户创建问题
"""
import asyncio
import os
import sys
import django
from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# 添加 Django 项目路径
sys.path.insert(0, 'E:\\HSdigitalportal\\enterprise_portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_portal.settings')

# 初始化 Django
django.setup()

from django.contrib.auth.hashers import make_password, check_password

DATABASE_URL = "postgresql+asyncpg://postgres:pwd123456@localhost:5432/myportaldb"


async def debug_user_creation():
    """调试用户创建问题"""
    
    print("=" * 80)
    print("调试用户创建问题")
    print("=" * 80)
    
    # 1. 检查数据库表结构
    print("\n【步骤 1】检查 auth_user 表结构")
    print("-" * 80)
    
    engine = create_async_engine(DATABASE_URL)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'auth_user'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            
            print(f"auth_user 表字段:")
            for col in columns:
                print(f"  {col[0]:30} {col[1]:20} nullable={col[2]} default={col[3]}")
                
        except Exception as e:
            print(f"查询表结构失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 2. 尝试手动创建用户
    print("\n【步骤 2】尝试手动创建用户")
    print("-" * 80)
    
    async with async_session() as session:
        try:
            hashed_password = make_password("Test123456")
            
            print(f"哈希密码: {hashed_password[:50]}...")
            
            # 尝试插入用户
            result = await session.execute(text("""
                INSERT INTO auth_user (
                    username, email, password, first_name, last_name,
                    phone, department, date_joined, created_at, updated_at,
                    is_active, is_staff, is_superuser
                ) VALUES (
                    :username, :email, :password, :first_name, :last_name,
                    :phone, :department, :date_joined, :created_at, :updated_at,
                    :is_active, :is_staff, :is_superuser
                )
                RETURNING id, username, email, password
            """), {
                "username": "test_user_debug",
                "email": "test_user_debug@example.com",
                "password": hashed_password,
                "first_name": "Test",
                "last_name": "User",
                "phone": None,
                "department": None,
                "date_joined": "2026-01-07 12:00:00",
                "created_at": "2026-01-07 12:00:00",
                "updated_at": "2026-01-07 12:00:00",
                "is_active": True,
                "is_staff": False,
                "is_superuser": False
            })
            
            user = result.fetchone()
            
            if user:
                print(f"✓ 用户创建成功:")
                print(f"  ID: {user[0]}")
                print(f"  用户名: {user[1]}")
                print(f"  邮箱: {user[2]}")
                print(f"  密码哈希: {user[3][:50]}...")
                
                # 清理测试用户
                await session.execute(text("DELETE FROM auth_user WHERE username = :username"), {"username": "test_user_debug"})
                await session.commit()
                print(f"已清理测试用户: test_user_debug")
                
        except Exception as e:
            print(f"✗ 用户创建失败: {e}")
            import traceback
            traceback.print_exc()
            await session.rollback()
    
    print("\n" + "=" * 80)
    print("调试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(debug_user_creation())
