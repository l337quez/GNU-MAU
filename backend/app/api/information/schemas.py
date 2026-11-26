from typing import Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Information Inputs DTOs
# ──────────────────────────────────────────────

class InformationCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Título del item de información")
    content: str = Field(..., min_length=1, description="Contenido o valor del item")
    category: str = Field(default="", description="Categoría libre (ej: 'git', 'docker', 'urls')")
    action: Optional[str] = Field(default=None, description="Acción a ejecutar: 'terminal', 'browser' o None")
    project_id: str = Field(..., min_length=1, description="ID del proyecto al que pertenece")
    encrypted: Optional[bool] = Field(default=False, description="Indica si el contenido está encriptado")


class InformationUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    category: Optional[str] = None
    action: Optional[str] = None
    project_id: Optional[str] = None
    encrypted: Optional[bool] = None


# ──────────────────────────────────────────────
# Information Output DTO
# ──────────────────────────────────────────────

class InformationResponse(BaseModel):
    id: str
    title: str
    content: str
    category: str
    action: Optional[str]
    project_id: Optional[str]
    encrypted: bool = False

    model_config = {"from_attributes": True}
