# 登录管理功能完善文档

## 功能概述

本次更新为 fastapi_amis_admin 系统完善了登录管理功能，新增了多项安全性和用户体验改进。

## 新增功能

### 1. 登录历史记录
- 记录每次登录的详细信息（IP地址、User-Agent、登录时间、登出时间等）
- 区分成功和失败的登录尝试
- 记录失败原因

**相关文件：**
- [app/core/auth.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/auth.py) - `record_login_history()` 和 `record_logout_history()` 函数

### 2. 登录失败次数限制
- 防止暴力破解攻击
- 默认最大失败次数：5次
- 默认锁定时长：30分钟
- 超过限制后自动锁定账户

**相关文件：**
- [app/core/auth.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/auth.py) - `check_login_attempts()` 函数
- [app/core/config.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/config.py) - `MAX_LOGIN_ATTEMPTS` 和 `LOCKOUT_MINUTES` 配置

### 3. 密码强度验证
- 验证密码长度（8-128字符）
- 要求包含大写字母、小写字母、数字、特殊字符中的至少三种
- 用于密码重置和修改密码场景

**相关文件：**
- [app/core/auth.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/auth.py) - `validate_password_strength()` 函数

### 4. 用户登出功能
- 记录登出时间到登录历史
- 从在线用户列表中移除
- 清除客户端令牌（需要客户端配合）

**相关文件：**
- [app/users/api/auth.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/users/api/auth.py) - `/api/logout` 接口

### 5. 记住我功能
- 延长令牌有效期（默认30天）
- 用户可选择是否启用

**相关文件：**
- [app/users/api/auth.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/users/api/auth.py) - `/api/login` 接口
- [app/core/config.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/config.py) - `REMEMBER_ME_DAYS` 配置

### 6. 验证码功能
- 生成图形验证码
- 防止自动化攻击
- 可配置是否启用
- 验证码有效期可配置

**相关文件：**
- [app/core/captcha.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/captcha.py) - 验证码管理器
- [app/users/api/auth.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/users/api/auth.py) - `/api/captcha` 接口
- [app/core/config.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/config.py) - `ENABLE_CAPTCHA` 和 `CAPTCHA_EXPIRE_SECONDS` 配置

### 7. 密码重置功能
- 通过邮箱请求密码重置
- 生成重置令牌（有效期1小时）
- 验证令牌并设置新密码
- 修改密码功能（需要旧密码验证）

**相关文件：**
- [app/core/password_reset.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/password_reset.py) - 密码重置管理器
- [app/users/api/auth.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/users/api/auth.py) - `/api/forgot-password`、`/api/reset-password`、`/api/change-password` 接口

### 8. 用户在线状态管理
- 实时跟踪在线用户
- 自动清理不活跃用户
- 记录用户活动日志
- 提供在线用户统计

**相关文件：**
- [app/core/online_users.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/online_users.py) - 在线用户管理器
- [app/core/middleware/user_activity.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/middleware/user_activity.py) - 用户活动跟踪中间件
- [app/users/api/auth.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/users/api/auth.py) - `/api/online-users` 和 `/api/activity-stats` 接口

### 9. 登录页面UI升级
- 现代化设计，渐变背景
- 集成验证码功能
- 集成记住我功能
- 改进的错误提示
- 加载动画效果

**相关文件：**
- [app/main.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/main.py) - `/login` 路由

## API 接口

### 登录相关

#### POST /api/login
用户登录（增强版）

请求体：
```json
{
  "username": "string",
  "password": "string",
  "remember_me": false,
  "captcha_code": "string",
  "captcha_key": "string"
}
```

响应：
```json
{
  "access_token": "string",
  "token_type": "bearer",
  "refresh_token": "string",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "phone": "string",
    "department": "string",
    "avatar": "string",
    "is_staff": true,
    "is_superuser": true,
    "date_joined": "2024-01-01T00:00:00",
    "last_login": "2024-01-01T00:00:00"
  }
}
```

#### POST /api/logout
用户登出

响应：
```json
{
  "message": "登出成功"
}
```

#### GET /api/captcha
获取验证码

响应：
```json
{
  "captcha_key": "string",
  "captcha_image": "data:image/png;base64,..."
}
```

### 密码管理

#### POST /api/forgot-password
请求密码重置

请求体：
```json
{
  "email": "user@example.com"
}
```

响应：
```json
{
  "message": "密码重置链接已发送到您的邮箱",
  "status": "success",
  "reset_token": "string"
}
```

#### POST /api/reset-password
重置密码

请求体：
```json
{
  "token": "string",
  "new_password": "string"
}
```

响应：
```json
{
  "message": "密码重置成功",
  "status": "success"
}
```

#### POST /api/change-password
修改密码（需要登录）

