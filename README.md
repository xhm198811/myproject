<<<<<<< HEAD
# 企业门户管理系统 (Enterprise Portal Management System)

<p align="center">
  <em>基于 FastAPI + FastAPI-Amis-Admin 构建的企业级后台管理系统</em>
</p>

<p align="center">
  <a href="#功能特性">功能特性</a> •
  <a href="#技术栈">技术栈</a> •
  <a href="#项目结构">项目结构</a> •
  <a href="#快速开始">快速开始</a> •
  <a href="#模块说明">模块说明</a>
</p>

## 📋 概述

企业门户管理系统是一个基于 **FastAPI** 框架和 **FastAPI-Amis-Admin** 构建的企业级后台管理平台。系统集成了组织架构管理、合同管理、项目管理、产品管理、报价管理等核心业务模块，提供完善的认证授权机制和数据管理功能。

系统采用现代化 Web 技术架构，前端基于百度 **Amis** 低代码框架，后端采用 **FastAPI** + **SQLModel** 构建，支持异步数据库操作，提供高性能、高可用的企业级解决方案。

## ✨ 功能特性

### 🔐 认证与安全
- **用户认证系统**：支持用户名密码登录、Token 认证（JWT）
- **验证码保护**：可配置的图形验证码功能
- **密码安全策略**：密码强度验证、定期更换提醒
- **会话管理**：在线用户监控、强制下线功能
- **访问控制**：基于角色的权限管理（RBAC）

### 🏢 组织架构管理
- **部门管理**：树形结构展示，支持无限层级
- **人员管理**：员工信息完整档案
- **部门调动历史**：记录员工部门变更历程
- **批量导入导出**：支持 Excel 批量导入人员数据

### 📄 合同管理
- **合同基本信息**：编号、名称、类型、金额
- **合同文件管理**：关联合同文档上传下载
- **合同状态跟踪**：审核中、已生效、已过期、已终止
- **合同服务管理**：关联服务项目和服务记录

### 📁 项目管理
- **项目信息管理**：项目名称、时间、负责人
- **项目文档管理**：项目相关文档上传
- **项目服务记录**：服务内容、费用明细
- **项目状态追踪**：进行中、已完成、已取消

### 📦 产品管理（Django 集成）
- **产品目录管理**：产品信息、价格、规格
- **报价记录管理**：客户报价历史记录
- **Django 系统集成**：与外部 Django 产品系统对接
- **用户数据同步**：同步 Django 系统的用户数据

### 💰 报价管理
- **报价单创建**：客户、产品、价格、数量
- **报价审批流程**：提交、审核、批准
- **报价历史记录**：完整的历史变更记录
- **报价转合同**：快速生成合同

### 🛠 通用功能
- **文件管理**：通用文件上传、下载
- **批量导入**：Excel 数据批量导入
- **数据复制**：快速复制现有记录
- **系统监控**：健康检查、数据库连接监控

## 🛠 技术栈

### 后端技术
- **FastAPI**：高性能异步 Web 框架
- **SQLModel**：SQLAlchemy + Pydantic 完美结合
- **SQLAlchemy**：强大的 ORM 框架
- **Pydantic**：数据验证和序列化
- **JWT**：JSON Web Token 认证
- **Uvicorn**：ASGI 服务器

### 前端技术
- **Amis**：百度开源的低代码 Admin 框架
- **Vue.js**：Amis 底层依赖
- **Ant Design**：部分 UI 组件

### 数据库
- **PostgreSQL**：主数据库（推荐）
- **SQLite**：开发环境轻量数据库

### 中间件
- **Redis**（可选）：缓存、会话存储
- **Celery**（可选）：异步任务队列

### 部署与运维
- **Docker**：容器化部署
- **Nginx**：反向代理、静态文件服务
- **Gunicorn**：生产环境 WSGI 服务器

## 📁 项目结构

