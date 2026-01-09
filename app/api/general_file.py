import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Form, Depends
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from app.core.db import get_async_db
from app.contracts.models.contract import (
    Contract, ContractAttachment, 
    MAX_FILE_SIZE, validate_file_type, 
    get_mime_type, get_file_category
)

router_logger = logging.getLogger("general_file_api")
router = APIRouter()

UPLOAD_BASE_DIR = Path("uploads")
UPLOAD_BASE_DIR.mkdir(parents=True, exist_ok=True)

@router.post("/upload/file")
async def general_upload_file(
    file: UploadFile = File(...),
    file_type: str = Query("general", description="文件类型"),
    category: str = Query("document", description="文件分类"),
    remark: str = Query("", description="备注"),
    session: AsyncSession = Depends(get_async_db)
):
    """
    通用文件上传接口，用于Amis admin文件上传
    """
    router_logger.info(f"开始通用文件上传，文件名: {file.filename}")
    
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_extension = Path(file.filename).suffix.lower()
        
        if not validate_file_type(file_extension):
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_extension}。支持类型: PDF, Word, Excel, PPT, TXT, 图片, 压缩包"
            )
        
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制({max_size_mb}MB)，当前文件: {file_size / (1024 * 1024):.2f}MB"
            )
        
        # 创建通用上传目录
        general_dir = UPLOAD_BASE_DIR / "general"
        general_dir.mkdir(parents=True, exist_ok=True)
        
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = general_dir / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        mime_type = get_mime_type(file.filename)
        category = get_file_category(file_extension)
        
        # 对于通用上传，我们不关联特定合同，但可以返回文件路径供后续处理
        return {
            "status": 0,  # Amis期望的状态码为0表示成功
            "msg": "文件上传成功",
            "data": {
                "id": str(uuid.uuid4()),
                "filename": file.filename,
                "originalName": file.filename,
                "url": f"/api/file/download/{unique_filename}",
                "path": str(file_path),
                "size": file_size,
                "mimeType": mime_type,
                "extension": file_extension.lstrip('.')
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"通用文件上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@router.post("/upload/contract-attachment")
async def upload_contract_attachment_from_amis(
    file: UploadFile = File(..., description="上传的文件"),
    contract_id: int = Form(..., description="合同ID"),
    file_type: str = Form("attachment", description="附件类型: content/attachment"),
    remark: str = Form("", description="备注"),
    session: AsyncSession = Depends(get_async_db)
):
    """
    从Amis界面上传合同附件
    """
    router_logger.info(f"从Amis界面上传合同附件，合同ID: {contract_id}, 文件名: {file.filename}")
    
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="文件名不能为空")
        
        file_extension = Path(file.filename).suffix.lower()
        
        if not validate_file_type(file_extension):
            raise HTTPException(
                status_code=400, 
                detail=f"不支持的文件类型: {file_extension}。支持类型: PDF, Word, Excel, PPT, TXT, 图片, 压缩包"
            )
        
        content = await file.read()
        file_size = len(content)
        
        if file_size > MAX_FILE_SIZE:
            max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
            raise HTTPException(
                status_code=400,
                detail=f"文件大小超过限制({max_size_mb}MB)，当前文件: {file_size / (1024 * 1024):.2f}MB"
            )
        
        contract_stmt = __import__('sqlmodel').select(Contract).where(Contract.id == contract_id)
        contract_result = await session.execute(contract_stmt)
        contract = contract_result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"合同不存在，ID: {contract_id}")
        
        contract_dir = UPLOAD_BASE_DIR / "contracts" / str(contract_id)
        contract_dir.mkdir(parents=True, exist_ok=True)
        
        unique_filename = f"{uuid.uuid4().hex}{file_extension}"
        file_path = contract_dir / unique_filename
        
        with open(file_path, "wb") as f:
            f.write(content)
        
        mime_type = get_mime_type(file.filename)
        category = get_file_category(file_extension)
        
        attachment = ContractAttachment(
            contract_id=contract_id,
            file_name=file.filename,
            file_path=str(file_path),
            file_size=file_size,
            file_extension=file_extension.lstrip('.'),
            mime_type=mime_type,
            file_category=category,
            file_type=file_type,
            uploader="current_user",
            upload_time=datetime.now(),
            download_count=0,
            is_active=True,
            remark=remark
        )
        
        session.add(attachment)
        await session.commit()
        await session.refresh(attachment)
        
        router_logger.info(f"合同附件上传成功，附件ID: {attachment.id}")
        
        return {
            "status": 0,  # Amis期望的状态码为0表示成功
            "msg": "文件上传成功",
            "data": {
                "id": attachment.id,
                "filename": attachment.file_name,
                "originalName": attachment.file_name,
                "url": f"/api/attachments/{attachment.id}/download",
                "path": str(file_path),
                "size": attachment.file_size,
                "mimeType": attachment.mime_type,
                "extension": attachment.file_extension
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"从Amis界面上传合同附件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")