# 剪贴板复制功能使用说明

## 概述

为 fastapi_amis_admin 的所有应用添加了统一的剪贴板复制按钮功能,支持在列表页和详情页复制记录数据。

## 功能特性

### 1. 快速复制 (复制按钮)
- **位置**: 列表页和详情页每行记录的操作栏
- **功能**: 一键复制记录的关键数据到剪贴板
- **返回**: 直接返回复制成功提示,不弹出对话框

### 2. 详情复制 (详情复制按钮)
- **位置**: 列表页和详情页每行记录的操作栏
- **功能**: 打开对话框,选择复制格式后复制完整数据
- **支持格式**:
  - **文本格式**: 格式化的文本,便于阅读
  - **JSON格式**: 结构化JSON数据
  - **Markdown表格**: Markdown表格格式

## 已配置的应用

以下应用已启用复制功能:

### 1. 合同管理 (ContractAdmin)
- **快速复制字段**: 合同编号、合同名称、类型、状态、签署日期、到期日期、甲方、乙方、金额
- **特殊格式化**:
  - 类型: 采购合同/销售合同
  - 状态: 草稿/待签署/已签署/执行中/已完成/已取消
  - 金额: ¥格式化显示

### 2. 产品管理 (ProductAdmin)
- **快速复制字段**: 产品名称、厚度、最终价格
- **特殊格式化**:
  - 厚度: 显示单位mm
  - 价格: ¥格式化显示

### 3. 项目管理 (ProjectAdmin)
- **快速复制字段**: 项目名称、状态、项目负责人、金额
- **特殊格式化**:
  - 状态: 待开始/进行中/已完成/延期/已取消
  - 金额: ¥格式化显示

### 4. 项目阶段管理 (ProjectStageAdmin)
- **快速复制字段**: 阶段名称、状态、计划开始时间、计划结束时间

### 5. 项目任务管理 (ProjectTaskAdmin)
- **快速复制字段**: 任务名称、状态、进度、优先级、执行人

### 6. 项目成员管理 (ProjectMemberAdmin)
- **快速复制字段**: 角色、权限

### 7. 项目文档管理 (ProjectDocumentAdmin)
- **快速复制字段**: 文档名称、分类、版本、上传者

### 8. 项目活动管理 (ProjectActivityAdmin)
- **快速复制字段**: 操作、内容

### 9. 材料配置管理 (MaterialConfigAdmin)
- **快速复制字段**: 材料名称、系数、厚度选项

### 10. 背衬类型管理 (BoardTypeAdmin)
- **快速复制字段**: 类型名称、最小厚度、最大厚度

### 11. 产品型号管理 (ProductModelAdmin)
- **快速复制字段**: 型号名称、版本

### 12. 报价记录管理 (QuotationRecordAdmin)
- **快速复制字段**: 产品名称、厚度、最终价格

### 13. 铝锭价格管理 (AluminumPriceAdmin)
- **快速复制字段**: 日期、价格
- **特殊格式化**:
  - 价格: ¥/吨格式化显示

### 14. 用户管理 (UserAdmin)
- **快速复制字段**: 用户名、邮箱、激活状态

### 15. 角色管理 (RoleAdmin)
- **快速复制字段**: 角色名称、显示名称、激活状态

### 16. 权限管理 (PermissionAdmin)
- **快速复制字段**: 权限名称、代码、模块、操作

### 17. 用户活动日志 (UserActivityLogAdmin)
- **快速复制字段**: 操作、描述、IP地址

### 18. 用户登录历史 (UserLoginHistoryAdmin)
- **快速复制字段**: 登录时间、IP地址、登录状态

## 使用方法

### 快速复制

1. 在列表页或详情页找到目标记录
2. 点击操作栏中的"复制"按钮
3. 系统会自动复制关键数据到剪贴板
4. 显示复制成功提示

### 详情复制

1. 在列表页或详情页找到目标记录
2. 点击操作栏中的"详情复制"按钮
3. 在弹出的对话框中选择复制格式:
   - **文本格式**: 适合一般文档粘贴
   - **JSON格式**: 适合开发者使用
   - **Markdown表格**: 适合Markdown文档
4. 可选: 输入要复制的字段名(逗号分隔,留空则复制所有字段)
5. 点击"复制到剪贴板"按钮

