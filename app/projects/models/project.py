from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.contracts.models.contract import Contract
    from app.organization.models.person import Person

# 项目模型
class Project(SQLModel, table=True):
    """项目模型"""
    __tablename__ = "projects"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    name: str = Field(title="项目名称", min_length=1, max_length=200)
    description: str = Field(title="项目描述", default="")
    planned_start_time: datetime = Field(title="计划开始时间")
    planned_end_time: datetime = Field(title="计划结束时间")
    actual_start_time: Optional[datetime] = Field(title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(title="实际结束时间", nullable=True)
    project_manager: Optional[int] = Field(title="项目负责人", foreign_key="persons.id", nullable=True)
    amount: float = Field(title="项目金额", ge=0)
    status: str = Field(title="项目状态", default="pending", description="待开始、进行中、已完成、已暂停、已终止")
    contract_id: Optional[int] = Field(title="关联合同ID", foreign_key="contracts.id", nullable=True)
    create_time: datetime = Field(default_factory=datetime.now, title="创建时间")
    update_time: datetime = Field(default_factory=datetime.now, title="更新时间")
    
    # 关系
    manager: Optional["Person"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "Project.project_manager == Person.id"
        }
    )
    stages: List["ProjectStage"] = Relationship(back_populates="project")
    members: List["ProjectMember"] = Relationship(back_populates="project")
    documents: List["ProjectDocument"] = Relationship(back_populates="project")

# 项目阶段模型
class ProjectStage(SQLModel, table=True):
    """项目阶段模型"""
    __tablename__ = "project_stages"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    project_id: int = Field(title="项目ID", foreign_key="projects.id")
    name: str = Field(title="阶段名称", min_length=1, max_length=100)
    description: str = Field(title="阶段描述", default="")
    planned_start_time: datetime = Field(title="计划开始时间")
    planned_end_time: datetime = Field(title="计划结束时间")
    actual_start_time: Optional[datetime] = Field(title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(title="实际结束时间", nullable=True)
    status: str = Field(title="阶段状态", default="pending", description="待开始、进行中、已完成、已暂停、已延期")
    create_time: datetime = Field(default_factory=datetime.now, title="创建时间")
    update_time: datetime = Field(default_factory=datetime.now, title="更新时间")
    
    # 关系
    project: Project = Relationship(back_populates="stages")
    tasks: List["ProjectTask"] = Relationship(back_populates="stage")

# 项目任务模型
class ProjectTask(SQLModel, table=True):
    """项目任务模型"""
    __tablename__ = "project_tasks"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    stage_id: int = Field(title="阶段ID", foreign_key="project_stages.id")
    name: str = Field(title="任务名称", min_length=1, max_length=100)
    description: str = Field(title="任务描述", default="")
    assignee: Optional[int] = Field(title="负责人", foreign_key="auth_user.id", nullable=True)
    planned_start_time: datetime = Field(title="计划开始时间")
    planned_end_time: datetime = Field(title="计划结束时间")
    actual_start_time: Optional[datetime] = Field(title="实际开始时间", nullable=True)
    actual_end_time: Optional[datetime] = Field(title="实际结束时间", nullable=True)
    priority: str = Field(title="优先级", default="medium", description="低、中、高")
    status: str = Field(title="任务状态", default="pending", description="待开始、进行中、已暂停、已完成、已延期")
    progress: int = Field(title="任务进度", default=0, ge=0, le=100)
    create_time: datetime = Field(default_factory=datetime.now, title="创建时间")
    update_time: datetime = Field(default_factory=datetime.now, title="更新时间")
    
    # 关系
    stage: ProjectStage = Relationship(back_populates="tasks")
    assignee_user: Optional["User"] = Relationship(back_populates="assigned_tasks")

# 项目成员模型
class ProjectMember(SQLModel, table=True):
    """项目成员模型"""
    __tablename__ = "project_members"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    project_id: int = Field(title="项目ID", foreign_key="projects.id")
    employee_id: Optional[int] = Field(default=None, title="员工ID", foreign_key="persons.id", nullable=True)
    role: str = Field(title="角色", default="member", description="负责人、成员、观察者")
    permissions: str = Field(title="权限", default="view", description="view、edit、manage")
    join_time: datetime = Field(default_factory=datetime.now, title="加入时间")
    
    # 关系
    project: Project = Relationship(back_populates="members")
    employee: Optional["Person"] = Relationship(
        sa_relationship_kwargs={
            "primaryjoin": "ProjectMember.employee_id == Person.id"
        }
    )

# 项目文档模型
class ProjectDocument(SQLModel, table=True):
    """项目文档模型"""
    __tablename__ = "project_documents"
    
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    project_id: int = Field(title="项目ID", foreign_key="projects.id")
    name: str = Field(title="文档名称", min_length=1, max_length=200)
    category: str = Field(title="文档分类", max_length=50)
    file_path: str = Field(title="文件路径", max_length=500)
    file_size: int = Field(title="文件大小")
    version: str = Field(title="版本", default="1.0.0")
    uploader: int = Field(title="上传人", foreign_key="auth_user.id")
    upload_time: datetime = Field(default_factory=datetime.now, title="上传时间")
    description: str = Field(title="文档描述", default="")
    
    # 关系
    project: Project = Relationship(back_populates="documents")
    uploader_user: "User" = Relationship()


