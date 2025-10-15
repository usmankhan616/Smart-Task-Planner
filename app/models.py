from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship
from datetime import datetime
from enum import Enum

class TaskStatus(str, Enum):
    SUBMITTED = "SUBMITTED"
    MANAGER_PENDING = "MANAGER_PENDING"
    MANAGER_APPROVED = "MANAGER_APPROVED"
    ADMIN_PENDING = "ADMIN_PENDING"
    ADMIN_APPROVED = "ADMIN_APPROVED"
    COMPLETED = "COMPLETED"
    REJECTED = "REJECTED"

class PlanRequest(SQLModel):
    goal: str

class Task(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    taskName: str
    description: str
    duration: str
    dependencies: str
    phase: str
    priority: str
    status: TaskStatus = Field(default=TaskStatus.SUBMITTED)
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    plan_id: Optional[int] = Field(default=None, foreign_key="plan.id")
    plan: Optional["Plan"] = Relationship(back_populates="tasks")
    
    progress_history: List["TaskProgress"] = Relationship(back_populates="task")

class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_goal: str
    created_at: Optional[datetime] = Field(default_factory=datetime.utcnow)
    
    tasks: List["Task"] = Relationship(back_populates="plan")
    
    owner_id: Optional[int] = Field(default=None, foreign_key="user.id")
    owner: Optional["User"] = Relationship(back_populates="plans")

class PlanResponse(SQLModel):
    plan: List[Task]

class TaskProgress(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    status: TaskStatus
    comment: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    task_id: Optional[int] = Field(default=None, foreign_key="task.id")
    task: Optional["Task"] = Relationship(back_populates="progress_history")

class User(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str
    
    plans: List["Plan"] = Relationship(back_populates="owner")
