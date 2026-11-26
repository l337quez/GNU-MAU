---
name: fastapi-module-generator
description: Generates clean-architecture backend modules for the GNU-MAU FastAPI backend.
---

# FastAPI Module Generator

This skill defines the directory and architecture patterns for creating new backend API modules in the GNU-MAU codebase. Any AI agent modifying or extending the backend must strictly follow this file-by-file blueprint, replacing all placeholder variables with the corresponding module names. All Python code generated must strictly adhere to the PEP standards (such as PEP 8).

---

## 📁 Directory Structure
Create a new folder under `backend/app/api/` named in **plural, snake_case English** representing the entity (referred to below as `<feature-plural>`):

```text
backend/app/api/<feature-plural>/
├── __init__.py
├── model.py
├── repository.py
├── schemas.py
├── service.py
└── router.py
```

---

## 📄 File Blueprints
*Placeholder Guide:*
- `<feature-plural>`: plural, snake_case entity name (e.g. `projects`, `diagrams`, `items`).
- `<feature-singular>`: singular, snake_case entity name (e.g. `project`, `diagram`, `item`).
- `<FeatureName>`: singular, CamelCase class name (e.g. `Project`, `Diagram`, `Item`).
- `<FeaturePlural>`: plural, CamelCase entity name (e.g. `Projects`, `Diagrams`, `Items`).

---

### 1. `model.py` (Database Model)
Defines the document structure that will be saved in MongoDB/Mongita.
```python
from pydantic import BaseModel, Field
from typing import Dict, Optional, List

class <FeatureName>Model(BaseModel):
    """
    Database validation model for <FeaturePlural>.
    """
    # Define fields required by the database document
    name: str = Field(..., description="Name of the <feature-singular>")
    description: str = Field(default="", description="Description of the <feature-singular>")
    # Include other custom fields...
```

---

### 2. `repository.py` (Database Access Layer)
Inherits from `BaseRepository` to perform raw DB queries (CRUD) on the collection.
```python
from bson.objectid import ObjectId
from app.shared.repositories.base import BaseRepository

class <FeatureName>Repository(BaseRepository):
    def __init__(self, db):
        # Pass the database client and the collection name in lowercase/plural
        super().__init__(db, "<feature-plural>")

    # Add custom repository queries here if needed
```

---

### 3. `schemas.py` (Request/Response DTOs)
Pydantic schemas used for validating API input payloads and serializing API output responses.
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class <FeatureName>Create(BaseModel):
    name: str
    description: Optional[str] = ""
    # Fields required for creation...

class <FeatureName>Update(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    # Fields allowed for updating (all should be Optional)...

class <FeatureName>Response(BaseModel):
    id: str # Converted from ObjectId (_id)
    name: str
    description: str
    # Other custom fields to return in the JSON...

    model_config = {"from_attributes": True}
```

---

### 4. `service.py` (Business Logic Layer)
Orchestrates operations, converts/maps database documents, and returns Pydantic Response schemas.
```python
from app.api.<feature-plural>.schemas import <FeatureName>Create, <FeatureName>Update, <FeatureName>Response
from app.api.<feature-plural>.model import <FeatureName>Model
from app.api.<feature-plural>.repository import <FeatureName>Repository
from fastapi import HTTPException, status
from bson import ObjectId

class <FeatureName>Service:
    def __init__(self, repo: <FeatureName>Repository):
        self.repo = repo

    def _serialize(self, doc: dict) -> dict:
        """Converts raw database elements with _id into dictionaries with id string."""
        return {
            "id": str(doc["_id"]),
            "name": doc.get("name", ""),
            "description": doc.get("description", ""),
            # Map other fields...
        }

    def get_all(self) -> List[<FeatureName>Response]:
        items = self.repo.get_all()
        return [<FeatureName>Response(**self._serialize(item)) for item in items]

    def get_by_id(self, item_id: str) -> <FeatureName>Response:
        try:
            oid = ObjectId(item_id)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid ID format")
            
        doc = self.repo.get_by_id(oid)
        if not doc:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="<FeatureName> not found")
        return <FeatureName>Response(**self._serialize(doc))

    def create(self, payload: <FeatureName>Create) -> <FeatureName>Response:
        new_model = <FeatureName>Model(
            name=payload.name,
            description=payload.description
        )
        doc = self.repo.create(new_model.model_dump())
        return <FeatureName>Response(**self._serialize(doc))

    def update(self, item_id: str, payload: <FeatureName>Update) -> <FeatureName>Response:
        # Fetch or raise 404
        self.get_by_id(item_id)
        
        update_data = {k: v for k, v in payload.model_dump().items() if v is not None}
        if not update_data:
             raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No fields provided for update")
             
        updated_doc = self.repo.update_metadata(item_id, update_data)
        return <FeatureName>Response(**self._serialize(updated_doc))

    def delete(self, item_id: str) -> None:
        self.get_by_id(item_id)
        self.repo.delete_by_id(item_id)
```

---

### 5. `router.py` (API Controllers / Endpoints)
Exposes FastAPI routes and handles dependency injection.
```python
from fastapi import APIRouter, Depends, status
from app.core.database import get_db
from app.api.<feature-plural>.schemas import <FeatureName>Create, <FeatureName>Response, <FeatureName>Update
from app.api.<feature-plural>.repository import <FeatureName>Repository
from app.api.<feature-plural>.service import <FeatureName>Service

router = APIRouter(prefix="/<feature-plural>", tags=["<FeaturePlural>"])

def get_<feature-singular>_service(db=Depends(get_db)) -> <FeatureName>Service:
    repo = <FeatureName>Repository(db)
    return <FeatureName>Service(repo)

@router.get("/", response_model=list[<FeatureName>Response])
def list_<feature-plural>(service: <FeatureName>Service = Depends(get_<feature-singular>_service)):
    return service.get_all()

@router.get("/{item_id}", response_model=<FeatureName>Response)
def get_<feature-singular>(item_id: str, service: <FeatureName>Service = Depends(get_<feature-singular>_service)):
    return service.get_by_id(item_id)

@router.post("/", response_model=<FeatureName>Response, status_code=status.HTTP_201_CREATED)
def create_<feature-singular>(payload: <FeatureName>Create, service: <FeatureName>Service = Depends(get_<feature-singular>_service)):
    return service.create(payload)

@router.put("/{item_id}", response_model=<FeatureName>Response)
def update_<feature-singular>(item_id: str, payload: <FeatureName>Update, service: <FeatureName>Service = Depends(get_<feature-singular>_service)):
    return service.update(item_id, payload)

@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_<feature-singular>(item_id: str, service: <FeatureName>Service = Depends(get_<feature-singular>_service)):
    service.delete(item_id)
```

---

### 6. `__init__.py` (Package Exports)
Exposes all components to allow clean imports from the package.
```python
from app.api.<feature-plural>.model import <FeatureName>Model
from app.api.<feature-plural>.repository import <FeatureName>Repository
from app.api.<feature-plural>.service import <FeatureName>Service
from app.api.<feature-plural>.schemas import <FeatureName>Create, <FeatureName>Update, <FeatureName>Response
from app.api.<feature-plural>.router import router
```

---

## 🔗 Registering the Router
Once the module files are created, you **must** register the router globally:
1. Open [routers.py](file:///c:/Users/l337q/OneDrive/Desktop/PROYECTOS/GNU-MAU/backend/app/api/routers.py).
2. Import the router:
   ```python
   from app.api.<feature-plural>.router import router as <feature-plural>_router
   ```
3. Register the router with the global `/api` prefix router:
   ```python
   api_router.include_router(<feature-plural>_router)
   ```
