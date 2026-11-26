from fastapi import APIRouter, Depends, status
from typing import List
from app.api.tasks.schemas import TaskCreate, TaskUpdate, TaskResponse
from app.api.tasks.service import TaskService
from app.api.auth.guards import get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/projects/{project_id}/tasks", tags=["Tasks"])

def get_task_service(db = Depends(get_db)) -> TaskService:
    return TaskService(db)

@router.post(
    "/",
    response_model=TaskResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new task"
)
def create_task(
    project_id: str,
    payload: TaskCreate,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Crea una nueva tarea en el proyecto y asume al usuario actual como creador.
    """
    return task_service.create_task(project_id, "admin", payload)

@router.get(
    "/",
    response_model=List[TaskResponse],
    status_code=status.HTTP_200_OK,
    summary="Get all tasks for a project"
)
def get_tasks(
    project_id: str,
    assignee_username: str = None,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Obtiene todas las tareas asociadas a un proyecto. Permite filtrar por asignado.
    """
    return task_service.get_tasks(project_id, assignee_username)

@router.put(
    "/{task_id}",
    response_model=TaskResponse,
    status_code=status.HTTP_200_OK,
    summary="Update a task"
)
def update_task(
    project_id: str,
    task_id: str,
    payload: TaskUpdate,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Actualiza una tarea existente (estado, asignación, prioridad, etc).
    """
    return task_service.update_task(project_id, task_id, payload)

@router.delete(
    "/{task_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a task"
)
def delete_task(
    project_id: str,
    task_id: str,
    task_service: TaskService = Depends(get_task_service)
):
    """
    Elimina una tarea del proyecto.
    """
    return task_service.delete_task(project_id, task_id)
