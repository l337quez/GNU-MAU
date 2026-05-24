from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.routers import api_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API Backend para GNU-MAU. Gestiona proyectos, info items, notas y tareas.",
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
