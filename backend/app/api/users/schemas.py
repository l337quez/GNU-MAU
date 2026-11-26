from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    public_key: Optional[str] = None
    image_profile: Optional[str] = None

class UserCreate(UserBase):
    password: str = Field(..., min_length=6)

class UserResponse(UserBase):
    id: str
    display_name: str
    created_at: datetime

    class Config:
        from_attributes = True
