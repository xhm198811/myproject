from datetime import datetime, timezone
import logging
from fastapi import APIRouter, HTTPException, Depends, Request
from sqlmodel.ext.asyncio.session import AsyncSession
from typing import Dict, Any, List
from sqlmodel import select

from ...core.db import get_async_db
from ...utils.copy_utils import copy_record, copy_records_batch
from ...contracts.models.contract import Contract
from ...users.models.user import User
from ...projects.models.project import Project

# 配置路由日志
router_logger = logging.getLogger("copy_router")

# 创建复制功能路由器
copy_router = APIRouter()

# -------------------- 合同相关复制功能 --------------------

@copy_router.post("/admin/ContractAdmin/quick_copy/{item_id}")
async def contract_quick_copy(
    item_id: str,
    session: AsyncSession = Depends(get_async_db)
):
    """
    合同快速复制 - Amis Admin界面调用的端点
    """
    router_logger.info(f"开始合同快速复制，ID: {item_id}")
    try:
        # 先检查记录是否存在
        router_logger.debug(f"检查合同记录是否存在，ID: {item_id}")
        result = await session.execute(select(Contract).where(Contract.id == int(item_id)))
        existing_contract = result.scalar_one_or_none()
        
        if not existing_contract:
            router_logger.warning(f"合同记录不存在，ID: {item_id}")
            raise HTTPException(status_code=404, detail=f"合同记录不存在，ID: {item_id}")
        
        router_logger.debug(f"找到合同记录，ID: {item_id}，名称: {existing_contract.name}")
        
        # 合同复制的转换函数（处理合同编号和状态）
        def contract_transform(record_dict: Dict[str, Any]) -> Dict[str, Any]:
            # 添加安全检查，确保字段存在
            contract_no = record_dict.get('contract_no', 'contract')
            contract_name = record_dict.get('name', '合同')
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            
            transformed_dict = {
                **record_dict,
                "contract_no": f"{contract_no}_副本_{timestamp}",  # 使用时间戳确保合同编号唯一
                "name": f"{contract_name}_副本_{timestamp}",  # 使用时间戳确保合同名称唯一
                "status": "draft",  # 使用正确的字段名 status
                "create_time": datetime.now(),  # 使用正确的字段名 create_time
                "update_time": datetime.now(),  # 使用正确的字段名 update_time
            }
            router_logger.debug(f"合同转换后字段: {transformed_dict}")
            return transformed_dict

        # 使用通用复制函数
        new_contract = await copy_record(
            session=session,
            model=Contract,
            item_id=int(item_id),
            transform=contract_transform
        )

        router_logger.info(f"合同快速复制成功，新合同ID: {new_contract.id}")
        return {"status": 200, "msg": "合同复制成功", "data": {"new_id": str(new_contract.id)}}

    except HTTPException as e:
        router_logger.error(f"合同快速复制HTTP异常: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        router_logger.error(f"合同快速复制失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"合同快速复制失败: {str(e)}")


# -------------------- 项目相关复制功能 --------------------

