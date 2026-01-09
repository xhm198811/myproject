from pydantic import BaseSettings, Field
from typing import Optional
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    """系统配置"""
    # 应用基本信息
    APP_NAME: str = "企业门户管理系统"
    APP_VERSION: str = "1.0.0"
    APP_DESCRIPTION: str = "基于FastAPI和Amis-Admin的企业级管理系统"
    
    # 运行模式
    DEBUG: bool = True
    
    # 安全配置
    SECRET_KEY: str = "your-secret-key-here"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    # 数据库配置
    DATABASE_URL: str = "postgresql://postgres:pwd123456@localhost:5432/myportaldb"
    DATABASE_URL_ASYNC: str = "postgresql+asyncpg://postgres:pwd123456@localhost:5432/myportaldb"
    
    # 数据库连接池配置
    DATABASE_POOL_SIZE: int = 10
    DATABASE_MAX_OVERFLOW: int = 20
    DATABASE_POOL_TIMEOUT: int = 30
    
    # Redis配置
    REDIS_URL: Optional[str] = None
    
    # Amis配置
    AMIS_CDN: str = "https://unpkg.com"
    AMIS_PKG: str = "amis@6.3.0"
    
    # 管理员配置
    ADMIN_PATH: str = "/admin"
    
    # 静态文件目录
    STATIC_DIR: str = "app/static"
    ADMIN_TITLE: str = "企业门户管理系统"
    ADMIN_ICON: str = ""
    
    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None
    
    # CORS配置
    CORS_ALLOW_CREDENTIALS: bool = True
    CORS_ALLOW_METHODS: list = ["*"]
    CORS_ALLOW_HEADERS: list = ["*"]
    CORS_ORIGINS: list = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
        "http://localhost:3002",
        "http://127.0.0.1:3002",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "http://localhost:8001",
        "http://127.0.0.1:8001",
        "http://localhost:8002",
        "http://127.0.0.1:8002",
        # 本地IP地址范围
        "http://192.168.0.11:3000",
        "http://192.168.0.11:3001",
        "http://192.168.0.11:3002",
        "http://192.168.0.11:8000",
        "http://192.168.0.11:8001",
        "http://192.168.0.11:8002",
    ]
    
    # API性能配置
    MAX_REQUEST_BODY_SIZE: int = 10 * 1024 * 1024  # 10MB
    ENABLE_RESPONSE_COMPRESSION: bool = True
    
    # 速率限制配置
    DEFAULT_RATE_LIMIT: int = 100  # 每分钟请求数
    
    # 登录安全配置
    MAX_LOGIN_ATTEMPTS: int = 5  # 最大登录失败次数
    LOCKOUT_MINUTES: int = 30  # 锁定时长（分钟）
    ENABLE_CAPTCHA: bool = False  # 是否启用验证码
    CAPTCHA_EXPIRE_SECONDS: int = 300  # 验证码过期时间（秒）
    
    # 密码策略配置
    MIN_PASSWORD_LENGTH: int = 8  # 最小密码长度
    MAX_PASSWORD_LENGTH: int = 128  # 最大密码长度
    REQUIRE_PASSWORD_COMPLEXITY: bool = True  # 是否要求密码复杂度
    
    # 会话配置
    REMEMBER_ME_DAYS: int = 30  # 记住我的天数
    SESSION_TIMEOUT_MINUTES: int = 60  # 会话超时时间（分钟）
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        env_prefix = ""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保CORS_ORIGINS是列表
        if isinstance(self.CORS_ORIGINS, str):
            import json
            self.CORS_ORIGINS = json.loads(self.CORS_ORIGINS)

# 创建配置实例
settings = Settings()
