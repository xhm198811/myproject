"""
复制功能错误处理和日志记录机制
提供统一的异常分类、错误恢复和日志记录功能
"""
import logging
import traceback
from enum import Enum
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass
from datetime import datetime
from fastapi_amis_admin.crud.schema import BaseApiOut
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, DatabaseError, OperationalError
from pydantic import BaseModel, Field


class CopyErrorCode(str, Enum):
    """复制功能错误码枚举"""
    # 通用错误 (1000-1099)
    UNKNOWN_ERROR = "COPY_1000"
    INVALID_PARAMETERS = "COPY_1001"
    OPERATION_TIMEOUT = "COPY_1002"
    RATE_LIMIT_EXCEEDED = "COPY_1003"
    
    # 数据相关错误 (1100-1199) 
    RECORD_NOT_FOUND = "COPY_1100"
    DATA_VALIDATION_FAILED = "COPY_1101"
    INTEGRITY_CONSTRAINT_VIOLATION = "COPY_1102"
    UNIQUE_CONSTRAINT_VIOLATION = "COPY_1103"
    FOREIGN_KEY_CONSTRAINT_VIOLATION = "COPY_1104"
    
    # 权限相关错误 (1200-1299)
    ACCESS_DENIED = "COPY_1200"
    INSUFFICIENT_PERMISSIONS = "COPY_1201"
    RESOURCE_ACCESS_DENIED = "COPY_1202"
    
    # 系统相关错误 (1300-1399)
    DATABASE_CONNECTION_ERROR = "COPY_1300"
    DATABASE_OPERATION_ERROR = "COPY_1301"
    ADAPTER_NOT_AVAILABLE = "COPY_1302"
    SESSION_ERROR = "COPY_1303"
    
    # 业务逻辑错误 (1400-1499)
    CANNOT_COPY_DELETED_RECORD = "COPY_1400"
    COPY_LIMIT_EXCEEDED = "COPY_1401"
    RELATIONSHIP_COPY_FAILED = "COPY_1402"
    CODE_GENERATION_FAILED = "COPY_1403"
    BATCH_PARTIAL_FAILURE = "COPY_1404"


@dataclass
class CopyErrorContext:
    """错误上下文信息"""
    model_name: str
    operation_type: str
    item_ids: List[int]
    user_id: Optional[str] = None
    request_id: Optional[str] = None
    additional_data: Optional[Dict[str, Any]] = None


class CopyErrorDetail(BaseModel):
    """复制错误详情模型"""
    code: CopyErrorCode = Field(..., description="错误码")
    message: str = Field(..., description="错误消息")
    user_message: str = Field(..., description="用户友好消息")
    technical_message: Optional[str] = Field(None, description="技术细节消息")
    context: Optional[Dict[str, Any]] = Field(None, description="错误上下文")
    recovery_suggestions: List[str] = Field(default_factory=list, description="恢复建议")
    retry_able: bool = Field(default=False, description="是否可重试")


