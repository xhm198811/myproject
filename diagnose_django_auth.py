"""
详细诊断 Django Admin 认证过程
"""
import os
import sys
import django

# 添加 Django 项目路径
sys.path.insert(0, 'E:\\HSdigitalportal\\enterprise_portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_portal.settings')

# 初始化 Django
django.setup()

from django.contrib.auth import authenticate
from django.contrib.auth.models import User as DjangoUser
from user_auth.models import User

def diagnose_django_auth():
    """诊断 Django 认证过程"""
    
    print("=" * 80)
    print("Django Admin 认证过程详细诊断")
    print("=" * 80)
    
    # 1. 检查自定义 User 模型
    print("\n【步骤 1】检查自定义 User 模型")
    print("-" * 80)
    
    try:
        user = User.objects.get(username='admin')
        print(f"✓ 找到用户: {user.username}")
        print(f"  ID: {user.id}")
        print(f"  邮箱: {user.email}")
        print(f"  is_staff: {user.is_staff}")
        print(f"  is_superuser: {user.is_superuser}")
        print(f"  is_active: {user.is_active}")
        print(f"  password 字段: {user.password}")
        print(f"  hashed_password 字段: {user.hashed_password[:50]}...")
    except User.DoesNotExist:
        print("✗ 未找到 admin 用户")
        return False
    except Exception as e:
        print(f"✗ 查询用户失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 测试 Django authenticate 函数
    print("\n【步骤 2】测试 Django authenticate 函数")
    print("-" * 80)
    
    test_passwords = ['admin', 'admin123', 'password123']
    
    for password in test_passwords:
        print(f"\n测试密码: {password}")
        
        authenticated_user = authenticate(username='admin', password=password)
        
        if authenticated_user:
            print(f"  ✓ 认证成功")
            print(f"    用户名: {authenticated_user.username}")
            print(f"    is_staff: {authenticated_user.is_staff}")
            print(f"    is_superuser: {authenticated_user.is_superuser}")
            print(f"    is_active: {authenticated_user.is_active}")
        else:
            print(f"  ✗ 认证失败")
    
    # 3. 检查密码验证
    print("\n【步骤 3】检查密码验证机制")
    print("-" * 80)
    
    from django.contrib.auth.hashers import check_password
    
    for password in test_passwords:
        print(f"\n测试密码: {password}")
        
        # 检查 password 字段（明文）
        is_valid_plain = (password == user.password)
        print(f"  password 字段（明文）: {'✓ 匹配' if is_valid_plain else '✗ 不匹配'}")
        
        # 检查 hashed_password 字段（哈希）
        is_valid_hashed = check_password(password, user.hashed_password)
        print(f"  hashed_password 字段（哈希）: {'✓ 匹配' if is_valid_hashed else '✗ 不匹配'}")
        
        # 检查 Django 默认的 password 字段
        is_valid_django = check_password(password, user.password)
        print(f"  Django password 字段: {'✓ 匹配' if is_valid_django else '✗ 不匹配'}")
    
    # 4. 检查 User 模型的认证方法
    print("\n【步骤 4】检查 User 模型的认证方法")
    print("-" * 80)
    
    print(f"User 模型类: {User.__name__}")
    print(f"User 模型基类: {[base.__name__ for base in User.__bases__]}")
    print(f"User 模型表名: {User._meta.db_table}")
    
    # 检查是否有自定义的认证方法
    if hasattr(user, 'check_password'):
        print(f"✓ User 模型有 check_password 方法")
    else:
        print(f"✗ User 模型没有 check_password 方法")
    
    # 5. 测试用户对象的方法
    print("\n【步骤 5】测试用户对象的方法")
    print("-" * 80)
    
    for password in test_passwords:
        print(f"\n测试密码: {password}")
        
        # 使用 user.check_password 方法
        if hasattr(user, 'check_password'):
            is_valid = user.check_password(password)
            print(f"  user.check_password(): {'✓ 匹配' if is_valid else '✗ 不匹配'}")
        
        # 使用 user.authenticate 方法（如果存在）
        if hasattr(user, 'authenticate'):
            is_valid = user.authenticate(password)
            print(f"  user.authenticate(): {'✓ 匹配' if is_valid else '✗ 不匹配'}")
    
    # 6. 检查 Django 认证后端
    print("\n【步骤 6】检查 Django 认证后端配置")
    print("-" * 80)
    
    from django.conf import settings
    
    print(f"AUTHENTICATION_BACKENDS:")
    for backend in settings.AUTHENTICATION_BACKENDS:
        print(f"  - {backend}")
    
    print(f"\nAUTH_USER_MODEL: {settings.AUTH_USER_MODEL}")
    
    # 7. 提供修复建议
    print("\n【步骤 7】修复建议")
    print("-" * 80)
    
    print("根据诊断结果，可能的问题和解决方案:")
    
    # 检查 password 字段是否是哈希格式
    if not user.password.startswith('pbkdf2_sha256$') and not user.password.startswith('bcrypt$'):
        print("\n1. password 字段不是哈希格式")
        print("   Django 的 authenticate 函数期望 password 字段是哈希格式")
        print("   解决方案:")
        print("   - 选项 1: 修改 User 模型，让 password 字段存储哈希密码")
        print("   - 选项 2: 创建自定义认证后端，使用 hashed_password 字段")
        print("   - 选项 3: 重写 User 模型的 check_password 方法")
    
    # 检查 hashed_password 字段是否可用
    if user.hashed_password.startswith('pbkdf2_sha256$') or user.hashed_password.startswith('bcrypt$'):
        print("\n2. hashed_password 字段是正确的哈希格式")
        print("   可以创建自定义认证后端使用此字段")
    
    print("\n建议的修复方案:")
    print("创建自定义认证后端，使用 hashed_password 字段进行认证")


if __name__ == "__main__":
    diagnose_django_auth()
