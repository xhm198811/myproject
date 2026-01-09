from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from ...core.db import get_async_db as get_db
from ..models.quote import Quote, QuoteItem, QuoteStatus
from ..schemas.quote import QuoteCreate, QuoteUpdate, QuoteRead, QuoteItemCreate, QuoteItemRead
from ..services.quote import quote_service

router = APIRouter(prefix="/quotes", tags=["quotes"])

@router.post("/", response_model=QuoteRead)
async def create_quote(
    quote: QuoteCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建报价单"""
    return await quote_service.create_quote(db, quote)

@router.get("/{quote_id}", response_model=QuoteRead)
async def get_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取报价单详情"""
    quote = await quote_service.get_quote(db, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return quote

@router.get("/", response_model=List[QuoteRead])
async def get_quotes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db)
):
    """获取报价单列表"""
    return await quote_service.get_quotes(db, skip, limit)

@router.put("/{quote_id}", response_model=QuoteRead)
async def update_quote(
    quote_id: int,
    quote_update: QuoteUpdate,
    db: AsyncSession = Depends(get_db)
):
    """更新报价单"""
    quote = await quote_service.update_quote(db, quote_id, quote_update)
    if not quote:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return quote

@router.delete("/{quote_id}")
async def delete_quote(
    quote_id: int,
    db: AsyncSession = Depends(get_db)
):
    """删除报价单"""
    success = await quote_service.delete_quote(db, quote_id)
    if not success:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return {"message": "报价单删除成功"}

@router.post("/{quote_id}/items", response_model=QuoteItemRead)
async def create_quote_item(
    quote_id: int,
    item: QuoteItemCreate,
    db: AsyncSession = Depends(get_db)
):
    """创建报价单项"""
    # 验证报价单存在
    quote = await quote_service.get_quote(db, quote_id)
    if not quote:
        raise HTTPException(status_code=404, detail="报价单不存在")
    
    # 设置quote_id
    item.quote_id = quote_id
    return await quote_service.create_quote_item(db, item)

@router.get("/{quote_id}/items", response_model=List[QuoteItemRead])
async def get_quote_items(
    quote_id: int,
    db: AsyncSession = Depends(get_db)
):
    """获取报价单项列表"""
    return await quote_service.get_quote_items(db, quote_id)

@router.put("/{quote_id}/status")
async def update_quote_status(
    quote_id: int,
    status: QuoteStatus,
    db: AsyncSession = Depends(get_db)
):
    """更新报价单状态"""
    quote = await quote_service.update_quote_status(db, quote_id, status)
    if not quote:
        raise HTTPException(status_code=404, detail="报价单不存在")
    return quote