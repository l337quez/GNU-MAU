import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "GNU-MAU API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Motor de base de datos: 'mongita' o 'mongodb'
    DB_ENGINE: str = os.getenv("DB_ENGINE", "mongita").lower()

    # MongoDB traditional settings
    MONGODB_URI: str = os.getenv("MONGODB_URI", "mongodb://localhost:27017")

    # Mongita: ruta al directorio de datos (misma base de datos que usa el desktop)
    MONGITA_DB_DIR: str = os.getenv(
        "MONGITA_DB_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "desktop", "app", "mongita_data"),
    )
    DB_NAME: str = os.getenv("DB_NAME", "projects_db")

    # Vault (Deprecated but kept for backwards compatibility)
    DEFAULT_STORAGE_PATH: str = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "desktop", "app", "storage"))
    LOCAL_VAULT_ENABLED: bool = os.getenv("LOCAL_VAULT_ENABLED", "false").lower() == "true"
    LOCAL_VAULT_PATH: str = os.getenv("LOCAL_VAULT_PATH", "")

    # ArangoDB Knowledge Graph
    ARANGO_URL: str = os.getenv("ARANGO_URL", "http://localhost:8529")
    ARANGO_ROOT_PASSWORD: str = os.getenv("ARANGO_ROOT_PASSWORD", "gnumau_secret")
    ARANGO_DB_NAME: str = os.getenv("ARANGO_DB_NAME", "gnu_mau_knowledge")

    # FIDO2 / WebAuthn Configuration
    RP_NAME: str = os.getenv("RP_NAME", "GNU-MAU Mobile")
    RP_ID: str = os.getenv("RP_ID", "localhost")
    ORIGIN: str = os.getenv("ORIGIN", "http://localhost:9000")
    
    # JWT Configuration
    JWT_SECRET: str = os.getenv("JWT_SECRET", "super_secret_jwt_key_2026_for_gnu_mau")
    JWT_ALGORITHM: str = "HS256"

    # Obsidian / Local Vault Sync Configuration
    LOCAL_VAULT_ENABLED: bool = os.getenv("LOCAL_VAULT_ENABLED", "false").lower() == "true"
    LOCAL_VAULT_PATH: str = os.getenv("LOCAL_VAULT_PATH", "")
    DEFAULT_STORAGE_PATH: str = os.getenv(
        "DEFAULT_STORAGE_PATH",
        os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "desktop", "app", "storage")),
    )



@lru_cache()
def get_settings() -> Settings:
    return Settings()
