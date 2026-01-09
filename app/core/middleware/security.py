from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.responses import Response


class SecurityMiddleware(BaseHTTPMiddleware):
    """安全中间件，设置现代安全响应头"""

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        # 防点击劫持
        response.headers["X-Frame-Options"] = "DENY"

        # 防 MIME 嗅探
        response.headers["X-Content-Type-Options"] = "nosniff"

        # 内容安全策略（CSP）
        # 注意：尽量避免 'unsafe-inline'，尤其是 script-src
        # 对于登录页面，需要允许内联脚本
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com https://cdn.jsdelivr.net 'unsafe-inline'; "
            "style-src 'self' https://unpkg.com https://cdn.jsdelivr.net 'unsafe-inline'; "
            "img-src 'self' data: https://cdn.jsdelivr.net https://unpkg.com; "
            "media-src 'self' data:; "
            "connect-src 'self'; "
            "font-src 'self' data: https://unpkg.com; "
            "frame-src 'self'; "
            "object-src 'none'; "
            "base-uri 'self'; "
            "form-action 'self'; "
            "upgrade-insecure-requests"
        )

        # 引用来源策略
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # 权限策略（禁用敏感功能）
        response.headers["Permissions-Policy"] = (
            "geolocation=(), "
            "microphone=(), "
            "camera=(), "
            "payment=(), "
            "usb=(), "
            "autoplay=()"
        )

        # HSTS（仅 HTTPS）
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response