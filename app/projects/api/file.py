"""
项目文件API
提供项目附件上传、下载、删除等功能
"""
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
from app.projects.models.project import ProjectDocument

router_logger = logging.getLogger("project_file_api")
project_file_router = APIRouter()

UPLOAD_BASE_DIR = Path("uploads/projects")
UPLOAD_BASE_DIR.mkdir(parents=True, exist_ok=True)

MAX_FILE_SIZE = 20 * 1024 * 1024  # 20MB

SUPPORTED_EXTENSIONS = [
    '.pdf', '.doc', '.docx', '.xls', '.xlsx', 
    '.ppt', '.pptx', '.txt', '.jpg', '.jpeg', 
    '.png', '.gif', '.zip', '.rar'
]

def validate_file_type(file_extension: str) -> bool:
    """验证文件类型"""
    return file_extension.lower() in SUPPORTED_EXTENSIONS

def get_mime_type(file_name: str) -> str:
    """获取文件MIME类型"""
    extension = Path(file_name).suffix.lower()
    mime_types = {
        '.pdf': 'application/pdf',
        '.doc': 'application/msword',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.xls': 'application/vnd.ms-excel',
        '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        '.ppt': 'application/vnd.ms-powerpoint',
        '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
        '.txt': 'text/plain',
        '.jpg': 'image/jpeg',
        '.jpeg': 'image/jpeg',
        '.png': 'image/png',
        '.gif': 'image/gif',
        '.zip': 'application/zip',
        '.rar': 'application/x-rar-compressed'
    }
    return mime_types.get(extension, 'application/octet-stream')

def get_file_category(file_extension: str) -> str:
    """获取文件分类"""
    extension = file_extension.lower()
    if extension in ['.pdf', '.doc', '.docx']:
        return 'document'
    elif extension in ['.xls', '.xlsx']:
        return 'spreadsheet'
    elif extension in ['.ppt', '.pptx']:
        return 'presentation'
    elif extension in ['.jpg', '.jpeg', '.png', '.gif']:
        return 'image'
    elif extension in ['.zip', '.rar']:
        return 'archive'
    else:
        return 'other'


