# Init for modular information feature package
from app.api.information.model import InformationModel
from app.api.information.repository import InformationRepository
from app.api.information.service import InformationService
from app.api.information.schemas import InformationCreate, InformationUpdate, InformationResponse
from app.api.information.router import router
