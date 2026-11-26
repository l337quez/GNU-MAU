from typing import Optional
from bson.objectid import ObjectId
from app.shared.repositories.base import BaseRepository


class InformationRepository(BaseRepository):
    def __init__(self, db):
        super().__init__(db, "information")

    def get_all(self) -> list:
        return self.find()

    def get_by_id(self, item_id: str | ObjectId) -> dict | None:
        return self.find_by_id(item_id)

    def get_by_project(self, project_id: str) -> list:
        """
        Return all items linked to a specific project.
        """
        return self.find({"project_id": project_id})

    def create(self, doc: dict) -> dict:
        return self.insert_one(doc)

    def update_metadata(self, item_id: str | ObjectId, update_data: dict) -> dict | None:
        self.update_by_id(item_id, {"$set": update_data})
        return self.get_by_id(item_id)

    def delete(self, item_id: str | ObjectId) -> None:
        self.delete_by_id(item_id)