@project_file_router.post("/projects/{project_id}/attachments")
async def upload_project_attachment(
    project_id: int,
    file: UploadFile = File(None),
    file_path: str = Query(None, description="文件路径（从Amis文件接收器返回）"),
    file_type: str = Query("attachment", description="附件类型: attachment/document/other"),
    remark: str = Query("", description="备注"),
    session: AsyncSession = Depends(get_async_db)
):
    """
    上传项目附件
    支持文件类型验证、大小限制
    支持直接上传文件或使用已上传的文件路径
    """
    router_logger.info(f"开始上传项目附件，项目ID: {project_id}, 文件名: {file.filename if file else file_path}")
    
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
            
            # 验证项目是否存在
            from app.projects.models.project import Project
            import sqlmodel
            project_stmt = sqlmodel.select(Project).where(Project.id == project_id)
            project_result = await session.execute(project_stmt)
            project = project_result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(status_code=404, detail=f"项目不存在，ID: {project_id}")
            
            # 创建项目目录
            project_dir = UPLOAD_BASE_DIR / str(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            new_file_path = project_dir / unique_filename
            
            # 移动文件
            import shutil
            shutil.move(str(path_obj), str(new_file_path))
            
            # 创建附件记录
            document = ProjectDocument(
                project_id=project_id,
                name=file_name,
                category=get_file_category(file_extension),
                file_path=str(new_file_path),
                file_size=file_size,
                version="1.0.0",
                uploader=1,  # TODO: 从认证信息获取用户ID
                upload_time=datetime.now(),
                description=remark
            )
            
            session.add(document)
            await session.commit()
            await session.refresh(document)
            
            router_logger.info(f"项目附件上传成功，附件ID: {document.id}")
            
            return {
                "status": 0,
                "msg": "附件上传成功",
                "data": {
                    "id": document.id,
                    "name": document.name,
                    "file_size": document.file_size,
                    "upload_time": document.upload_time.isoformat() if document.upload_time else None
                }
            }
        
        # 如果直接上传文件
        elif file:
            # 验证文件类型
            file_extension = Path(file.filename).suffix.lower()
            if not validate_file_type(file_extension):
                raise HTTPException(
                    status_code=400, 
                    detail=f"不支持的文件类型: {file_extension}。支持类型: PDF, Word, Excel, PPT, TXT, 图片, 压缩包"
                )
            
            # 验证项目是否存在
            from app.projects.models.project import Project
            import sqlmodel
            project_stmt = sqlmodel.select(Project).where(Project.id == project_id)
            project_result = await session.execute(project_stmt)
            project = project_result.scalar_one_or_none()
            
            if not project:
                raise HTTPException(status_code=404, detail=f"项目不存在，ID: {project_id}")
            
            # 创建项目目录
            project_dir = UPLOAD_BASE_DIR / str(project_id)
            project_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成唯一文件名
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            new_file_path = project_dir / unique_filename
            
            # 保存文件
            content = await file.read()
            with open(new_file_path, "wb") as f:
                f.write(content)
            
            # 创建附件记录
            document = ProjectDocument(
                project_id=project_id,
                name=file.filename,
                category=get_file_category(file_extension),
                file_path=str(new_file_path),
                file_size=len(content),
                version="1.0.0",
                uploader=1,  # TODO: 从认证信息获取用户ID
                upload_time=datetime.now(),
                description=remark
            )
            
            session.add(document)
            await session.commit()
            await session.refresh(document)
            
            router_logger.info(f"项目附件上传成功，附件ID: {document.id}")
            
            return {
                "status": 0,
                "msg": "附件上传成功",
                "data": {
                    "id": document.id,
                    "name": document.name,
                    "file_size": document.file_size,
                    "upload_time": document.upload_time.isoformat() if document.upload_time else None
                }
            }
        
        else:
            raise HTTPException(status_code=400, detail="请选择要上传的文件")
            
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"上传项目附件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"上传附件失败: {str(e)}")


@project_file_router.get("/projects/{project_id}/attachments")
async def get_project_attachments(
    project_id: int,
    session: AsyncSession = Depends(get_async_db)
):
    """
    获取项目附件列表
    """
    try:
        import sqlmodel
        from app.projects.models.project import Project
        
        # 验证项目是否存在
        project_stmt = sqlmodel.select(Project).where(Project.id == project_id)
        project_result = await session.execute(project_stmt)
        project = project_result.scalar_one_or_none()
        
        if not project:
            raise HTTPException(status_code=404, detail=f"项目不存在，ID: {project_id}")
        
        # 查询附件列表
        document_stmt = sqlmodel.select(ProjectDocument).where(
            ProjectDocument.project_id == project_id
        ).order_by(ProjectDocument.upload_time.desc())
        document_result = await session.execute(document_stmt)
        documents = document_result.scalars().all()
        
        # 格式化返回数据
        attachments = []
        for doc in documents:
            attachments.append({
                "id": doc.id,
                "name": doc.name,
                "category": doc.category,
                "file_size": doc.file_size,
                "version": doc.version,
                "uploader": doc.uploader,
                "upload_time": doc.upload_time.isoformat() if doc.upload_time else None,
                "description": doc.description
            })
        
        return {
            "status": 0,
            "msg": "",
            "data": {
                "items": attachments,
                "total": len(attachments)
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"获取项目附件列表失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"获取附件列表失败: {str(e)}")


@project_file_router.get("/attachments/{attachment_id}/download")
async def download_project_attachment(
    attachment_id: int,
    session: AsyncSession = Depends(get_async_db)
):
    """
    下载项目附件
    """
    try:
        import sqlmodel
        
        # 查询附件
        document_stmt = sqlmodel.select(ProjectDocument).where(ProjectDocument.id == attachment_id)
        document_result = await session.execute(document_stmt)
        document = document_result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail=f"附件不存在，ID: {attachment_id}")
        
        # 验证文件是否存在
        file_path = Path(document.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"文件不存在: {document.file_path}")
        
        router_logger.info(f"下载项目附件，附件ID: {attachment_id}, 文件名: {document.name}")
        
        return FileResponse(
            path=str(file_path),
            filename=document.name,
            media_type=get_mime_type(document.name)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"下载项目附件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"下载附件失败: {str(e)}")


@project_file_router.delete("/attachments/{attachment_id}")
async def delete_project_attachment(
    attachment_id: int,
    session: AsyncSession = Depends(get_async_db)
):
    """
    删除项目附件
    """
    try:
        import sqlmodel
        
        # 查询附件
        document_stmt = sqlmodel.select(ProjectDocument).where(ProjectDocument.id == attachment_id)
        document_result = await session.execute(document_stmt)
        document = document_result.scalar_one_or_none()
        
        if not document:
            raise HTTPException(status_code=404, detail=f"附件不存在，ID: {attachment_id}")
        
        # 删除文件
        file_path = Path(document.file_path)
        if file_path.exists():
            file_path.unlink()
        
        # 删除数据库记录
        await session.delete(document)
        await session.commit()
        
        router_logger.info(f"删除项目附件成功，附件ID: {attachment_id}")
        
        return {
            "status": 0,
            "msg": "附件删除成功",
            "data": {}
        }
        
    except HTTPException:
        raise
    except Exception as e:
        router_logger.error(f"删除项目附件失败: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除附件失败: {str(e)}")
