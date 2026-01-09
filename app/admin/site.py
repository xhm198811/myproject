import sys
import os
# 添加路径以确保可以导入 fastapi_amis_admin
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

try:
    from fastapi_amis_admin.admin import AdminSite
    from fastapi_amis_admin.admin.settings import Settings
except ImportError:
    # 如果仍然导入失败，尝试其他方式
    pass

from ..core.config import settings as app_settings
from ..users.admin import UserAdmin
from fastapi import Request

# 创建自定义AdminSite类
class CustomAdminSite(AdminSite):
    """自定义管理站点"""

    async def has_page_permission(self, request, obj=None, action=None):
        """自定义权限检查 - 检查用户是否已登录"""
        print(f"[DEBUG] CustomAdminSite.has_page_permission called: obj={obj}, action={action}")
        
        if not hasattr(request.state, 'user') or request.state.user is None:
            print(f"[DEBUG] CustomAdminSite.has_page_permission: No user in request.state")
            return False
        
        user = request.state.user
        print(f"[DEBUG] CustomAdminSite.has_page_permission: user={user}")
        
        if not user.get('is_active', True):
            print(f"[DEBUG] CustomAdminSite.has_page_permission: User is not active")
            return False
        
        if not user.get('is_staff', False) and not user.get('is_superuser', False):
            print(f"[DEBUG] CustomAdminSite.has_page_permission: User is not staff or superuser")
            return False
        
        print(f"[DEBUG] CustomAdminSite.has_page_permission: Permission granted")
        return True

    def error_no_page_permission(self, request):
        """自定义无权限错误处理 - 重定向到登录页面"""
        from fastapi.responses import RedirectResponse
        original_url = str(request.url)
        login_url = f"/login?redirect={original_url}"
        return RedirectResponse(url=login_url)

    async def get_page_html(self, request, page):
        """自定义页面HTML，使用CDN资源"""
        # 获取原始HTML
        html = await super().get_page_html(request, page)

        # 添加令牌验证和设置脚本
        token_script = """
        <script>
        // 页面加载时验证和设置认证令牌
        (function() {
            console.log('[Admin Page] 页面加载开始');
            
            // 设置全局函数来验证令牌
            window.verifyAndSetToken = async function() {
                const access_token = localStorage.getItem('access_token');
                if (!access_token) {
                    console.log('[Admin Page] 未找到访问令牌');
                    return false;
                }
                
                try {
                    console.log('[Admin Page] 验证令牌有效性');
                    const response = await fetch('/api/auth/verify', {
                        method: 'GET',
                        headers: {
                            'Authorization': 'Bearer ' + access_token,
                            'Content-Type': 'application/json'
                        }
                    });
                    
                    const data = await response.json();
                    console.log('[Admin Page] 令牌验证结果:', data);
                    
                    if (data.code === 200 && data.data.valid) {
                        console.log('[Admin Page] 令牌验证成功');
                        return true;
                    } else {
                        console.log('[Admin Page] 令牌验证失败，清理本地存储');
                        localStorage.removeItem('access_token');
                        localStorage.removeItem('refresh_token');
                        localStorage.removeItem('user');
                        return false;
                    }
                } catch (error) {
                    console.error('[Admin Page] 令牌验证错误:', error);
                    return false;
                }
            };
            
            // 设置fetch拦截器
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                const access_token = localStorage.getItem('access_token');
                console.log('[Fetch Interceptor] URL:', url, 'Token exists:', !!access_token);
                if (access_token) {
                    options = options || {};
                    options.headers = options.headers || {};
                    options.headers['Authorization'] = 'Bearer ' + access_token;
                    console.log('[Fetch Interceptor] Adding Authorization header');
                }
                return originalFetch.call(window, url, options);
            };
            
            // 页面加载完成后验证令牌
            document.addEventListener('DOMContentLoaded', async function() {
                console.log('[Admin Page] DOM加载完成，验证令牌');
                const isValid = await window.verifyAndSetToken();
                if (!isValid) {
                    console.log('[Admin Page] 令牌无效，跳转到登录页面');
                    setTimeout(() => {
                        window.location.href = '/login?redirect=' + encodeURIComponent(window.location.href);
                    }, 1000);
                }
            });
            
            // 页面离开时清理（可选）
            window.addEventListener('beforeunload', function() {
                console.log('[Admin Page] 页面即将离开');
            });
        })();
        </script>
        """

        # 在</body>标签之前插入脚本
        html = html.replace("</body>", token_script + "</body>")

        return html

