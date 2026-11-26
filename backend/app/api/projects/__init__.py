# Init for modular projects feature package
from app.api.projects.model import ProjectModel, InfoItemModel
from app.api.projects.repository import ProjectRepository
from app.api.projects.service import ProjectService
from app.api.projects.schemas import InfoItem, ProjectCreate, ProjectUpdate, ProjectResponse
from app.api.projects.router import router
