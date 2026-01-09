from typing import Optional, List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from ..models.project import (
    Project, ProjectStage, ProjectTask,
    ProjectMember, ProjectDocument
)
from datetime import datetime

class ProjectService:
    """项目服务"""
    
    # ==================== 项目基础操作 ====================
    
    async def create_project(self, db: AsyncSession, project_data: Dict[str, Any]) -> Project:
        """创建项目"""
        project = Project(**project_data)
        db.add(project)
        await db.commit()
        await db.refresh(project)
        return project
    
    async def get_project_by_id(self, db: AsyncSession, project_id: int) -> Optional[Project]:
        """通过ID获取项目"""
        result = await db.execute(select(Project).where(Project.id == project_id))
        return result.scalar_one_or_none()
    
    async def get_projects(self, db: AsyncSession, skip: int = 0, limit: int = 100, filters: Dict[str, Any] = None) -> List[Project]:
        """获取项目列表"""
        query = select(Project)
        
        # 应用过滤条件
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(Project, key):
                    query = query.where(getattr(Project, key) == value)
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def update_project(self, db: AsyncSession, project_id: int, project_data: Dict[str, Any]) -> Optional[Project]:
        """更新项目"""
        # 更新时间
        project_data["update_time"] = datetime.now()
        
        result = await db.execute(
            update(Project)
            .where(Project.id == project_id)
            .values(**project_data)
            .returning(Project)
        )
        
        await db.commit()
        return result.scalar_one_or_none()
    
    async def delete_project(self, db: AsyncSession, project_id: int) -> bool:
        """删除项目"""
        result = await db.execute(delete(Project).where(Project.id == project_id))
        await db.commit()
        return result.rowcount > 0
    
    async def quick_copy_project(self, db: AsyncSession, project_id: int, custom_data: Dict[str, Any] = None) -> Dict[str, Any]:
        """快速复制项目
        
        Args:
            db: 数据库会话
            project_id: 原项目ID
            custom_data: 自定义项目数据（用于覆盖原项目信息）
            
        Returns:
            Dict: 包含新项目ID的响应数据
        """
        # 获取原项目信息
        original_project = await self.get_project_by_id(db, project_id)
        if not original_project:
            raise ValueError(f"项目ID {project_id} 不存在")
        
        # 生成新项目名称
        new_name = custom_data.get('name', f"{original_project.name}（副本）") if custom_data else f"{original_project.name}（副本）"
        
        # 创建新项目数据
        new_project_data = {
            "name": new_name,
            "description": custom_data.get('description') if custom_data and custom_data.get('description') else original_project.description,
            "planned_start_time": custom_data.get('planned_start_time') if custom_data and custom_data.get('planned_start_time') else original_project.planned_start_time,
            "planned_end_time": custom_data.get('planned_end_time') if custom_data and custom_data.get('planned_end_time') else original_project.planned_end_time,
            "project_manager": custom_data.get('project_manager') if custom_data and custom_data.get('project_manager') else original_project.project_manager,
            "amount": custom_data.get('amount') if custom_data and custom_data.get('amount') else original_project.amount,
            "status": "pending",
            "contract_id": custom_data.get('contract_id') if custom_data and custom_data.get('contract_id') else original_project.contract_id,
            "create_time": datetime.now(),
            "update_time": datetime.now()
        }
        
        # 创建新项目
        new_project = Project(**new_project_data)
        db.add(new_project)
        await db.flush()
        await db.refresh(new_project)
        
        # 复制项目阶段
        original_stages = await self.get_project_stages(db, project_id)
        stage_mapping = {}
        new_stages = []
        
        # 先创建所有阶段
        for stage in original_stages:
            new_stage = ProjectStage(
                project_id=new_project.id,
                name=stage.name,
                description=stage.description,
                planned_start_time=stage.planned_start_time,
                planned_end_time=stage.planned_end_time,
                status="pending",
                create_time=datetime.now(),
                update_time=datetime.now()
            )
            db.add(new_stage)
            new_stages.append((stage, new_stage))
        
        # 批量flush获取阶段ID
        await db.flush()
        
        # 建立阶段ID映射
        for stage, new_stage in new_stages:
            stage_mapping[stage.id] = new_stage.id
        
        # 批量创建所有任务
        for stage, new_stage in new_stages:
            original_tasks = await self.get_project_tasks(db, stage.id)
            for task in original_tasks:
                new_task = ProjectTask(
                    stage_id=new_stage.id,
                    name=task.name,
                    description=task.description,
                    assignee=task.assignee,
                    planned_start_time=task.planned_start_time,
                    planned_end_time=task.planned_end_time,
                    priority=task.priority,
                    status="pending",
                    progress=0,
                    create_time=datetime.now(),
                    update_time=datetime.now()
                )
                db.add(new_task)
        
        # 提交事务
        await db.commit()
        
        return {
            "new_id": new_project.id,
            "new_name": new_project.name,
            "original_project_name": original_project.name
        }
    
    async def batch_delete_projects(self, db: AsyncSession, project_ids: List[int]) -> Dict[str, Any]:
        """批量删除项目
        
        Args:
            db: 数据库会话
            project_ids: 项目ID列表
            
        Returns:
            Dict: 包含删除成功和失败数量的结果
        """
        success_count = 0
        failed_ids = []
        
        # 先查询哪些ID存在
        existing_stmt = select(Project.id).where(Project.id.in_(project_ids))
        existing_result = await db.execute(existing_stmt)
        existing_ids = [row[0] for row in existing_result.fetchall()]
        
        # 不存在的ID就是失败的ID
        failed_ids = [pid for pid in project_ids if pid not in existing_ids]
        
        # 删除存在的项目及其相关数据
        if existing_ids:
            # 删除项目文档（包括物理文件）
            doc_stmt = select(ProjectDocument).where(ProjectDocument.project_id.in_(existing_ids))
            doc_result = await db.execute(doc_stmt)
            documents = doc_result.scalars().all()
            
            for document in documents:
                # 删除物理文件
                import os
                if document.file_path and os.path.exists(document.file_path):
                    try:
                        os.remove(document.file_path)
                    except Exception as e:
                        pass  # 忽略删除文件失败
            
            # 删除项目文档记录
            doc_delete_stmt = delete(ProjectDocument).where(ProjectDocument.project_id.in_(existing_ids))
            await db.execute(doc_delete_stmt)
            
            # 删除项目阶段任务
            task_stmt = delete(ProjectTask).where(
                ProjectTask.stage_id.in_(
                    select(ProjectStage.id).where(ProjectStage.project_id.in_(existing_ids))
                )
            )
            await db.execute(task_stmt)
            
            # 删除项目阶段
            stage_stmt = delete(ProjectStage).where(ProjectStage.project_id.in_(existing_ids))
            await db.execute(stage_stmt)
            
            # 删除项目成员
            member_stmt = delete(ProjectMember).where(ProjectMember.project_id.in_(existing_ids))
            await db.execute(member_stmt)
            

            
            # 删除项目本身
            delete_stmt = delete(Project).where(Project.id.in_(existing_ids))
            await db.execute(delete_stmt)
            
            # 认为删除成功（因为我们已经验证了这些ID存在）
            success_count = len(existing_ids)
        
        # 提交事务
        await db.commit()
        
        return {
            "success_count": success_count,
            "failed_count": len(failed_ids),
            "failed_ids": failed_ids
        }
    
    # ==================== 项目阶段操作 ====================
    
    async def create_project_stage(self, db: AsyncSession, stage_data: Dict[str, Any]) -> ProjectStage:
        """创建项目阶段"""
        stage = ProjectStage(**stage_data)
        db.add(stage)
        await db.commit()
        await db.refresh(stage)
        return stage
    
    async def get_project_stages(self, db: AsyncSession, project_id: int) -> List[ProjectStage]:
        """获取项目阶段列表"""
        result = await db.execute(
            select(ProjectStage)
            .where(ProjectStage.project_id == project_id)
            .order_by(ProjectStage.id)
        )
        return result.scalars().all()
    
    async def update_project_stage(self, db: AsyncSession, stage_id: int, stage_data: Dict[str, Any]) -> Optional[ProjectStage]:
        """更新项目阶段"""
        # 更新时间
        stage_data["update_time"] = datetime.now()
        
        result = await db.execute(
            update(ProjectStage)
            .where(ProjectStage.id == stage_id)
            .values(**stage_data)
            .returning(ProjectStage)
        )
        
        await db.commit()
        return result.scalar_one_or_none()
    
    async def delete_project_stage(self, db: AsyncSession, stage_id: int) -> bool:
        """删除项目阶段"""
        result = await db.execute(delete(ProjectStage).where(ProjectStage.id == stage_id))
        await db.commit()
        return result.rowcount > 0
    
    # ==================== 项目任务操作 ====================
    
    async def create_project_task(self, db: AsyncSession, task_data: Dict[str, Any]) -> ProjectTask:
        """创建项目任务"""
        task = ProjectTask(**task_data)
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task
    
    async def get_project_tasks(self, db: AsyncSession, stage_id: int) -> List[ProjectTask]:
        """获取项目阶段任务列表"""
        result = await db.execute(
            select(ProjectTask)
            .where(ProjectTask.stage_id == stage_id)
            .order_by(ProjectTask.id)
        )
        return result.scalars().all()
    
    async def update_project_task(self, db: AsyncSession, task_id: int, task_data: Dict[str, Any]) -> Optional[ProjectTask]:
        """更新项目任务"""
        # 更新时间
        task_data["update_time"] = datetime.now()
        
        result = await db.execute(
            update(ProjectTask)
            .where(ProjectTask.id == task_id)
            .values(**task_data)
            .returning(ProjectTask)
        )
        
        await db.commit()
        return result.scalar_one_or_none()
    
    async def delete_project_task(self, db: AsyncSession, task_id: int) -> bool:
        """删除项目任务"""
        result = await db.execute(delete(ProjectTask).where(ProjectTask.id == task_id))
        await db.commit()
        return result.rowcount > 0
    
    # ==================== 项目成员操作 ====================
    
    async def add_project_member(self, db: AsyncSession, member_data: Dict[str, Any]) -> ProjectMember:
        """添加项目成员"""
        member = ProjectMember(**member_data)
        db.add(member)
        await db.commit()
        await db.refresh(member)
        return member
    
    async def get_project_members(self, db: AsyncSession, project_id: int) -> List[ProjectMember]:
        """获取项目成员列表"""
        result = await db.execute(
            select(ProjectMember)
            .where(ProjectMember.project_id == project_id)
            .order_by(ProjectMember.id)
        )
        return result.scalars().all()
    
    async def update_project_member(self, db: AsyncSession, member_id: int, member_data: Dict[str, Any]) -> Optional[ProjectMember]:
        """更新项目成员"""
        result = await db.execute(
            update(ProjectMember)
            .where(ProjectMember.id == member_id)
            .values(**member_data)
            .returning(ProjectMember)
        )
        
        await db.commit()
        return result.scalar_one_or_none()
    
    async def remove_project_member(self, db: AsyncSession, member_id: int) -> bool:
        """移除项目成员"""
        result = await db.execute(delete(ProjectMember).where(ProjectMember.id == member_id))
        await db.commit()
        return result.rowcount > 0
    
    # ==================== 项目文档操作 ====================
    
    async def upload_project_document(self, db: AsyncSession, doc_data: Dict[str, Any]) -> ProjectDocument:
        """上传项目文档"""
        document = ProjectDocument(**doc_data)
        db.add(document)
        await db.commit()
        await db.refresh(document)
        return document
    
    async def get_project_documents(self, db: AsyncSession, project_id: int) -> List[ProjectDocument]:
        """获取项目文档列表"""
        result = await db.execute(
            select(ProjectDocument)
            .where(ProjectDocument.project_id == project_id)
            .order_by(ProjectDocument.upload_time.desc())
        )
        return result.scalars().all()
    
    async def update_project_document(self, db: AsyncSession, doc_id: int, doc_data: Dict[str, Any]) -> Optional[ProjectDocument]:
        """更新项目文档"""
        result = await db.execute(
            update(ProjectDocument)
            .where(ProjectDocument.id == doc_id)
            .values(**doc_data)
            .returning(ProjectDocument)
        )
        
        await db.commit()
        return result.scalar_one_or_none()
    
    async def delete_project_document(self, db: AsyncSession, doc_id: int) -> bool:
        """删除项目文档"""
        result = await db.execute(delete(ProjectDocument).where(ProjectDocument.id == doc_id))
        await db.commit()
        return result.rowcount > 0
    

    
    # ==================== 统计相关 ====================
    
    async def get_project_count(self, db: AsyncSession, filters: Dict[str, Any] = None) -> int:
        """获取项目总数"""
        query = select(func.count(Project.id))
        
        if filters:
            for key, value in filters.items():
                if value is not None and hasattr(Project, key):
                    query = query.where(getattr(Project, key) == value)
        
        result = await db.execute(query)
        return result.scalar()
    
    async def get_project_stats(self, db: AsyncSession, project_id: int) -> Dict[str, Any]:
        """获取项目统计信息"""
        # 项目基本信息
        project = await self.get_project_by_id(db, project_id)
        if not project:
            return None
        
        # 统计项目阶段数
        stages_count = await db.execute(
            select(func.count(ProjectStage.id)).where(ProjectStage.project_id == project_id)
        )
        
        # 统计项目任务数
        tasks_count = await db.execute(
            select(func.count(ProjectTask.id)).join(ProjectStage)
            .where(ProjectStage.project_id == project_id)
        )
        
        # 统计已完成任务数
        completed_tasks_count = await db.execute(
            select(func.count(ProjectTask.id)).join(ProjectStage)
            .where(ProjectStage.project_id == project_id)
            .where(ProjectTask.status == "completed")
        )
        
        # 统计项目成员数
        members_count = await db.execute(
            select(func.count(ProjectMember.id)).where(ProjectMember.project_id == project_id)
        )
        
        # 统计项目文档数
        documents_count = await db.execute(
            select(func.count(ProjectDocument.id)).where(ProjectDocument.project_id == project_id)
        )
        
        return {
            "project_id": project_id,
            "name": project.name,
            "status": project.status,
            "stages_count": stages_count.scalar(),
            "tasks_count": tasks_count.scalar(),
            "completed_tasks_count": completed_tasks_count.scalar(),
            "members_count": members_count.scalar(),
            "documents_count": documents_count.scalar(),
            "create_time": project.create_time,
            "update_time": project.update_time
        }

# 创建项目服务实例
project_service = ProjectService()