@copy_router.post("/admin/ProjectAdmin/quick_copy/{item_id}")
async def project_quick_copy(
    item_id: str,
    session: AsyncSession = Depends(get_async_db)
):
    """
    项目快速复制 - Amis Admin界面调用的端点
    """
    router_logger.info(f"开始项目快速复制，ID: {item_id}")
    try:
        router_logger.debug(f"检查项目记录是否存在，ID: {item_id}")
        result = await session.execute(select(Project).where(Project.id == int(item_id)))
        existing_project = result.scalar_one_or_none()
        
        if not existing_project:
            router_logger.warning(f"项目记录不存在，ID: {item_id}")
            raise HTTPException(status_code=404, detail=f"项目记录不存在，ID: {item_id}")
        
        router_logger.debug(f"找到项目记录，ID: {item_id}，名称: {existing_project.name}")
        
        def project_transform(record_dict: Dict[str, Any]) -> Dict[str, Any]:
            project_name = record_dict.get('name', '项目')
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            
            transformed_dict = {
                **record_dict,
                "name": f"{project_name}_副本_{timestamp}",
                "status": "planning",
                "create_time": datetime.now(),
                "update_time": datetime.now(),
            }
            router_logger.debug(f"项目转换后字段: {transformed_dict}")
            return transformed_dict

        new_project = await copy_record(
            session=session,
            model=Project,
            item_id=int(item_id),
            transform=project_transform
        )

        router_logger.info(f"项目快速复制成功，新项目ID: {new_project.id}")
        return {"status": 200, "msg": "项目复制成功", "data": {"new_id": str(new_project.id)}}

    except HTTPException as e:
        router_logger.error(f"项目快速复制HTTP异常: {e.status_code} - {e.detail}")
        raise
    except Exception as e:
        router_logger.error(f"项目快速复制失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"项目快速复制失败: {str(e)}")


@copy_router.post("/admin/ContractAdmin/copy_create")
async def contract_copy_create(
    request: Request,
    session: AsyncSession = Depends(get_async_db)
):
    """
    合同批量复制 - Amis Admin界面调用的端点
    """
    router_logger.info("开始合同批量复制")
    try:
        json_data = await request.json()
        item_ids = json_data.get("ids", [])
        copy_count = int(json_data.get("copy_count", 1))
        
        router_logger.debug(f"批量复制参数: 记录IDs={item_ids}, 复制数量={copy_count}")

        # 合同批量复制的转换函数（支持批量索引）
        def contract_batch_transform(record_dict: Dict[str, Any], index: int) -> Dict[str, Any]:
            # 使用时间戳确保合同编号唯一
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            transformed_dict = {
                **record_dict,
                "contract_no": f"{record_dict.get('contract_no', 'contract')}_副本_{timestamp}_{index+1}",
                "name": f"{record_dict.get('name', '合同')}_副本_{timestamp}_{index+1}",
                "status": "draft",  # 新合同默认草稿状态
                "create_time": datetime.now(),  # 更新创建时间
                "update_time": datetime.now(),  # 更新更新时间
            }
            router_logger.debug(f"合同批量转换后字段，索引{index}: {transformed_dict}")
            return transformed_dict

        # 使用通用批量复制函数
        new_records = await copy_records_batch(
            session=session,
            model=Contract,
            item_ids=[int(id) for id in item_ids],
            transform=contract_batch_transform,
            copy_count=copy_count
        )

        new_ids = [str(record.id) for record in new_records]
        router_logger.info(f"合同批量复制成功，共创建{len(new_ids)}条记录")
        return {"status": 200, "msg": f"成功复制 {len(new_ids)} 条记录", "data": {"new_ids": new_ids}}

    except Exception as e:
        router_logger.error(f"合同批量复制失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"合同批量复制失败: {str(e)}")


# -------------------- 用户相关复制功能 --------------------

@copy_router.post("/admin/UserAdmin/quick_copy/{item_id}")
async def user_quick_copy(
    item_id: str,
    session: AsyncSession = Depends(get_async_db)
):
    """
    用户快速复制 - Amis Admin界面调用的端点
    """
    router_logger.info(f"开始用户快速复制，ID: {item_id}")
    try:
        # 处理日期时间字段的辅助函数
        def convert_datetime(dt):
            """
            将可能有时区的datetime对象转换为无时区对象
            """
            if dt is None:
                return None
            # 检查是否已经是无时区对象
            if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                return dt
            # 转换为UTC并移除时区信息
            return dt.astimezone(timezone.utc).replace(tzinfo=None)

        # 用户复制的转换函数
        def user_transform(record_dict: Dict[str, Any]) -> Dict[str, Any]:
            # 添加时间戳确保用户名唯一
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            # 先复制基础字段
            transformed_dict = {
                **record_dict,
                "username": f"{record_dict.get('username', 'user')}_副本_{timestamp}",
                "email": f"copy_{timestamp}_{record_dict.get('email', 'user@example.com')}",
                "last_login": None,  # 新用户没有登录记录
            }

            # 处理所有日期时间字段 - 转换为无时区信息
            datetime_fields = ['date_joined', 'created_at', 'updated_at']
            for field in datetime_fields:
                if field in transformed_dict:
                    transformed_dict[field] = convert_datetime(transformed_dict[field])

            # 处理IP地址字段
            if 'last_login_ip' in transformed_dict:
                transformed_dict['last_login_ip'] = None  # 新用户没有登录IP

            router_logger.debug(f"用户转换后字段: {transformed_dict}")
            return transformed_dict

        # 使用通用复制函数
        new_user = await copy_record(
            session=session,
            model=User,
            item_id=int(item_id),
            transform=user_transform
        )

        router_logger.info(f"用户快速复制成功，新用户ID: {new_user.id}")
        return {"status": 200, "msg": "用户复制成功", "data": {"new_id": str(new_user.id)}}

    except Exception as e:
        router_logger.error(f"用户快速复制失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"用户快速复制失败: {str(e)}")


# -------------------- 通用API接口（供外部调用） --------------------

# 合同快速复制接口
@copy_router.post("/contracts/fast-copy/{contract_id}")
async def copy_contract_fast(
    contract_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    通用合同快速复制接口 - 供外部系统调用
    """
    router_logger.info(f"开始通用合同快速复制，ID: {contract_id}")
    try:
        # 复用合同快速复制的转换函数
        def contract_transform(record_dict: Dict[str, Any]) -> Dict[str, Any]:
            # 添加时间戳确保合同编号唯一
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            transformed_dict = {
                **record_dict,
                "contract_no": f"{record_dict.get('contract_no', 'contract')}_副本_{timestamp}",
                "name": f"{record_dict.get('name', '合同')}_副本_{timestamp}",
                "status": "draft",  # 新合同默认草稿状态
                "create_time": datetime.now(),  # 更新创建时间
                "update_time": datetime.now(),  # 更新更新时间
            }
            return transformed_dict

        # 使用通用复制函数
        new_contract = await copy_record(db, Contract, contract_id, contract_transform)
        router_logger.info(f"通用合同快速复制完成，新合同ID: {new_contract.id}")
        return {"status": "success", "data": new_contract}
    except Exception as e:
        router_logger.error(f"通用合同快速复制失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"复制失败: {str(e)}")


# 用户快速复制接口
@copy_router.post("/users/fast-copy/{user_id}")
async def copy_user_fast(
    user_id: int,
    db: AsyncSession = Depends(get_async_db)
):
    """
    通用用户快速复制接口 - 供外部系统调用
    """
    router_logger.info(f"开始通用用户快速复制，ID: {user_id}")
    try:
        # 复用用户快速复制的转换函数
        def convert_datetime(dt):
            if dt is None:
                return None
            if not hasattr(dt, 'tzinfo') or dt.tzinfo is None:
                return dt
            return dt.astimezone(timezone.utc).replace(tzinfo=None)

        def user_transform(record_dict: Dict[str, Any]) -> Dict[str, Any]:
            # 添加时间戳确保用户名唯一
            timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
            transformed_dict = {
                **record_dict,
                "username": f"{record_dict.get('username', 'user')}_副本_{timestamp}",
                "email": f"copy_{timestamp}_{record_dict.get('email', 'user@example.com')}",
                "last_login": None,
            }

            datetime_fields = ['date_joined', 'created_at', 'updated_at']
            for field in datetime_fields:
                if field in transformed_dict:
                    transformed_dict[field] = convert_datetime(transformed_dict[field])

            if 'last_login_ip' in transformed_dict:
                transformed_dict['last_login_ip'] = None

            return transformed_dict

        # 使用通用复制函数
        new_user = await copy_record(db, User, user_id, user_transform)
        router_logger.info(f"通用用户快速复制完成，新用户ID: {new_user.id}")
        return {"status": "success", "data": new_user}
    except Exception as e:
        router_logger.error(f"通用用户快速复制失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"复制失败: {str(e)}")
