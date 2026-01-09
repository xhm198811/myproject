"""
Django API客户端配置
用于从Django后台获取产品数据
修复与FastAPI应用的集成问题
"""
import httpx
import asyncio
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DjangoAPIClient:
    """Django API客户端"""
    
    def __init__(self, base_url: str = "http://127.0.0.1:8000/api/v1/", django_username: str = "admin", django_password: str = "admin123"):
        self.base_url = base_url.rstrip("/")
        self.client = httpx.AsyncClient(
            timeout=30.0,
            follow_redirects=True,  # 自动跟随重定向
            headers={"User-Agent": "FastAPI-Django-Integration/1.0"}  # 添加用户代理
        )
        self._auth_token: Optional[str] = None
        self.django_username = django_username
        self.django_password = django_password
        self._login_attempts = 0  # 登录尝试次数，避免无限循环
    
    async def login_and_get_token(self):
        """登录Django并获取认证令牌"""
        try:
            login_url = f"{self.base_url}/auth/login/"
            login_data = {
                "username": self.django_username,
                "password": self.django_password
            }
            
            # 发送登录请求
            response = await self.client.post(
                login_url, 
                json=login_data,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json"
                }
            )
            
            print(f"Django登录URL: {login_url}")
            print(f"Django登录响应状态: {response.status_code}")
            print(f"Django登录响应内容: {response.text[:500]}...")  # 只显示前500字符
            
            # 检查响应状态
            if response.status_code == 404:
                print("Django登录端点不存在，尝试使用通用登录端点")
                # 尝试使用通用登录端点
                login_url = f"{self.base_url}/login/"
                response = await self.client.post(
                    login_url, 
                    json=login_data,
                    headers={
                        "Content-Type": "application/json",
                        "Accept": "application/json"
                    }
                )
                print(f"通用登录响应状态: {response.status_code}")
            
            # 不使用raise_for_status，而是检查响应状态码
            if response.status_code != 200:
                print(f"登录失败，状态码: {response.status_code}")
                return False
            
            # 解析响应获取令牌
            data = response.json()
            print(f"Django登录响应数据: {data}")
            
            if data.get("success") and "data" in data and "access" in data["data"]:
                self.set_auth_token(data["data"]["access"])
                print(f"成功获取Django认证令牌")
                self._login_attempts = 0  # 重置登录尝试计数
                return True
            elif "access" in data:
                # 某些Django API可能直接返回access token
                self.set_auth_token(data["access"])
                print(f"成功获取Django认证令牌 (格式2)")
                self._login_attempts = 0
                return True
            elif "token" in data:
                # 某些Django API可能使用token字段
                self.set_auth_token(data["token"])
                print(f"成功获取Django认证令牌 (格式3)")
                self._login_attempts = 0
                return True
            else:
                print(f"登录响应格式不正确: {data}")
                return False
        except httpx.ConnectError as e:
            print(f"Django API连接失败 (请确认Django服务是否正在运行): {e}")
            return False
        except httpx.TimeoutException as e:
            print(f"Django API请求超时: {e}")
            return False
        except Exception as e:
            print(f"Django登录失败: {e}")
            return False
    
    def set_auth_token(self, token: str):
        """设置认证令牌"""
        self._auth_token = token
        # 更新客户端默认头
        self.client.headers.update({"Authorization": f"Bearer {token}"})
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "FastAPI-Django-Integration/1.0"
        }
        if self._auth_token:
            headers["Authorization"] = f"Bearer {self._auth_token}"
        return headers
    
    async def ensure_authenticated(self) -> bool:
        """确保已认证，如果未认证则尝试登录"""
        if not self._auth_token:
            if self._login_attempts >= 3:
                print("已达到最大登录尝试次数，跳过登录")
                return False
            self._login_attempts += 1
            success = await self.login_and_get_token()
            if success:
                self._login_attempts = 0  # 登录成功后重置计数
            return success
        return True
    
    async def get_products(self, page: int = 1, limit: int = 20, search: str = "") -> Dict[str, Any]:
        """获取产品列表"""
        # 确保已认证
        if not await self.ensure_authenticated():
            print("无法认证，返回空产品列表")
            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
        
        params = {
            "page": page,
            "limit": limit
        }
        
        if search:
            params["search"] = search
            
        try:
            url = f"{self.base_url}/products/"
            print(f"请求URL: {url}, 参数: {params}")
            
            # 使用认证访问
            response = await self.client.get(
                url, 
                params=params, 
                headers=self._get_headers()
            )
            
            print(f"产品列表响应状态: {response.status_code}")
            print(f"产品列表响应头: {dict(response.headers)}")
            
            # 检查响应状态
            if response.status_code == 404:
                print("产品API端点不存在，尝试替代端点")
                # 尝试使用替代端点
                alt_url = f"{self.base_url}/products/list/"
                response = await self.client.get(
                    alt_url, 
                    params=params, 
                    headers=self._get_headers()
                )
                print(f"替代端点响应状态: {response.status_code}")
            
            response.raise_for_status()
            
            # Django API 返回的是数组格式，需要转换为分页格式
            raw_data = response.json()
            print(f"原始响应数据类型: {type(raw_data)}, 长度: {len(str(raw_data)) if hasattr(raw_data, '__len__') else 'N/A'}")
            
            # 检查数据格式
            if isinstance(raw_data, list):
                # 如果是列表格式，包装成分页格式
                total = len(raw_data)
                start = (page - 1) * limit
                end = min(start + limit, total)
                
                return {
                    "count": total,
                    "results": raw_data[start:end],
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit
                }
            elif isinstance(raw_data, dict):
                # 如果已经是分页格式，直接返回
                if "results" in raw_data:
                    return raw_data
                elif "items" in raw_data:
                    # 兼容items格式
                    items = raw_data["items"]
                    total = raw_data.get("total", len(items))
                    return {
                        "count": total,
                        "results": items,
                        "page": raw_data.get("page", page),
                        "limit": raw_data.get("limit", limit),
                        "total_pages": (total + limit - 1) // limit
                    }
                else:
                    # 如果是单个对象，包装成列表
                    return {
                        "count": 1,
                        "results": [raw_data],
                        "page": page,
                        "limit": limit,
                        "total_pages": 1
                    }
            else:
                print(f"未知的数据格式: {type(raw_data)}")
                return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                
        except httpx.HTTPStatusError as e:
            print(f"HTTP错误状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
            
            if e.response.status_code == 401:
                print("认证失败，清除令牌并尝试重新登录...")
                self._auth_token = None  # 清除无效令牌
                if await self.ensure_authenticated():  # 重新认证
                    # 使用新令牌重试
                    try:
                        response = await self.client.get(
                            url, 
                            params=params, 
                            headers=self._get_headers()
                        )
                        response.raise_for_status()
                        
                        # 处理重试后的响应
                        raw_data = response.json()
                        if isinstance(raw_data, list):
                            total = len(raw_data)
                            start = (page - 1) * limit
                            end = min(start + limit, total)
                            
                            return {
                                "count": total,
                                "results": raw_data[start:end],
                                "page": page,
                                "limit": limit,
                                "total_pages": (total + limit - 1) // limit
                            }
                        elif isinstance(raw_data, dict) and "results" in raw_data:
                            return raw_data
                        else:
                            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                    except Exception as e2:
                        print(f"重试也失败: {e2}")
                        return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                else:
                    return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
            else:
                print(f"获取产品列表失败: {e}")
                return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
        except httpx.ConnectError as e:
            print(f"连接Django API失败: {e}")
            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
        except Exception as e:
            print(f"获取产品列表失败: {e}")
            import traceback
            traceback.print_exc()
            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
    
    async def get_product_detail(self, product_id: int) -> Dict:
        """获取产品详情"""
        # 确保已认证
        if not await self.ensure_authenticated():
            return {"error": "认证失败"}
            
        try:
            url = f"{self.base_url}/products/{product_id}/"
            response = await self.client.get(url, headers=self._get_headers())
            
            if response.status_code == 404:
                # 尝试替代端点
                alt_url = f"{self.base_url}/products/detail/{product_id}/"
                response = await self.client.get(alt_url, headers=self._get_headers())
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取产品详情失败: {e}")
            return {"error": str(e)}
    
    async def get_product_price(self, product_id: int) -> Dict:
        """获取产品价格"""
        # 确保已认证
        if not await self.ensure_authenticated():
            return {"price": 0, "error": "认证失败"}
            
        try:
            url = f"{self.base_url}/products/{product_id}/price/"
            response = await self.client.get(url, headers=self._get_headers())
            
            if response.status_code == 404:
                # 尝试替代端点
                alt_url = f"{self.base_url}/products/{product_id}/pricing/"
                response = await self.client.get(alt_url, headers=self._get_headers())
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取产品价格失败: {e}")
            return {"price": 0, "error": str(e)}
    
    async def get_materials(self) -> List[Dict]:
        """获取材质列表"""
        # 确保已认证
        if not await self.ensure_authenticated():
            return []
            
        try:
            url = f"{self.base_url}/materials/"
            response = await self.client.get(url, headers=self._get_headers())
            
            if response.status_code == 404:
                # 尝试替代端点
                alt_url = f"{self.base_url}/material-options/"
                response = await self.client.get(alt_url, headers=self._get_headers())
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取材质列表失败: {e}")
            return []
    
    async def get_board_types(self) -> List[Dict]:
        """获取背衬类型列表"""
        # 确保已认证
        if not await self.ensure_authenticated():
            return []
            
        try:
            url = f"{self.base_url}/board-types/"
            response = await self.client.get(url, headers=self._get_headers())
            
            if response.status_code == 404:
                # 尝试替代端点
                alt_url = f"{self.base_url}/backing-options/"
                response = await self.client.get(alt_url, headers=self._get_headers())
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取背衬类型列表失败: {e}")
            return []
    
    async def get_quotation_history(self, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """获取报价记录历史"""
        # 确保已认证
        if not await self.ensure_authenticated():
            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
            
        params = {
            "page": page,
            "limit": limit
        }
        
        try:
            url = f"{self.base_url}/quotation/history/"
            print(f"请求报价记录URL: {url}")
            
            response = await self.client.get(url, params=params, headers=self._get_headers())
            
            if response.status_code == 404:
                # 尝试替代端点
                alt_url = f"{self.base_url}/quotes/history/"
                response = await self.client.get(alt_url, params=params, headers=self._get_headers())
            
            response.raise_for_status()
            raw_data = response.json()
            
            # 标准化响应格式
            if isinstance(raw_data, list):
                total = len(raw_data)
                start = (page - 1) * limit
                end = min(start + limit, total)
                
                return {
                    "count": total,
                    "results": raw_data[start:end],
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit
                }
            elif isinstance(raw_data, dict) and "results" in raw_data:
                return raw_data
            else:
                return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                print("认证失败，尝试重新登录...")
                self._auth_token = None  # 清除无效令牌
                if await self.ensure_authenticated():  # 重新认证
                    # 使用新令牌重试
                    try:
                        response = await self.client.get(url, params=params, headers=self._get_headers())
                        response.raise_for_status()
                        raw_data = response.json()
                        
                        if isinstance(raw_data, list):
                            total = len(raw_data)
                            start = (page - 1) * limit
                            end = min(start + limit, total)
                            
                            return {
                                "count": total,
                                "results": raw_data[start:end],
                                "page": page,
                                "limit": limit,
                                "total_pages": (total + limit - 1) // limit
                            }
                        elif isinstance(raw_data, dict) and "results" in raw_data:
                            return raw_data
                        else:
                            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                    except Exception as e2:
                        print(f"重试也失败: {e2}")
                        return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                else:
                    return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
            else:
                print(f"获取报价记录失败: {e}")
                return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
        except Exception as e:
            print(f"获取报价记录失败: {e}")
            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
    
    async def create_product(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """创建新产品"""
        # 确保已认证
        if not await self.ensure_authenticated():
            return {"status": 1, "msg": "认证失败", "data": {}}
            
        try:
            url = f"{self.base_url}/products/"
            print(f"创建产品URL: {url}")
            print(f"产品数据: {product_data}")
            
            response = await self.client.post(
                url, 
                json=product_data, 
                headers=self._get_headers()
            )
            
            print(f"创建产品响应状态: {response.status_code}")
            
            if response.status_code == 404:
                # 尝试替代端点
                alt_url = f"{self.base_url}/products/create/"
                response = await self.client.post(
                    alt_url, 
                    json=product_data, 
                    headers=self._get_headers()
                )
                print(f"替代端点响应状态: {response.status_code}")
            
            response.raise_for_status()
            
            result = response.json()
            print(f"创建产品响应数据: {result}")
            
            return {"status": 0, "msg": "产品创建成功", "data": result}
            
        except httpx.HTTPStatusError as e:
            print(f"HTTP错误状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
            
            if e.response.status_code == 401:
                print("认证失败，清除令牌并尝试重新登录...")
                self._auth_token = None
                if await self.ensure_authenticated():
                    try:
                        response = await self.client.post(
                            url, 
                            json=product_data, 
                            headers=self._get_headers()
                        )
                        response.raise_for_status()
                        result = response.json()
                        return {"status": 0, "msg": "产品创建成功", "data": result}
                    except Exception as e2:
                        print(f"重试也失败: {e2}")
                        return {"status": 1, "msg": f"创建产品失败: {str(e2)}", "data": {}}
                else:
                    return {"status": 1, "msg": "认证失败", "data": {}}
            else:
                return {"status": 1, "msg": f"创建产品失败: {e.response.text}", "data": {}}
        except Exception as e:
            print(f"创建产品失败: {e}")
            import traceback
            traceback.print_exc()
            return {"status": 1, "msg": f"创建产品失败: {str(e)}", "data": {}}
    
    async def close(self):
        """关闭客户端"""
        await self.client.aclose()
    
    async def get_users(self, page: int = 1, limit: int = 20, search: str = "") -> Dict[str, Any]:
        """获取用户列表"""
        if not await self.ensure_authenticated():
            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
        
        params = {
            "page": page,
            "limit": limit
        }
        
        if search:
            params["search"] = search
        
        try:
            url = f"{self.base_url}/users/"
            print(f"请求用户列表URL: {url}, 参数: {params}")
            
            response = await self.client.get(
                url, 
                params=params, 
                headers=self._get_headers()
            )
            
            print(f"用户列表响应状态: {response.status_code}")
            
            if response.status_code == 404:
                alt_url = f"{self.base_url}/users/list/"
                response = await self.client.get(
                    alt_url, 
                    params=params, 
                    headers=self._get_headers()
                )
                print(f"替代端点响应状态: {response.status_code}")
            
            response.raise_for_status()
            raw_data = response.json()
            
            if isinstance(raw_data, list):
                total = len(raw_data)
                start = (page - 1) * limit
                end = min(start + limit, total)
                
                return {
                    "count": total,
                    "results": raw_data[start:end],
                    "page": page,
                    "limit": limit,
                    "total_pages": (total + limit - 1) // limit
                }
            elif isinstance(raw_data, dict):
                if "results" in raw_data:
                    return raw_data
                elif "items" in raw_data:
                    items = raw_data["items"]
                    total = raw_data.get("total", len(items))
                    return {
                        "count": total,
                        "results": items,
                        "page": raw_data.get("page", page),
                        "limit": raw_data.get("limit", limit),
                        "total_pages": (total + limit - 1) // limit
                    }
                else:
                    return {
                        "count": 1,
                        "results": [raw_data],
                        "page": page,
                        "limit": limit,
                        "total_pages": 1
                    }
            else:
                print(f"未知的数据格式: {type(raw_data)}")
                return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                
        except httpx.HTTPStatusError as e:
            print(f"HTTP错误状态码: {e.response.status_code}")
            print(f"响应内容: {e.response.text}")
            
            if e.response.status_code == 401:
                print("认证失败，清除令牌并尝试重新登录...")
                self._auth_token = None
                if await self.ensure_authenticated():
                    try:
                        response = await self.client.get(
                            url, 
                            params=params, 
                            headers=self._get_headers()
                        )
                        response.raise_for_status()
                        
                        raw_data = response.json()
                        if isinstance(raw_data, list):
                            total = len(raw_data)
                            start = (page - 1) * limit
                            end = min(start + limit, total)
                            
                            return {
                                "count": total,
                                "results": raw_data[start:end],
                                "page": page,
                                "limit": limit,
                                "total_pages": (total + limit - 1) // limit
                            }
                        elif isinstance(raw_data, dict) and "results" in raw_data:
                            return raw_data
                        else:
                            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                    except Exception as e2:
                        print(f"重试也失败: {e2}")
                        return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
                else:
                    return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
            else:
                print(f"获取用户列表失败: {e}")
                return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
        except httpx.ConnectError as e:
            print(f"连接Django API失败: {e}")
            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
        except Exception as e:
            print(f"获取用户列表失败: {e}")
            import traceback
            traceback.print_exc()
            return {"count": 0, "results": [], "page": page, "limit": limit, "total_pages": 0}
    
    async def get_user_detail(self, user_id: int) -> Dict:
        """获取用户详情"""
        if not await self.ensure_authenticated():
            return {"error": "认证失败"}
        
        try:
            url = f"{self.base_url}/users/{user_id}/"
            response = await self.client.get(url, headers=self._get_headers())
            
            if response.status_code == 404:
                alt_url = f"{self.base_url}/users/detail/{user_id}/"
                response = await self.client.get(alt_url, headers=self._get_headers())
            
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"获取用户详情失败: {e}")
            return {"error": str(e)}

# 全局客户端实例
django_client = DjangoAPIClient()

async def test_django_connection():
    """测试Django API连接"""
    try:
        print("开始测试Django API连接...")
        print(f"Django API基础URL: {django_client.base_url}")
        
        # 测试登录
        login_success = await django_client.login_and_get_token()
        if not login_success:
            print("Django登录失败，无法继续测试")
            return False
        
        # 测试获取产品列表
        products = await django_client.get_products()
        print(f"成功获取产品数据: {len(products.get('results', []))} 个产品")
        
        # 显示第一个产品的详细信息（如果有）
        if products.get('results'):
            first_product = products['results'][0]
            print(f"第一个产品: {first_product}")
        
        return True
    except Exception as e:
        print(f"Django API连接测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_django_connection())



