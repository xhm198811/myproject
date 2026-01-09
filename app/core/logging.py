import logging
import sys
from app.core.config import settings

# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# 配置根日志
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        logging.StreamHandler(sys.stdout),  # 控制台输出
        logging.FileHandler("app.log", encoding="utf-8")  # 文件输出
    ]
)

# 全局日志实例
logger = logging.getLogger("enterprise-portal")