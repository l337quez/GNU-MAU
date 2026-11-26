from pydantic import BaseModel, Field
from typing import Optional, Literal
from datetime import datetime

class TaskBase(BaseModel):
    title: str = Field(..., min_length=1)
    description: Optional[str] = ""
    assignee_username: Optional[str] = None
    status: Literal["todo", "in_progress", "review", "done"] = "todo"
    priority: Literal["low", "medium", "high", "urgent"] = "medium"

class TaskCreate(TaskBase):
    pass

class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    assignee_username: Optional[str] = None
    status: Optional[Literal["todo", "in_progress", "review", "done"]] = None
    priority: Optional[Literal["low", "medium", "high", "urgent"]] = None

class TaskResponse(TaskBase):
    id: str
    project_id: str
    creator_username: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
