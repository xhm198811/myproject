"""
FastAPI-Amis-Admin 完整应用示例
包含完整的配置、路由和管理后台
"""

from fastapi import FastAPI
from fastapi_amis_admin.admin.settings import Settings
from fastapi_amis_admin.admin.site import AdminSite
from fastapi_amis_admin.amis import Page, Property, Divider
import platform
import fastapi_amis_admin
import sqlalchemy
import pydantic

# 创建FastAPI应用
app = FastAPI(
    title="FastAPI-Amis-Admin 演示应用",
    description="基于 FastAPI 和 Amis 的后台管理系统",
    version="1.0.0"
)

# 创建Settings配置
settings = Settings(
    database_url_async="sqlite+aiosqlite:///amisadmin.db",
    site_title="FastAPI-Amis-Admin 演示",
    version="1.0.0",
    debug=True,
    amis_pkg="amis@6.3.0",
    amis_theme="cxd"
)

# 创建AdminSite实例
site = AdminSite(settings=settings)

# 挂载后台管理系统
site.mount_app(app)


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "欢迎使用 FastAPI-Amis-Admin 演示应用",
        "docs": "/docs",
        "redoc": "/redoc",
        "admin": "/admin",
        "version": "1.0.0"
    }


@app.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "app_name": settings.site_title,
        "app_version": settings.version,
        "amis_version": settings.amis_pkg,
        "amis_theme": settings.amis_theme
    }


@app.get("/api/info")
async def app_info():
    """应用信息"""
    return {
        "system": {
            "os": platform.system(),
            "python": platform.python_version(),
        },
        "dependencies": {
            "fastapi_amis_admin": fastapi_amis_admin.__version__,
            "sqlalchemy": sqlalchemy.__version__,
            "pydantic": pydantic.__version__,
        },
        "settings": {
            "site_title": settings.site_title,
            "site_path": settings.site_path,
            "amis_cdn": settings.amis_cdn,
            "amis_pkg": settings.amis_pkg,
            "amis_theme": settings.amis_theme,
            "database_url_async": settings.database_url_async,
            "debug": settings.debug
        }
    }


if __name__ == "__main__":
    import uvicorn

    print("=" * 80)
    print("FastAPI-Amis-Admin 演示应用启动中...")
    print("=" * 80)
    print(f"应用标题: {settings.site_title}")
    print(f"应用版本: {settings.version}")
    print(f"Amis 版本: {settings.amis_pkg}")
    print(f"Amis 主题: {settings.amis_theme}")
    print(f"数据库: {settings.database_url_async}")
    print(f"调试模式: {settings.debug}")
    print("=" * 80)
    print("访问地址:")
    print(f"  - 主页: http://localhost:8001/")
    print(f"  - 管理后台: http://localhost:8001{settings.site_path}")
    print(f"  - API 文档: http://localhost:8001/docs")
    print(f"  - ReDoc: http://localhost:8001/redoc")
    print(f"  - 健康检查: http://localhost:8001/api/health")
    print(f"  - 应用信息: http://localhost:8001/api/info")
    print("=" * 80)
    print("按 Ctrl+C 停止服务器")
    print("=" * 80)
    print()

    uvicorn.run(app, host="0.0.0.0", port=8001)
