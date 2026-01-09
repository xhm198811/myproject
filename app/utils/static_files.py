from fastapi import Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
import os
import re

class AmisStaticFiles(StaticFiles):
    """自定义Amis静态文件处理器，用于正确映射资源文件路径"""
    
    def __init__(self, directory: str):
        super().__init__(directory=directory)
    
    async def __call__(self, scope, receive, send):
        request = Request(scope, receive)
        path = request.url.path
        
        # 检查是否是Amis资源请求
        if "/static/amis/" in path:
            # 提取文件名
            match = re.search(r"/static/amis/(?:[^/]+/)+([^/]+)$", path)
            if match:
                filename = match.group(1)
                # 检查文件是否存在于本地
                file_path = os.path.join(self.directory, filename)
                if os.path.exists(file_path):
                    # 重定向到正确的本地文件路径
                    new_path = f"/static/amis/{filename}"
                    return await RedirectResponse(url=new_path).scope, receive, send
        
        # 如果不是Amis资源或文件不存在，使用默认处理
        return await super().__call__(scope, receive, send)