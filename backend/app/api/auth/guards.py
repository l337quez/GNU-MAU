from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from app.core.database import get_db
from app.api.auth.service import AuthService

# Indica a FastAPI que busque el token en la cabecera 'Authorization: Bearer <TOKEN>'
# tokenUrl indica a Swagger/Docs dónde se encuentra el endpoint que emite el token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login/verify")

def get_auth_service(db = Depends(get_db)) -> AuthService:
    """
    Dependencia de FastAPI para inyectar AuthService.
    """
    return AuthService(db)

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    auth_service: AuthService = Depends(get_auth_service)
) -> dict:
    """
    Verify user JWT token.
    """
    username = auth_service.verify_jwt_token(token)
    
    user_doc = auth_service.db.users.find_one({"username": username})
    if not user_doc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or unauthorized"
        )
        
    return {
        "username": user_doc["username"],
        "display_name": user_doc["display_name"]
    }
