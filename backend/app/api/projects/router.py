from typing import Annotated

from bson.objectid import ObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.core.database import get_db
from app.api.projects.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.api.projects.repository import ProjectRepository
from app.shared.helpers import serialize_project, get_project_or_404, DEFAULT_ICON

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_project_repository(db=Depends(get_db)) -> ProjectRepository:
    """FastAPI Dependency Injection for the ProjectRepository."""
    return ProjectRepository(db)


# ────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────

@router.get("/", response_model=list[ProjectResponse], summary="Listar todos los proyectos")
def list_projects(repo: ProjectRepository = Depends(get_project_repository)):
    """Devuelve la lista completa de proyectos almacenados."""
    projects = repo.get_all()
    return [ProjectResponse(**serialize_project(p)) for p in projects]


@router.get("/{project_id}", response_model=ProjectResponse, summary="Obtener un proyecto por ID")
def get_project(project_id: str, repo: ProjectRepository = Depends(get_project_repository)):
    """Devuelve un proyecto específico por su ID."""
    project = get_project_or_404(repo, project_id)
    return ProjectResponse(**serialize_project(project))


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo proyecto")
def create_project(payload: ProjectCreate, repo: ProjectRepository = Depends(get_project_repository)):
    """Crea un proyecto nuevo con nombre, descripción e info opcional."""
    info_dict = {k: v.model_dump() for k, v in payload.info.items()} if payload.info else {}
    doc = repo.create(
        name=payload.name,
        description=payload.description,
        icon_path=payload.icon_path or DEFAULT_ICON,
        info=info_dict
    )
    return ProjectResponse(**serialize_project(doc))


@router.put("/{project_id}", response_model=ProjectResponse, summary="Actualizar un proyecto completo")
def update_project(project_id: str, payload: ProjectUpdate, repo: ProjectRepository = Depends(get_project_repository)):
    """
    Actualiza los campos de un proyecto existente.
    Solo se actualizan los campos que se envíen (PATCH semántico aunque use PUT).
    """
    get_project_or_404(repo, project_id)  # Valida existencia

    update_data: dict = {}
    if payload.name is not None:
        update_data["name"] = payload.name
    if payload.description is not None:
        update_data["description"] = payload.description
    if payload.icon_path is not None:
        update_data["icon_path"] = payload.icon_path
    if payload.info is not None:
        update_data["info"] = {k: v.model_dump() for k, v in payload.info.items()}

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se enviaron campos para actualizar")

    updated = repo.update_metadata(project_id, update_data)
    return ProjectResponse(**serialize_project(updated))


@router.patch("/{project_id}/icon", response_model=ProjectResponse, summary="Actualizar solo el icono del proyecto")
def update_project_icon(project_id: str, icon_path: str, repo: ProjectRepository = Depends(get_project_repository)):
    """Actualiza únicamente la ruta del icono/gif del proyecto."""
    get_project_or_404(repo, project_id)
    updated = repo.update_icon(project_id, icon_path)
    return ProjectResponse(**serialize_project(updated))


@router.patch("/{project_id}/info", response_model=ProjectResponse, summary="Agregar o actualizar un info item")
def upsert_info_item(project_id: str, key: str, value: str, action: str | None = None, category: str = "", repo: ProjectRepository = Depends(get_project_repository)):
    """
    Agrega un nuevo par key/value al campo `info` del proyecto,
    o lo actualiza si ya existe.
    """
    get_project_or_404(repo, project_id)
    updated = repo.upsert_info(project_id, key, value, action, category)
    return ProjectResponse(**serialize_project(updated))


@router.delete("/{project_id}/info/{key}", response_model=ProjectResponse, summary="Eliminar un info item")
def delete_info_item(project_id: str, key: str, repo: ProjectRepository = Depends(get_project_repository)):
    """Elimina un par key/value específico del campo `info` del proyecto."""
    project = get_project_or_404(repo, project_id)
    info = project.get("info", {})
    if key not in info:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"La key '{key}' no existe en este proyecto")
    updated = repo.delete_info(project_id, key)
    return ProjectResponse(**serialize_project(updated))


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un proyecto")
def delete_project(project_id: str, repo: ProjectRepository = Depends(get_project_repository)):
    """Elimina permanentemente un proyecto y todos sus datos."""
    get_project_or_404(repo, project_id)
    repo.delete_by_id(project_id)
