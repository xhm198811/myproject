from fastapi import Request, Response
from fastapi.responses import JSONResponse
import logging
import traceback
import time
from typing import Callable, Any
import json

logger = logging.getLogger(__name__)

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response

class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """增强的错误处理中间件"""
    
    def __init__(self, app):
        super().__init__(app)
        self.request_start_time = {}
    
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """处理请求并捕获错误"""
        request_id = id(request)
        start_time = time.time()
        self.request_start_time[request_id] = start_time
        
        try:
            # 记录请求开始
            logger.info(f"开始处理请求 - {request.method} {request.url.path}")
            
            # 处理请求
            response = await call_next(request)
            
            # 记录响应时间和状态
            duration = time.time() - start_time
            
            # 记录4xx和5xx错误请求的详细信息
            if response.status_code >= 400:
                try:
                    # 尝试读取请求体用于调试（只在非400错误时读取）
                    body_str = "无请求体"
                    if response.status_code != 400:
                        try:
                            body = await request.body()
                            body_str = body.decode('utf-8') if body else "无请求体"
                        except Exception:
                            body_str = "无法读取请求体"
                except Exception:
                    body_str = "无法读取请求体"
                
                logger.warning(f"请求错误 - {request.method} {request.url.path} - 状态码: {response.status_code} - 耗时: {duration:.2f}ms - 请求体: {body_str[:500]}")
            else:
                logger.info(f"请求完成 - {request.method} {request.url.path} - 状态码: {response.status_code} - 耗时: {duration:.2f}ms")
            
            return response
            
        except Exception as e:
            # 捕获所有未处理的异常
            duration = time.time() - start_time
            logger.error(f"请求失败 - {request.method} {request.url.path} - 耗时: {duration:.2f}ms")
            logger.error(f"错误详情: {str(e)}")
            logger.error(f"错误堆栈: {traceback.format_exc()}")
            
            # 返回友好的错误响应
            error_response = {
                "status": 1,
                "msg": f"服务器内部错误: {str(e)}",
                "data": None,
                "error_type": type(e).__name__,
                "request_id": str(request_id),
                "path": request.url.path,
                "method": request.method
            }
            
            return JSONResponse(
                status_code=500,
                content=error_response,
                headers={
                    "Content-Type": "application/json",
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                }
            )
        
        finally:
            # 清理请求时间记录
            if request_id in self.request_start_time:
                del self.request_start_time[request_id]

async def log_request_middleware(request: Request, call_next: Callable) -> Response:
    """请求日志中间件"""
    start_time = time.time()
    
    # 记录请求开始
    logger.info(f"开始处理请求 - {request.method} {request.url.path}")
    
    try:
        response = await call_next(request)
        
        # 记录响应
        duration = time.time() - start_time
        logger.info(f"请求完成 - {request.method} {request.url.path} - 状态码: {response.status_code} - 耗时: {duration:.2f}ms")
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"请求失败 - {request.method} {request.url.path} - 耗时: {duration:.2f}ms")
        logger.error(f"错误详情: {str(e)}")
        logger.error(f"错误堆栈: {traceback.format_exc()}")
        
        # 重新抛出异常让错误处理中间件处理
        raise

async def chunked_encoding_fix_middleware(request: Request, call_next: Callable) -> Response:
    """修复chunked编码问题的中间件"""
    try:
        response = await call_next(request)
        
        # 确保响应有正确的Content-Length头
        if hasattr(response, 'body') and response.body:
            content_length = len(response.body)
            response.headers['Content-Length'] = str(content_length)
        
        # 设置适当的缓存和连接头
        response.headers['Connection'] = 'keep-alive'
        response.headers['Keep-Alive'] = 'timeout=5, max=100'
        
        return response
        
    except Exception as e:
        logger.error(f"Chunked编码中间件错误: {str(e)}")
        raise

async def cors_middleware(request: Request, call_next: Callable) -> Response:
    """CORS中间件"""
    response = await call_next(request)
    
    # 添加CORS头
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, X-Requested-With'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    # 处理预检请求
    if request.method == 'OPTIONS':
        return Response(status_code=200, headers=response.headers)
    
    return response