```
fastapi-amis-admin-master/
├── app/                          # 应用主目录
│   ├── __init__.py              # 应用初始化
│   ├── main.py                  # FastAPI 应用入口
│   ├── admin/                   # Admin 管理模块
│   │   └── site.py             # Admin 站点配置
│   ├── api/                     # API 路由
│   │   ├── batch_import.py     # 批量导入接口
│   │   ├── general_file.py     # 通用文件接口
│   │   └── copy/               # 数据复制接口
│   │       └── copy_router.py
│   ├── contracts/              # 合同管理模块
│   │   ├── admin.py            # 合同 Admin
│   │   ├── api/                # 合同 API
│   │   │   ├── contract.py
│   │   │   └── file.py
│   │   ├── models/             # 合同模型
│   │   │   └── contract.py
│   │   ├── schemas/            # Pydantic 模式
│   │   └── services/           # 业务逻辑
│   ├── core/                   # 核心配置
│   │   ├── auth.py             # 认证授权
│   │   ├── config.py           # 配置管理
│   │   ├── db.py               # 数据库初始化
│   │   ├── logging.py          # 日志配置
│   │   └── middleware/         # 中间件
│   ├── forms/                  # 表单管理
│   ├── middleware/             # HTTP 中间件
│   ├── organization/           # 组织架构模块
│   │   ├── admin.py            # 组织 Admin
│   │   ├── models/             # 组织模型
│   │   │   ├── organization.py
│   │   │   └── person.py
│   │   ├── schemas/            # 模式定义
│   │   └── services/           # 业务逻辑
│   ├── products/               # 产品管理模块
│   │   ├── admin/              # 产品 Admin
│   │   ├── api/                # 产品 API
│   │   │   ├── django_client.py
│   │   │   ├── django_products.py
│   │   │   └── django_users.py
│   │   ├── models/             # 产品模型
│   │   └── schemas/            # 模式定义
│   ├── projects/               # 项目管理模块
│   │   ├── admin.py            # 项目 Admin
│   │   ├── api/                # 项目 API
│   │   ├── models/             # 项目模型
│   │   ├── schemas/            # 模式定义
│   │   └── services/           # 业务逻辑
│   ├── quotes/                 # 报价管理模块
│   │   ├── admin.py            # 报价 Admin
│   │   ├── api/                # 报价 API
│   │   ├── models/             # 报价模型
│   │   ├── schemas/            # 模式定义
│   │   └── services/           # 业务逻辑
│   ├── users/                  # 用户管理模块
│   │   ├── admin.py            # 用户 Admin
│   │   ├── api/                # 用户 API
│   │   │   ├── auth.py
│   │   │   ├── auth_new.py
│   │   │   ├── schemas.py
│   │   │   └── user.py
│   │   └── models/             # 用户模型
│   └── utils/                  # 工具模块
│       ├── batch_import.py     # 批量导入工具
│       ├── captcha.py          # 验证码工具
│       ├── clipboard_copy_action.py  # 剪贴板复制
│       └── static_files.py     # 静态文件
├── demo/                        # 示例代码
├── docs/                        # 文档
├── .env                         # 环境变量
├── .env.example                # 环境变量示例
├── requirements.txt            # Python 依赖
├── README.md                   # 项目说明（本文档）
└── app.log                     # 应用日志
```

## 🚀 快速开始

### 环境要求

- **Python 3.9+**
- **PostgreSQL 12+** 或 **SQLite**
- **Node.js 16+**（前端开发可选）

### 1. 克隆项目

```bash
git clone <repository-url>
cd fastapi-amis-admin-master
```

### 2. 创建虚拟环境

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境 (Windows)
venv\Scripts\activate

# 激活虚拟环境 (Linux/Mac)
source venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

主要配置项：

```env
# 应用配置
APP_NAME=企业门户管理系统
APP_VERSION=1.0.0
DEBUG=True

# 安全配置
SECRET_KEY=your-secret-key-here-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# 数据库配置
DATABASE_URL=postgresql://postgres:pwd123456@localhost:5432/myportaldb
DATABASE_URL_ASYNC=postgresql+asyncpg://postgres:pwd123456@localhost:5432/myportaldb

# CORS 配置
CORS_ORIGINS=["http://localhost:8000", "http://localhost:3000"]
CORS_ALLOW_CREDENTIALS=True

# 验证码配置
ENABLE_CAPTCHA=False

# 静态文件目录
STATIC_DIR=./static
```

### 5. 初始化数据库

```bash
# 创建数据库 (PostgreSQL)
createdb myportaldb

# 运行初始化脚本
python -m app.main
```

### 6. 创建超级用户

```bash
python create_test_user.py
```

### 7. 启动服务

开发模式：

```bash
python -m uvicorn app.main:app --reload --port 8001
```

生产模式：

```bash
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8001
```

### 8. 访问系统

