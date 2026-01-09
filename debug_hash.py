"""
详细调试 Django PBKDF2 哈希解析
"""
import hashlib
import base64

def debug_django_hash(hashed_password: str, plain_password: str = "password123"):
    """详细调试 Django 哈希解析"""
    print("=" * 70)
    print("详细调试 Django PBKDF2 哈希解析")
    print("=" * 70)
    
    print(f"\n原始哈希: {hashed_password}")
    print(f"明文密码: {plain_password}")
    
    parts = hashed_password.split('$')
    print(f"\n按 '$' 分割后的 parts 数组:")
    for i, part in enumerate(parts):
        print(f"  parts[{i}] = '{part}' (长度: {len(part)})")
    
    if len(parts) >= 5:
        print("\n提取组件:")
        print(f"  parts[0] (算法前缀): '{parts[0]}'")
        print(f"  parts[1] (算法类型): '{parts[1]}'")
        print(f"  parts[2] (迭代次数): '{parts[2]}'")
        print(f"  parts[3] (salt): '{parts[3]}'")
        print(f"  parts[4] (哈希值): '{parts[4]}'")
        
        try:
            iterations = int(parts[2])
            salt = parts[3]
            stored_hash = parts[4]
            
            print(f"\n迭代次数: {iterations}")
            print(f"Salt: '{salt}'")
            print(f"存储的哈希: '{stored_hash}'")
            
            password_bytes = plain_password.encode('utf-8')
            salt_bytes = salt.encode('utf-8')
            
            hash_obj = hashlib.pbkdf2_hmac('sha256', password_bytes, salt_bytes, iterations)
            hash_b64 = base64.urlsafe_b64encode(hash_obj).decode('ascii').rstrip('=')
            
            print(f"\n计算得到的哈希: '{hash_b64}'")
            print(f"存储的哈希:       '{stored_hash}'")
            print(f"哈希长度对比: 计算={len(hash_b64)}, 存储={len(stored_hash)}")
            print(f"\n匹配结果: {hash_b64 == stored_hash}")
            
            if hash_b64 != stored_hash:
                print("\n调试: 尝试不同的编码方式...")
                
                # 尝试标准 Base64
                hash_b64_std = base64.b64encode(hash_obj).decode('ascii')
                print(f"标准 Base64: '{hash_b64_std}'")
                
                # 检查是否有尾随 = 被错误处理
                print(f"\n存储的哈希包含 '=' 吗? { '=' in stored_hash }")
                print(f"计算得到的哈希包含 '=' 吗? { '=' in hash_b64 }")
                
        except Exception as e:
            print(f"\n错误: {e}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    # 测试用户 abc 的哈希
    test_hash = "$pbkdf2-sha256$29000$klKq9f7fu/de6z1HCEFISQ$zhoCHjJWJlyOzY9oPBu6/Vxkq7CzAa0klDakFSLrKDw"
    debug_django_hash(test_hash)
