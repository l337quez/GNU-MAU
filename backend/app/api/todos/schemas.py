from pydantic import BaseModel, Field
from typing import Optional


class TodoCreate(BaseModel):
    """
    Schema for creating a TODO list.
    """
    title: str = Field(..., min_length=1, description="Title of the TODO list")
    content: Optional[str] = Field(default="☐ My first task", description="Markdown content of the TODO list")


class TodoUpdate(BaseModel):
    """
    Schema for updating a TODO list.
    """
    title: Optional[str] = Field(default=None, description="Title of the TODO list")
    content: Optional[str] = Field(default=None, description="Markdown content of the TODO list")


class TodoResponse(BaseModel):
    """
    Schema for returning TODO list details.
    """
    id: str
    project_id: str
    title: str
    content: str

    model_config = {"from_attributes": True}
