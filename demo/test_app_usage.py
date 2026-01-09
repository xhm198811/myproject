"""
测试 FastAPI-Amis-Admin 的 app 调用
展示 app 的创建、配置和挂载过程
"""

from fastapi import FastAPI
from fastapi_amis_admin.admin.settings import Settings
from fastapi_amis_admin.admin.site import AdminSite
import inspect

print("=" * 80)
print("FastAPI-Amis-Admin App 调用分析")
print("=" * 80)
print()

# 步骤 1: 创建 FastAPI 应用
print("步骤 1: 创建 FastAPI 应用")
print("-" * 80)
app = FastAPI(title="测试应用", version="1.0.0")
print(f"✓ FastAPI 应用已创建")
print(f"  - 应用类型: {type(app)}")
print(f"  - 应用标题: {app.title}")
print(f"  - 应用版本: {app.version}")
print()

# 步骤 2: 创建 Settings 配置
print("步骤 2: 创建 Settings 配置")
print("-" * 80)
settings = Settings(
    database_url_async="sqlite+aiosqlite:///amisadmin.db",
    site_title="测试管理系统",
    version="1.0.0",
    debug=True
)
print(f"✓ Settings 配置已创建")
print(f"  - site_title: {settings.site_title}")
print(f"  - site_path: {settings.site_path}")
print(f"  - amis_cdn: {settings.amis_cdn}")
print(f"  - amis_pkg: {settings.amis_pkg}")
print(f"  - amis_theme: {settings.amis_theme}")
print(f"  - database_url_async: {settings.database_url_async}")
print()

# 步骤 3: 创建 AdminSite 实例
print("步骤 3: 创建 AdminSite 实例")
print("-" * 80)
site = AdminSite(settings=settings)
print(f"✓ AdminSite 实例已创建")
print(f"  - 实例类型: {type(site)}")
print(f"  - 内部 FastAPI 实例: {type(site.fastapi)}")
print(f"  - 内部路由: {type(site.router)}")
print(f"  - 数据库引擎: {type(site.engine)}")
print(f"  - Amis 解析器: {type(site.amis_parser)}")
print()

# 步骤 4: 分析 mount_app 方法
print("步骤 4: 分析 mount_app 方法")
print("-" * 80)
mount_app_method = site.mount_app
print(f"✓ mount_app 方法签名:")
print(f"  {inspect.signature(mount_app_method)}")
print()
print(f"✓ mount_app 方法文档:")
print(f"  {mount_app_method.__doc__}")
print()

# 步骤 5: 挂载后台管理系统
print("步骤 5: 挂载后台管理系统到 FastAPI 应用")
print("-" * 80)
site.mount_app(app)
print(f"✓ 后台管理系统已挂载")
print(f"  - 挂载路径: {settings.site_path}")
print(f"  - 主应用对象: {app}")
print(f"  - Admin 应用对象: {site.application}")
print()

# 步骤 6: 检查应用路由
print("步骤 6: 检查应用路由")
print("-" * 80)
print(f"✓ 主应用路由数量: {len(app.routes)}")
print()
for route in app.routes:
    print(f"  - {route.path} [{type(route).__name__}]")
print()

# 步骤 7: 检查 AdminSite 的 FastAPI 实例
print("步骤 7: 检查 AdminSite 内部的 FastAPI 实例")
print("-" * 80)
print(f"✓ AdminSite 内部 FastAPI 路由数量: {len(site.fastapi.routes)}")
print()
for route in site.fastapi.routes:
    print(f"  - {route.path} [{type(route).__name__}]")
print()

# 步骤 8: 访问地址信息
print("步骤 8: 访问地址信息")
print("-" * 80)
print(f"✓ 应用访问地址:")
print(f"  - 主页: http://localhost:8001/")
print(f"  - 管理后台: http://localhost:8001{settings.site_path}")
print(f"  - API 文档: http://localhost:8001/docs")
print(f"  - ReDoc: http://localhost:8001/redoc")
print()

# 步骤 9: 应用配置总结
print("步骤 9: 应用配置总结")
print("-" * 80)
print(f"✓ FastAPI 主应用:")
print(f"  - 对象: {app}")
print(f"  - 标题: {app.title}")
print(f"  - 版本: {app.version}")
print()
print(f"✓ AdminSite 管理后台:")
print(f"  - 对象: {site}")
print(f"  - 内部 FastAPI: {site.fastapi}")
print(f"  - 挂载路径: {settings.site_path}")
print(f"  - 数据库: {settings.database_url_async}")
print(f"  - Amis 版本: {settings.amis_pkg}")
print(f"  - Amis 主题: {settings.amis_theme}")
print()

print("=" * 80)
print("✅ App 调用分析完成")
print("=" * 80)
print()
print("启动应用命令:")
print("  uvicorn.run(app, host='0.0.0.0', port=8001)")
