from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    username: str
    user_id: int
    is_superuser: bool


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=150, description="用户名")
    password: str = Field(..., min_length=1, max_length=128, description="密码")
    remember_me: bool = Field(default=False, description="记住我")
    captcha_code: Optional[str] = Field(default=None, description="验证码")
    captcha_key: Optional[str] = Field(default=None, description="验证码密钥")


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: str
    expires_in: int
    user: dict


class LogoutResponse(BaseModel):
    message: str = "登出成功"


class UserCreate(BaseModel):
    username: str
    email: str
    password: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    department: str | None = None


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    department: str | None = None
    is_active: bool
    is_staff: bool
    is_superuser: bool
    date_joined: datetime
    last_login: datetime | None = None
    
    class Config:
        from_attributes = True


class UserUpdate(BaseModel):
    email: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    department: str | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., description="邮箱地址")


class ResetPasswordRequest(BaseModel):
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=8, max_length=128, description="新密码")
