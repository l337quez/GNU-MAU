from typing import Optional
from fastapi import APIRouter, Depends, status

from app.core.database import get_db
from app.api.information.schemas import InformationCreate, InformationResponse, InformationUpdate
from app.api.information.repository import InformationRepository
from app.api.information.service import InformationService

router = APIRouter(prefix="/information", tags=["Information"])


def get_information_service(db=Depends(get_db)) -> InformationService:
    """FastAPI Dependency Injection for InformationService."""
    repo = InformationRepository(db)
    return InformationService(repo)


# ────────────────────────────────────────────────────
# Endpoints
# ────────────────────────────────────────────────────

@router.get(
    "/",
    response_model=list[InformationResponse],
    summary="Listar todos los information items",
)
def list_information(
    project_id: Optional[str] = None,
    service: InformationService = Depends(get_information_service),
):
    """
    Return all information items.
    Optionally, you can filter by `project_id` to see only the items of a project.
    """
    return service.get_all(project_id=project_id)


@router.get(
    "/project/{project_id}",
    response_model=list[InformationResponse],
    summary="Listar todos los information items de un proyecto",
)
def list_project_information(
    project_id: str,
    service: InformationService = Depends(get_information_service),
):
    """
    Return all information items belonging to the specified project ID.
    """
    return service.get_all(project_id=project_id)


@router.get(
    "/{item_id}",
    response_model=InformationResponse,
    summary="Get an information item by ID",
)
def get_information(item_id: str, service: InformationService = Depends(get_information_service)):
    """Return a specific information item by its ID."""
    return service.get_by_id(item_id)


@router.post(
    "/",
    response_model=InformationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new information item",
)
def create_information(payload: InformationCreate, service: InformationService = Depends(get_information_service)):
    """
    Create a new information item. It can be optionally linked to a project via `project_id`.
    The `action` field can be `terminal`, `browser` or `null`.
    """
    return service.create(payload)


@router.put(
    "/{item_id}",
    response_model=InformationResponse,
    summary="Update an information item",
)
def update_information(item_id: str, payload: InformationUpdate, service: InformationService = Depends(get_information_service)):
    """
    Update the fields of an existing information item.
    Only the fields that are sent are updated.
    """
    return service.update(item_id, payload)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an information item",
)
def delete_information(item_id: str, service: InformationService = Depends(get_information_service)):
    """Permanently delete an information item."""
    service.delete(item_id)