- **管理后台**：http://localhost:8001/admin
- **API 文档**：http://localhost:8001/docs
- **登录页面**：http://localhost:8001/login
- **健康检查**：http://localhost:8001/api/health

默认账号：`admin` / `admin123`

## 📖 模块说明

### 组织架构模块 (organization)

提供企业组织架构的完整管理功能，包括：

- **部门管理 (OrganizationAdmin)**
  - 树形结构展示
  - 部门信息：名称、编码、负责人、状态
  - 层级关系管理
  
- **人员管理 (PersonAdmin)**
  - 员工基本信息：姓名、工号、联系方式
  - 所属部门关联
  - 员工状态管理
  - 批量导入功能

- **部门调动历史 (PersonDepartmentHistoryAdmin)**
  - 调动记录完整追踪
  - 原部门、新部门记录
  - 调动原因和备注

### 合同管理模块 (contracts)

完整的合同生命周期管理：

- **合同管理 (ContractAdmin)**
  - 合同基本信息管理
  - 合同状态流转
  - 金额和日期管理
  
- **合同文件管理 (ContractFileAdmin)**
  - 合同文档上传
  - 文件类型分类
  - 版本管理

- **合同服务管理 (ContractServiceAdmin)**
  - 服务项目关联
  - 服务费用记录

### 项目管理模块 (projects)

项目信息和服务管理：

- **项目管理 (ProjectAdmin)**
  - 项目基本信息
  - 时间和进度管理
  - 负责人分配
  
- **项目文件管理 (ProjectFileAdmin)**
  - 项目文档上传
  - 文档分类

- **项目服务管理 (ProjectServiceAdmin)**
  - 服务内容记录
  - 费用明细

### 产品管理模块 (products)

与 Django 系统集成的产品管理：

- **产品管理 (ProductAdmin)**
  - 产品信息管理
  - 价格和规格
  
- **报价记录 (QuotationRecordAdmin)**
  - 客户报价记录
  - 报价历史

- **Django 集成 (DjangoProductAdmin)**
  - 产品数据同步
  - 用户数据同步

### 报价管理模块 (quotes)

报价单完整管理流程：

- **报价管理 (QuoteAdmin)**
  - 报价单创建和编辑
  - 产品明细添加
  - 金额计算
  
- **报价明细 (QuoteDetailAdmin)**
  - 产品明细管理
  - 数量和单价

- **报价历史 (QuoteHistoryAdmin)**
  - 变更历史记录
  - 审批流程

### 用户管理模块 (users)

用户认证和授权：

- **用户管理 (UserAdmin)**
  - 用户信息管理
  - 权限分配
  
- **认证接口**
  - 登录 / 登出
  - Token 刷新
  - 密码重置

### 工具模块 (utils)

通用工具集合：

- **批量导入 (batch_import)**
  - Excel 数据导入
  - 数据验证
  - 错误处理
  
- **验证码 (captcha)**
  - 图形验证码生成
  - 验证逻辑

- **剪贴板复制 (clipboard_copy)**
  - 表格数据复制
  - Excel 兼容

## 🔧 API 接口

### 认证接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/login/` | POST | 用户登录 |
| `/api/auth/verify` | GET | 验证 Token |
| `/api/auth/refresh` | POST | 刷新 Token |
| `/api/captcha` | GET | 获取验证码 |

### 用户接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/users/` | GET | 获取用户列表 |
| `/api/users/` | POST | 创建用户 |
| `/api/users/{id}` | GET | 获取用户详情 |
| `/api/users/{id}` | PUT | 更新用户 |
| `/api/users/{id}` | DELETE | 删除用户 |

### 组织接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/organizations/` | GET | 获取部门列表 |
| `/api/persons/` | GET | 获取人员列表 |
| `/api/persons/import` | POST | 批量导入人员 |

### 合同接口

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/contracts/` | GET | 获取合同列表 |
| `/api/contracts/` | POST | 创建合同 |
| `/api/contracts/{id}` | GET | 合同详情 |
| `/api/contracts/files/` | POST | 上传合同文件 |

## 📊 数据库模型

### 核心模型

```python
# 用户模型
class User(SQLModel, table=True):
    id: Optional[int]
    username: str
    email: Optional[str]
    hashed_password: str
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

# 部门模型
class Organization(SQLModel, table=True):
    id: Optional[int]
    name: str
    code: Optional[str]
    parent_id: Optional[int]
    status: str

