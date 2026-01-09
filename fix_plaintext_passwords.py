#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复用户明文密码问题
将数据库中的明文密码转换为PBKDF2-SHA256哈希格式
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from passlib.context import CryptContext

from app.core.config import settings


def fix_plaintext_passwords():
    """修复明文密码问题"""
    print("=" * 100)
    print("用户明文密码修复工具")
    print("=" * 100)
    print()

    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    try:
        engine = create_engine(settings.DATABASE_URL, echo=False)

        with engine.connect() as conn:
            print("1. 查找需要修复的用户...")
            print("-" * 100)

            result = conn.execute(text("""
                SELECT 
                    id,
                    username,
                    hashed_password,
                    CASE 
                        WHEN hashed_password IS NULL THEN 'NULL'
                        WHEN length(hashed_password) < 20 THEN '明文密码'
                        ELSE '已哈希'
                    END as password_type
                FROM auth_user
                ORDER BY id
            """))

            users = result.fetchall()
            print(f"总共 {len(users)} 个用户\n")

            users_to_fix = []
            for user in users:
                print(f"  用户: {user[1]} (ID:{user[0]}) - 密码: {user[2]}")
                if user[2] and len(user[2]) < 20 and not user[2].startswith('$'):
                    users_to_fix.append(user)

            print()
            print(f"需要修复的用户数量: {len(users_to_fix)}")
            print()

            if users_to_fix:
                print("2. 开始修复明文密码...")
                print("-" * 100)

                fixed_count = 0
                for user in users_to_fix:
                    user_id = user[0]
                    username = user[1]
                    old_password = user[2]

                    new_hash = pwd_context.hash(old_password)

                    print(f"  修复用户: {username} (ID:{user_id})")
                    print(f"    旧密码: {old_password}")
                    print(f"    新哈希: {new_hash[:50]}...")

                    conn.execute(
                        text("UPDATE auth_user SET hashed_password = :new_hash WHERE id = :user_id"),
                        {"new_hash": new_hash, "user_id": user_id}
                    )
                    fixed_count += 1

                conn.commit()
                print()
                print(f"成功修复 {fixed_count} 个用户的密码")
                print()
            else:
                print("2. 没有发现需要修复的明文密码")
                print()

            print("3. 验证修复结果...")
            print("-" * 100)

            result = conn.execute(text("""
                SELECT 
                    id,
                    username,
                    hashed_password,
                    LEFT(hashed_password, 60) as hash_preview
                FROM auth_user
                ORDER BY id
            """))

            users_after = result.fetchall()
            print(f"{'ID':<5} {'用户名':<15} {'密码哈希预览':<65} {'长度'}")
            print("-" * 90)

            for user in users_after:
                pwd_len = len(user[2]) if user[2] else 0
                print(f"{user[0]:<5} {user[1]:<15} {user[3]:<65} {pwd_len}")

            print()

            django_format = 0
            passlib_format = 0
            other_format = 0

            for user in users_after:
                hash_val = user[2] if user[2] else ''
                if hash_val.startswith('pbkdf2_sha256$') or hash_val.startswith('$pbkdf2'):
                    django_format += 1
                elif hash_val.startswith('$') or 'pbkdf2' in hash_val.lower():
                    passlib_format += 1
                else:
                    other_format += 1

            print(f"  - PBKDF2格式: {django_format} 人")
            print(f"  - Passlib格式: {passlib_format} 人")
            print(f"  - 其他格式: {other_format} 人")
            print()

            if other_format == 0:
                print("所有用户密码已正确哈希!")
            else:
                print("仍有用户密码需要进一步处理")

        engine.dispose()

    except SQLAlchemyError as e:
        print(f"数据库错误: {e}")
        return False
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


def test_password_verification():
    """测试密码验证功能"""
    print()
    print("=" * 100)
    print("密码验证测试")
    print("=" * 100)
    print()

    pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

    try:
        engine = create_engine(settings.DATABASE_URL, echo=False)

        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT id, username, hashed_password FROM auth_user ORDER BY id
            """))

            users = result.fetchall()
            print(f"{'ID':<5} {'用户名':<15} {'测试结果'}")
            print("-" * 50)

            for user in users:
                user_id = user[0]
                username = user[1]
                stored_hash = user[2]

                test_passwords = ['password123', 'admin123', '123456', 'password', username]

                found_password = None
                for pwd in test_passwords:
                    if pwd_context.verify(pwd, stored_hash):
                        found_password = pwd
                        break

                if found_password:
                    print(f"{user_id:<5} {username:<15} 密码可能是: {found_password}")
                else:
                    print(f"{user_id:<5} {username:<15} 未找到匹配密码")

        engine.dispose()

    except SQLAlchemyError as e:
        print(f"数据库错误: {e}")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    print("开始执行密码修复...")
    print()

    success = fix_plaintext_passwords()
    test_password_verification()

    if success:
        print()
        print("=" * 100)
        print("修复完成")
        print("=" * 100)
    else:
        print("修复失败")
        sys.exit(1)
