import os
import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, Depends
from fastapi.responses import FileResponse
from sqlmodel.ext.asyncio.session import AsyncSession
from datetime import datetime

from app.core.db import get_async_db
from app.contracts.models.contract import (
    Contract, ContractAttachment, 
    MAX_FILE_SIZE, validate_file_type, 
    get_mime_type, get_file_category
)

router_logger = logging.getLogger("contract_file_api")
file_router = APIRouter()

UPLOAD_BASE_DIR = Path("uploads/contracts")
UPLOAD_BASE_DIR.mkdir(parents=True, exist_ok=True)

@file_router.post("/contracts/{contract_id}/attachments")
async def upload_contract_attachment(
    contract_id: int,
    file: UploadFile = File(None),
    file_path: str = Query(None, description="文件路径（从Amis文件接收器返回）"),
    file_type: str = Query("attachment", description="附件类型: content/attachment"),
    remark: str = Query("", description="备注"),
    session: AsyncSession = Depends(get_async_db)
):
    """
    上传合同附件
    支持文件类型验证、大小限制
    支持直接上传文件或使用已上传的文件路径
    """
    router_logger.info(f"开始上传合同附件，合同ID: {contract_id}, 文件名: {file.filename if file else file_path}")
    
    try:
        # 如果提供了文件路径，则使用已上传的文件
        if file_path:
            # 从文件路径中提取文件信息
            path_obj = Path(file_path)
            file_name = path_obj.name
            
            # 验证文件是否存在
            if not path_obj.exists():
                raise HTTPException(status_code=400, detail=f"文件不存在: {file_path}")
            
            # 获取文件信息
            file_size = path_obj.stat().st_size
            file_extension = path_obj.suffix.lower()
            
            # 验证文件类型
            if not validate_file_type(file_extension):
                raise HTTPException(
                    status_code=400, 
                    detail=f"不支持的文件类型: {file_extension}。支持类型: PDF, Word, Excel, PPT, TXT, 图片, 压缩包"
                )
            
            # 验证文件大小
            if file_size > MAX_FILE_SIZE:
                max_size_mb = MAX_FILE_SIZE / (1024 * 1024)
                raise HTTPException(
                    status_code=400,
                    detail=f"文件大小超过限制({max_size_mb}MB)，当前文件: {file_size / (1024 * 1024):.2f}MB"
                )
            
            # 移动文件到合同目录
            contract_stmt = __import__('sqlmodel').select(Contract).where(Contract.id == contract_id)
            contract_result = await session.execute(contract_stmt)
            contract = contract_result.scalar_one_or_none()
            
            if not contract:
                raise HTTPException(status_code=404, detail=f"合同不存在，ID: {contract_id}")
            
            contract_dir = UPLOAD_BASE_DIR / str(contract_id)
            contract_dir.mkdir(parents=True, exist_ok=True)
            
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            new_file_path = contract_dir / unique_filename
            
            # 移动文件
            import shutil
            shutil.move(str(path_obj), str(new_file_path))
            
            mime_type = get_mime_type(file_name)
            category = get_file_category(file_extension)
            
            attachment = ContractAttachment(
                contract_id=contract_id,
                file_name=file_name,
                file_path=str(new_file_path),
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
            
            router_logger.info(f"合同附件上传成功（使用文件路径），附件ID: {attachment.id}")
            
            return {
                "status": 200,
                "msg": "文件上传成功",
                "data": {
                    "id": attachment.id,
                    "file_name": attachment.file_name,
                    "file_size": attachment.file_size,
                    "file_category": attachment.file_category,
                    "upload_time": attachment.upload_time.isoformat()
                }
            }
        
        # 如果直接上传文件
        elif file:
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
            
            contract_dir = UPLOAD_BASE_DIR / str(contract_id)
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
            
            router_logger.info(f"合同附件上传成功（直接上传），附件ID: {attachment.id}")
            
            return {
                "status": 200,
                "msg": "文件上传成功",
                "data": {
                    "id": attachment.id,
                    "file_name": attachment.file_name,
                    "file_size": attachment.file_size,
                    "file_category": attachment.file_category,
                    "upload_time": attachment.upload_time.isoformat()
                }
            }
        else:
            raise HTTPException(status_code=400, detail="必须提供文件或文件路径")
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"合同附件上传失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"文件上传失败: {str(e)}")


@file_router.get("/contracts/{contract_id}/attachments")
async def get_contract_attachments(
    contract_id: int,
    file_type: Optional[str] = Query(None, description="附件类型筛选"),
    session: AsyncSession = Depends(get_async_db)
):
    """
    获取合同附件列表
    """
    router_logger.info(f"获取合同附件列表，合同ID: {contract_id}")
    
    try:
        contract_stmt = __import__('sqlmodel').select(Contract).where(Contract.id == contract_id)
        contract_result = await session.execute(contract_stmt)
        contract = contract_result.scalar_one_or_none()
        
        if not contract:
            raise HTTPException(status_code=404, detail=f"合同不存在，ID: {contract_id}")
        
        attachment_stmt = __import__('sqlmodel').select(ContractAttachment).where(
            ContractAttachment.contract_id == contract_id,
            ContractAttachment.is_active == True
        )
        
        if file_type:
            attachment_stmt = attachment_stmt.where(ContractAttachment.file_type == file_type)
        
        attachment_stmt = attachment_stmt.order_by(ContractAttachment.upload_time.desc())
        
        result = await session.execute(attachment_stmt)
        attachments = result.scalars().all()
        
        return {
            "status": 200,
            "msg": "获取成功",
            "data": [
                {
                    "id": att.id,
                    "file_name": att.file_name,
                    "file_size": att.file_size,
                    "file_extension": att.file_extension,
                    "file_category": att.file_category,
                    "file_type": att.file_type,
                    "mime_type": att.mime_type,
                    "upload_time": att.upload_time.isoformat(),
                    "download_count": att.download_count,
                    "remark": att.remark
                }
                for att in attachments
            ]
        }
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"获取合同附件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取附件列表失败: {str(e)}")


