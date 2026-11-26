from pydantic import BaseModel, Field
from typing import Dict, Optional

class InfoItemModel(BaseModel):
    value: str
    action: Optional[str] = None
    category: str = ""
    encrypted: bool = False

class ProjectModel(BaseModel):
    """
    Modelo de Base de Datos para el proyecto.
    Define estrictamente la forma del documento que se guarda en Mongita.
    """
    name: str
    description: str = ""
    icon_path: str = "assets/project_images/default_icon.png"
    info: Dict[str, InfoItemModel] = Field(default_factory=dict)
