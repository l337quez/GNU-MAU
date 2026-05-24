from bson.objectid import ObjectId
from fastapi import HTTPException, status

DEFAULT_ICON = "assets/project_images/default_icon.png"


def serialize_project(doc: dict) -> dict:
    """Convierte el documento de Mongita a un dict compatible con ProjectResponse."""
    info_raw = doc.get("info", {})
    info = {}
    for key, val in info_raw.items():
        if isinstance(val, dict):
            info[key] = val
        else:
            info[key] = {"value": str(val), "action": None, "category": ""}

    return {
        "id": str(doc["_id"]),
        "name": doc.get("name", ""),
        "description": doc.get("description", ""),
        "icon_path": doc.get("icon_path", DEFAULT_ICON),
        "info": info,
    }


def get_project_or_404(repo, project_id: str) -> dict:
    """Busca un proyecto por ID a través de su repositorio y lanza 404 si no existe."""
    try:
        oid = ObjectId(project_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de proyecto inválido")

    project = repo.get_by_id(oid)
    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Proyecto no encontrado")
    return project
