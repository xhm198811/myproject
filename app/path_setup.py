"""路径设置模块 - 在所有其他模块导入之前导入"""

import sys
import os

# 添加项目根目录到 Python 路径
# 这确保 app 目录可以访问 fastapi_amis_admin
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)