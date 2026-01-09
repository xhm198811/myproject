"""调试 verify_password 函数"""
import hashlib
import base64

def debug_verify_password(plain_password: str, hashed_password: str) -> bool:
    """调试密码验证函数"""
    plain_password = plain_password[:72]
    
    print(f"\n明文密码: {plain_password}")
    print(f"哈希密码: {hashed_password}")
    
    # 检查是否为 Django 风格的 pbkdf2_sha256 哈希
    if hashed_password.startswith("$pbkdf2_sha256$") or hashed_password.startswith("$pbkdf2-sha256$"):
        print("识别为 Django PBKDF2-SHA256 格式")
        
        # 使用 '$' 作为分隔符分割整个字符串
        parts = hashed_password.split('$')
        print(f"分割后的部分: {parts}")
        print(f"分割部分数量: {len(parts)}")
        
        if len(parts) >= 5:
            try:
                # parts[0] 是空字符串（因为以 $ 开头）
                # parts[1] 是算法/迭代类型
                # parts[2] 是迭代次数
                # parts[3] 是 salt
                # parts[4] 是 hash
                algorithm = parts[1]
                iterations = int(parts[2])
                salt = parts[3]
                stored_hash = parts[4]
                
                print(f"  算法: {algorithm}")
                print(f"  迭代次数: {iterations}")
                print(f"  Salt: {salt}")
                print(f"  存储的哈希: {stored_hash}")
                
                password_bytes = plain_password.encode('utf-8')
                salt_bytes = salt.encode('utf-8')
                
                print(f"  密码字节长度: {len(password_bytes)}")
                print(f"  Salt 字节长度: {len(salt_bytes)}")
                
                # 计算 PBKDF2-HMAC-SHA256
                hash_obj = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, iterations)
                print(f"  计算的哈希字节长度: {len(hash_obj)}")
                
                # Django 使用 URL-safe Base64 并去除填充符 '='
                hash_b64 = base64.urlsafe_b64encode(hash_obj).decode('ascii').rstrip('=')
                print(f"  计算的哈希 (Base64): {hash_b64}")
                print(f"  存储的哈希 (Base64): {stored_hash}")
                
                result = hash_b64 == stored_hash
                print(f"\n  验证结果: {'✓ 成功' if result else '✗ 失败'}")
                
                return result
            except (ValueError, IndexError, Exception) as e:
                print(f"  错误: {e}")
                import traceback
                traceback.print_exc()
                return False
        else:
            print("  错误: 哈希格式不正确，部分数量不足")
            return False
    else:
        print("无法识别的哈希格式")
        return False

print("=" * 70)
print("调试 verify_password 函数")
print("=" * 70)

test_password = "admin123"
print(f"\n测试密码: {test_password}")

# 生成哈希
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["pbkdf2_sha256", "bcrypt"], deprecated="auto")
hash1 = pwd_context.hash(test_password)
print(f"\n生成的哈希: {hash1}")

# 调试验证
result = debug_verify_password(test_password, hash1)
print(f"\n最终结果: {'✓ 成功' if result else '✗ 失败'}")

print("\n" + "=" * 70)