# 人员模型
class Person(SQLModel, table=True):
    id: Optional[int]
    name: str
    employee_id: Optional[str]
    organization_id: Optional[int]
    phone: Optional[str]
    email: Optional[str]
    status: str

# 合同模型
class Contract(SQLModel, table=True):
    id: Optional[int]
    contract_number: str
    title: str
    contract_type: str
    amount: float
    start_date: date
    end_date: date
    status: str
```

## 🔒 安全配置

### 生产环境建议

1. **修改密钥**
   ```env
   SECRET_KEY=your-production-secret-key-min-32-chars
   ```

2. **启用 HTTPS**
   - 配置 Nginx SSL 证书
   - 设置 `UVICORN_SSL_CERT` 和 `UVICORN_SSL_KEY`

3. **禁用调试模式**
   ```env
   DEBUG=False
   ```

4. **配置 CORS**
   ```env
   CORS_ORIGINS=["https://your-domain.com"]
   ```

5. **启用验证码**
   ```env
   ENABLE_CAPTCHA=True
   ```

### 密码策略

系统支持以下密码策略：

- 最小长度：8 位
- 必须包含大小写字母
- 必须包含数字
- 必须包含特殊字符

## 📈 监控与日志

### 日志配置

日志文件位置：`app/app.log`

日志级别可通过配置调整：

```python
# app/core/logging.py
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### 健康检查

```bash
curl http://localhost:8001/api/health
```

响应示例：

```json
{
  "code": 200,
  "message": "healthy",
  "data": {
    "app": {
      "name": "企业门户管理系统",
      "version": "1.0.0",
      "status": "healthy"
    },
    "database": {
      "status": "healthy",
      "message": "数据库连接正常"
    }
  }
}
```

## 🐳 Docker 部署

### 构建镜像

```bash
docker build -t enterprise-portal .
```

### 运行容器

```bash
docker run -d \
  --name portal \
  -p 8001:8001 \
  -v $(pwd)/.env:/app/.env \
  -v $(pwd)/static:/app/static \
  enterprise-portal
```

### Docker Compose

```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8001:8001"
    volumes:
      - ./.env:/app/.env
      - ./static:/app/static
    depends_on:
      - db
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/portaldb

  db:
    image: postgres:14
    environment:
      POSTGRES_DB: portaldb
      POSTGRES_USER: user
      POSTGRES_PASSWORD: pass
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

## 🧪 测试

### 运行测试

```bash
pytest app/
```

### 生成测试报告

```bash
pytest app/ --html=test_report.html
```

## 📝 开发指南

### 添加新模块

1. 创建模块目录：`app/new_module/`
2. 定义模型：`app/new_module/models/new_model.py`
3. 创建 Admin：`app/new_module/admin.py`
4. 注册 Admin：`app/admin/site.py`
5. 添加 API 路由（可选）：`app/new_module/api/`

### 自定义页面

```python
from fastapi_amis_admin.admin import admin
from fastapi_amis_admin.amis import Page

@site.register_admin
class CustomPageAdmin(admin.PageAdmin):
    page_schema = PageSchema(label='自定义页面', icon='fa fa-star')
    
    page = Page(title='自定义页面', body='Hello World!')
```

### 自定义 Action

```python
from fastapi_amis_admin.amis.components import Action

class MyFormAdmin(admin.FormAdmin):
    # ...
    async def handle(self, request: Request, data: BaseModel, **kwargs) -> BaseApiOut[Any]:
        # 自定义处理逻辑
        return BaseApiOut(msg='操作成功')
```

## 🤝 贡献指南

1. Fork 本仓库
2. 创建特性分支：`git checkout -b feature/new-feature`
3. 提交更改：`git commit -am 'Add new feature'`
4. 推送分支：`git push origin feature/new-feature`
5. 创建 Pull Request

## 📄 许可证

本项目基于 Apache License 2.0 协议开源。

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/)
- [FastAPI-Amis-Admin](https://github.com/amisadmin/fastapi_amis_admin)
- [SQLModel](https://sqlmodel.tiangolo.com/)
- [Amis](https://baidu.github.io/amis/)
- [Ant Design](https://ant.design/)

---

<p align="center">
  <strong>企业门户管理系统</strong> - 让管理更简单
</p>
=======
# myproject
>>>>>>> 1e37e3b051914f65961779517dd29da09258b948
