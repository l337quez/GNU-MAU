from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime

class UserModel(BaseModel):
    """
    Representa a un usuario en la base de datos, soportando tanto registro con contraseña
    como FIDO2.
    """
    username: str
    email: EmailStr
    hashed_password: str
    display_name: str
    public_key: Optional[str] = None
    image_profile: Optional[str] = None
    credentials: List[Dict[str, Any]] = Field(default_factory=list) # FIDO2 credentials
    created_at: datetime = Field(default_factory=datetime.utcnow)
