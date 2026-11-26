from fastapi import APIRouter, Depends, status

from app.core.database import get_db
from app.api.todos.schemas import TodoCreate, TodoResponse, TodoUpdate
from app.api.todos.repository import TodoRepository
from app.api.todos.service import TodoService


router = APIRouter(tags=["Todos"])


def get_todo_service(db=Depends(get_db)) -> TodoService:
    """
    FastAPI Dependency Injection helper to instantiate the TodoService.
    """
    repo = TodoRepository(db)
    return TodoService(repo)


@router.post(
    "/projects/{project_id}/todos",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear un nuevo TODO para un proyecto"
)
def create_todo(
    project_id: str,
    payload: TodoCreate,
    service: TodoService = Depends(get_todo_service)
):
    """
    Creates a new TODO list associated with the given project.
    """
    return service.create(project_id, payload)


@router.get(
    "/projects/{project_id}/todos",
    response_model=list[TodoResponse],
    summary="Listar todos los TODOs de un proyecto"
)
def list_project_todos(
    project_id: str,
    service: TodoService = Depends(get_todo_service)
):
    """
    Returns all TODO lists associated with a specific project.
    """
    return service.get_all_by_project(project_id)


@router.get(
    "/todos/{todo_id}",
    response_model=TodoResponse,
    summary="Obtener el detalle de un TODO por ID"
)
def get_todo(
    todo_id: str,
    service: TodoService = Depends(get_todo_service)
):
    """
    Returns the details of a single TODO list by ID.
    """
    return service.get_by_id(todo_id)


@router.put(
    "/todos/{todo_id}",
    response_model=TodoResponse,
    summary="Actualizar un TODO por ID"
)
def update_todo(
    todo_id: str,
    payload: TodoUpdate,
    service: TodoService = Depends(get_todo_service)
):
    """
    Updates an existing TODO list by ID.
    """
    return service.update(todo_id, payload)


@router.delete(
    "/todos/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un TODO"
)
def delete_todo(
    todo_id: str,
    service: TodoService = Depends(get_todo_service)
):
    """
    Permanently deletes a TODO list.
    """
    service.delete(todo_id)
