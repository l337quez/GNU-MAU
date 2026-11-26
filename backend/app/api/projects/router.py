from fastapi import APIRouter, Depends, status

from app.core.database import get_db
from app.api.projects.schemas import ProjectCreate, ProjectResponse, ProjectUpdate
from app.api.projects.repository import ProjectRepository
from app.api.projects.service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


def get_project_service(db=Depends(get_db)) -> ProjectService:
    """FastAPI Dependency Injection for the ProjectService."""
    repo = ProjectRepository(db)
    return ProjectService(repo)


# ────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────

@router.get("/", response_model=list[ProjectResponse], summary="Listar todos los proyectos")
def list_projects(service: ProjectService = Depends(get_project_service)):
    """Devuelve la lista completa de proyectos almacenados."""
    return service.get_all()


@router.get("/{project_id}", response_model=ProjectResponse, summary="Obtener un proyecto por ID")
def get_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """Devuelve un proyecto específico por su ID."""
    return service.get_by_id(project_id)


@router.post("/", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo proyecto")
def create_project(payload: ProjectCreate, service: ProjectService = Depends(get_project_service)):
    """Crea un proyecto nuevo con nombre, descripción e info opcional."""
    return service.create(payload)


@router.put("/{project_id}", response_model=ProjectResponse, summary="Actualizar un proyecto completo")
def update_project(project_id: str, payload: ProjectUpdate, service: ProjectService = Depends(get_project_service)):
    """
    Actualiza los campos de un proyecto existente.
    Solo se actualizan los campos que se envíen (PATCH semántico aunque use PUT).
    """
    return service.update(project_id, payload)


@router.patch("/{project_id}/icon", response_model=ProjectResponse, summary="Actualizar solo el icono del proyecto")
def update_project_icon(project_id: str, icon_path: str, service: ProjectService = Depends(get_project_service)):
    """Actualiza únicamente la ruta del icono/gif del proyecto."""
    return service.update_icon(project_id, icon_path)


@router.patch("/{project_id}/info", response_model=ProjectResponse, summary="Agregar o actualizar un info item")
def upsert_info_item(project_id: str, key: str, value: str, action: str | None = None, category: str = "", encrypted: bool = False, service: ProjectService = Depends(get_project_service)):
    """
    Agrega un nuevo par key/value al campo `info` del proyecto,
    o lo actualiza si ya existe.
    """
    return service.upsert_info(project_id, key, value, action, category, encrypted)


@router.delete("/{project_id}/info/{key}", response_model=ProjectResponse, summary="Eliminar un info item")
def delete_info_item(project_id: str, key: str, service: ProjectService = Depends(get_project_service)):
    """Elimina un par key/value específico del campo `info` del proyecto."""
    return service.delete_info(project_id, key)


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un proyecto")
def delete_project(project_id: str, service: ProjectService = Depends(get_project_service)):
    """Elimina permanentemente un proyecto y todos sus datos."""
    service.delete(project_id)
