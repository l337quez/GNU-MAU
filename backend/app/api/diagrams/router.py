from fastapi import APIRouter, Depends, status
from app.core.database import get_db
from app.api.diagrams.schemas import DiagramCreate, DiagramResponse, DiagramUpdate
from app.api.diagrams.repository import DiagramRepository
from app.api.diagrams.service import DiagramService

router = APIRouter(tags=["Diagrams"])

def get_diagram_service(db=Depends(get_db)) -> DiagramService:
    repo = DiagramRepository(db)
    return DiagramService(repo)

@router.post("/projects/{project_id}/diagrams", response_model=DiagramResponse, status_code=status.HTTP_201_CREATED, summary="Crear un nuevo diagrama para un proyecto")
def create_diagram(project_id: str, payload: DiagramCreate, service: DiagramService = Depends(get_diagram_service)):
    return service.create(project_id, payload)

@router.get("/projects/{project_id}/diagrams", response_model=list[DiagramResponse], summary="Listar todos los diagramas de un proyecto")
def list_project_diagrams(project_id: str, service: DiagramService = Depends(get_diagram_service)):
    return service.get_all_by_project(project_id)

@router.get("/diagrams/{diagram_id}", response_model=DiagramResponse, summary="Obtener el detalle de un diagrama por ID")
def get_diagram(diagram_id: str, service: DiagramService = Depends(get_diagram_service)):
    return service.get_by_id(diagram_id)

@router.put("/diagrams/{diagram_id}", response_model=DiagramResponse, summary="Actualizar un diagrama por ID")
def update_diagram(diagram_id: str, payload: DiagramUpdate, service: DiagramService = Depends(get_diagram_service)):
    return service.update(diagram_id, payload)

@router.delete("/diagrams/{diagram_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Eliminar un diagrama")
def delete_diagram(diagram_id: str, service: DiagramService = Depends(get_diagram_service)):
    service.delete(diagram_id)
