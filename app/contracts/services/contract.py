from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from ..models.contract import Contract, ContractStatusLog, ContractAttachment
from datetime import datetime
import logging

class ContractService:
    """合同服务"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def create_contract(self, db: AsyncSession, contract_data: Dict[str, Any]) -> Contract:
        """创建合同"""
        # 创建合同对象
        contract = Contract(**contract_data)
        
        # 保存到数据库（不自动提交，由调用者控制）
        db.add(contract)
        await db.flush()
        await db.refresh(contract)
        
        return contract
    
    async def get_contract_by_id(self, db: AsyncSession, contract_id: int) -> Optional[Contract]:
        """通过ID获取合同"""
        result = await db.execute(
            select(Contract).where(Contract.id == contract_id)
        )
        return result.scalar_one_or_none()
    
    async def get_contract_by_no(self, db: AsyncSession, contract_no: str) -> Optional[Contract]:
        """通过合同编号获取合同"""
        result = await db.execute(
            select(Contract).where(Contract.contract_no == contract_no)
        )
        return result.scalar_one_or_none()
    
    async def get_contracts(self, db: AsyncSession, skip: int = 0, limit: int = 100, filters: Dict[str, Any] = None) -> List[Contract]:
        """获取合同列表"""
        query = select(Contract)
        
        # 应用过滤条件
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(Contract, key):
                    if isinstance(value, (list, tuple)):
                        query = query.where(getattr(Contract, key).in_(value))
                    else:
                        query = query.where(getattr(Contract, key) == value)
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_contract(self, db: AsyncSession, contract_id: int, contract_data: Dict[str, Any]) -> Optional[Contract]:
        """更新合同"""
        # 检查是否存在
        old_contract = await self.get_contract_by_id(db, contract_id)
        if not old_contract:
            return None
        
        # 更新时间
        contract_data["update_time"] = datetime.now()
        
        # 更新合同信息
        await db.execute(
            update(Contract)
            .where(Contract.id == contract_id)
            .values(**contract_data)
        )
        
        # 刷新获取更新后的对象
        await db.refresh(old_contract)
        
        # 如果状态发生变化，记录状态变更日志
        if hasattr(old_contract, 'status') and old_contract.status != contract_data.get('status', old_contract.status):
            await self.create_contract_status_log(
                db=db,
                contract_id=contract_id,
                old_status=getattr(old_contract, 'old_status', 'unknown'),
                new_status=contract_data.get('status', old_contract.status),
                operator=contract_data.get("operator", "system"),
                remark=contract_data.get("status_remark", "")
            )
        
        await db.commit()
        return old_contract
    
    async def delete_contract(self, db: AsyncSession, contract_id: int) -> bool:
        """删除合同"""
        result = await db.execute(delete(Contract).where(Contract.id == contract_id))
        await db.commit()
        return result.rowcount > 0
    
    async def batch_delete_contracts(self, db: AsyncSession, contract_ids: List[int]) -> Dict[str, Any]:
        """批量删除合同
        
        Args:
            db: 数据库会话
            contract_ids: 合同ID列表
            
        Returns:
            Dict: 包含删除成功和失败数量的结果
        """
        if not contract_ids:
            return {
                "success_count": 0,
                "failed_count": 0,
                "failed_ids": []
            }
        
        success_count = 0
        failed_ids = []
        
        # 使用单个查询检查所有ID是否存在
        existing_stmt = select(Contract.id).where(Contract.id.in_(contract_ids))
        existing_result = await db.execute(existing_stmt)
        existing_ids = [row[0] for row in existing_result.fetchall()]
        
        # 确定不存在的ID
        failed_ids = [cid for cid in contract_ids if cid not in existing_ids]
        
        # 删除存在的合同及其相关数据
        if existing_ids:
            # 删除合同状态日志
            status_log_stmt = delete(ContractStatusLog).where(ContractStatusLog.contract_id.in_(existing_ids))
            await db.execute(status_log_stmt)
            
            # 删除合同附件
            attachment_stmt = delete(ContractAttachment).where(ContractAttachment.contract_id.in_(existing_ids))
            await db.execute(attachment_stmt)
            
            # 删除合同本身
            delete_stmt = delete(Contract).where(Contract.id.in_(existing_ids))
            result = await db.execute(delete_stmt)
            success_count = result.rowcount
        
        # 提交事务
        await db.commit()
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids
        }
    
    async def create_contract_status_log(self, db: AsyncSession, contract_id: int, old_status: str, new_status: str, operator: str, remark: str = "") -> ContractStatusLog:
        """创建合同状态变更记录"""
        status_log = ContractStatusLog(
            contract_id=contract_id,
            old_status=old_status,
            new_status=new_status,
            operator=operator,
            remark=remark
        )
        
        db.add(status_log)
        await db.commit()
        await db.refresh(status_log)
        
        return status_log
    
    async def get_contract_status_logs(self, db: AsyncSession, contract_id: int) -> List[ContractStatusLog]:
        """获取合同状态变更记录"""
        result = await db.execute(
            select(ContractStatusLog)
            .where(ContractStatusLog.contract_id == contract_id)
            .order_by(ContractStatusLog.operate_time.desc())
        )
        return result.scalars().all()
    
    async def upload_contract_attachment(self, db: AsyncSession, contract_id: int, attachment_data: Dict[str, Any]) -> ContractAttachment:
        """上传合同附件"""
        attachment = ContractAttachment(
            contract_id=contract_id,
            **attachment_data
        )
        
        db.add(attachment)
        await db.flush()
        await db.refresh(attachment)
        
        return attachment
    
    async def get_contract_attachments(self, db: AsyncSession, contract_id: int) -> List[ContractAttachment]:
        """获取合同附件列表"""
        result = await db.execute(
            select(ContractAttachment)
            .where(ContractAttachment.contract_id == contract_id)
            .order_by(ContractAttachment.upload_time.desc())
        )
        return result.scalars().all()
    
    async def delete_contract_attachment(self, db: AsyncSession, attachment_id: int) -> bool:
        """删除合同附件"""
        result = await db.execute(delete(ContractAttachment).where(ContractAttachment.id == attachment_id))
        await db.commit()
        return result.rowcount > 0
    
    async def copy_contract(self, contract_id: int) -> Optional[Contract]:
        """快速复制合同记录
        
        Args:
            contract_id: 要复制的合同ID
            
        Returns:
            复制后的合同对象
        """
        from ...core.db import get_async_db
        from sqlalchemy.ext.asyncio import AsyncSession
        
        async for db in get_async_db():
            try:
                # 获取原合同
                original_contract = await self.get_contract_by_id(db, contract_id)
                if not original_contract:
                    self.logger.error(f"合同不存在: {contract_id}")
                    return None
                
                # 创建新合同数据（排除ID和创建时间）
                contract_dict = original_contract.dict()
                contract_dict.pop("id", None)
                contract_dict.pop("create_time", None)
                contract_dict.pop("update_time", None)
                
                # 生成唯一合同编号
                base_contract_no = contract_dict["contract_no"]
                new_contract_no = f"{base_contract_no}_copy"
                
                # 检查并生成唯一编号
                suffix = 1
                while True:
                    existing = await self.get_contract_by_no(db, new_contract_no)
                    if not existing:
                        break
                    new_contract_no = f"{base_contract_no}_copy{suffix}"
                    suffix += 1
                
                contract_dict["contract_no"] = new_contract_no
                contract_dict["name"] = f"{contract_dict['name']}_copy"
                contract_dict["status"] = "draft"  # 新合同默认草稿状态
                
                # 创建新合同
                new_contract = await self.create_contract(db, contract_dict)
                await db.commit()
                
                self.logger.info(f"合同复制成功: 原ID={contract_id}, 新ID={new_contract.id}, 新编号={new_contract_no}")
                return new_contract
            except Exception as e:
                self.logger.error(f"合同复制失败: {str(e)}")
                await db.rollback()
                return None
    
    async def get_contract_count(self, db: AsyncSession, filters: Dict[str, Any] = None) -> int:
        """获取合同总数"""
        query = select(func.count(Contract.id))
        
        # 应用过滤条件
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(Contract, key):
                    if isinstance(value, (list, tuple)):
                        query = query.where(getattr(Contract, key).in_(value))
                    else:
                        query = query.where(getattr(Contract, key) == value)
        
        result = await db.execute(query)
        return result.scalar()
    
    async def get_contracts_by_status(self, db: AsyncSession, status: str, skip: int = 0, limit: int = 100) -> List[Contract]:
        """按状态获取合同列表"""
        result = await db.execute(
            select(Contract)
            .where(Contract.status == status)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def get_contracts_by_department(self, db: AsyncSession, department: str, skip: int = 0, limit: int = 100) -> List[Contract]:
        """按部门获取合同列表"""
        result = await db.execute(
            select(Contract)
            .where(Contract.department == department)
            .offset(skip)
            .limit(limit)
        )
        return result.scalars().all()
    
    async def quick_copy_contract(self, db: AsyncSession, contract_id: int, new_contract_no: str = None, custom_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """快速复制合同
        
        Args:
            db: 数据库会话
            contract_id: 原合同ID
            new_contract_no: 新合同编号（如果不提供则自动生成）
            custom_data: 自定义合同数据（用于覆盖原合同信息）
            
        Returns:
            Dict: 包含新合同ID的响应数据
        """
        # 获取原合同信息
        original_contract = await self.get_contract_by_id(db, contract_id)
        if not original_contract:
            raise ValueError(f"合同ID {contract_id} 不存在")
        
        # 生成新合同编号
        if not new_contract_no:
            if custom_data and custom_data.get('new_contract_no'):
                new_contract_no = custom_data['new_contract_no']
            else:
                # 自动生成合同编号：原编号 + "-副本" + 时间戳
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
                new_contract_no = f"{original_contract.contract_no}-副本{timestamp}"
        
        # 检查新合同编号是否已存在
        existing_contract = await self.get_contract_by_no(db, new_contract_no)
        if existing_contract:
            raise ValueError(f"合同编号 {new_contract_no} 已存在")
        
        # 创建新合同数据（排除ID和唯一字段）
        new_contract_data = {
            "contract_no": new_contract_no,
            "name": custom_data.get('name', f"{original_contract.name}（副本）") if custom_data else f"{original_contract.name}（副本）",
            "type": custom_data.get('type', original_contract.type) if custom_data else original_contract.type,
            "signing_date": custom_data.get('signing_date', original_contract.signing_date) if custom_data else original_contract.signing_date,
            "expiry_date": custom_data.get('expiry_date', original_contract.expiry_date) if custom_data else original_contract.expiry_date,
            "party_a": custom_data.get('party_a', original_contract.party_a) if custom_data else original_contract.party_a,
            "party_b": custom_data.get('party_b', original_contract.party_b) if custom_data else original_contract.party_b,
            "amount": custom_data.get('amount', original_contract.amount) if custom_data else original_contract.amount,
            "status": custom_data.get('status', "draft"),  # 新合同状态默认为草稿，除非自定义
            "department": custom_data.get('department', original_contract.department) if custom_data else original_contract.department,
            "creator": custom_data.get('creator', original_contract.creator) if custom_data else original_contract.creator,
            "description": custom_data.get('description', original_contract.description) if custom_data else original_contract.description,
            "create_time": datetime.now(),
            "update_time": datetime.now()
        }
        
        # 创建新合同
        new_contract = await self.create_contract(db, new_contract_data)
        
        # 复制合同附件
        original_attachments = await self.get_contract_attachments(db, contract_id)
        for attachment in original_attachments:
            new_attachment = ContractAttachment(
                contract_id=new_contract.id,
                file_name=attachment.file_name,
                file_path=attachment.file_path,
                file_size=attachment.file_size,
                file_type=attachment.file_type,
                uploader=attachment.uploader,
                upload_time=datetime.now(),
                remark=f"复制自合同 {original_contract.contract_no}: {attachment.remark}"
            )
            db.add(new_attachment)
        
        # 提交所有更改
        await db.commit()
        
        return {
            "new_id": new_contract.id,
            "new_contract_no": new_contract.contract_no,
            "original_contract_no": original_contract.contract_no
        }

# 创建合同服务实例
contract_service = ContractService()