from bson.objectid import ObjectId
from app.shared.repositories.base import BaseRepository

class DiagramRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "diagrams")

    def get_by_project_id(self, project_id: str) -> list:
        return self.find({"project_id": project_id})
