from fastapi import Request, Response
from fastapi.responses import RedirectResponse, FileResponse
import os
import re
import logging

logger = logging.getLogger(__name__)

async def amis_cdn_middleware(request: Request, call_next):
    """Amis CDN中间件，将CDN请求重定向到本地文件"""
    path = request.url.path
    
    # 检查是否是Amis CDN请求
    if re.search(r"/static/amis/[^/]+/[^/]+/[^/]+$", path):
        # 提取文件名
        filename = path.split("/")[-1]
        
        # 检查文件是否存在于本地
        file_path = os.path.join("E:/HSdigitalportal/fastapi_amis_admin/static/amis", filename)
        if os.path.exists(file_path):
            try:
                # 设置适当的缓存头
                headers = {
                    "Cache-Control": "public, max-age=86400",  # 缓存1天
                    "Access-Control-Allow-Origin": "*",
                }
                
                # 返回本地文件
                return FileResponse(file_path, headers=headers)
            except Exception as e:
                logger.error(f"Error serving file {file_path}: {e}")
    
    # 如果不是Amis CDN请求或文件不存在，继续处理
    response = await call_next(request)
    return response