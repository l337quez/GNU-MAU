from bson.objectid import ObjectId
from app.shared.repositories.base import BaseRepository


class ProjectRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "projects")

    def get_all(self) -> list:
        return self.find()

    def get_by_id(self, project_id: str | ObjectId) -> dict | None:
        return self.find_by_id(project_id)

    def create(self, name: str, description: str, icon_path: str, info: dict = None) -> dict:
        if info is None:
            info = {}
        doc = {
            "name": name,
            "description": description,
            "icon_path": icon_path,
            "info": info
        }
        return self.insert_one(doc)

    def update_metadata(self, project_id: str | ObjectId, update_data: dict) -> dict | None:
        self.update_by_id(project_id, {"$set": update_data})
        return self.get_by_id(project_id)

    def update_icon(self, project_id: str | ObjectId, icon_path: str) -> dict | None:
        self.update_by_id(project_id, {"$set": {"icon_path": icon_path}})
        return self.get_by_id(project_id)

    def upsert_info(self, project_id: str | ObjectId, key: str, value: str, action: str | None = None, category: str = "") -> dict | None:
        project = self.get_by_id(project_id)
        if not project:
            return None
        info = project.get("info", {})
        info[key] = {"value": value, "action": action, "category": category}
        self.update_by_id(project_id, {"$set": {"info": info}})
        return self.get_by_id(project_id)

    def delete_info(self, project_id: str | ObjectId, key: str) -> dict | None:
        project = self.get_by_id(project_id)
        if not project:
            return None
        info = project.get("info", {})
        if key in info:
            del info[key]
            self.update_by_id(project_id, {"$set": {"info": info}})
        return self.get_by_id(project_id)
