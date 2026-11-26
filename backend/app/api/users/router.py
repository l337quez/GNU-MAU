from fastapi import APIRouter, Depends, status
from app.api.users.schemas import UserCreate, UserResponse
from app.api.users.service import UserService
from app.api.auth.guards import get_current_user
from app.core.database import get_db

router = APIRouter(prefix="/users", tags=["Users"])

def get_user_service(db = Depends(get_db)) -> UserService:
    return UserService(db)

@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user"
)
def register_user(
    payload: UserCreate,
    user_service: UserService = Depends(get_user_service)
):
    """
    Registra un usuario nuevo en el sistema con correo electrónico y contraseña.
    """
    return user_service.register_user(payload)

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get current user profile"
)
def get_current_user_profile(
    current_user: dict = Depends(get_current_user),
    user_service: UserService = Depends(get_user_service)
):
    """
    Obtiene el perfil completo del usuario autenticado actual.
    """
    return user_service.get_user_by_username(current_user["username"])
