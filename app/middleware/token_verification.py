#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token验证和fetch拦截器中间件
"""

import re
from typing import Callable
from fastapi import Request, Response
from fastapi.responses import HTMLResponse
from starlette.middleware.base import BaseHTTPMiddleware
import logging

logger = logging.getLogger(__name__)

class TokenVerificationMiddleware(BaseHTTPMiddleware):
    """令牌验证和脚本注入中间件"""

    # 注入的脚本内容
    TOKEN_SCRIPT = '''
    <script>
    // 令牌验证和fetch拦截器脚本
    (function() {
        console.log('[Token Middleware] 页面加载开始');
        
        // 设置全局函数来验证令牌
        window.verifyAndSetToken = async function() {
            const access_token = localStorage.getItem('access_token');
            if (!access_token) {
                console.log('[Token Middleware] 未找到访问令牌');
                return false;
            }
            
            try {
                console.log('[Token Middleware] 验证令牌有效性');
                const response = await fetch('/api/auth/verify', {
                    method: 'GET',
                    headers: {
                        'Authorization': 'Bearer ' + access_token,
                        'Content-Type': 'application/json'
                    }
                });
                
                const data = await response.json();
                console.log('[Token Middleware] 令牌验证结果:', data);
                
                if (data.code === 200 && data.data.valid) {
                    console.log('[Token Middleware] 令牌验证成功');
                    return true;
                } else {
                    console.log('[Token Middleware] 令牌验证失败，清理本地存储');
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    localStorage.removeItem('user');
                    return false;
                }
            } catch (error) {
                console.error('[Token Middleware] 令牌验证错误:', error);
                return false;
            }
        };
        
        // 设置fetch拦截器
        const originalFetch = window.fetch;
        window.fetch = function(url, options = {}) {
            const access_token = localStorage.getItem('access_token');
            console.log('[Fetch Interceptor] URL:', url, 'Token exists:', !!access_token);
            if (access_token) {
                options = options || {};
                options.headers = options.headers || {};
                options.headers['Authorization'] = 'Bearer ' + access_token;
                console.log('[Fetch Interceptor] Adding Authorization header');
            }
            return originalFetch.call(window, url, options);
        };
        
        // 页面加载完成后验证令牌
        document.addEventListener('DOMContentLoaded', async function() {
            console.log('[Token Middleware] DOM加载完成，验证令牌');
            const isValid = await window.verifyAndSetToken();
            if (!isValid) {
                console.log('[Token Middleware] 令牌无效，跳转到登录页面');
                setTimeout(() => {
                    window.location.href = '/login?redirect=' + encodeURIComponent(window.location.href);
                }, 1000);
            }
        });
        
        // 页面离开时清理（可选）
        window.addEventListener('beforeunload', function() {
            console.log('[Token Middleware] 页面即将离开');
        });
    })();
    </script>
    '''

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """拦截响应并注入脚本"""
        logger.info(f"[Token Middleware] 拦截请求: {request.method} {request.url.path}")
        
        # 只对HTML响应进行处理
        response = await call_next(request)
        
        # 检查是否为HTML响应且是admin页面
        logger.info(f"[Token Middleware] 检查响应类型: {type(response)}, 路径: {request.url.path}")
        
        if (isinstance(response, HTMLResponse) and 
            '/admin' in str(request.url.path) and
            response.headers.get('content-type', '').startswith('text/html')):
            
            try:
                # 获取原始HTML内容
                html_content = response.body.decode('utf-8')
                logger.info(f"[Token Middleware] 正在处理HTML响应，路径: {request.url.path}")
                
                # 检查是否已经有我们的脚本（避免重复注入）
                if 'verifyAndSetToken' not in html_content:
                    # 在</body>标签之前插入脚本
                    if '</body>' in html_content:
                        modified_html = html_content.replace('</body>', self.TOKEN_SCRIPT + '</body>')
                    elif '</html>' in html_content:
                        # 如果没有</body>标签，在</html>前插入
                        modified_html = html_content.replace('</html>', self.TOKEN_SCRIPT + '</html>')
                    else:
                        # 如果都没有，在内容末尾添加
                        modified_html = html_content + self.TOKEN_SCRIPT
                    
                    # 创建新的HTML响应
                    new_response = HTMLResponse(content=modified_html)
                    
                    # 复制原响应的头部信息
                    for key, value in response.headers.items():
                        new_response.headers[key] = value
                    
                    logger.info(f"[Token Middleware] 脚本注入成功，路径: {request.url.path}")
                    return new_response
                else:
                    logger.info(f"[Token Middleware] 脚本已存在，跳过注入，路径: {request.url.path}")
                    
            except Exception as e:
                logger.error(f"[Token Middleware] 脚本注入失败: {e}")
                # 注入失败时返回原始响应
                return response
        
        return response