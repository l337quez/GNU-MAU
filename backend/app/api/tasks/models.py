from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class TaskModel(BaseModel):
    """
    Modelo de base de datos para una Tarea (Jira-style).
    """
    project_id: str
    title: str
    description: str = ""
    creator_username: str
    assignee_username: Optional[str] = None
    status: str = "todo" # 'todo', 'in_progress', 'review', 'done'
    priority: str = "medium" # 'low', 'medium', 'high', 'urgent'
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
