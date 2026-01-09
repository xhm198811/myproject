from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
import logging
from ...core.db import get_async_db
from ...core.auth import get_current_active_user, get_current_superuser
from ..services.contract import contract_service
from ..models.contract import Contract, ContractStatusLog, ContractAttachment

# 创建API路由器
router = APIRouter(prefix="/contracts", tags=["contracts"])

from pydantic import BaseModel

# 合同创建请求模型
class ContractCreateRequest(BaseModel):
    contract_no: str
    name: str
    type: str
    signing_date: str
    expiry_date: str
    party_a: str
    party_b: str
    amount: float
    status: str = "draft"
    department: str
    creator: str
    description: str = ""

# 合同更新请求模型
class ContractUpdateRequest(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    signing_date: Optional[str] = None
    expiry_date: Optional[str] = None
    party_a: Optional[str] = None
    party_b: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    operator: str = "system"
    status_remark: str = ""

# 合同状态变更请求模型
class ContractStatusChangeRequest(BaseModel):
    new_status: str
    operator: str
    remark: str

# 合同快速复制请求模型
class ContractQuickCopyRequest(BaseModel):
    new_contract_no: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None

@router.post("/", response_model=Dict[str, Any])
async def create_contract(
    contract_data: ContractCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """创建合同"""
    # 检查合同编号是否已存在
    existing_contract = await contract_service.get_contract_by_no(db, contract_data.contract_no)
    if existing_contract:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="合同编号已存在"
        )
    
    # 创建合同
    contract = await contract_service.create_contract(db, contract_data.dict())
    
    # 提交事务
    await db.commit()
    
    return {
        "status": 0,
        "msg": "合同创建成功",
        "data": contract.dict()
    }

@router.get("/", response_model=Dict[str, Any])
async def get_contracts(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    department: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取合同列表"""
    # 构建过滤条件
    filters = {
        "status": status,
        "department": department
    }
    
    contracts = await contract_service.get_contracts(db, skip=skip, limit=limit, filters=filters)
    contract_count = await contract_service.get_contract_count(db, filters=filters)
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": {
            "items": [contract.dict() for contract in contracts],
            "total": contract_count
        }
    }

@router.get("/{contract_id}", response_model=Dict[str, Any])
async def get_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取指定合同信息"""
    contract = await contract_service.get_contract_by_id(db, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合同不存在"
        )
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": contract.dict()
    }

@router.put("/{contract_id}", response_model=Dict[str, Any])
async def update_contract(
    contract_id: int,
    contract_data: ContractUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """更新合同"""
    # 转换为字典并过滤掉None值
    update_data = contract_data.dict(exclude_unset=True)
    
    contract = await contract_service.update_contract(db, contract_id, update_data)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合同不存在"
        )
    
    return {
        "status": 0,
        "msg": "更新成功",
        "data": contract.dict()
    }

@router.delete("/item/{ids}", response_model=Dict[str, Any])
async def batch_delete_contracts(
    ids: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_superuser)
):
    """批量删除合同（仅超级用户）"""
    try:
        # 解析ID列表
        contract_ids = [int(id_str.strip()) for id_str in ids.split(",")]
        
        # 执行批量删除
        result = await contract_service.batch_delete_contracts(db, contract_ids)
        
        # 构建响应消息
        msg_parts = []
        if result["success_count"] > 0:
            msg_parts.append(f"成功删除 {result['success_count']} 个合同")
        if result["failed_count"] > 0:
            msg_parts.append(f"失败 {result['failed_count']} 个合同（ID: {', '.join(map(str, result['failed_ids']))}）")
        
        return {
            "status": 0,
            "msg": "，".join(msg_parts),
            "data": result
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"ID格式错误: {str(e)}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"批量删除失败: {str(e)}"
        )