@file_router.get("/attachments/{attachment_id}/download")
async def download_attachment(
    attachment_id: int,
    session: AsyncSession = Depends(get_async_db)
):
    """
    下载合同附件
    """
    router_logger.info(f"下载合同附件，附件ID: {attachment_id}")
    
    try:
        attachment_stmt = __import__('sqlmodel').select(ContractAttachment).where(
            ContractAttachment.id == attachment_id,
            ContractAttachment.is_active == True
        )
        result = await session.execute(attachment_stmt)
        attachment = result.scalar_one_or_none()
        
        if not attachment:
            raise HTTPException(status_code=404, detail=f"附件不存在或已删除，ID: {attachment_id}")
        
        if not os.path.exists(attachment.file_path):
            raise HTTPException(status_code=404, detail="文件不存在，请联系管理员")
        
        attachment.download_count += 1
        await session.commit()
        
        return FileResponse(
            path=attachment.file_path,
            filename=attachment.file_name,
            media_type=attachment.mime_type
        )
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"下载附件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载失败: {str(e)}")


@file_router.delete("/attachments/{attachment_id}")
async def delete_attachment(
    attachment_id: int,
    session: AsyncSession = Depends(get_async_db)
):
    """
    删除合同附件（软删除）
    """
    router_logger.info(f"删除合同附件，附件ID: {attachment_id}")
    
    try:
        attachment_stmt = __import__('sqlmodel').select(ContractAttachment).where(
            ContractAttachment.id == attachment_id
        )
        result = await session.execute(attachment_stmt)
        attachment = result.scalar_one_or_none()
        
        if not attachment:
            raise HTTPException(status_code=404, detail=f"附件不存在，ID: {attachment_id}")
        
        attachment.is_active = False
        await session.commit()
        
        if os.path.exists(attachment.file_path):
            try:
                os.remove(attachment.file_path)
            except Exception as e:
                router_logger.warning(f"物理文件删除失败: {attachment.file_path}, 错误: {e}")
        
        router_logger.info(f"合同附件删除成功，附件ID: {attachment_id}")
        
        return {
            "status": 200,
            "msg": "附件已删除"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"删除附件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


@file_router.get("/attachments/{attachment_id}/info")
async def get_attachment_info(
    attachment_id: int,
    session: AsyncSession = Depends(get_async_db)
):
    """
    获取附件详细信息
    """
    try:
        attachment_stmt = __import__('sqlmodel').select(ContractAttachment).where(
            ContractAttachment.id == attachment_id
        )
        result = await session.execute(attachment_stmt)
        attachment = result.scalar_one_or_none()
        
        if not attachment:
            raise HTTPException(status_code=404, detail=f"附件不存在，ID: {attachment_id}")
        
        return {
            "status": 200,
            "data": {
                "id": attachment.id,
                "contract_id": attachment.contract_id,
                "file_name": attachment.file_name,
                "file_size": attachment.file_size,
                "file_size_formatted": f"{attachment.file_size / 1024:.2f} KB" if attachment.file_size < 1024*1024 else f"{attachment.file_size / (1024*1024):.2f} MB",
                "file_extension": attachment.file_extension,
                "mime_type": attachment.mime_type,
                "file_category": attachment.file_category,
                "file_type": attachment.file_type,
                "uploader": attachment.uploader,
                "upload_time": attachment.upload_time.isoformat(),
                "download_count": attachment.download_count,
                "is_active": attachment.is_active,
                "remark": attachment.remark
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"获取附件信息失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取信息失败: {str(e)}")