class CopyErrorHandler:
    """复制功能错误处理器"""
    
    def __init__(self):
        self.logger = self._setup_logger()
        self._error_mappings = self._initialize_error_mappings()
    
    def _setup_logger(self) -> logging.Logger:
        """设置结构化日志记录器"""
        logger = logging.getLogger("copy_error_handler")
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            logger.setLevel(logging.INFO)
        return logger
    
    def _initialize_error_mappings(self) -> Dict[type, CopyErrorDetail]:
        """初始化异常到错误详情的映射"""
        return {
            ValueError: CopyErrorDetail(
                code=CopyErrorCode.INVALID_PARAMETERS,
                message="参数验证失败",
                user_message="输入的数据格式不正确，请检查后重试",
                technical_message=None,
                recovery_suggestions=["检查输入参数格式", "确认必填字段已填写"],
                retry_able=False
            ),
            
            IntegrityError: CopyErrorDetail(
                code=CopyErrorCode.INTEGRITY_CONSTRAINT_VIOLATION,
                message="数据库完整性约束违反",
                user_message="数据完整性检查失败，可能是数据重复或关联关系不正确",
                technical_message=None,
                recovery_suggestions=[
                    "检查唯一字段是否有重复值",
                    "确认关联记录是否存在",
                    "验证外键关系是否正确"
                ],
                retry_able=True
            ),
            
            OperationalError: CopyErrorDetail(
                code=CopyErrorCode.DATABASE_CONNECTION_ERROR,
                message="数据库操作错误",
                user_message="数据库暂时无法访问，请稍后重试",
                technical_message=None,
                recovery_suggestions=[
                    "检查数据库连接状态",
                    "确认数据库服务正在运行",
                    "稍后重试操作"
                ],
                retry_able=True
            ),
            
            DatabaseError: CopyErrorDetail(
                code=CopyErrorCode.DATABASE_OPERATION_ERROR,
                message="数据库操作失败",
                user_message="数据库操作出现问题，请稍后重试",
                technical_message=None,
                recovery_suggestions=[
                    "检查数据库状态",
                    "联系系统管理员",
                    "稍后重试操作"
                ],
                retry_able=True
            ),
            
            PermissionError: CopyErrorDetail(
                code=CopyErrorCode.ACCESS_DENIED,
                message="访问被拒绝",
                user_message="您没有权限执行此操作",
                technical_message=None,
                recovery_suggestions=[
                    "确认您有相应的操作权限",
                    "联系管理员申请权限",
                    "使用有权限的账户操作"
                ],
                retry_able=False
            )
        }
    
    def handle_exception(
        self, 
        exception: Exception, 
        context: CopyErrorContext,
        include_traceback: bool = False
    ) -> BaseApiOut:
        """处理异常并返回统一的API响应"""
        
        # 获取错误详情
        error_detail = self._get_error_detail(exception)
        
        # 添加上下文信息
        error_detail.context = {
            "model_name": context.model_name,
            "operation_type": context.operation_type,
            "item_ids": context.item_ids,
            "user_id": context.user_id,
            "request_id": context.request_id,
            "timestamp": datetime.now().isoformat(),
            **(context.additional_data or {})
        }
        
        # 添加技术细节
        if include_traceback or self.logger.isEnabledFor(logging.DEBUG):
            error_detail.technical_message = str(exception)
        
        # 记录结构化日志
        self._log_error(error_detail, exception, include_traceback)
        
        # 构建响应数据
        response_data = {
            "error_code": error_detail.code,
            "error_message": error_detail.message,
            "user_message": error_detail.user_message,
            "retry_able": error_detail.retry_able,
            "recovery_suggestions": error_detail.recovery_suggestions,
            "context": error_detail.context
        }
        
        if error_detail.technical_message and self.logger.isEnabledFor(logging.DEBUG):
            response_data["technical_message"] = error_detail.technical_message
        
        # 确定HTTP状态码
        status_code = self._determine_status_code(error_detail.code)
        
        return BaseApiOut(
            status=status_code,
            msg=error_detail.user_message,
            data=response_data
        )
    
    def _get_error_detail(self, exception: Exception) -> CopyErrorDetail:
        """根据异常类型获取错误详情"""
        exception_type = type(exception)
        
        # 直接匹配
        if exception_type in self._error_mappings:
            return self._error_mappings[exception_type]
        
        # 检查继承关系
        for mapped_type, error_detail in self._error_mappings.items():
            if isinstance(exception, mapped_type):
                return error_detail
        
        # 特殊处理一些常见错误
        error_message = str(exception).lower()
        
        if "unique constraint" in error_message or "duplicate" in error_message:
            return CopyErrorDetail(
                code=CopyErrorCode.UNIQUE_CONSTRAINT_VIOLATION,
                message="唯一约束违反",
                user_message="数据重复，该值已存在",
                technical_message=str(exception),
                recovery_suggestions=["修改为唯一值", "检查是否有重复数据"],
                retry_able=False
            )
        
        if "foreign key constraint" in error_message:
            return CopyErrorDetail(
                code=CopyErrorCode.FOREIGN_KEY_CONSTRAINT_VIOLATION,
                message="外键约束违反",
                user_message="关联数据不存在或已被删除",
                technical_message=str(exception),
                recovery_suggestions=["确认关联记录存在", "检查外键关系"],
                retry_able=False
            )
        
        # 默认未知错误
        return CopyErrorDetail(
            code=CopyErrorCode.UNKNOWN_ERROR,
            message="未知错误",
            user_message="操作失败，请稍后重试或联系管理员",
            technical_message=str(exception),
            recovery_suggestions=["稍后重试", "联系系统管理员"],
            retry_able=True
        )
    
    def _determine_status_code(self, error_code: CopyErrorCode) -> int:
        """根据错误码确定HTTP状态码"""
        if error_code in [
            CopyErrorCode.RECORD_NOT_FOUND,
            CopyErrorCode.RESOURCE_ACCESS_DENIED
        ]:
            return 404
        
        if error_code in [
            CopyErrorCode.ACCESS_DENIED,
            CopyErrorCode.INSUFFICIENT_PERMISSIONS
        ]:
            return 403
        
        if error_code in [
            CopyErrorCode.INVALID_PARAMETERS,
            CopyErrorCode.DATA_VALIDATION_FAILED,
            CopyErrorCode.INTEGRITY_CONSTRAINT_VIOLATION,
            CopyErrorCode.UNIQUE_CONSTRAINT_VIOLATION,
            CopyErrorCode.FOREIGN_KEY_CONSTRAINT_VIOLATION,
            CopyErrorCode.CANNOT_COPY_DELETED_RECORD,
            CopyErrorCode.COPY_LIMIT_EXCEEDED,
            CopyErrorCode.RELATIONSHIP_COPY_FAILED,
            CopyErrorCode.CODE_GENERATION_FAILED
        ]:
            return 400
        
        if error_code in [
            CopyErrorCode.OPERATION_TIMEOUT,
            CopyErrorCode.RATE_LIMIT_EXCEEDED
        ]:
            return 408
        
        # 系统错误返回500
        return 500
    
    def _log_error(
        self, 
        error_detail: CopyErrorDetail, 
        exception: Exception, 
        include_traceback: bool
    ):
        """记录结构化错误日志"""
        log_data = {
            "error_code": error_detail.code,
            "error_message": error_detail.message,
            "user_message": error_detail.user_message,
            "context": error_detail.context,
            "retry_able": error_detail.retry_able
        }
        
        if include_traceback:
            log_data["traceback"] = traceback.format_exc()
        
        # 根据错误级别记录日志
        if error_detail.code in [
            CopyErrorCode.DATABASE_CONNECTION_ERROR,
            CopyErrorCode.DATABASE_OPERATION_ERROR,
            CopyErrorCode.ADAPTER_NOT_AVAILABLE
        ]:
            self.logger.error(f"系统错误: {log_data}")
        elif error_detail.code in [
            CopyErrorCode.ACCESS_DENIED,
            CopyErrorCode.INSUFFICIENT_PERMISSIONS
        ]:
            self.logger.warning(f"权限错误: {log_data}")
        elif error_detail.retry_able:
            self.logger.info(f"可重试错误: {log_data}")
        else:
            self.logger.error(f"业务错误: {log_data}")
    
    def create_partial_failure_response(
        self,
        successful_items: List[Any],
        failed_items: List[Dict[str, Any]],
        context: CopyErrorContext
    ) -> BaseApiOut:
        """创建部分失败的响应"""
        response_data = {
            "total_attempted": len(successful_items) + len(failed_items),
            "successful_count": len(successful_items),
            "failed_count": len(failed_items),
            "successful_items": [
                {"id": item.id, "name": getattr(item, 'name', f"Item_{item.id}")}
                for item in successful_items
            ],
            "failed_items": failed_items,
            "partial_failure": True,
            "suggestions": [
                "检查失败项目的具体错误信息",
                "对失败的单独重试",
                "联系管理员处理系统级错误"
            ]
        }
        
        return BaseApiOut(
            status=207,  # Multi-Status for partial success
            msg=f"部分完成：成功{len(successful_items)}个，失败{len(failed_items)}个",
            data=response_data
        )


# 全局错误处理器实例
copy_error_handler = CopyErrorHandler()


def handle_copy_exception(
    exception: Exception,
    model_name: str,
    operation_type: str,
    item_ids: List[int],
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
    include_traceback: bool = False
) -> BaseApiOut:
    """便捷函数：处理复制功能异常"""
    context = CopyErrorContext(
        model_name=model_name,
        operation_type=operation_type,
        item_ids=item_ids,
        user_id=user_id,
        request_id=request_id
    )
    
    return copy_error_handler.handle_exception(exception, context, include_traceback)