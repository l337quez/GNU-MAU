from typing import Optional
from pydantic import BaseModel, Field


# ──────────────────────────────────────────────
# Info Item: cada par key/value dentro de un proyecto
# ──────────────────────────────────────────────
class InfoItem(BaseModel):
    value: str
    action: Optional[str] = None   # None | "terminal" | "browser"
    category: Optional[str] = ""


# ──────────────────────────────────────────────
# Project Schemas
# ──────────────────────────────────────────────
class ProjectCreate(BaseModel):
    name: str = Field(..., min_length=1, description="Nombre del proyecto")
    description: str = Field(default="", description="Descripción del proyecto")
    icon_path: Optional[str] = "assets/project_images/default_icon.png"
    info: Optional[dict[str, InfoItem]] = {}


class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    icon_path: Optional[str] = None
    info: Optional[dict[str, InfoItem]] = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    icon_path: str
    info: dict[str, InfoItem] = {}

    model_config = {"from_attributes": True}
