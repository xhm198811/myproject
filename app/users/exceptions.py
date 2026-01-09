from fastapi import HTTPException
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

# User Management Exceptions
class UserNotFoundError(HTTPException):
    def __init__(self, detail: str = "用户不存在"):
        super().__init__(status_code=404, detail=detail)

class UserAlreadyExistsError(HTTPException):
    def __init__(self, detail: str = "用户已存在"):
        super().__init__(status_code=400, detail=detail)

class InvalidCredentialsError(HTTPException):
    def __init__(self, detail: str = "无效的凭据"):
        super().__init__(status_code=401, detail=detail)

class EmailNotVerifiedError(HTTPException):
    def __init__(self, detail: str = "邮箱未验证"):
        super().__init__(status_code=403, detail=detail)

class PasswordResetExpiredError(HTTPException):
    def __init__(self, detail: str = "密码重置链接已过期"):
        super().__init__(status_code=400, detail=detail)

class PasswordResetInvalidError(HTTPException):
    def __init__(self, detail: str = "密码重置链接无效"):
        super().__init__(status_code=400, detail=detail)

# Permission and Role Exceptions
class PermissionDeniedError(HTTPException):
    def __init__(self, detail: str = "权限不足"):
        super().__init__(status_code=403, detail=detail)

class RoleNotFoundError(HTTPException):
    def __init__(self, detail: str = "角色不存在"):
        super().__init__(status_code=404, detail=detail)
