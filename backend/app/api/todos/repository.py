from app.shared.repositories.base import BaseRepository


class TodoRepository(BaseRepository):
    """
    Repository to handle CRUD operations on the 'todos' database collection.
    """
    def __init__(self, db):
        super().__init__(db, "todos")

    def get_by_project_id(self, project_id: str) -> list:
        """
        Retrieve all TODO items associated with a project.
        """
        return self.find({"project_id": project_id})
