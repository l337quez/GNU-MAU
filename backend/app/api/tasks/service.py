from fastapi import HTTPException, status
from bson import ObjectId
from datetime import datetime
from app.api.tasks.schemas import TaskCreate, TaskUpdate
from app.api.tasks.models import TaskModel
from app.core.database import get_db

class TaskService:
    def __init__(self, db):
        self.db = db
        self.collection = self.db.tasks

    def create_task(self, project_id: str, creator_username: str, payload: TaskCreate) -> dict:
        new_task = TaskModel(
            project_id=project_id,
            title=payload.title,
            description=payload.description,
            creator_username=creator_username,
            assignee_username=payload.assignee_username,
            status=payload.status,
            priority=payload.priority
        )
        
        doc = new_task.model_dump()
        result = self.collection.insert_one(doc)
        doc["id"] = str(result.inserted_id)
        return doc

    def get_tasks(self, project_id: str, assignee_username: str = None) -> list[dict]:
        query = {"project_id": project_id}
        if assignee_username:
            query["assignee_username"] = assignee_username
            
        tasks = []
        for doc in self.collection.find(query):
            doc["id"] = str(doc.pop("_id"))
            tasks.append(doc)
        return tasks

    def update_task(self, project_id: str, task_id: str, payload: TaskUpdate) -> dict:
        update_data = payload.model_dump(exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data provided for update")
            
        update_data["updated_at"] = datetime.utcnow()
        
        try:
            obj_id = ObjectId(task_id)
        except Exception:
            # Handle Mongita simple string IDs or invalid ObjectIds
            obj_id = task_id
            
        result = self.collection.find_one_and_update(
            {"_id": obj_id, "project_id": project_id},
            {"$set": update_data},
            return_document=True
        )
        
        if not result:
            # Try with string ID if ObjectId failed to find it (for mongita compatibility)
            result = self.collection.find_one_and_update(
                {"_id": task_id, "project_id": project_id},
                {"$set": update_data},
                return_document=True
            )
            if not result:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
            
        result["id"] = str(result.pop("_id"))
        return result

    def delete_task(self, project_id: str, task_id: str):
        try:
            obj_id = ObjectId(task_id)
        except Exception:
            obj_id = task_id
            
        result = self.collection.delete_one({"_id": obj_id, "project_id": project_id})
        
        if result.deleted_count == 0:
            result = self.collection.delete_one({"_id": task_id, "project_id": project_id})
            if result.deleted_count == 0:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
        
        return {"detail": "Task deleted successfully"}
