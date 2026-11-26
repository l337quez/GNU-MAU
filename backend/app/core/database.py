from app.core.config import get_settings

settings = get_settings()

# Cliente genérico (puede ser MongitaClientDisk o pymongo.MongoClient)
_client = None


def get_client():
    global _client
    if _client is None:
        if settings.DB_ENGINE == "mongodb":
            from pymongo import MongoClient
            _client = MongoClient(settings.MONGODB_URI)
        else:
            from mongita import MongitaClientDisk
            _client = MongitaClientDisk(settings.MONGITA_DB_DIR)
    return _client


def get_db():
    """Dependencia de FastAPI: inyecta la base de datos en los endpoints."""
    client = get_client()
    db = client[settings.DB_NAME]
    try:
        yield db
    finally:
        pass  # Ni PyMongo ni Mongita requieren cierre explícito por request
