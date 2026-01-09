# FastAPI-Amis-Admin Demo 应用

## 📦 应用说明

这是一个完整的 FastAPI-Amis-Admin 演示应用，展示了如何集成和使用 fastapi-amis-admin 框架。

## 🚀 快速启动

```bash
cd demo
python app.py
```

## 🌐 访问地址

- **主页**: http://localhost:8001/
- **管理后台**: http://localhost:8001/admin
- **API 文档**: http://localhost:8001/docs
- **ReDoc**: http://localhost:8001/redoc
- **健康检查**: http://localhost:8001/api/health
- **应用信息**: http://localhost:8001/api/info

## 📋 应用配置

### Settings 配置

```python
settings = Settings(
    database_url_async="sqlite+aiosqlite:///amisadmin.db",
    site_title="FastAPI-Amis-Admin 演示",
    version="1.0.0",
    debug=True,
    amis_pkg="amis@6.3.0",
    amis_theme="cxd"
)
```

### 配置说明

| 配置项 | 值 | 说明 |
|--------|-----|------|
| `database_url_async` | `sqlite+aiosqlite:///amisadmin.db` | 异步数据库连接 |
| `site_title` | `FastAPI-Amis-Admin 演示` | 站点标题 |
| `version` | `1.0.0` | 应用版本 |
| `debug` | `True` | 调试模式 |
| `amis_pkg` | `amis@6.3.0` | Amis 前端框架版本 |
| `amis_theme` | `cxd` | Amis 主题 |

## 🏗️ 应用架构

```
FastAPI 主应用 (app)
    ↓
AdminSite 实例 (site)
    ↓
内部 FastAPI 实例 (site.fastapi)
    ↓
管理后台路由和功能
```

## 📝 API 端点

### 主页
```
GET /
```
返回应用基本信息和导航链接。

### 健康检查
```
GET /api/health
```
返回应用健康状态和基本信息。

### 应用信息
```
GET /api/info
```
返回系统信息、依赖版本和配置详情。

## 🛠️ 技术栈

- **FastAPI**: 0.103.2
- **Pydantic**: 1.10.26
- **SQLAlchemy**: 2.0.44
- **FastAPI-Amis-Admin**: 0.7.3
- **Amis**: 6.3.0
- **Uvicorn**: 0.38.0

## 📂 文件结构

```
demo/
├── app.py              # 主应用文件
├── demo-simple.py      # 简单示例
├── demo-form.py        # 表单示例
├── demo-model.py       # 模型示例
└── test_app_usage.py   # 应用使用测试
```

## 🔧 开发说明

### 添加新的管理页面

```python
from fastapi_amis_admin.admin import admin

# 创建管理页面
@site.register_admin
class MyAdmin(admin.ModelAdmin):
    page_schema = admin.PageSchema(label="我的页面", icon="fa fa-list")
    # 配置页面...
```

### 自定义路由

```python
@app.get("/api/custom")
async def custom_endpoint():
    return {"message": "自定义端点"}
```

### 修改配置

编辑 `app.py` 中的 `Settings` 配置：

```python
settings = Settings(
    # 修改配置项
    site_title="您的标题",
    amis_theme="antd",  # 更改主题
    # ...
)
```

## 🎨 Amis 主题

支持的主题：
- `cxd` - 默认主题
- `antd` - Ant Design 风格
- `dark` - 暗色主题
- `ang` - Angular 风格

## 📚 相关文档

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [Amis 官方文档](https://baidu.gitee.io/amis/zh-CN/docs/index)
- [FastAPI-Amis-Admin 文档](http://docs.amis.work/)

## 📄 许可证

Apache License 2.0
