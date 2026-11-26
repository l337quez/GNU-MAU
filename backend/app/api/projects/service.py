from typing import List
from fastapi import HTTPException, status
from app.api.projects.schemas import ProjectCreate, ProjectUpdate, ProjectResponse
from app.api.projects.model import ProjectModel, InfoItemModel
from app.api.projects.repository import ProjectRepository
from app.shared.helpers import serialize_project, get_project_or_404, DEFAULT_ICON

class ProjectService:
    def __init__(self, repo: ProjectRepository):
        self.repo = repo

    def get_all(self) -> List[ProjectResponse]:
        projects = self.repo.get_all()
        return [ProjectResponse(**serialize_project(p)) for p in projects]

    def get_by_id(self, project_id: str) -> ProjectResponse:
        project = get_project_or_404(self.repo, project_id)
        return ProjectResponse(**serialize_project(project))

    def create(self, payload: ProjectCreate) -> ProjectResponse:
        # 1. Transformar payload (DTO) a diccionarios de InfoItemModel
        info_dict = {}
        if payload.info:
            for k, v in payload.info.items():
                info_dict[k] = InfoItemModel(
                    value=v.value,
                    action=v.action,
                    category=v.category,
                    encrypted=v.encrypted
                )
        
        # 2. Crear instancia del Modelo (Pydantic valida el documento completo)
        new_project = ProjectModel(
            name=payload.name,
            description=payload.description,
            icon_path=payload.icon_path or DEFAULT_ICON,
            info=info_dict
        )

        # 3. Guardar en Base de Datos convirtiendo a dict
        doc = self.repo.create(new_project.model_dump())
        
        return ProjectResponse(**serialize_project(doc))

    def update(self, project_id: str, payload: ProjectUpdate) -> ProjectResponse:
        get_project_or_404(self.repo, project_id)

        update_data: dict = {}
        if payload.name is not None:
            update_data["name"] = payload.name
        if payload.description is not None:
            update_data["description"] = payload.description
        if payload.icon_path is not None:
            update_data["icon_path"] = payload.icon_path
        if payload.info is not None:
            # Aquí podríamos instanciar InfoItemModel para validar si es necesario
            update_data["info"] = {
                k: InfoItemModel(value=v.value, action=v.action, category=v.category, encrypted=v.encrypted).model_dump()
                for k, v in payload.info.items()
            }

        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No se enviaron campos para actualizar")

        updated = self.repo.update_metadata(project_id, update_data)
        return ProjectResponse(**serialize_project(updated))

    def update_icon(self, project_id: str, icon_path: str) -> ProjectResponse:
        get_project_or_404(self.repo, project_id)
        updated = self.repo.update_icon(project_id, icon_path)
        return ProjectResponse(**serialize_project(updated))

    def upsert_info(self, project_id: str, key: str, value: str, action: str | None = None, category: str = "", encrypted: bool = False) -> ProjectResponse:
        get_project_or_404(self.repo, project_id)
        
        # Validar formato con el modelo antes de guardar
        info_item = InfoItemModel(value=value, action=action, category=category, encrypted=encrypted)
        
        updated = self.repo.upsert_info(project_id, key, info_item.model_dump())
        return ProjectResponse(**serialize_project(updated))

    def delete_info(self, project_id: str, key: str) -> ProjectResponse:
        project = get_project_or_404(self.repo, project_id)
        info = project.get("info", {})
        if key not in info:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"La key '{key}' no existe en este proyecto")
        
        updated = self.repo.delete_info(project_id, key)
        return ProjectResponse(**serialize_project(updated))

    def delete(self, project_id: str) -> None:
        get_project_or_404(self.repo, project_id)
        self.repo.delete_by_id(project_id)
