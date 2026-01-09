from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Any, Optional
import logging
from ...core.db import get_async_db
from ...core.auth import get_current_active_user, get_current_superuser
from ..services.project import project_service
from ..models.project import (
    Project, ProjectStage, ProjectTask, 
    ProjectMember, ProjectDocument
)
from datetime import datetime

# 创建API路由器
router = APIRouter(prefix="/projects", tags=["projects"])

from pydantic import BaseModel

# 项目创建请求模型
class ProjectCreateRequest(BaseModel):
    name: str
    description: str = ""
    planned_start_time: str
    planned_end_time: str
    project_manager: Optional[int] = None
    amount: float
    status: str = "pending"
    contract_id: Optional[int] = None

# 项目更新请求模型
class ProjectUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    planned_start_time: Optional[str] = None
    planned_end_time: Optional[str] = None
    project_manager: Optional[int] = None
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    amount: Optional[float] = None
    status: Optional[str] = None
    contract_id: Optional[int] = None

# 项目阶段创建请求模型
class ProjectStageCreateRequest(BaseModel):
    project_id: int
    name: str
    description: str = ""
    planned_start_time: str
    planned_end_time: str
    status: str = "pending"

# 项目阶段更新请求模型
class ProjectStageUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    planned_start_time: Optional[str] = None
    planned_end_time: Optional[str] = None
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    status: Optional[str] = None

# 项目任务创建请求模型
class ProjectTaskCreateRequest(BaseModel):
    stage_id: int
    name: str
    description: str = ""
    assignee: Optional[int] = None
    planned_start_time: str
    planned_end_time: str
    priority: str = "medium"
    status: str = "pending"
    progress: int = 0

# 项目任务更新请求模型
class ProjectTaskUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    assignee: Optional[int] = None
    planned_start_time: Optional[str] = None
    planned_end_time: Optional[str] = None
    actual_start_time: Optional[str] = None
    actual_end_time: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None
    progress: Optional[int] = None

# 项目成员添加请求模型
class ProjectMemberAddRequest(BaseModel):
    project_id: int
    employee_id: int
    role: str = "member"
    permissions: str = "view"

# 项目成员更新请求模型
class ProjectMemberUpdateRequest(BaseModel):
    role: Optional[str] = None
    permissions: Optional[str] = None

# 项目快速复制请求模型
class ProjectQuickCopyRequest(BaseModel):
    new_name: Optional[str] = None
    custom_data: Optional[Dict[str, Any]] = None

