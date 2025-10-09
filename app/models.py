from typing import List, Optional
from sqlmodel import Field, SQLModel, Relationship

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
    
    plan_id: Optional[int] = Field(default=None, foreign_key="plan.id")
    plan: Optional["Plan"] = Relationship(back_populates="tasks")

class Plan(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_goal: str
    
    tasks: List["Task"] = Relationship(back_populates="plan")

class PlanResponse(SQLModel):
    plan: List[Task]