"""
修复 Django User 模型的 password 字段
将明文密码转换为 Django 的哈希格式
"""
import os
import sys
import django

# 添加 Django 项目路径
sys.path.insert(0, 'E:\\HSdigitalportal\\enterprise_portal')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'enterprise_portal.settings')

# 初始化 Django
django.setup()

from user_auth.models import User

def fix_user_password():
    """修复用户密码字段"""
    
    print("=" * 80)
    print("修复 Django User 模型的 password 字段")
    print("=" * 80)
    
    try:
        # 获取 admin 用户
        user = User.objects.get(username='admin')
        
        print(f"\n当前用户信息:")
        print(f"  用户名: {user.username}")
        print(f"  当前 password 字段: {user.password}")
        
        # 设置密码为哈希格式
        new_password = "admin123"
        user.set_password(new_password)
        user.save()
        
        print(f"\n密码已更新:")
        print(f"  新 password 字段: {user.password[:50]}...")
        
        # 验证密码
        print(f"\n验证密码:")
        is_valid = user.check_password(new_password)
        print(f"  密码 '{new_password}' 验证: {'✓ 成功' if is_valid else '✗ 失败'}")
        
        # 检查其他字段
        print(f"\n用户状态:")
        print(f"  is_staff: {user.is_staff}")
        print(f"  is_superuser: {user.is_superuser}")
        print(f"  is_active: {user.is_active}")
        
        print("\n✓ 密码修复完成！现在应该可以登录 Django admin 了。")
        
    except User.DoesNotExist:
        print("✗ 未找到 admin 用户")
    except Exception as e:
        print(f"✗ 修复失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    fix_user_password()