@router.delete("/{contract_id}", response_model=Dict[str, Any])
async def delete_contract(
    contract_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_superuser)
):
    """删除合同（仅超级用户）"""
    success = await contract_service.delete_contract(db, contract_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合同不存在"
        )
    
    return {
        "status": 0,
        "msg": "删除成功"
    }

@router.post("/{contract_id}/status", response_model=Dict[str, Any])
async def change_contract_status(
    contract_id: int,
    status_data: ContractStatusChangeRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """变更合同状态"""
    # 获取当前合同
    contract = await contract_service.get_contract_by_id(db, contract_id)
    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="合同不存在"
        )
    
    # 更新合同状态
    update_data = {
        "status": status_data.new_status,
        "operator": status_data.operator,
        "status_remark": status_data.remark
    }
    
    updated_contract = await contract_service.update_contract(db, contract_id, update_data)
    
    return {
        "status": 0,
        "msg": "状态变更成功",
        "data": updated_contract.dict()
    }

@router.get("/{contract_id}/status-logs", response_model=Dict[str, Any])
async def get_contract_status_logs(
    contract_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取合同状态变更记录"""
    logs = await contract_service.get_contract_status_logs(db, contract_id)
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": {
            "items": [log.dict() for log in logs],
            "total": len(logs)
        }
    }

@router.post("/{contract_id}/quick_copy", response_model=Dict[str, Any])
async def quick_copy_contract(
    contract_id: int,
    copy_request: ContractQuickCopyRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """快速复制合同"""
    try:
        new_contract = await contract_service.quick_copy_contract(
            db=db,
            contract_id=contract_id,
            new_contract_no=copy_request.new_contract_no,
            custom_data=copy_request.custom_data
        )
        
        return {
            "status": 0,
            "msg": "合同复制成功",
            "data": new_contract
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except HTTPException as e:
        raise e
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"复制合同失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"复制合同失败: {str(e)}"
        )


# ======================
# 合同分析API端点
# ======================

@router.get("/analysis/total", response_model=Dict[str, Any])
async def get_total_contracts(
    db: AsyncSession = Depends(get_async_db)
):
    """获取合同总数"""
    try:
        result = await db.execute(select(func.count(Contract.id)))
        total = result.scalar_one()
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "value": total,
                "className": "text-primary"
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取合同总数失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/active", response_model=Dict[str, Any])
async def get_active_contracts(
    db: AsyncSession = Depends(get_async_db)
):
    """获取生效合同数"""
    try:
        result = await db.execute(
            select(func.count(Contract.id)).where(Contract.status == "已生效")
        )
        active = result.scalar_one()
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "value": active,
                "className": "text-success"
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取生效合同数失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/total_amount", response_model=Dict[str, Any])
async def get_total_amount(
    db: AsyncSession = Depends(get_async_db)
):
    """获取合同总金额"""
    try:
        result = await db.execute(select(func.sum(Contract.amount)))
        total_amount = result.scalar() or 0
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "value": f"¥{total_amount:,.2f}",
                "className": "text-warning"
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取合同总金额失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/avg_amount", response_model=Dict[str, Any])
async def get_avg_amount(
    db: AsyncSession = Depends(get_async_db)
):
    """获取平均合同金额"""
    try:
        result = await db.execute(select(func.avg(Contract.amount)))
        avg_amount = result.scalar() or 0
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "value": f"¥{avg_amount:,.2f}",
                "className": "text-info"
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取平均合同金额失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/status_distribution", response_model=Dict[str, Any])
async def get_status_distribution(
    db: AsyncSession = Depends(get_async_db)
):
    """获取合同状态分布"""
    try:
        result = await db.execute(
            select(Contract.status, func.count(Contract.id)).group_by(Contract.status)
        )
        data = result.all()
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "type": "pie",
                "data": [
                    {
                        "name": status,
                        "value": count
                    }
                    for status, count in data
                ]
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取合同状态分布失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/type_distribution", response_model=Dict[str, Any])
async def get_type_distribution(
    db: AsyncSession = Depends(get_async_db)
):
    """获取合同类型分布"""
    try:
        result = await db.execute(
            select(Contract.type, func.count(Contract.id)).group_by(Contract.type)
        )
        data = result.all()
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "type": "bar",
                "data": [
                    {
                        "type": "类型",
                        "value": count
                    }
                    for type_name, count in data
                ]
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取合同类型分布失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/monthly_trend", response_model=Dict[str, Any])
async def get_monthly_trend(
    db: AsyncSession = Depends(get_async_db)
):
    """获取月度合同趋势"""
    try:
        from sqlalchemy import text
        
        expiring_date = datetime.now() - timedelta(days=365)
        result = await db.execute(
            select(Contract)
            .where(Contract.create_time >= expiring_date)
            .order_by(Contract.create_time)
        )
        contracts = result.scalars().all()
        
        monthly_data = {}
        for contract in contracts:
            month_key = contract.create_time.strftime('%Y-%m')
            if month_key not in monthly_data:
                monthly_data[month_key] = {"count": 0, "amount": 0}
            monthly_data[month_key]["count"] += 1
            monthly_data[month_key]["amount"] += contract.amount or 0
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "type": "line",
                "data": {
                    "columns": ["月份", "合同数量", "合同金额"],
                    "rows": [
                        [month, data["count"], data["amount"]]
                        for month, data in sorted(monthly_data.items())
                    ]
                }
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取月度合同趋势失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/department_distribution", response_model=Dict[str, Any])
async def get_department_distribution(
    db: AsyncSession = Depends(get_async_db)
):
    """获取部门合同分布"""
    try:
        result = await db.execute(
            select(Contract.department, func.count(Contract.id)).group_by(Contract.department)
        )
        data = result.all()
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "type": "radar",
                "data": {
                    "columns": ["部门", "合同数量"],
                    "rows": [
                        [dept, count]
                        for dept, count in data
                    ]
                }
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取部门合同分布失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/expiring_contracts", response_model=Dict[str, Any])
async def get_expiring_contracts(
    db: AsyncSession = Depends(get_async_db)
):
    """获取即将到期的合同"""
    try:
        expiring_date = datetime.now().date() + timedelta(days=30)
        result = await db.execute(
            select(Contract)
            .where(
                and_(
                    Contract.expiry_date <= expiring_date,
                    Contract.expiry_date >= datetime.now().date(),
                    Contract.status == "已生效"
                )
            )
            .order_by(Contract.expiry_date)
            .limit(10)
        )
        contracts = result.scalars().all()
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "items": [
                    {
                        "id": contract.id,
                        "contract_no": contract.contract_no,
                        "name": contract.name,
                        "expiry_date": contract.expiry_date.isoformat() if contract.expiry_date else None,
                        "party_b": contract.party_b,
                        "amount": contract.amount
                    }
                    for contract in contracts
                ],
                "total": len(contracts)
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取即将到期合同失败: {str(e)}",
            "data": None
        }

@router.get("/analysis/recent_contracts", response_model=Dict[str, Any])
async def get_recent_contracts(
    db: AsyncSession = Depends(get_async_db)
):
    """获取最近创建的合同"""
    try:
        result = await db.execute(
            select(Contract)
            .order_by(Contract.create_time.desc())
            .limit(10)
        )
        contracts = result.scalars().all()
        
        return {
            "status": 0,
            "msg": "success",
            "data": {
                "items": [
                    {
                        "id": contract.id,
                        "contract_no": contract.contract_no,
                        "name": contract.name,
                        "create_time": contract.create_time.isoformat() if contract.create_time else None,
                        "status": contract.status,
                        "amount": contract.amount
                    }
                    for contract in contracts
                ],
                "total": len(contracts)
            }
        }
    except Exception as e:
        return {
            "status": 500,
            "msg": f"获取最近创建合同失败: {str(e)}",
            "data": None
        }




