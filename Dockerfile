FROM python:3.11-slim

# Instalar dependencias del sistema necesarias para PySide6 (Qt6 GUI)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglx-mesa0 \
    libegl1 \
    libdbus-1-3 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libglib2.0-0 \
    libfontconfig1 \
    fontconfig \
    fonts-noto-color-emoji \
    libx11-xcb1 \
    libxcb-cursor0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instalar Poetry
RUN pip install --no-cache-dir poetry

WORKDIR /app

# Copiar definiciones de dependencias
COPY pyproject.toml poetry.lock* ./

# Instalar dependencias de Python
RUN poetry config virtualenvs.create false \
    && poetry lock \
    && poetry install --no-root --no-interaction --no-ansi

# Copiar el código del proyecto
COPY . /app

# Crear carpetas de datos
RUN mkdir -p /app/mongita_data /app/storage

CMD ["python", "main.py"]
