from fastapi import APIRouter, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from app.api.auth.schemas import (
    RegisterOptionsRequest, 
    RegisterVerifyRequest, 
    LoginOptionsRequest, 
    LoginVerifyRequest, 
    TokenResponse, 
    UserProfile
)
from app.api.auth.guards import get_auth_service, get_current_user
from app.api.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Iniciar sesión con usuario y contraseña (Estándar)",
    status_code=status.HTTP_200_OK
)
def login_with_password(
    form_data: OAuth2PasswordRequestForm = Depends(),
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Endpoint estándar para iniciar sesión usando email/username y contraseña.
    """
    return auth_service.login_with_password(form_data.username, form_data.password)


@router.post(
    "/register/options", 
    summary="Obtener opciones para registrar dispositivo FIDO2",
    status_code=status.HTTP_200_OK
)
def get_register_options(
    payload: RegisterOptionsRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Genera el reto (challenge) y los parámetros requeridos por la API WebAuthn del cliente
    para crear una nueva credencial (Passkey/llave física).
    """
    return auth_service.get_registration_options(payload.username, payload.display_name)


@router.post(
    "/register/verify", 
    summary="Verificar y guardar credencial FIDO2 registrada",
    status_code=status.HTTP_201_CREATED
)
def verify_registration(
    payload: RegisterVerifyRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Recibe la respuesta de creación de credencial del cliente, la verifica mediante la
    criptografía FIDO2 y la guarda en la base de datos asociada al usuario.
    """
    # En el flujo de registro, si es usuario nuevo se creará usando su display_name
    # Para simplificar, buscamos si ya existe el usuario para mantener su display_name anterior,
    # o de lo contrario usamos el username como display_name por defecto.
    user_doc = auth_service.db.users.find_one({"username": payload.username})
    display_name = user_doc["display_name"] if user_doc else payload.username
    
    return auth_service.verify_registration(
        username=payload.username,
        display_name=display_name,
        credential_dict=payload.credential
    )


@router.post(
    "/login/options", 
    summary="Obtener opciones para iniciar sesión con FIDO2",
    status_code=status.HTTP_200_OK
)
def get_login_options(
    payload: LoginOptionsRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Genera el reto (challenge) de autenticación y lista las credenciales FIDO2 registradas
    para el usuario para permitir el inicio de sesión.
    """
    return auth_service.get_login_options(payload.username)


@router.post(
    "/login/verify", 
    response_model=TokenResponse,
    summary="Verificar firma de inicio de sesión FIDO2 y emitir JWT",
    status_code=status.HTTP_200_OK
)
def verify_login(
    payload: LoginVerifyRequest,
    auth_service: AuthService = Depends(get_auth_service)
):
    """
    Verifica la aserción firmada por el dispositivo del cliente. Si es válida, emite
    un token JWT de sesión para autorizar peticiones posteriores.
    """
    return auth_service.verify_login(payload.username, payload.credential)


@router.get(
    "/profile", 
    response_model=UserProfile,
    summary="Obtener perfil del usuario autenticado (Protegido)",
    status_code=status.HTTP_200_OK
)
def get_profile(
    current_user: dict = Depends(get_current_user)
):
    """
    Endpoint protegido por el guard get_current_user.
    Retorna el perfil del usuario autenticado actual.
    """
    return UserProfile(
        username=current_user["username"],
        display_name=current_user["display_name"]
    )
