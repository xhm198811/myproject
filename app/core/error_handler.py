from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import ValidationError
from .login import logger
from ..users.exceptions import (
    UserNotFoundError,
    UserAlreadyExistsError,
    InvalidCredentialsError,
    EmailNotVerifiedError,
    PasswordResetExpiredError,
    PasswordResetInvalidError,
    PermissionDeniedError,
    RoleNotFoundError
)

def setup_exception_handlers(app: FastAPI):
    """设置异常处理器"""
    
    # 用户管理异常处理器
    @app.exception_handler(UserNotFoundError)
    async def user_not_found_exception_handler(request, exc):
        logger.error(f"用户不存在: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "msg": exc.detail, "data": None}
        )
    
    @app.exception_handler(UserAlreadyExistsError)
    async def user_already_exists_exception_handler(request, exc):
        logger.error(f"用户已存在: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "msg": exc.detail, "data": None}
        )
    
    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_exception_handler(request, exc):
        logger.error(f"无效的凭据: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "msg": exc.detail, "data": None}
        )
    
    @app.exception_handler(EmailNotVerifiedError)
    async def email_not_verified_exception_handler(request, exc):
        logger.error(f"邮箱未验证: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "msg": exc.detail, "data": None}
        )
    
    @app.exception_handler(PasswordResetExpiredError)
    async def password_reset_expired_exception_handler(request, exc):
        logger.error(f"密码重置链接已过期: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "msg": exc.detail, "data": None}
        )
    
    @app.exception_handler(PasswordResetInvalidError)
    async def password_reset_invalid_exception_handler(request, exc):
        logger.error(f"密码重置链接无效: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "msg": exc.detail, "data": None}
        )
    
    @app.exception_handler(PermissionDeniedError)
    async def permission_denied_exception_handler(request, exc):
        logger.error(f"权限不足: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "msg": exc.detail, "data": None}
        )
    
    @app.exception_handler(RoleNotFoundError)
    async def role_not_found_exception_handler(request, exc):
        logger.error(f"角色不存在: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"status": exc.status_code, "msg": exc.detail, "data": None}
        )
    

    
    # FastAPI 默认异常处理器扩展
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request, exc):
        logger.error(f"请求验证错误: {exc}")
        # 格式化验证错误信息
        error_details = []
        for error in exc.errors():
            field = "".join(error["loc"])
            message = error["msg"]
            error_details.append(f"{field}: {message}")
        
        return JSONResponse(
            status_code=422,
            content={
                "status": 422,
                "msg": "请求参数验证失败",
                "data": {
                    "errors": error_details,
                    "raw": exc.errors()
                }
            }
        )
    
    # Pydantic 验证错误处理器
    @app.exception_handler(ValidationError)
    async def pydantic_validation_exception_handler(request, exc):
        logger.error(f"Pydantic验证错误: {exc}")
        # 格式化验证错误信息
        error_details = []
        for error in exc.errors():
            field = "".join(error["loc"])
            message = error["msg"]
            error_details.append(f"{field}: {message}")
        
        return JSONResponse(
            status_code=422,
            content={
                "status": 422,
                "msg": "数据验证失败",
                "data": {
                    "errors": error_details,
                    "raw": exc.errors()
                }
            }
        )
