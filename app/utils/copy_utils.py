import logging
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlmodel import SQLModel
from typing import Type, Dict, Callable, Any, List
from fastapi import HTTPException

# 配置日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

async def copy_record(
    session,
    model: Type[SQLModel],
    item_id: int,
    transform: Callable[[Dict[str, Any]], Dict[str, Any]]  # 字段转换函数（处理唯一值等）
):
    """
    通用记录复制工具函数
    
    Args:
        session: 数据库会话
        model: 数据模型类
        item_id: 要复制的记录ID
        transform: 字段转换函数，用于处理唯一值等
        
    Returns:
        新创建的记录
        
    Raises:
        HTTPException: 记录不存在或复制失败
    """
    try:
        # 查询原记录
        logger.debug(f"开始复制{model.__name__}记录，ID: {item_id}")
        result = await session.execute(select(model).where(model.id == item_id))
        record = result.scalar_one_or_none()
        
        if not record:
            logger.warning(f"{model.__name__}记录不存在，ID: {item_id}")
            raise HTTPException(status_code=404, detail=f"{model.__name__}记录不存在")
        
        # 复制并转换字段
        record_dict = record.dict(exclude={"id"})  # 排除主键
        logger.info(f"原记录字段列表: {list(record_dict.keys())}")
        logger.debug(f"原记录字段: {record_dict}")
        
        transformed_dict = transform(record_dict)  # 自定义转换（如修改唯一字段）
        logger.debug(f"转换后字段: {transformed_dict}")
        
        # 创建新记录
        new_record = model(**transformed_dict)
        session.add(new_record)
        
        logger.debug(f"添加新记录到会话: {new_record}")
        await session.flush()  # 提前获取新ID
        logger.debug(f"会话刷新成功，新记录ID: {new_record.id}")
        
        await session.commit()  # 提交事务 - 关键修复！
        logger.debug(f"事务提交成功")
        
        await session.refresh(new_record)  # 获取完整的新记录数据
        logger.debug(f"记录刷新成功，完整新记录: {new_record}")
        
        return new_record
    except HTTPException as e:
        # 直接传递HTTP异常（如404）
        logger.error(f"HTTP异常: {e.status_code} - {e.detail}")
        raise
    except IntegrityError as e:
        await session.rollback()  # 回滚事务
        logger.error(f"数据库约束冲突: {str(e)}")
        raise HTTPException(status_code=400, detail=f"数据库约束冲突: {str(e)}")
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"数据库操作失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {str(e)}")
    except Exception as e:
        logger.error(f"复制记录失败: {str(e)}，模型: {model.__name__}", exc_info=True)  # 添加完整堆栈跟踪和模型信息
        raise HTTPException(status_code=500, detail=f"复制失败: {str(e)}")


async def copy_records_batch(
    session,
    model: Type[SQLModel],
    item_ids: list[int],
    transform: Callable[[Dict[str, Any], int], Dict[str, Any]],  # 字段转换函数（支持批量索引）
    copy_count: int = 1
):
    """
    通用批量记录复制工具函数
    
    Args:
        session: 数据库会话
        model: 数据模型类
        item_ids: 要复制的记录ID列表
        transform: 字段转换函数，用于处理唯一值等，接收(record_dict, index)参数
        copy_count: 每条记录的复制数量
        
    Returns:
        新创建的记录列表
        
    Raises:
        HTTPException: 复制失败
    """
    try:
        if not item_ids:
            logger.warning("批量复制时没有提供记录ID列表")
            raise HTTPException(status_code=400, detail="请选择要复制的记录")
        
        logger.debug(f"开始批量复制{model.__name__}记录，IDs: {item_ids}，复制数量: {copy_count}")
        records_to_insert = []
        
        # 收集所有要插入的记录数据
        for item_id in item_ids:
            # 查询原记录
            result = await session.execute(select(model).where(model.id == int(item_id)))
            record = result.scalar_one_or_none()
            
            if record:
                logger.debug(f"处理原记录ID: {item_id}")
                record_dict = record.dict(exclude={"id"})
                logger.debug(f"原记录字段: {record_dict}")
                
                for i in range(copy_count):
                    # 创建转换后的字典（支持批量索引）
                    transformed_dict = transform(record_dict, i)
                    logger.debug(f"第{i+1}个副本转换后字段: {transformed_dict}")
                    
                    # 添加到待插入列表
                    records_to_insert.append(transformed_dict)
        
        if not records_to_insert:
            logger.warning("没有记录需要复制")
            return []
        
        # 使用批量插入提升性能
        logger.debug(f"准备批量插入{len(records_to_insert)}条记录")
        
        # 执行批量插入
        from sqlalchemy import insert
        result = await session.execute(
            insert(model),
            records_to_insert
        )
        
        logger.debug("批量插入完成")
        await session.commit()  # 提交事务
        
        # 查询新插入的记录
        # 注意：批量插入后，PostgreSQL支持RETURNING子句获取新ID
        new_records = []
        if model.__table__.c.get('id') is not None:
            # 如果有自增ID，查询最新插入的记录
            # 这里简单实现，实际项目中可以使用RETURNING子句获取所有新ID
            last_id_result = await session.execute(
                select(model.id).order_by(model.id.desc()).limit(len(records_to_insert))
            )
            new_ids = [row[0] for row in last_id_result.fetchall()]
            
            # 查询新创建的记录
            if new_ids:
                new_ids = sorted(new_ids)
                logger.debug(f"新插入记录的ID列表: {new_ids}")
                
                result = await session.execute(
                    select(model).where(model.id.in_(new_ids))
                )
                new_records = result.scalars().all()
        
        logger.info(f"批量复制完成，共创建{len(new_records)}条新记录")
        return new_records
    except IntegrityError as e:
        await session.rollback()  # 回滚事务
        logger.error(f"批量复制数据库约束冲突: {str(e)}")
        raise HTTPException(status_code=400, detail=f"数据库约束冲突: {str(e)}")
    except SQLAlchemyError as e:
        await session.rollback()
        logger.error(f"批量复制数据库操作失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"数据库操作失败: {str(e)}")
    except Exception as e:
        logger.error(f"批量复制失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"批量复制失败: {str(e)}")
