FROM python:3.12-slim

# Evitar que Python escriba archivos .pyc en el disco
ENV PYTHONDONTWRITEBYTECODE=1

# Evitar que Python almacene en búfer stdout y stderr (útil para logs de Docker)
ENV PYTHONUNBUFFERED=1

# Configurar variables de Poetry
ENV POETRY_VERSION=2.0.1
ENV POETRY_HOME="/opt/poetry"
ENV POETRY_VIRTUALENVS_CREATE=false
ENV PATH="$POETRY_HOME/bin:$PATH"

# Instalar curl y Poetry
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && curl -sSL https://install.python-poetry.org | python3 - \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copiar archivos de dependencias de Poetry
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias del sistema usando Poetry
RUN poetry install --no-interaction --no-ansi --no-root

# Copiar el código del backend
COPY . .

# Puerto por el cual escucha FastAPI
EXPOSE 9000

# Comando para iniciar la aplicación con Uvicorn a través de Poetry
CMD ["poetry", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
