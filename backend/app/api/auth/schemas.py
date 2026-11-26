from pydantic import BaseModel, Field
from typing import Dict, Any

class RegisterOptionsRequest(BaseModel):
    """
    Solicitud para iniciar el registro de un nuevo dispositivo FIDO2.
    """
    username: str = Field(..., min_length=3, max_length=50, description="Nombre de usuario único")
    display_name: str = Field(..., min_length=2, max_length=100, description="Nombre de pantalla o real")

class RegisterVerifyRequest(BaseModel):
    """
    Verificación del registro de FIDO2 enviado por el cliente.
    """
    username: str
    credential: Dict[str, Any]  # Objeto JSON retornado por la API WebAuthn del navegador/móvil

class LoginOptionsRequest(BaseModel):
    """
    Solicitud para iniciar el proceso de Login.
    """
    username: str

class LoginVerifyRequest(BaseModel):
    """
    Verificación de autenticación de FIDO2 enviado por el cliente.
    """
    username: str
    credential: Dict[str, Any]  # Objeto JSON retornado por navigator.credentials.get()

class TokenResponse(BaseModel):
    """
    Respuesta que entrega el token de sesión JWT tras un login exitoso.
    """
    access_token: str
    token_type: str = "bearer"

class UserProfile(BaseModel):
    """
    Representación básica de perfil de usuario.
    """
    username: str
    display_name: str