请求体：
```json
{
  "old_password": "string",
  "new_password": "string"
}
```

响应：
```json
{
  "message": "密码修改成功",
  "status": "success"
}
```

### 用户状态

#### GET /api/online-users
获取在线用户列表（需要登录）

响应：
```json
{
  "status": "success",
  "data": [
    {
      "id": 1,
      "username": "string",
      "email": "string",
      "first_name": "string",
      "last_name": "string",
      "department": "string",
      "avatar": "string",
      "is_staff": true,
      "is_superuser": true,
      "last_activity": "2024-01-01T00:00:00",
      "ip_address": "string",
      "user_agent": "string"
    }
  ],
  "count": 1
}
```

#### GET /api/activity-stats
获取用户活动统计（需要登录）

查询参数：
- `days`: 统计天数（默认7天）

响应：
```json
{
  "status": "success",
  "data": {
    "total_activities": 100,
    "unique_users": 10,
    "daily_stats": {
      "2024-01-01": 50,
      "2024-01-02": 50
    },
    "period_days": 7
  }
}
```

## 配置选项

在 [app/core/config.py](file:///e:/HSdigitalportal/fastapi-amis-admin-master/app/core/config.py) 中可以配置以下选项：

```python
# 登录安全配置
MAX_LOGIN_ATTEMPTS = 5  # 最大登录失败次数
LOCKOUT_MINUTES = 30  # 锁定时长（分钟）
ENABLE_CAPTCHA = False  # 是否启用验证码
CAPTCHA_EXPIRE_SECONDS = 300  # 验证码过期时间（秒）

# 密码策略配置
MIN_PASSWORD_LENGTH = 8  # 最小密码长度
MAX_PASSWORD_LENGTH = 128  # 最大密码长度
REQUIRE_PASSWORD_COMPLEXITY = True  # 是否要求密码复杂度

# 会话配置
REMEMBER_ME_DAYS = 30  # 记住我的天数
SESSION_TIMEOUT_MINUTES = 60  # 会话超时时间（分钟）
```

## 数据库模型

### UserLoginHistory
用户登录历史表

字段：
- `id`: 主键
- `user_id`: 用户ID
- `login_time`: 登录时间
- `logout_time`: 登出时间
- `ip_address`: IP地址
- `user_agent`: User-Agent信息
- `login_status`: 登录状态（success/failure）
- `failure_reason`: 失败原因

### UserActivityLog
用户活动日志表

字段：
- `id`: 主键
- `user_id`: 用户ID
- `action`: 操作类型
- `description`: 操作描述
- `ip_address`: IP地址
- `user_agent`: User-Agent信息
- `meta_data`: 元数据（JSON）
- `created_at`: 创建时间

## 使用说明

### 启用验证码

在 `app/core/config.py` 中设置：
```python
ENABLE_CAPTCHA = True
```

### 修改密码强度要求

在 `app/core/config.py` 中调整：
```python
MIN_PASSWORD_LENGTH = 10
MAX_PASSWORD_LENGTH = 64
REQUIRE_PASSWORD_COMPLEXITY = True
```

### 调整登录失败限制

在 `app/core/config.py` 中修改：
```python
MAX_LOGIN_ATTEMPTS = 3  # 减少最大失败次数
LOCKOUT_MINUTES = 60  # 增加锁定时长
```

### 集成用户活动跟踪中间件

在 `app/main.py` 中添加：
```python
from app.core.middleware.user_activity import UserActivityMiddleware

app.add_middleware(UserActivityMiddleware)
```

## 安全建议

1. **生产环境配置**
   - 修改 `SECRET_KEY` 为强随机字符串
   - 启用验证码功能
   - 调整登录失败限制参数
   - 配置HTTPS

2. **密码策略**
   - 要求密码复杂度
   - 定期要求用户修改密码
   - 实现密码历史记录，防止重复使用旧密码

3. **监控**
   - 监控登录失败次数
   - 监控异常登录行为
   - 定期审查登录历史

4. **邮件集成**
   - 实现邮件发送功能用于密码重置
   - 发送登录提醒邮件
   - 发送异常活动警报

## 注意事项

1. 验证码功能需要 Pillow 库，确保已安装：
   ```bash
   pip install Pillow
   ```

2. 密码重置功能在生产环境中需要配置邮件服务

3. 在线用户管理器使用内存存储，重启服务后会丢失在线状态

4. 用户活动日志会持续增长，建议定期清理历史数据

5. 登录页面UI已升级，确保前端资源可访问

## 后续改进建议

1. 实现双因素认证（2FA）
2. 添加登录设备管理
3. 实现密码历史记录
4. 添加账户安全评分
5. 实现异常登录检测
6. 添加邮件通知功能
7. 实现SSO单点登录
8. 添加OAuth2第三方登录
