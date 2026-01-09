from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete
from ..models.quote import Quote, QuoteItem, QuoteStatus
from ..schemas.quote import QuoteCreate, QuoteUpdate, QuoteItemCreate
from datetime import datetime

class QuoteService:
    """报价单服务类"""
    
    def __init__(self):
        pass
    
    async def create_quote(self, db: AsyncSession, quote_create: QuoteCreate) -> Quote:
        """创建报价单"""
        db_quote = Quote(**quote_create.dict())
        db.add(db_quote)
        await db.commit()
        await db.refresh(db_quote)
        return db_quote
    
    async def get_quote(self, db: AsyncSession, quote_id: int) -> Optional[Quote]:
        """获取报价单"""
        result = await db.execute(
            select(Quote).where(Quote.id == quote_id)
        )
        return result.scalar_one_or_none()
    
    async def get_quotes(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[Quote]:
        """获取报价单列表"""
        result = await db.execute(
            select(Quote).offset(skip).limit(limit)
        )
        return result.scalars().all()
    
    async def update_quote(self, db: AsyncSession, quote_id: int, quote_update: QuoteUpdate) -> Optional[Quote]:
        """更新报价单"""
        # 获取报价单
        db_quote = await self.get_quote(db, quote_id)
        if not db_quote:
            return None
        
        # 更新时间
        update_data = quote_update.dict(exclude_unset=True)
        update_data['updated_at'] = datetime.now()
        
        # 更新报价单信息
        result = await db.execute(
            update(Quote)
            .where(Quote.id == quote_id)
            .values(**update_data)
            .returning(Quote)
        )
        
        await db.commit()
        return result.scalar_one_or_none()
    
    async def delete_quote(self, db: AsyncSession, quote_id: int) -> bool:
        """删除报价单"""
        result = await db.execute(
            delete(Quote).where(Quote.id == quote_id)
        )
        await db.commit()
        return result.rowcount > 0
    
    async def create_quote_item(self, db: AsyncSession, item_create: QuoteItemCreate) -> QuoteItem:
        """创建报价单项"""
        db_item = QuoteItem(**item_create.dict())
        db.add(db_item)
        await db.commit()
        await db.refresh(db_item)
        return db_item
    
    async def get_quote_items(self, db: AsyncSession, quote_id: int) -> List[QuoteItem]:
        """获取报价单项列表"""
        result = await db.execute(
            select(QuoteItem).where(QuoteItem.quote_id == quote_id)
        )
        return result.scalars().all()
    
    async def update_quote_status(self, db: AsyncSession, quote_id: int, status: QuoteStatus) -> Optional[Quote]:
        """更新报价单状态"""
        # 更新状态和时间
        result = await db.execute(
            update(Quote)
            .where(Quote.id == quote_id)
            .values(
                status=status,
                updated_at=datetime.now()
            )
            .returning(Quote)
        )
        
        await db.commit()
        return result.scalar_one_or_none()

# 创建服务实例
quote_service = QuoteService()