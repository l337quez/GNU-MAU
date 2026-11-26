from typing import List
from bson import ObjectId
from fastapi import HTTPException, status

from app.api.todos.schemas import TodoCreate, TodoUpdate, TodoResponse
from app.api.todos.model import TodoModel
from app.api.todos.repository import TodoRepository


class TodoService:
    """
    Service to handle business logic for TODO items.
    """
    def __init__(self, repo: TodoRepository):
        self.repo = repo

    def _serialize(self, doc: dict) -> dict:
        """
        Convert raw database dict with ObjectId to a serialization-friendly format.
        """
        return {
            "id": str(doc["_id"]),
            "project_id": doc.get("project_id", ""),
            "title": doc.get("title", ""),
            "content": doc.get("content", "")
        }

    def get_all_by_project(self, project_id: str) -> List[TodoResponse]:
        """
        Get all TODO items belonging to a project.
        """
        docs = self.repo.get_by_project_id(project_id)
        return [TodoResponse(**self._serialize(d)) for d in docs]

    def get_by_id(self, todo_id: str) -> TodoResponse:
        """
        Get a specific TODO item by its unique ID.
        """
        try:
            oid = ObjectId(todo_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de TODO inválido"
            )

        doc = self.repo.find_by_id(oid)
        if not doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="TODO no encontrado"
            )
        return TodoResponse(**self._serialize(doc))

    def create(self, project_id: str, payload: TodoCreate) -> TodoResponse:
        """
        Create a new TODO item associated with a project.
        """
        # Validate that the project exists in the database
        try:
            proj_oid = ObjectId(project_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de proyecto inválido"
            )
        project = self.repo.db["projects"].find_one({"_id": proj_oid})
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El proyecto con ID {project_id} no existe"
            )

        new_model = TodoModel(
            title=payload.title,
            content=payload.content if payload.content is not None else "☐ My first task",
            project_id=project_id
        )
        doc = self.repo.insert_one(new_model.model_dump())
        return TodoResponse(**self._serialize(doc))

    def update(self, todo_id: str, payload: TodoUpdate) -> TodoResponse:
        """
        Update an existing TODO item.
        """
        # Verify existence
        self.get_by_id(todo_id)

        update_data = {}
        if payload.title is not None:
            update_data["title"] = payload.title
        if payload.content is not None:
            update_data["content"] = payload.content

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No se enviaron campos para actualizar"
            )

        self.repo.update_by_id(todo_id, {"$set": update_data})

        try:
            oid = ObjectId(todo_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de TODO inválido"
            )

        updated_doc = self.repo.find_by_id(oid)
        return TodoResponse(**self._serialize(updated_doc))

    def delete(self, todo_id: str) -> None:
        """
        Delete a TODO item by its ID.
        """
        self.get_by_id(todo_id)
        self.repo.delete_by_id(todo_id)
