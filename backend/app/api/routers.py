from fastapi import APIRouter
from app.api import projects
from app.api import information
from app.api.auth import router as auth
from app.api.diagrams.router import router as diagrams
from app.api.todos.router import router as todos
from app.api.notes import router as notes
from app.api.users.router import router as users_router
from app.api.tasks.router import router as tasks_router
from app.api.tools.router import router as tools_router

api_router = APIRouter(prefix="/api")
api_router.include_router(projects.router)
api_router.include_router(information.router)
api_router.include_router(auth.router)
api_router.include_router(users_router)
api_router.include_router(tasks_router)
api_router.include_router(tools_router)
api_router.include_router(diagrams)
api_router.include_router(todos)
api_router.include_router(notes)

