from fastapi import HTTPException, status
from passlib.context import CryptContext
from app.api.users.schemas import UserCreate, UserResponse
from app.api.users.models import UserModel
from app.core.database import get_db

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UserService:
    def __init__(self, db):
        self.db = db

    def get_password_hash(self, password: str) -> str:
        return pwd_context.hash(password)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def register_user(self, payload: UserCreate) -> dict:
        # Check if username or email already exists
        if self.db.users.find_one({"username": payload.username}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username already registered"
            )
        
        if self.db.users.find_one({"email": payload.email}):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )

        hashed_password = self.get_password_hash(payload.password)
        
        new_user = UserModel(
            username=payload.username,
            email=payload.email,
            hashed_password=hashed_password,
            display_name=payload.username, # Can be updated later
            public_key=payload.public_key,
            image_profile=payload.image_profile,
            credentials=[]
        )
        
        result = self.db.users.insert_one(new_user.model_dump())
        
        # Return UserResponse dict
        user_dict = new_user.model_dump()
        user_dict["id"] = str(result.inserted_id)
        
        return user_dict

    def get_user_by_username(self, username: str) -> dict:
        user = self.db.users.find_one({"username": username})
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user["id"] = str(user["_id"])
        return user
