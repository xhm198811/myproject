from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import time
from collections import defaultdict
from typing import Dict, Tuple

class RateLimitMiddleware(BaseHTTPMiddleware):
    """速率限制中间件"""
    
    def __init__(self, app, requests_per_minute: int = 60):
        """初始化速率限制中间件"""
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.rate_limit_store: Dict[str, Dict[str, Tuple[int, float]]] = defaultdict(dict)
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求并进行速率限制检查"""
        # 获取客户端IP地址
        client_ip = request.client.host if request.client else "unknown"
        path = request.url.path
        key = f"{client_ip}:{path}"
        
        # 获取当前时间
        current_time = time.time()
        
        # 获取该客户端在该路径的请求记录
        request_info = self.rate_limit_store.get(key)
        
        if request_info:
            request_count, window_start = request_info
            
            # 计算窗口时间（1分钟）
            window_end = window_start + 60
            
            if current_time < window_end:
                # 在同一窗口内
                if request_count >= self.requests_per_minute:
                    # 超出速率限制
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="请求过于频繁，请稍后再试"
                    )
                else:
                    # 增加请求计数
                    self.rate_limit_store[key] = (request_count + 1, window_start)
            else:
                # 窗口过期，重置计数
                self.rate_limit_store[key] = (1, current_time)
        else:
            # 第一次请求，初始化计数
            self.rate_limit_store[key] = (1, current_time)
        
        # 处理请求
        response = await call_next(request)
        
        # 设置速率限制响应头
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(
            self.requests_per_minute - self.rate_limit_store[key][0]
        )
        response.headers["X-RateLimit-Reset"] = str(
            int(self.rate_limit_store[key][1] + 60)
        )
        
        return response
