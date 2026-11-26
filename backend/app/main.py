from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import api_router
from app.core.config import get_settings

settings = get_settings()

# ─────────────────────────────────────────────
# OpenAPI / Swagger metadata
# ─────────────────────────────────────────────
description = """
## GNU-MAU API 🛠️

API Backend para la aplicación de escritorio **GNU-MAU**.

Gestiona de forma centralizada toda la información de tus proyectos de desarrollo:

* 📁 **Projects** — Crea, actualiza y elimina proyectos. Cada proyecto puede tener un icono, descripción e items de info embebidos.
* 📋 **Information** — Gestiona items de información independientes vinculables a proyectos: comandos de terminal, URLs, notas técnicas, etc.

---
> Diseñado para correr localmente junto a la app de escritorio PySide.
"""

tags_metadata = [
    {
        "name": "Projects",
        "description": "CRUD completo de proyectos. Incluye gestión de ícono y de items `info` embebidos.",
    },
    {
        "name": "Information",
        "description": "Items de información independientes (comandos, URLs, notas). Pueden vincularse opcionalmente a un proyecto.",
    },
    {
        "name": "Health",
        "description": "Endpoints de estado de la API.",
    },
]

from contextlib import asynccontextmanager
from app.api.notes.database import arango_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize ArangoDB connection and schema on startup
    arango_manager.initialize()
    yield
    # Cleanup if needed

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description=description,
    lifespan=lifespan,

    contact={
        "name": "GNU-MAU Dev",
        "url": "https://github.com/l337quez/GNU-MAU",
    },
    license_info={
        "name": "GPL-3.0",
        "url": "https://www.gnu.org/licenses/gpl-3.0.html",
    },
    openapi_tags=tags_metadata,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS: permite peticiones desde la app PySide o cualquier cliente local
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, limitar a orígenes específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Incluir todos los routers de la API
app.include_router(api_router)


@app.get("/", tags=["Health"])
def root():
    return {"app": settings.APP_NAME, "version": settings.APP_VERSION, "status": "running"}


@app.get("/api/health", tags=["Health"])
def health_check():
    return {"status": "ok"}

