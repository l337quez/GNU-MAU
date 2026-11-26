from typing import List, Optional
from bson.objectid import ObjectId
from fastapi import HTTPException, status

from app.api.information.schemas import InformationCreate, InformationUpdate, InformationResponse
from app.api.information.model import InformationModel
from app.api.information.repository import InformationRepository


def _serialize(doc: dict) -> dict:
    """Convierte un documento de Mongita al dict que espera InformationResponse."""
    return {
        "id": str(doc["_id"]),
        "title": doc.get("title", ""),
        "content": doc.get("content", ""),
        "category": doc.get("category", ""),
        "action": doc.get("action"),
        "project_id": doc.get("project_id"),
        "encrypted": doc.get("encrypted", False),
    }


def _get_or_404(repo: InformationRepository, item_id: str) -> dict:
    try:
        oid = ObjectId(item_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de información inválido")

    doc = repo.get_by_id(oid)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Information item no encontrado")
    return doc


class InformationService:
    def __init__(self, repo: InformationRepository):
        self.repo = repo

    def get_all(self, project_id: Optional[str] = None) -> List[InformationResponse]:
        """Retorna todos los items. Si se pasa project_id, filtra por proyecto."""
        if project_id:
            docs = self.repo.get_by_project(project_id)
        else:
            docs = self.repo.get_all()
        return [InformationResponse(**_serialize(d)) for d in docs]

    def get_by_id(self, item_id: str) -> InformationResponse:
        doc = _get_or_404(self.repo, item_id)
        return InformationResponse(**_serialize(doc))

    def create(self, payload: InformationCreate) -> InformationResponse:
        # Validar que el proyecto exista en la base de datos
        try:
            proj_oid = ObjectId(payload.project_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ID de proyecto inválido"
            )
        project = self.repo.db["projects"].find_one({"_id": proj_oid})
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"El proyecto con ID {payload.project_id} no existe"
            )

        # 1. Crear instancia del Modelo (Pydantic valida el documento completo)
        new_item = InformationModel(
            title=payload.title,
            content=payload.content,
            category=payload.category,
            action=payload.action,
            project_id=payload.project_id,
            encrypted=payload.encrypted or False,
        )

        # 2. Guardar en BD convirtiendo a dict via .model_dump()
        doc = self.repo.create(new_item.model_dump())
        return InformationResponse(**_serialize(doc))

    def update(self, item_id: str, payload: InformationUpdate) -> InformationResponse:
        _get_or_404(self.repo, item_id)

        update_data: dict = {}
        if payload.title is not None:
            update_data["title"] = payload.title
        if payload.content is not None:
            update_data["content"] = payload.content
        if payload.category is not None:
            update_data["category"] = payload.category
        if payload.action is not None:
            update_data["action"] = payload.action
        if payload.project_id is not None:
            try:
                proj_oid = ObjectId(payload.project_id)
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="ID de proyecto inválido"
                )
            project = self.repo.db["projects"].find_one({"_id": proj_oid})
            if not project:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"El proyecto con ID {payload.project_id} no existe"
                )
            update_data["project_id"] = payload.project_id
        if payload.encrypted is not None:
            update_data["encrypted"] = payload.encrypted

        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se enviaron campos para actualizar")

        updated = self.repo.update_metadata(item_id, update_data)
        return InformationResponse(**_serialize(updated))

    def delete(self, item_id: str) -> None:
        _get_or_404(self.repo, item_id)
        self.repo.delete(item_id)
