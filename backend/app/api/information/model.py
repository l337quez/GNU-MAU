from pydantic import BaseModel, Field
from typing import Optional


class InformationModel(BaseModel):
    """
    Modelo de Base de Datos para un Information Item.
    Define estrictamente la forma del documento que se guarda en Mongita.
    """
    title: str
    content: str
    category: str = ""
    action: Optional[str] = None     # None | "terminal" | "browser"
    project_id: str                  # ID del proyecto vinculado
    encrypted: bool = False