# 创建AdminSite实例
site = CustomAdminSite(
    settings=Settings(
        database_url_async=app_settings.DATABASE_URL_ASYNC,
        site_title=app_settings.ADMIN_TITLE,
        site_icon=app_settings.ADMIN_ICON,
        site_path=app_settings.ADMIN_PATH,
        amis_cdn=app_settings.AMIS_CDN,
        amis_pkg=app_settings.AMIS_PKG,
        debug=app_settings.DEBUG,
        # 设置正确的文件上传API端点
        amis_file_receiver="post:/api/upload/file",
        amis_image_receiver="post:/api/upload/file"
    )
)

# 注册Admin组件
# 注册用户管理
from ..users.admin import UserAdmin, RoleAdmin, PermissionAdmin, UserActivityLogAdmin, UserLoginHistoryAdmin
# 注册用户管理（隐藏角色管理和权限管理）
site.register_admin(UserAdmin)
# 暂时隐藏角色管理和权限管理
# site.register_admin(RoleAdmin, PermissionAdmin)
# 暂时隐藏用户活动日志和用户登录历史
# site.register_admin(UserActivityLogAdmin, UserLoginHistoryAdmin)

# 注册登录表单（已屏蔽）
# from .users.login_admin import UserLoginFormAdmin
# site.register_admin(UserLoginFormAdmin)

# 注册合同管理
from ..contracts.admin import ContractAdmin, ContractStatusLogAdmin, ContractAttachmentAdmin
site.register_admin(ContractAdmin, ContractStatusLogAdmin, ContractAttachmentAdmin)

# 注册项目管理
from app.projects.admin import (
    ProjectAdmin, ProjectStageAdmin, ProjectTaskAdmin,
    ProjectDocumentAdmin
)
site.register_admin(
    ProjectAdmin, ProjectStageAdmin, ProjectTaskAdmin,
    ProjectDocumentAdmin
)

# 注册产品管理 - 暂时隐藏，只保留Django产品管理
# from .products.admin_module import (
#     ProductAdmin, ProductModelAdmin, MaterialConfigAdmin, 
#     BoardTypeAdmin, QuotationRecordAdmin, AluminumPriceAdmin
# )

# site.register_admin(
#     ProductAdmin, ProductModelAdmin, MaterialConfigAdmin, 
#     BoardTypeAdmin, QuotationRecordAdmin, AluminumPriceAdmin
# )

# 注册Django产品管理
from ..products.admin import DjangoProductAdmin, QuotationRecordPageAdmin
site.register_admin(DjangoProductAdmin, QuotationRecordPageAdmin)

# 注册组织人员管理
from ..organization.admin import (
    OrganizationAdmin,
    OrganizationRoleAdmin,
    PersonAdmin,
    PersonDepartmentHistoryAdmin,
)
site.register_admin(
    OrganizationAdmin,
    OrganizationRoleAdmin,
    PersonAdmin,
    PersonDepartmentHistoryAdmin,
)

# 注册报价单管理 - 暂时隐藏
# from .quotes.admin import QuoteAdmin, QuoteItemAdmin
# site.register_admin(QuoteAdmin, QuoteItemAdmin)

# 注册自定义表单管理 - 暂时隐藏
# from .forms.admin import CustomFormAdmin
# site.register_admin(CustomFormAdmin)
