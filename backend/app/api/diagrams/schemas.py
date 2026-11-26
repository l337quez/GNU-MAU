from pydantic import BaseModel, Field
from typing import List, Optional

class DiagramCreate(BaseModel):
    name: str = Field(..., description="Nombre del diagrama")
    type: Optional[str] = "Advanced Architecture"
    nodes: Optional[List[dict]] = []
    connections: Optional[List[dict]] = []

class DiagramUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[str] = None
    nodes: Optional[List[dict]] = None
    connections: Optional[List[dict]] = None

class DiagramResponse(BaseModel):
    id: str
    project_id: str
    name: str
    type: str
    nodes: List[dict] = []
    connections: List[dict] = []

    model_config = {"from_attributes": True}
