import os
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME: str = "GNU-MAU API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "true").lower() == "true"

    # Mongita: ruta al directorio de datos (misma base de datos que usa el desktop)
    MONGITA_DB_DIR: str = os.getenv(
        "MONGITA_DB_DIR",
        os.path.join(os.path.dirname(__file__), "..", "..", "..", "desktop", "app", "mongita_data"),
    )
    DB_NAME: str = os.getenv("DB_NAME", "projects_db")


@lru_cache()
def get_settings() -> Settings:
    return Settings()
