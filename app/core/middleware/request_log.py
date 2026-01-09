from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response
import time
from app.core.logging import logger

class RequestLogMiddleware(BaseHTTPMiddleware):
    """请求日志中间件"""
    
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        """处理请求并记录日志"""
        # 记录请求开始时间
        start_time = time.time()
        
        # 记录请求信息
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        url = str(request.url)
        headers = dict(request.headers)
        
        # 移除敏感信息
        if "authorization" in headers:
            headers["authorization"] = "Bearer ***"
        if "cookie" in headers:
            headers["cookie"] = "***"
        
        logger.info(
            f"请求开始 - {method} {url} - IP: {client_ip}",
            extra={
                "client_ip": client_ip,
                "method": method,
                "url": url,
                "headers": headers
            }
        )
        
        try:
            # 处理请求
            response = await call_next(request)
        except Exception as e:
            # 记录异常信息
            end_time = time.time()
            process_time = (end_time - start_time) * 1000
            logger.error(
                f"请求异常 - {method} {url} - IP: {client_ip} - 耗时: {process_time:.2f}ms - 异常: {str(e)}",
                extra={
                    "client_ip": client_ip,
                    "method": method,
                    "url": url,
                    "process_time": process_time,
                    "error": str(e)
                }
            )
            raise e
        
        # 记录响应信息
        end_time = time.time()
        process_time = (end_time - start_time) * 1000
        status_code = response.status_code
        
        logger.info(
            f"请求完成 - {method} {url} - IP: {client_ip} - 状态码: {status_code} - 耗时: {process_time:.2f}ms",
            extra={
                "client_ip": client_ip,
                "method": method,
                "url": url,
                "status_code": status_code,
                "process_time": process_time
            }
        )
        
        return response