@router.post("/", response_model=Dict[str, Any])
async def create_project(
    project_data: ProjectCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """创建项目"""
    # 转换字符串日期为datetime对象
    project_dict = project_data.dict()
    
    # 转换日期字段
    if project_dict.get('planned_start_time'):
        try:
            project_dict['planned_start_time'] = datetime.fromisoformat(project_dict['planned_start_time'])
        except ValueError:
            # 如果是日期格式（如 "2024-01-01"），转换为datetime
            project_dict['planned_start_time'] = datetime.strptime(project_dict['planned_start_time'], "%Y-%m-%d")
    if project_dict.get('planned_end_time'):
        try:
            project_dict['planned_end_time'] = datetime.fromisoformat(project_dict['planned_end_time'])
        except ValueError:
            # 如果是日期格式（如 "2024-01-01"），转换为datetime
            project_dict['planned_end_time'] = datetime.strptime(project_dict['planned_end_time'], "%Y-%m-%d")
    
    project = await project_service.create_project(db, project_dict)
    
    # 提交事务
    await db.commit()
    
    return {
        "status": 0,
        "msg": "项目创建成功",
        "data": project.dict()
    }

@router.get("/", response_model=Dict[str, Any])
async def get_projects(
    skip: int = 0,
    limit: int = 100,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取项目列表"""
    filters = {"status": status}
    
    projects = await project_service.get_projects(db, skip=skip, limit=limit, filters=filters)
    project_count = await project_service.get_project_count(db, filters=filters)
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": {
            "items": [project.dict() for project in projects],
            "total": project_count
        }
    }

@router.get("/{project_id}", response_model=Dict[str, Any])
async def get_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取指定项目信息"""
    project = await project_service.get_project_by_id(db, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": project.dict()
    }

@router.put("/{project_id}", response_model=Dict[str, Any])
async def update_project(
    project_id: int,
    project_data: ProjectUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """更新项目"""
    update_data = project_data.dict(exclude_unset=True)
    
    # 转换日期字段
    if update_data.get('planned_start_time'):
        try:
            update_data['planned_start_time'] = datetime.fromisoformat(update_data['planned_start_time'])
        except ValueError:
            update_data['planned_start_time'] = datetime.strptime(update_data['planned_start_time'], "%Y-%m-%d")
    if update_data.get('planned_end_time'):
        try:
            update_data['planned_end_time'] = datetime.fromisoformat(update_data['planned_end_time'])
        except ValueError:
            update_data['planned_end_time'] = datetime.strptime(update_data['planned_end_time'], "%Y-%m-%d")
    if update_data.get('actual_start_time'):
        try:
            update_data['actual_start_time'] = datetime.fromisoformat(update_data['actual_start_time'])
        except ValueError:
            update_data['actual_start_time'] = datetime.strptime(update_data['actual_start_time'], "%Y-%m-%d")
    if update_data.get('actual_end_time'):
        try:
            update_data['actual_end_time'] = datetime.fromisoformat(update_data['actual_end_time'])
        except ValueError:
            update_data['actual_end_time'] = datetime.strptime(update_data['actual_end_time'], "%Y-%m-%d")
    
    project = await project_service.update_project(db, project_id, update_data)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    return {
        "status": 0,
        "msg": "更新成功",
        "data": project.dict()
    }

@router.delete("/{project_id}", response_model=Dict[str, Any])
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_superuser)
):
    """删除项目（仅超级用户）"""
    success = await project_service.delete_project(db, project_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    return {
        "status": 0,
        "msg": "删除成功"
    }

@router.delete("/item/{ids}", response_model=Dict[str, Any])
async def batch_delete_projects(
    ids: str,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_superuser)
):
    """批量删除项目（仅超级用户）"""
    try:
        # 解析ID列表
        project_ids = [int(id_str.strip()) for id_str in ids.split(",")]
        
        # 执行批量删除
        result = await project_service.batch_delete_projects(db, project_ids)
        
        # 构建响应消息
        msg_parts = []
        if result["success_count"] > 0:
            msg_parts.append(f"成功删除 {result['success_count']} 个项目")
        if result["failed_count"] > 0:
            msg_parts.append(f"失败 {result['failed_count']} 个项目（ID: {', '.join(map(str, result['failed_ids']))}）")
        
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

@router.post("/{project_id}/quick_copy", response_model=Dict[str, Any])
async def quick_copy_project(
    project_id: int,
    copy_request: ProjectQuickCopyRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """快速复制项目"""
    try:
        # 处理custom_data中的日期字段
        custom_data = copy_request.custom_data
        if custom_data:
            # 转换日期字段
            if custom_data.get('planned_start_time'):
                try:
                    custom_data['planned_start_time'] = datetime.fromisoformat(custom_data['planned_start_time'])
                except ValueError:
                    custom_data['planned_start_time'] = datetime.strptime(custom_data['planned_start_time'], "%Y-%m-%d")
            if custom_data.get('planned_end_time'):
                try:
                    custom_data['planned_end_time'] = datetime.fromisoformat(custom_data['planned_end_time'])
                except ValueError:
                    custom_data['planned_end_time'] = datetime.strptime(custom_data['planned_end_time'], "%Y-%m-%d")
        
        new_project = await project_service.quick_copy_project(
            db=db,
            project_id=project_id,
            custom_data=custom_data
        )
        
        return {
            "status": 0,
            "msg": "项目复制成功",
            "data": new_project
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
        logger.error(f"复制项目失败: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"复制项目失败: {str(e)}"
        )

@router.get("/{project_id}/stats", response_model=Dict[str, Any])
async def get_project_stats(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取项目统计信息"""
    stats = await project_service.get_project_stats(db, project_id)
    if not stats:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目不存在"
        )
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": stats
    }

# ==================== 项目阶段相关 ====================

@router.post("/stages", response_model=Dict[str, Any])
async def create_project_stage(
    stage_data: ProjectStageCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """创建项目阶段"""
    # 转换字符串日期为datetime对象
    stage_dict = stage_data.dict()
    
    # 转换日期字段
    if stage_dict.get('planned_start_time'):
        stage_dict['planned_start_time'] = datetime.fromisoformat(stage_dict['planned_start_time'])
    if stage_dict.get('planned_end_time'):
        stage_dict['planned_end_time'] = datetime.fromisoformat(stage_dict['planned_end_time'])
    
    stage = await project_service.create_project_stage(db, stage_dict)
    
    return {
        "status": 0,
        "msg": "项目阶段创建成功",
        "data": stage.dict()
    }

@router.get("/{project_id}/stages", response_model=Dict[str, Any])
async def get_project_stages(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取项目阶段列表"""
    stages = await project_service.get_project_stages(db, project_id)
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": {
            "items": [stage.dict() for stage in stages],
            "total": len(stages)
        }
    }

@router.put("/stages/{stage_id}", response_model=Dict[str, Any])
async def update_project_stage(
    stage_id: int,
    stage_data: ProjectStageUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """更新项目阶段"""
    update_data = stage_data.dict(exclude_unset=True)
    
    # 转换日期字段
    if update_data.get('planned_start_time'):
        update_data['planned_start_time'] = datetime.fromisoformat(update_data['planned_start_time'])
    if update_data.get('planned_end_time'):
        update_data['planned_end_time'] = datetime.fromisoformat(update_data['planned_end_time'])
    if update_data.get('actual_start_time'):
        update_data['actual_start_time'] = datetime.fromisoformat(update_data['actual_start_time'])
    if update_data.get('actual_end_time'):
        update_data['actual_end_time'] = datetime.fromisoformat(update_data['actual_end_time'])
    
    stage = await project_service.update_project_stage(db, stage_id, update_data)
    if not stage:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目阶段不存在"
        )
    
    return {
        "status": 0,
        "msg": "项目阶段更新成功",
        "data": stage.dict()
    }

@router.delete("/stages/{stage_id}", response_model=Dict[str, Any])
async def delete_project_stage(
    stage_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """删除项目阶段"""
    success = await project_service.delete_project_stage(db, stage_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目阶段不存在"
        )
    
    return {
        "status": 0,
        "msg": "项目阶段删除成功"
    }

# ==================== 项目任务相关 ====================

@router.post("/tasks", response_model=Dict[str, Any])
async def create_project_task(
    task_data: ProjectTaskCreateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """创建项目任务"""
    # 转换字符串日期为datetime对象
    task_dict = task_data.dict()
    
    # 转换日期字段
    if task_dict.get('planned_start_time'):
        task_dict['planned_start_time'] = datetime.fromisoformat(task_dict['planned_start_time'])
    if task_dict.get('planned_end_time'):
        task_dict['planned_end_time'] = datetime.fromisoformat(task_dict['planned_end_time'])
    
    task = await project_service.create_project_task(db, task_dict)
    
    return {
        "status": 0,
        "msg": "项目任务创建成功",
        "data": task.dict()
    }

@router.get("/stages/{stage_id}/tasks", response_model=Dict[str, Any])
async def get_project_tasks(
    stage_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取项目阶段任务列表"""
    tasks = await project_service.get_project_tasks(db, stage_id)
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": {
            "items": [task.dict() for task in tasks],
            "total": len(tasks)
        }
    }

@router.put("/tasks/{task_id}", response_model=Dict[str, Any])
async def update_project_task(
    task_id: int,
    task_data: ProjectTaskUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """更新项目任务"""
    update_data = task_data.dict(exclude_unset=True)
    
    # 转换日期字段
    if update_data.get('planned_start_time'):
        update_data['planned_start_time'] = datetime.fromisoformat(update_data['planned_start_time'])
    if update_data.get('planned_end_time'):
        update_data['planned_end_time'] = datetime.fromisoformat(update_data['planned_end_time'])
    if update_data.get('actual_start_time'):
        update_data['actual_start_time'] = datetime.fromisoformat(update_data['actual_start_time'])
    if update_data.get('actual_end_time'):
        update_data['actual_end_time'] = datetime.fromisoformat(update_data['actual_end_time'])
    
    task = await project_service.update_project_task(db, task_id, update_data)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目任务不存在"
        )
    
    return {
        "status": 0,
        "msg": "项目任务更新成功",
        "data": task.dict()
    }

@router.delete("/tasks/{task_id}", response_model=Dict[str, Any])
async def delete_project_task(
    task_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """删除项目任务"""
    success = await project_service.delete_project_task(db, task_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目任务不存在"
        )
    
    return {
        "status": 0,
        "msg": "项目任务删除成功"
    }

# ==================== 项目成员相关 ====================

@router.post("/members", response_model=Dict[str, Any])
async def add_project_member(
    member_data: ProjectMemberAddRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """添加项目成员"""
    member = await project_service.add_project_member(db, member_data.dict())
    
    return {
        "status": 0,
        "msg": "项目成员添加成功",
        "data": member.dict()
    }

@router.get("/{project_id}/members", response_model=Dict[str, Any])
async def get_project_members(
    project_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """获取项目成员列表"""
    members = await project_service.get_project_members(db, project_id)
    
    return {
        "status": 0,
        "msg": "获取成功",
        "data": {
            "items": [member.dict() for member in members],
            "total": len(members)
        }
    }

@router.put("/members/{member_id}", response_model=Dict[str, Any])
async def update_project_member(
    member_id: int,
    member_data: ProjectMemberUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """更新项目成员"""
    update_data = member_data.dict(exclude_unset=True)
    
    member = await project_service.update_project_member(db, member_id, update_data)
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目成员不存在"
        )
    
    return {
        "status": 0,
        "msg": "项目成员更新成功",
        "data": member.dict()
    }

@router.delete("/members/{member_id}", response_model=Dict[str, Any])
async def remove_project_member(
    member_id: int,
    db: AsyncSession = Depends(get_async_db),
    current_user: Dict[str, Any] = Depends(get_current_active_user)
):
    """移除项目成员"""
    success = await project_service.remove_project_member(db, member_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="项目成员不存在"
        )
    
    return {
        "status": 0,
        "msg": "项目成员移除成功"
    }
