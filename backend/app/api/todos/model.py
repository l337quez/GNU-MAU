from pydantic import BaseModel, Field


class TodoModel(BaseModel):
    """
    Database validation model for TODO items.
    """
    title: str = Field(..., description="Title of the TODO list")
    content: str = Field(default="☐ My first task", description="Markdown content of the TODO list")
    project_id: str = Field(..., description="The ID of the parent project")