## 自定义配置

如需为新的Admin类添加复制功能,请参考以下步骤:

### 1. 导入必要的模块

```python
from ..utils.clipboard_copy_action import add_clipboard_copy_actions, ClipboardCopyAction, QuickClipboardCopyAction
from ..utils.copy_config import get_copy_config
```

### 2. 在Admin类的__init__方法中添加复制功能

```python
def __init__(self, app: "AdminApp"):
    super().__init__(app)
    if not hasattr(self, 'custom_actions'):
        self.custom_actions = []

    # 获取复制配置
    copy_config = get_copy_config('YourAdminClassName')

    # 添加快速复制
    self.custom_actions.append(
        QuickClipboardCopyAction(
            admin=self,
            name="quick_copy",
            label="复制",
            copy_fields=copy_config.get('quick_copy_fields', []),
            field_formatters=copy_config.get('field_formatters', {})
        )
    )

    # 添加详情复制
    self.custom_actions.append(
        ClipboardCopyAction(
            admin=self,
            name="clipboard_copy",
            label="详情复制",
            copy_format='text',
            field_formatters=copy_config.get('field_formatters', {})
        )
    )
```

### 3. 在copy_config.py中添加配置

```python
# Admin类名称复制配置
your_admin_copy_fields = [
    'field1', 'field2', 'field3'
]

your_admin_field_formatters = {
    'field1': lambda x: f"标签:{x}" if x else "",
    'field2': lambda x: f"数值:{x}" if x else "",
    # ...
}

# 添加到get_copy_config函数的configs字典中
def get_copy_config(admin_name: str):
    configs = {
        # ... 其他配置 ...
        'YourAdminClassName': {
            'quick_copy_fields': your_admin_copy_fields,
            'field_formatters': your_admin_field_formatters,
        },
    }
    return configs.get(admin_name, {})
```

## 技术实现

### 文件结构

```
app/
├── utils/
│   ├── clipboard_copy_action.py  # 剪贴板复制动作模块
│   ├── copy_config.py             # 复制功能配置
│   ├── enhanced_copy_action.py    # 增强版复制(保留)
│   ├── copy_action.py             # 基础复制(保留)
│   └── copy_utils.py              # 复制工具(保留)
├── admin.py                       # Admin站点配置
├── main.py                        # 应用入口
├── contracts/admin.py             # 合同管理Admin
├── products/admin_module.py       # 产品管理Admin
├── projects/admin.py              # 项目管理Admin
└── users/admin.py                 # 用户管理Admin
```

### 核心组件

1. **ClipboardCopyAction**: 完整复制动作
   - 支持多种格式(文本/JSON/Markdown)
   - 支持自定义字段选择
   - 提供预览功能

2. **QuickClipboardCopyAction**: 快速复制动作
   - 一键复制关键数据
   - 支持自定义字段和格式化
   - 直接返回结果,无对话框

3. **copy_config.py**: 配置模块
   - 统一管理所有Admin的复制配置
   - 支持字段格式化函数

### 路由注册

复制功能路由在应用启动时自动注册:

```python
# 在main.py的lifespan函数中
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    site.register_copy_routes(app)  # 注册复制路由
    yield
```

## 注意事项

1. **浏览器兼容性**: 剪贴板复制功能需要现代浏览器支持
2. **权限要求**: 用户需要有对应Admin的访问权限
3. **数据安全**: 敏感字段(如密码)不会被复制
4. **性能考虑**: 复制操作不会影响数据库性能

## 常见问题

### Q: 复制按钮不显示怎么办?

A: 检查以下几点:
1. 确认Admin类已正确添加复制功能代码
2. 检查应用是否已重启
3. 查看浏览器控制台是否有错误

### Q: 复制的内容格式不正确?

A:
1. 检查field_formatters配置是否正确
2. 确认数据类型是否支持格式化
3. 查看后端日志是否有错误

### Q: 如何添加新的复制格式?

A:
1. 在ClipboardCopyAction类中添加新的格式化方法
2. 在前端对话框的格式选择中添加新选项
3. 更新文档说明

## 未来改进

- 支持批量复制多个记录
- 添加复制历史记录
- 支持自定义复制模板
- 添加复制权限控制
- 支持跨应用复制

## 联系支持

如有问题或建议,请联系开发团队。
