from sqlmodel import SQLModel, Field
from typing import Optional, List
from datetime import datetime
from pydantic import validator

# 项目基础模型
class ProjectBase(SQLModel):
    """项目基础模型"""
    name: str = Field(title="项目名称", min_length=1, max_length=200)
    description: str = Field(title="项目描述", default="")
    planned_start_time: datetime = Field(title="计划开始时间")
    planned_end_time: datetime = Field(title="计划结束时间")
    project_manager: Optional[int] = Field(title="项目负责人", nullable=True)
    amount: float = Field(title="项目金额", ge=0)
    status: str = Field(title="项目状态", default="pending", description="待开始、进行中、已完成、已暂停、已终止")
    contract_id: Optional[int] = Field(title="关联合同ID", nullable=True)
    
    @validator('planned_end_time')
    def planned_end_time_after_start_time(cls, v, values):
        if 'planned_start_time' in values and v <= values['planned_start_time']:
            raise ValueError('计划结束时间必须晚于计划开始时间')
        return v

class ProjectCreate(ProjectBase):
    """创建项目模型"""
    pass

class ProjectUpdate(SQLModel):
    """更新项目模型"""
    name: Optional[str] = Field(None, title="项目名称", min_length=1, max_length=200)
    description: Optional[str] = Field(None, title="项目描述")
    planned_start_time: Optional[datetime] = Field(None, title="计划开始时间")
    planned_end_time: Optional[datetime] = Field(None, title="计划结束时间")
    project_manager: Optional[int] = Field(None, title="项目负责人", nullable=True)
    amount: Optional[float] = Field(None, title="项目金额", ge=0)
    status: Optional[str] = Field(None, title="项目状态", description="待开始、进行中、已完成、已暂停、已终止")
    contract_id: Optional[int] = Field(None, title="关联合同ID", nullable=True)
    actual_start_time: Optional[datetime] = Field(None, title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(None, title="实际结束时间", nullable=True)

class ProjectRead(ProjectBase):
    """读取项目模型"""
    id: int
    actual_start_time: Optional[datetime] = Field(None, title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(None, title="实际结束时间", nullable=True)
    create_time: datetime
    update_time: datetime

# 批量导入项目模型
class ProjectBatchCreate(SQLModel):
    """批量创建项目模型"""
    projects: List[ProjectCreate] = Field(title="项目列表")

class ProjectBatchResult(SQLModel):
    """批量创建结果模型"""
    success_count: int = Field(title="成功数量")
    error_count: int = Field(title="错误数量")
    errors: List[dict] = Field(title="错误信息", default_factory=list)

# 项目阶段基础模型
class ProjectStageBase(SQLModel):
    """项目阶段基础模型"""
    project_id: int = Field(title="项目ID")
    name: str = Field(title="阶段名称", min_length=1, max_length=100)
    description: str = Field(title="阶段描述", default="")
    planned_start_time: datetime = Field(title="计划开始时间")
    planned_end_time: datetime = Field(title="计划结束时间")
    status: str = Field(title="阶段状态", default="pending", description="待开始、进行中、已完成、已暂停、已延期")
    
    @validator('planned_end_time')
    def planned_end_time_after_start_time(cls, v, values):
        if 'planned_start_time' in values and v <= values['planned_start_time']:
            raise ValueError('计划结束时间必须晚于计划开始时间')
        return v

class ProjectStageCreate(ProjectStageBase):
    """创建项目阶段模型"""
    pass

class ProjectStageUpdate(SQLModel):
    """更新项目阶段模型"""
    name: Optional[str] = Field(None, title="阶段名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, title="阶段描述")
    planned_start_time: Optional[datetime] = Field(None, title="计划开始时间")
    planned_end_time: Optional[datetime] = Field(None, title="计划结束时间")
    status: Optional[str] = Field(None, title="阶段状态", description="待开始、进行中、已完成、已暂停、已延期")
    actual_start_time: Optional[datetime] = Field(None, title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(None, title="实际结束时间", nullable=True)

class ProjectStageRead(ProjectStageBase):
    """读取项目阶段模型"""
    id: int
    actual_start_time: Optional[datetime] = Field(None, title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(None, title="实际结束时间", nullable=True)
    create_time: datetime
    update_time: datetime

# 批量导入项目阶段模型
class ProjectStageBatchCreate(SQLModel):
    """批量创建项目阶段模型"""
    stages: List[ProjectStageCreate] = Field(title="阶段列表")

class ProjectStageBatchResult(SQLModel):
    """批量创建结果模型"""
    success_count: int = Field(title="成功数量")
    error_count: int = Field(title="错误数量")
    errors: List[dict] = Field(title="错误信息", default_factory=list)

# 项目任务基础模型
class ProjectTaskBase(SQLModel):
    """项目任务基础模型"""
    stage_id: int = Field(title="阶段ID")
    name: str = Field(title="任务名称", min_length=1, max_length=100)
    description: str = Field(title="任务描述", default="")
    assignee: Optional[int] = Field(title="负责人", nullable=True)
    planned_start_time: datetime = Field(title="计划开始时间")
    planned_end_time: datetime = Field(title="计划结束时间")
    priority: str = Field(title="优先级", default="medium", description="低、中、高")
    status: str = Field(title="任务状态", default="pending", description="待开始、进行中、已暂停、已完成、已延期")
    progress: int = Field(title="任务进度", default=0, ge=0, le=100)
    
    @validator('planned_end_time')
    def planned_end_time_after_start_time(cls, v, values):
        if 'planned_start_time' in values and v <= values['planned_start_time']:
            raise ValueError('计划结束时间必须晚于计划开始时间')
        return v

class ProjectTaskCreate(ProjectTaskBase):
    """创建项目任务模型"""
    pass

class ProjectTaskUpdate(SQLModel):
    """更新项目任务模型"""
    name: Optional[str] = Field(None, title="任务名称", min_length=1, max_length=100)
    description: Optional[str] = Field(None, title="任务描述")
    assignee: Optional[int] = Field(None, title="负责人", nullable=True)
    planned_start_time: Optional[datetime] = Field(None, title="计划开始时间")
    planned_end_time: Optional[datetime] = Field(None, title="计划结束时间")
    priority: Optional[str] = Field(None, title="优先级", description="低、中、高")
    status: Optional[str] = Field(None, title="任务状态", description="待开始、进行中、已暂停、已完成、已延期")
    progress: Optional[int] = Field(None, title="任务进度", ge=0, le=100)
    actual_start_time: Optional[datetime] = Field(None, title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(None, title="实际结束时间", nullable=True)

class ProjectTaskRead(ProjectTaskBase):
    """读取项目任务模型"""
    id: int
    actual_start_time: Optional[datetime] = Field(None, title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(None, title="实际结束时间", nullable=True)
    create_time: datetime
    update_time: datetime

# 批量导入项目任务模型
class ProjectTaskBatchCreate(SQLModel):
    """批量创建项目任务模型"""
    tasks: List[ProjectTaskCreate] = Field(title="任务列表")

class ProjectTaskBatchResult(SQLModel):
    """批量创建结果模型"""
    success_count: int = Field(title="成功数量")
    error_count: int = Field(title="错误数量")
    errors: List[dict] = Field(title="错误信息", default_factory=list)

# 项目成员基础模型
class ProjectMemberBase(SQLModel):
    """项目成员基础模型"""
    project_id: int = Field(title="项目ID")
    employee_id: int = Field(title="员工ID")
    role: str = Field(title="角色", default="member", description="负责人、成员、观察者")
    permissions: str = Field(title="权限", default="view", description="view、edit、manage")

class ProjectMemberCreate(ProjectMemberBase):
    """创建项目成员模型"""
    pass

class ProjectMemberUpdate(SQLModel):
    """更新项目成员模型"""
    role: Optional[str] = Field(None, title="角色", description="负责人、成员、观察者")
    permissions: Optional[str] = Field(None, title="权限", description="view、edit、manage")

class ProjectMemberRead(ProjectMemberBase):
    """读取项目成员模型"""
    id: int
    join_time: datetime

# 批量导入项目成员模型
class ProjectMemberBatchCreate(SQLModel):
    """批量创建项目成员模型"""
    members: List[ProjectMemberCreate] = Field(title="成员列表")

class ProjectMemberBatchResult(SQLModel):
    """批量创建结果模型"""
    success_count: int = Field(title="成功数量")
    error_count: int = Field(title="错误数量")
    errors: List[dict] = Field(title="错误信息", default_factory=list)

# 项目文档基础模型
class ProjectDocumentBase(SQLModel):
    """项目文档基础模型"""
    project_id: int = Field(title="项目ID")
    name: str = Field(title="文档名称", min_length=1, max_length=200)
    category: str = Field(title="文档分类", max_length=50)
    file_path: str = Field(title="文件路径", max_length=500)
    file_size: int = Field(title="文件大小")
    version: str = Field(title="版本", default="1.0.0")
    uploader: int = Field(title="上传人")
    description: str = Field(title="文档描述", default="")

class ProjectDocumentCreate(ProjectDocumentBase):
    """创建项目文档模型"""
    pass

class ProjectDocumentUpdate(SQLModel):
    """更新项目文档模型"""
    name: Optional[str] = Field(None, title="文档名称", min_length=1, max_length=200)
    category: Optional[str] = Field(None, title="文档分类", max_length=50)
    file_path: Optional[str] = Field(None, title="文件路径", max_length=500)
    file_size: Optional[int] = Field(None, title="文件大小")
    version: Optional[str] = Field(None, title="版本")
    uploader: Optional[int] = Field(None, title="上传人")
    description: Optional[str] = Field(None, title="文档描述")

class ProjectDocumentRead(ProjectDocumentBase):
    """读取项目文档模型"""
    id: int
    upload_time: datetime

