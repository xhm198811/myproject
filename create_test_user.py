"""创建测试用户"""
import asyncio
import httpx

BASE_URL = "http://localhost:8001"

async def create_test_user():
    """创建测试用户"""
    print("=" * 70)
    print("创建测试用户")
    print("=" * 70)
    
    async with httpx.AsyncClient() as client:
        # 先登录获取 token
        login_data = {
            "username": "admin",
            "password": "admin123"
        }
        
        print(f"\n1. 登录获取令牌...")
        response = await client.post(
            f"{BASE_URL}/api/token",
            data=login_data,
            timeout=4
        )
        
        if response.status_code != 200:
            print(f"✗ 登录失败: {response.text}")
            return
        
        token_data = response.json()
        access_token = token_data.get("access_token")
        print(f"✓ 登录成功")
        
        headers = {
            "Authorization": f"Bearer {access_token}"
        }
        
        # 创建测试用户
        test_user_data = {
            "username": "testuser2",
            "email": "testuser2@example.com",
            "password": "test123",
            "first_name": "测试",
            "last_name": "用户",
            "is_active": True,
            "is_staff": False,
            "is_superuser": False
        }
        
        print(f"\n2. 创建测试用户...")
        print(f"  用户名: {test_user_data['username']}")
        print(f"  邮箱: {test_user_data['email']}")
        
        response = await client.post(
            f"{BASE_URL}/api/django-users/create",
            json=test_user_data,
            headers=headers,
            timeout=10.0
        )
        
        print(f"\n3. 创建用户响应:")
        print(f"  状态码: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"  消息: {result.get('msg', '')}")
            print(f"  用户ID: {result.get('data', {}).get('id', '')}")
            print(f"✓ 用户创建成功")
        else:
            print(f"  响应内容: {response.text}")
            print(f"✗ 用户创建失败")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    asyncio.run(create_test_user())
