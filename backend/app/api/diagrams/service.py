from typing import List
from fastapi import HTTPException, status
from bson import ObjectId
from app.api.diagrams.schemas import DiagramCreate, DiagramUpdate, DiagramResponse
from app.api.diagrams.model import DiagramModel
from app.api.diagrams.repository import DiagramRepository

class DiagramService:
    def __init__(self, repo: DiagramRepository):
        self.repo = repo

    def _serialize(self, doc: dict) -> dict:
        return {
            "id": str(doc["_id"]),
            "project_id": doc.get("project_id", ""),
            "name": doc.get("name", ""),
            "type": doc.get("type", "Advanced Architecture"),
            "nodes": doc.get("nodes", []),
            "connections": doc.get("connections", [])
        }

    def get_all_by_project(self, project_id: str) -> List[DiagramResponse]:
        docs = self.repo.get_by_project_id(project_id)
        return [DiagramResponse(**self._serialize(d)) for d in docs]

    def get_by_id(self, diagram_id: str) -> DiagramResponse:
        try:
            oid = ObjectId(diagram_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de diagrama inválido")
        
        doc = self.repo.get_by_id(oid)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Diagrama no encontrado")
        return DiagramResponse(**self._serialize(doc))

    def create(self, project_id: str, payload: DiagramCreate) -> DiagramResponse:
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

        new_model = DiagramModel(
            name=payload.name,
            project_id=project_id,
            type=payload.type or "Advanced Architecture",
            nodes=payload.nodes or [],
            connections=payload.connections or []
        )
        doc = self.repo.create(new_model.model_dump())
        return DiagramResponse(**self._serialize(doc))

    def update(self, diagram_id: str, payload: DiagramUpdate) -> DiagramResponse:
        # Validar existencia
        self.get_by_id(diagram_id)

        update_data = {}
        if payload.name is not None:
            update_data["name"] = payload.name
        if payload.type is not None:
            update_data["type"] = payload.type
        if payload.nodes is not None:
            update_data["nodes"] = payload.nodes
        if payload.connections is not None:
            update_data["connections"] = payload.connections

        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se enviaron campos para actualizar")

        updated_doc = self.repo.update_metadata(diagram_id, update_data)
        return DiagramResponse(**self._serialize(updated_doc))

    def delete(self, diagram_id: str) -> None:
        self.get_by_id(diagram_id)
        self.repo.delete_by_id(diagram_id)
