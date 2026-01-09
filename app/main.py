# 1. 基础导入（规范排序 + 补充缺失依赖）
import os
import sys
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from contextlib import asynccontextmanager

# FastAPI 核心导入
from fastapi import FastAPI, Request, HTTPException, Depends, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, HTMLResponse, Response
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.exceptions import RequestValidationError

# 第三方依赖
from sqlalchemy.ext.asyncio import AsyncSession
from jose import JWTError, jwt
from pydantic import ValidationError

# 2. 核心配置导入（绝对导入 + 补充类型提示）
from app.core.config import settings
from app.core.db import init_db, get_async_db, engine  # 补充engine定义
from app.core.logging import logger
from app.core.auth import authenticate_user, create_access_token, create_refresh_token
from app.admin.site import site  # Amis Admin站点

# 3. 路由导入（整理顺序，统一命名）
from app.users.api.user import router as users_router
from app.users.api.auth import router as auth_router
from app.contracts.api.contract import router as contracts_router
from app.contracts.api.file import file_router as contracts_file_router
from app.projects.api.project import router as projects_router
from app.projects.api.file import project_file_router
from app.products.api.django_products import router as django_products_router
from app.products.api.django_users import router as django_users_router
from app.quotes.api.quote import router as quote_router
from app.api.copy.copy_router import copy_router
from app.api.general_file import router as general_file_router
from app.api.batch_import import router as batch_import_router

# 4. 中间件导入（修正重复编号，规范顺序）
from app.middleware.error_handling import ErrorHandlingMiddleware
from app.core.middleware.auth import AuthenticationMiddleware
from app.middleware.amis_cdn import amis_cdn_middleware
from app.middleware.clipboard_injection import clipboard_script_injection_middleware
from app.middleware.token_verification import TokenVerificationMiddleware

# 5. 工具/模型导入（补充缺失依赖）
from app.utils.captcha import create_captcha, verify_captcha
from app.users.api.schemas import TokenResponse, LoginRequest, UserResponse  # 补充用户模型

# ======================
# 数据库健康检查（补充缺失的db_manager实现）
# ======================
class DatabaseManager:
    """数据库连接管理器（补充健康检查依赖）"""
    @staticmethod
    async def health_check() -> Dict[str, str]:
        """检查数据库连接状态"""
        try:
            async with engine.connect() as conn:
                await conn.execute("SELECT 1")  # 测试查询
                return {"status": "healthy", "message": "数据库连接正常"}
        except Exception as e:
            logger.error(f"数据库健康检查失败: {str(e)}")
            return {"status": "unhealthy", "message": str(e)}

# 全局数据库管理器实例
db_manager = DatabaseManager()

