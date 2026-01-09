from fastapi import Request, Response
from fastapi.responses import FileResponse
import os
import re
import httpx
import mimetypes
import logging

logger = logging.getLogger(__name__)

async def amis_resource_middleware(request: Request, call_next):
    """Amis资源中间件，处理所有Amis资源请求"""
    path = request.url.path
    
    # 检查是否是Amis资源请求 - 只匹配本地路径，不匹配CDN路径
    if re.match(r"^(?:/(?:amis|static/amis))/.*", path):
        # 处理双斜杠问题
        path = path.replace("//", "/")
        
        # 提取相对路径
        # 从路径中提取amis后的部分
        match = re.search(r"/(amis|static/amis)/(.*)", path)
        if match:
            relative_path = match.group(2)
        else:
            relative_path = path.split("/")[-1]
        
        # 尝试多个可能的文件路径
        possible_paths = [
            # 原始路径
            relative_path,
            # 处理sdk子目录的情况 - 如果请求sdk/sdk.js，尝试直接使用sdk.js
            relative_path.replace("sdk/", ""),
            # 处理其他可能的路径
            relative_path.replace("sdk/thirds/", ""),
            # 特别处理 rest.js 文件
            "rest.js" if relative_path.endswith("rest.js") else None,
        ]
        
        # 尝试找到存在的文件
        file_path = None
        for possible_path in possible_paths:
            if possible_path is None:
                continue
            test_path = os.path.join("E:/HSdigitalportal/fastapi_amis_admin/static/amis", possible_path)
            if os.path.exists(test_path):
                file_path = test_path
                break
        
        if file_path:
            # 使用mimetypes库获取正确的MIME类型
            media_type, _ = mimetypes.guess_type(file_path)
            if not media_type:
                # 如果无法猜测，根据扩展名设置默认值
                if file_path.endswith(".css"):
                    media_type = "text/css"
                elif file_path.endswith(".js"):
                    media_type = "application/javascript"
                elif file_path.endswith(".woff2"):
                    media_type = "font/woff2"
                elif file_path.endswith(".woff"):
                    media_type = "font/woff"
                elif file_path.endswith(".ttf"):
                    media_type = "font/ttf"
                elif file_path.endswith(".svg"):
                    media_type = "image/svg+xml"
                else:
                    media_type = "application/octet-stream"
            
            try:
                # 读取文件内容
                with open(file_path, "rb") as f:
                    content = f.read()
                
                # 设置适当的缓存头
                headers = {
                    "Cache-Control": "public, max-age=86400",  # 缓存1天
                    "Access-Control-Allow-Origin": "*",
                }
                
                return Response(content=content, media_type=media_type, headers=headers)
            except Exception as e:
                logger.error(f"Error reading file {file_path}: {e}")
                # 继续处理，返回404
        else:
            # 如果本地文件不存在，尝试从CDN获取
            try:
                # 构建CDN URL - 修正路径 - 更新到6.13.0版本
                if relative_path.startswith("sdk/"):
                    cdn_url = f"https://unpkg.com/amis@6.13.0/{relative_path}"
                else:
                    cdn_url = f"https://unpkg.com/amis@6.13.0/sdk/{relative_path}"
                
                logger.info(f"Fetching {relative_path} from CDN: {cdn_url}")
                
                # 从CDN获取文件
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(cdn_url)
                    if response.status_code == 200:
                        # 获取正确的MIME类型
                        media_type = response.headers.get("content-type", "")
                        if not media_type:
                            # 如果没有提供，根据扩展名设置默认值
                            if relative_path.endswith(".css"):
                                media_type = "text/css"
                            elif relative_path.endswith(".js"):
                                media_type = "application/javascript"
                            elif relative_path.endswith(".woff2"):
                                media_type = "font/woff2"
                            elif relative_path.endswith(".woff"):
                                media_type = "font/woff"
                            elif relative_path.endswith(".ttf"):
                                media_type = "font/ttf"
                            elif relative_path.endswith(".svg"):
                                media_type = "image/svg+xml"
                            else:
                                media_type = "application/octet-stream"
                        
                        # 设置适当的缓存头
                        headers = {
                            "Cache-Control": "public, max-age=86400",  # 缓存1天
                            "Access-Control-Allow-Origin": "*",
                        }
                        
                        return Response(content=response.content, media_type=media_type, headers=headers)
                    else:
                        logger.warning(f"CDN returned {response.status_code} for {cdn_url}")
            except Exception as e:
                logger.error(f"Failed to fetch {relative_path} from CDN: {e}")
    
    # 如果不是Amis资源请求或文件不存在，继续处理
    response = await call_next(request)
    return response