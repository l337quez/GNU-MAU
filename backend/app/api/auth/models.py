from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime

class CredentialModel(BaseModel):
    """
    Represents a registered FIDO2 credential.
    """
    credential_id: str  # Representación base64url o hex
    public_key: str     # Representación base64url o hex de los bytes de la clave pública
    sign_count: int = 0 # Contador de firmas para prevenir ataques de clonación

class UserModel(BaseModel):
    """
    Represents a registered user with FIDO2 support.
    """
    username: str
    display_name: str
    credentials: List[CredentialModel] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)

class TempStateModel(BaseModel):
    """
    Guarda el reto/estado temporal ('state') retornado por Yubico fido2
    entre la petición de opciones y la verificación final.
    """
    state_id: str  # Generalmente el username o user_id temporal
    state: Dict[str, Any]  # Contiene el reto ('challenge') y otros metadatos en bytes
    created_at: datetime = Field(default_factory=datetime.utcnow)