# ======================
# 应用生命周期管理（增强错误处理）
# ======================
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期钩子：启动时初始化，关闭时清理
    参考：https://fastapi.tiangolo.com/advanced/events/
    """
    logger.info(f"启动{settings.APP_NAME} v{settings.APP_VERSION} (DEBUG: {settings.DEBUG})")
    try:
        # 初始化数据库
        await init_db()
        logger.info("数据库初始化完成")
        
        # 初始化Amis Admin站点
        logger.info(f"挂载Amis Admin到路径: {settings.ADMIN_PATH}")
        
        yield  # 应用运行中
    except Exception as e:
        logger.error(f"应用启动失败: {str(e)}", exc_info=True)
        raise
    finally:
        # 安全关闭数据库引擎
        try:
            await engine.dispose()
            logger.info("数据库引擎已关闭")
        except Exception as e:
            logger.warning(f"关闭数据库引擎失败: {str(e)}")
        logger.info("应用已正常关闭")

# ======================
# 创建FastAPI应用实例（最佳实践配置）
# ======================
app = FastAPI(
    title=settings.APP_NAME,
    description=settings.APP_DESCRIPTION,
    version=settings.APP_VERSION,
    lifespan=lifespan,
    docs_url="/docs" if settings.DEBUG else None,  # 生产环境关闭docs
    redoc_url="/redoc" if settings.DEBUG else None,
    openapi_url="/openapi.json" if settings.DEBUG else None,
)

# ======================
# 中间件注册（严格按优先级排序，关键！）
# 优先级：CORS → 错误处理 → 认证 → 业务中间件
# ======================
# 1. CORS中间件（最先注册，解决跨域问题）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=settings.CORS_ALLOW_CREDENTIALS,
    allow_methods=settings.CORS_ALLOW_METHODS,
    allow_headers=settings.CORS_ALLOW_HEADERS,
)

# 2. 统一错误处理中间件（捕获所有异常）
app.add_middleware(ErrorHandlingMiddleware)

# 3. 认证中间件（用户身份验证）
app.add_middleware(AuthenticationMiddleware)

# 4. Token验证中间件（令牌有效性检查）
app.add_middleware(TokenVerificationMiddleware)

# 5. Amis CDN中间件（静态资源优化）
app.middleware("http")(amis_cdn_middleware)

# 6. 剪贴板脚本注入中间件（前端功能支持）
app.middleware("http")(clipboard_script_injection_middleware)

# ======================
# 静态文件挂载（鲁棒性优化 + 路径验证）
# ======================
# 验证并创建静态目录
static_dir = settings.STATIC_DIR
if not os.path.isabs(static_dir):
    # 转换为绝对路径，避免相对路径问题
    static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), static_dir))

if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
    logger.warning(f"静态目录不存在，已自动创建: {static_dir}")

# 挂载静态文件（添加缓存控制，提升性能）
app.mount(
    "/static",
    StaticFiles(
        directory=static_dir,
        html=True  # 支持静态HTML文件
    ),
    name="static"
)

# ======================
# API路由注册（批量注册 + 日志记录）
# ======================
api_routers = [
    (users_router, "/api"),
    (auth_router, "/api"),
    (contracts_router, "/api"),
    (contracts_file_router, "/api"),
    (projects_router, "/api"),
    (project_file_router, "/api"),
    (django_products_router, "/api"),
    (django_users_router, "/api"),
    (quote_router, "/api"),
    (copy_router, "/api"),
    (general_file_router, "/api"),
    (batch_import_router, "/api"),
]

# 批量注册并记录日志
for router, prefix in api_routers:
    router_name = router.prefix if router.prefix else router.tags[0] if router.tags else "unknown"
    app.include_router(router, prefix=prefix)
    logger.info(f"注册API路由: {prefix} -> {router_name}")

# ======================
# Amis Admin挂载（核心功能）
# ======================
site.mount_app(app)
logger.info(f"Amis Admin站点挂载完成，访问路径: {settings.ADMIN_PATH}")

# ======================
# 核心接口实现（兼容JSON/表单登录 + 完善错误处理）
# ======================
@app.get("/api/captcha", response_class=JSONResponse)
async def get_captcha():
    """生成验证码（前端依赖）"""
    try:
        captcha_data = await create_captcha()
        logger.debug("验证码生成成功")
        return captcha_data
    except Exception as e:
        logger.error(f"生成验证码失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"生成验证码失败: {str(e)}"
        )

@app.post("/api/login/", response_model=TokenResponse)
async def login(
    request: Request,
    db: AsyncSession = Depends(get_async_db)
):
    """登录接口（前端依赖）- 支持 JSON 和表单数据"""
    
    # 解析请求体
    try:
        content_type = request.headers.get("content-type", "")
        
        if "application/json" in content_type:
            body = await request.json()
            username = body.get("username")
            password = body.get("password")
            captcha_key = body.get("captcha_key")
            captcha_code = body.get("captcha_code")
        else:
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
            captcha_key = form.get("captcha_key")
            captcha_code = form.get("captcha_code")
    except Exception as e:
        logger.error(f"解析请求体失败: {e}")
        raise HTTPException(status_code=400, detail="请求数据格式错误")
    
    if not username or not password:
        raise HTTPException(status_code=400, detail="用户名和密码不能为空")
    
    # 1. 验证验证码（仅在启用时）
    if settings.ENABLE_CAPTCHA:
        if not captcha_key or not captcha_code:
            raise HTTPException(status_code=400, detail="验证码信息不完整")
        if not await verify_captcha(captcha_key, captcha_code):
            logger.warning(f"验证码验证失败: 密钥={captcha_key[:8]}... 输入={captcha_code}")
            raise HTTPException(status_code=400, detail="验证码错误")

    # 2. 验证用户身份
    user = await authenticate_user(db=db, username=username, password=password)
    if not user:
        logger.warning(f"登录失败: 用户名={username} 密码验证失败")
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 3. 生成Token
    try:
        access_token = create_access_token(
            data={"sub": user["username"], "user_id": user["id"]},
            expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        )
        refresh_token = create_refresh_token(
            data={"sub": user["username"]}
        )
    except Exception as e:
        logger.error(f"生成Token失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="生成认证令牌失败")

    # 4. 记录登录日志
    client_ip = request.client.host if request.client else "unknown"
    logger.info(f"用户登录成功: 用户名={username} IP={client_ip}")

    # 5. 返回标准化结果
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        user=UserResponse(
            username=user["username"],
            email=user["email"],
            full_name=f"{user.get('first_name', '')} {user.get('last_name', '')}".strip(),
            roles=["admin"] if user["is_superuser"] else ["user"]
        )
    )

@app.get("/api/auth/verify")
async def verify_token(request: Request):
    """验证当前令牌是否有效（增强版）"""
    try:
        # 从请求头获取Authorization
        authorization = request.headers.get("Authorization", "")
        scheme, token = get_authorization_scheme_param(authorization)

        # 从Cookie备用获取（兼容前端存储方式）
        if not token:
            token = request.cookies.get("access_token", "")
            scheme = "bearer"

        if scheme.lower() != "bearer" or not token:
            return JSONResponse(
                status_code=200,
                content={
                    "code": 401,
                    "message": "未提供有效令牌",
                    "data": {"valid": False}
                }
            )

        # 解码并验证Token
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": True}  # 验证过期时间
        )
        username = payload.get("sub")

        if not username:
            raise JWTError("Token中缺少用户名信息")

        return JSONResponse(
            status_code=200,
            content={
                "code": 200,
                "message": "令牌有效",
                "data": {
                    "valid": True,
                    "username": username,
                    "exp": payload.get("exp")  # 返回过期时间
                }
            }
        )

    except JWTError as e:
        logger.warning(f"Token验证失败: {str(e)}")
        return JSONResponse(
            status_code=200,
            content={
                "code": 401,
                "message": "令牌无效或已过期",
                "data": {"valid": False}
            }
        )
    except Exception as e:
        logger.error(f"验证令牌异常: {str(e)}", exc_info=True)
        return JSONResponse(
            status_code=200,
            content={
                "code": 500,
                "message": "服务器内部错误",
                "data": {"valid": False}
            }
        )

@app.get("/api/health", response_class=JSONResponse)
async def health_check():
    """健康检查接口（增强版，含详细状态）"""
    health_status = {
        "app": {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "healthy",
            "debug": settings.DEBUG
        },
        "database": {
            "status": "unknown",
            "message": ""
        },
        "system": {
            "python_version": sys.version,
            "platform": sys.platform
        }
    }

    # 检查数据库连接
    try:
        db_health = await db_manager.health_check()
        health_status["database"] = db_health
    except Exception as e:
        health_status["database"] = {
            "status": "error",
            "message": str(e)
        }

    # 整体状态判断
    overall_status = "healthy" if health_status["database"]["status"] == "healthy" else "unhealthy"

    return JSONResponse(
        content={
            "code": 200 if overall_status == "healthy" else 503,
            "message": overall_status,
            "data": health_status
        }
    )

# ======================
# 页面路由（优化模板渲染 + 兼容性）
# ======================
@app.get("/", response_class=JSONResponse)
async def root():
    """根路径（API导航）"""
    return {
        "code": 200,
        "message": f"欢迎使用{settings.APP_NAME}",
        "data": {
            "docs": "/docs" if settings.DEBUG else None,
            "redoc": "/redoc" if settings.DEBUG else None,
            "health": "/api/health",
            "admin": settings.ADMIN_PATH,
            "login": "/login",
            "version": settings.APP_VERSION
        }
    }

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, redirect: Optional[str] = None):
    """登录页面（优化版，支持验证码开关）"""
    redirect_url = redirect or settings.ADMIN_PATH
    captcha_display = "flex" if settings.ENABLE_CAPTCHA else "none"
    captcha_enabled = str(settings.ENABLE_CAPTCHA).lower()

    # 读取HTML模板（避免硬编码，可优化为文件读取）
    html_template = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>登录 - {app_name}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            margin: 0;
            padding: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
        }}
        .login-container {{
            background-color: white;
            border-radius: 12px;
            box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
            padding: 48px;
            width: 100%;
            max-width: 420px;
            animation: fadeIn 0.5s ease-in;
        }}
        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(-20px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}
        .login-header {{
            text-align: center;
            margin-bottom: 32px;
        }}
        .login-title {{
            color: #333;
            font-size: 28px;
            font-weight: 600;
            margin: 0 0 8px 0;
        }}
        .login-subtitle {{
            color: #666;
            font-size: 14px;
            margin: 0;
        }}
        .form-group {{
            margin-bottom: 20px;
        }}
        .form-label {{
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
            font-size: 14px;
        }}
        .form-input {{
            width: 100%;
            padding: 12px 16px;
            border: 2px solid #e8e8e8;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
            box-sizing: border-box;
        }}
        .form-input:focus {{
            outline: none;
            border-color: #667eea;
            box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
        }}
        .captcha-group {{
            display: {captcha_display};
            gap: 12px;
            align-items: center;
        }}
        .captcha-input {{
            flex: 1;
        }}
        .captcha-image {{
            width: 120px;
            height: 40px;
            border-radius: 8px;
            cursor: pointer;
            border: 2px solid #e8e8e8;
            transition: all 0.3s;
        }}
        .captcha-image:hover {{
            border-color: #667eea;
        }}
        .remember-me {{
            display: flex;
            align-items: center;
            margin-bottom: 24px;
        }}
        .remember-me input {{
            width: 18px;
            height: 18px;
            margin-right: 8px;
            cursor: pointer;
        }}
        .remember-me label {{
            color: #666;
            font-size: 14px;
            cursor: pointer;
        }}
        .login-button {{
            width: 100%;
            padding: 14px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }}
        .login-button:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
        }}
        .login-button:active {{
            transform: translateY(0);
        }}
        .login-button:disabled {{
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }}
        .error-message {{
            color: #f5222d;
            text-align: center;
            margin-top: 16px;
            font-size: 14px;
            padding: 12px;
            background-color: #fff1f0;
            border-radius: 6px;
            border: 1px solid #ffa39e;
            display: none;
        }}
        .error-message.show {{
            display: block;
        }}
        .loading {{
            display: inline-block;
            width: 16px;
            height: 16px;
            border: 2px solid #ffffff;
            border-radius: 50%;
            border-top-color: transparent;
            animation: spin 0.8s linear infinite;
            margin-right: 8px;
        }}
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
    </style>
</head>
<body>
    <div class="login-container">
        <div class="login-header">
            <h1 class="login-title">{app_name}</h1>
            <p class="login-subtitle">请登录您的账户</p>
        </div>
        <form id="login-form">
            <div class="form-group">
                <label for="username" class="form-label">用户名</label>
                <input type="text" id="username" name="username" class="form-input" placeholder="请输入用户名" required autocomplete="username">
            </div>
            <div class="form-group">
                <label for="password" class="form-label">密码</label>
                <input type="password" id="password" name="password" class="form-input" placeholder="请输入密码" required autocomplete="current-password">
            </div>
            <div class="form-group captcha-group" id="captcha-group">
                <input type="text" id="captcha_code" name="captcha_code" class="form-input captcha-input" placeholder="请输入验证码">
                <img id="captcha-image" class="captcha-image" src="" alt="验证码" title="点击刷新验证码">
                <input type="hidden" id="captcha_key" name="captcha_key">
            </div>
            <div class="remember-me">
                <input type="checkbox" id="remember_me" name="remember_me">
                <label for="remember_me">记住我（30天）</label>
            </div>
            <button type="submit" class="login-button" id="login-button">
                <span id="button-text">登录</span>
            </button>
            <div id="error-message" class="error-message"></div>
        </form>
    </div>
    <script>
        const redirectUrl = "{redirect_url}";
        const captchaEnabled = {captcha_enabled};
        let captchaKey = '';
        
        async function loadCaptcha() {{
            if (!captchaEnabled) return;
            
            try {{
                const response = await fetch('/api/captcha');
                const data = await response.json();
                
                if (data.code === 200 && data.data?.captcha_key && data.data?.captcha_image) {{
                    captchaKey = data.data.captcha_key;
                    document.getElementById('captcha_key').value = captchaKey;
                    document.getElementById('captcha-image').src = data.data.captcha_image;
                }}
            }} catch (error) {{
                console.error('加载验证码失败:', error);
                captchaEnabled && showError('加载验证码失败，请刷新页面重试');
            }}
        }}
        
        function showError(message) {{
            const el = document.getElementById('error-message');
            el.textContent = message;
            el.classList.add('show');
            setTimeout(() => el.classList.remove('show'), 5000);
        }}
        
        // 绑定验证码刷新事件
        document.getElementById('captcha-image')?.addEventListener('click', loadCaptcha);
        
        // 登录表单提交
        document.getElementById('login-form').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value.trim();
            const captchaCode = captchaEnabled ? document.getElementById('captcha_code').value.trim() : '';
            const rememberMe = document.getElementById('remember_me').checked;
            const loginButton = document.getElementById('login-button');
            const buttonText = document.getElementById('button-text');
            
            // 基础校验
            if (!username) return showError('请输入用户名');
            if (!password) return showError('请输入密码');
            if (captchaEnabled && !captchaCode) return showError('请输入验证码');
            
            // 禁用按钮，显示加载状态
            loginButton.disabled = true;
            buttonText.innerHTML = '<span class="loading"></span>登录中...';
            
            try {{
                // 构建请求数据
                const requestData = {{ username, password, remember_me: rememberMe }};
                if (captchaEnabled && captchaKey && captchaCode) {{
                    requestData.captcha_key = captchaKey;
                    requestData.captcha_code = captchaCode;
                }}
                
                // 发送登录请求（JSON格式）
                const response = await fetch('/api/login', {{
                    method: 'POST',
                    headers: {{ 'Content-Type': 'application/json' }},
                    body: JSON.stringify(requestData)
                }});
                
                const data = await response.json();
                
                if (response.ok) {{
                    // 存储Token
                    localStorage.setItem('access_token', data.access_token);
                    localStorage.setItem('refresh_token', data.refresh_token);
                    localStorage.setItem('user', JSON.stringify(data.user));
                    
                    // Cookie存储（兼容服务端）
                    const maxAge = rememberMe ? 30 * 24 * 60 * 60 : 2 * 60 * 60;
                    document.cookie = `access_token=${{data.access_token}}; path=/; max-age=${{maxAge}}; SameSite=Lax`;
                    document.cookie = `refresh_token=${{data.refresh_token}}; path=/; max-age=${{maxAge}}; SameSite=Lax`;
                    
                    // 自动添加Authorization头
                    const originalFetch = window.fetch;
                    window.fetch = (url, options = {{}}) => {{
                        const token = localStorage.getItem('access_token');
                        if (token) {{
                            options.headers = {{
                                ...options.headers,
                                'Authorization': `Bearer ${{token}}`
                            }};
                        }}
                        return originalFetch(url, options);
                    }};
                    
                    // 跳转
                    buttonText.innerHTML = '✅ 登录成功，正在跳转...';
                    setTimeout(() => window.location.href = redirectUrl, 800);
                }} else {{
                    showError(data.detail || '登录失败，请检查用户名和密码');
                    captchaEnabled && (loadCaptcha(), document.getElementById('captcha_code').value = '');
                }}
            }} catch (error) {{
                showError('网络错误，请稍后重试');
                console.error('登录请求失败:', error);
            }} finally {{
                loginButton.disabled = false;
                buttonText.textContent = '登录';
            }}
        }});
        
        // 页面加载时初始化验证码
        window.addEventListener('load', loadCaptcha);
    </script>
</body>
</html>
    """.format(
        app_name=settings.APP_NAME,
        redirect_url=redirect_url,
        captcha_display=captcha_display,
        captcha_enabled=captcha_enabled
    )

    return HTMLResponse(content=html_template)

# ======================
# 启动入口（使用配置文件，兼容多种启动方式）
# ======================
def main() -> None:
    """应用启动入口（脚本运行）"""
    import uvicorn

    # 打印启动信息
    logger.info("=" * 80)
    logger.info(f"启动 {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"调试模式: {'开启' if settings.DEBUG else '关闭'}")
    logger.info(f"验证码功能: {'开启' if settings.ENABLE_CAPTCHA else '关闭'}")
    logger.info(f"访问地址: http://{settings.HOST}:{settings.PORT}")
    logger.info(f"管理后台: http://{settings.HOST}:{settings.PORT}{settings.ADMIN_PATH}")
    logger.info("=" * 80)

    # 启动服务器（使用配置文件参数）
    uvicorn.run(
        "app.main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.DEBUG,
        log_level="info" if settings.DEBUG else "warning",
        access_log=settings.DEBUG,
        workers=1 if settings.DEBUG else 4,  # 生产环境多进程
    )

if __name__ == "__main__":
    main()