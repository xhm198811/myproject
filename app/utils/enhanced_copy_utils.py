"""
增强版复制工具函数
集成统一错误处理、智能重试和性能优化
"""
import asyncio
import time
from typing import Type, Dict, Callable, Any, List, Optional, Tuple
from functools import wraps
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError, SQLAlchemyError, OperationalError
from sqlmodel import SQLModel
from fastapi import HTTPException
from fastapi_amis_admin.crud.schema import BaseApiOut

from .copy_error_handler import (
    handle_copy_exception, 
    CopyErrorCode, 
    CopyErrorContext,
    copy_error_handler
)


class RetryConfig:
    """重试配置"""
    def __init__(
        self,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 30.0,
        backoff_factor: float = 2.0,
        retryable_exceptions: Tuple = (OperationalError, IntegrityError)
    ):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.backoff_factor = backoff_factor
        self.retryable_exceptions = retryable_exceptions


def with_retry(config: RetryConfig = None):
    """重试装饰器"""
    if config is None:
        config = RetryConfig()
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            
            for attempt in range(config.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    
                    if attempt == config.max_attempts - 1:
                        # 最后一次尝试失败，抛出异常
                        break
                    
                    # 计算延迟时间
                    delay = min(
                        config.base_delay * (config.backoff_factor ** attempt),
                        config.max_delay
                    )
                    
                    # 记录重试日志
                    copy_error_handler.logger.warning(
                        f"第{attempt + 1}次尝试失败，{delay}秒后重试: {str(e)}"
                    )
                    
                    await asyncio.sleep(delay)
                except Exception as e:
                    # 非重试异常直接抛出
                    raise e
            
            # 所有重试都失败了
            raise last_exception
        
        return wrapper
    return decorator


class CopyOperationResult:
    """复制操作结果"""
    def __init__(self):
        self.successful_items: List[SQLModel] = []
        self.failed_items: List[Dict[str, Any]] = []
        self.partial_failure: bool = False
    
    def add_success(self, item: SQLModel):
        """添加成功项"""
        self.successful_items.append(item)
    
    def add_failure(self, item_id: int, error: Exception, context: str):
        """添加失败项"""
        self.failed_items.append({
            "item_id": item_id,
            "error_message": str(error),
            "error_type": type(error).__name__,
            "context": context
        })
        self.partial_failure = True
    
    def is_complete_success(self) -> bool:
        """是否完全成功"""
        return len(self.failed_items) == 0 and len(self.successful_items) > 0
    
    def is_complete_failure(self) -> bool:
        """是否完全失败"""
        return len(self.successful_items) == 0 and len(self.failed_items) > 0


async def enhanced_copy_record(
    session,
    model: Type[SQLModel],
    item_id: int,
    transform: Callable[[Dict[str, Any]], Dict[str, Any]],
    context: CopyErrorContext,
    retry_config: RetryConfig = None
) -> Tuple[Optional[SQLModel], Optional[Exception]]:
    """
    增强版单条记录复制
    
    Returns:
        Tuple[新记录, 异常] - 成功时异常为None，失败时记录为None
    """
    if retry_config is None:
        retry_config = RetryConfig()
    
    @with_retry(retry_config)
    async def _do_copy():
        try:
            # 查询原记录
            copy_error_handler.logger.debug(f"开始复制{model.__name__}记录，ID: {item_id}")
            result = await session.execute(select(model).where(model.id == item_id))
            record = result.scalar_one_or_none()
            
            if not record:
                raise HTTPException(
                    status_code=404, 
                    detail=f"{model.__name__}记录不存在"
                )
            
            # 复制并转换字段
            record_dict = record.dict(exclude={"id"})
            transformed_dict = transform(record_dict)
            
            # 创建新记录
            new_record = model(**transformed_dict)
            session.add(new_record)
            await session.flush()
            await session.refresh(new_record)
            
            copy_error_handler.logger.info(
                f"成功复制{model.__name__}记录：{item_id} -> {new_record.id}"
            )
            
            return new_record
            
        except IntegrityError as e:
            # 特殊处理完整性错误
            if "duplicate" in str(e).lower() or "unique" in str(e).lower():
                # 尝试生成唯一值
                try:
                    record_dict = record.dict(exclude={"id"})
                    # 调用转换函数重新生成
                    transformed_dict = transform(record_dict)
                    new_record = model(**transformed_dict)
                    session.add(new_record)
                    await session.flush()
                    await session.refresh(new_record)
                    return new_record
                except:
                    # 如果还是失败，抛出原始异常
                    raise e
            else:
                raise e
    
    try:
        new_record = await _do_copy()
        return new_record, None
    except Exception as e:
        copy_error_handler.logger.error(
            f"复制{model.__name__}记录失败，ID: {item_id}, 错误: {str(e)}",
            exc_info=True
        )
        return None, e


async def enhanced_copy_records_batch(
    session,
    model: Type[SQLModel],
    item_ids: List[int],
    transform: Callable[[Dict[str, Any], int], Dict[str, Any]],
    context: CopyErrorContext,
    copy_count: int = 1,
    continue_on_error: bool = True,
    max_concurrent: int = 5
) -> BaseApiOut:
    """
    增强版批量记录复制
    
    Args:
        session: 数据库会话
        model: 数据模型类
        item_ids: 要复制的记录ID列表
        transform: 字段转换函数
        context: 错误上下文
        copy_count: 每条记录的复制数量
        continue_on_error: 遇到错误时是否继续处理其他记录
        max_concurrent: 最大并发数
        
    Returns:
        BaseApiOut: 包含成功和失败统计的响应
    """
    if not item_ids:
        return handle_copy_exception(
            ValueError("没有提供要复制的记录ID"),
            model.__name__,
            "batch_copy",
            [],
            user_id=context.user_id,
            request_id=context.request_id
        )
    
    copy_error_handler.logger.info(
        f"开始批量复制{model.__name__}，IDs: {item_ids}，每条复制{copy_count}份"
    )
    
    result = CopyOperationResult()
    
    # 控制并发数
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def copy_single_record_with_context(item_id: int, copy_index: int):
        async with semaphore:
            # 为每个复制操作创建独立的转换函数
            def transform_with_index(record_dict: Dict[str, Any]) -> Dict[str, Any]:
                return transform(record_dict, copy_index)
            
            new_item, error = await enhanced_copy_record(
                session, model, item_id, transform_with_index, context
            )
            
            if new_item:
                result.add_success(new_item)
            else:
                result.add_failure(
                    item_id, 
                    error, 
                    f"第{copy_index + 1}个副本"
                )
    
    # 创建所有复制任务
    tasks = []
    for item_id in item_ids:
        for copy_index in range(copy_count):
            task = copy_single_record_with_context(item_id, copy_index)
            if continue_on_error:
                # 继续执行模式，不传播异常
                task = asyncio.create_task(task)
            else:
                # 快速失败模式
                task = asyncio.create_task(task)
            
            tasks.append(task)
    
    # 执行所有任务
    try:
        await asyncio.gather(*tasks, return_exceptions=continue_on_error)
    except Exception as e:
        if not continue_on_error:
            return handle_copy_exception(
                e,
                model.__name__,
                "batch_copy",
                item_ids,
                user_id=context.user_id,
                request_id=context.request_id
            )
    
    # 提交成功的操作
    if result.successful_items:
        try:
            await session.commit()
            copy_error_handler.logger.info(
                f"批量复制完成，成功{len(result.successful_items)}条，失败{len(result.failed_items)}条"
            )
        except Exception as e:
            return handle_copy_exception(
                e,
                model.__name__,
                "batch_commit",
                [item.id for item in result.successful_items],
                user_id=context.user_id,
                request_id=context.request_id
            )
    else:
        # 全部失败，回滚
        await session.rollback()
    
    # 构建响应
    if result.is_complete_success():
        return BaseApiOut(
            status=200,
            msg=f"成功复制{len(result.successful_items)}条记录",
            data={
                "successful_count": len(result.successful_items),
                "failed_count": 0,
                "items": [
                    {"id": item.id, "name": getattr(item, 'name', f"副本_{item.id}")}
                    for item in result.successful_items
                ]
            }
        )
    elif result.is_complete_failure():
        # 全部失败，返回第一个错误
        first_failure = result.failed_items[0]
        return BaseApiOut(
            status=400,
            msg="所有复制操作都失败了",
            data={
                "error_details": result.failed_items,
                "total_attempted": len(result.failed_items)
            }
        )
    else:
        # 部分失败
        return copy_error_handler.create_partial_failure_response(
            result.successful_items,
            result.failed_items,
            context
        )


async def copy_with_validation(
    session,
    model: Type[SQLModel],
    item_id: int,
    transform: Callable[[Dict[str, Any]], Dict[str, Any]],
    context: CopyErrorContext,
    validate_before_copy: bool = True
) -> BaseApiOut:
    """
    带验证的复制操作
    
    Args:
        validate_before_copy: 是否在复制前验证数据
    """
    try:
        # 预验证
        if validate_before_copy:
            result = await session.execute(select(model).where(model.id == item_id))
            record = result.scalar_one_or_none()
            
            if not record:
                return handle_copy_exception(
                    HTTPException(status_code=404, detail=f"{model.__name__}记录不存在"),
                    model.__name__,
                    "copy_with_validation",
                    [item_id],
                    user_id=context.user_id,
                    request_id=context.request_id
                )
            
            # 基本业务规则验证
            validation_result = await validate_copy_rules(record, model, session)
            if not validation_result.is_valid:
                return BaseApiOut(
                    status=400,
                    msg="复制前验证失败",
                    data={
                        "validation_errors": validation_result.errors,
                        "suggestions": validation_result.suggestions
                    }
                )
        
        # 执行复制
        new_record, error = await enhanced_copy_record(
            session, model, item_id, transform, context
        )
        
        if error:
            return handle_copy_exception(
                error,
                model.__name__,
                "copy_with_validation",
                [item_id],
                user_id=context.user_id,
                request_id=context.request_id
            )
        
        await session.commit()
        
        return BaseApiOut(
            status=200,
            msg="复制成功",
            data={
                "new_record_id": new_record.id,
                "validation_passed": validate_before_copy
            }
        )
        
    except Exception as e:
        await session.rollback()
        return handle_copy_exception(
            e,
            model.__name__,
            "copy_with_validation",
            [item_id],
            user_id=context.user_id,
            request_id=context.request_id
        )


class ValidationResult:
    """验证结果"""
    def __init__(self):
        self.is_valid: bool = True
        self.errors: List[str] = []
        self.suggestions: List[str] = []


async def validate_copy_rules(record: SQLModel, model: Type[SQLModel], session) -> ValidationResult:
    """验证复制业务规则"""
    result = ValidationResult()
    
    # 基本状态检查
    if hasattr(record, 'status'):
        status = getattr(record, 'status', '').lower()
        if status in ['deleted', 'archived', 'cancelled']:
            result.is_valid = False
            result.errors.append(f"不能复制状态为 '{status}' 的记录")
            result.suggestions.append("请选择活跃状态的记录进行复制")
    
    # 模型特定验证
    model_name = model.__name__.lower()
    
    if 'contract' in model_name:
        # 合同特定验证
        if hasattr(record, 'end_date') and record.end_date:
            from datetime import datetime
            if record.end_date < datetime.now().date():
                result.is_valid = False
                result.errors.append("不能复制已过期的合同")
                result.suggestions.append("请选择未过期的合同进行复制")
    
    elif 'user' in model_name:
        # 用户特定验证
        if hasattr(record, 'is_active') and not record.is_active:
            result.is_valid = False
            result.errors.append("不能复制已禁用的用户")
            result.suggestions.append("请选择活跃用户进行复制")
    
    return result