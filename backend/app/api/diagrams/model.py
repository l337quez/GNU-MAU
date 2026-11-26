from pydantic import BaseModel, Field
from typing import List, Optional

class DiagramModel(BaseModel):
    """
    Modelo de Base de Datos para la validación de diagramas.
    """
    name: str
    project_id: str
    type: str = "Advanced Architecture"
    nodes: List[dict] = Field(default_factory=list)
    connections: List[dict] = Field(default_factory=list)
