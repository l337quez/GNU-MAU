from mongita import MongitaClientDisk
from app.core.config import get_settings

settings = get_settings()

# Cliente Mongita reutilizable (singleton a nivel de módulo)
_client: MongitaClientDisk | None = None


def get_client() -> MongitaClientDisk:
    global _client
    if _client is None:
        _client = MongitaClientDisk(settings.MONGITA_DB_DIR)
    return _client


def get_db():
    """Dependencia de FastAPI: inyecta la base de datos en los endpoints."""
    client = get_client()
    db = client[settings.DB_NAME]
    try:
        yield db
    finally:
        pass  # Mongita no requiere cierre explícito por request
