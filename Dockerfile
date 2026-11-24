FROM python:3.11-slim-bookworm

# Runtime configuration: user data and config live in mounted volumes so
# rebuilding the image never loses the database, storage or settings.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    QT_X11_NO_MITSHM=1 \
    GNU_MAU_CONFIG_DIR=/config \
    GNU_MAU_DATA_DIR=/data

# System libraries required by PySide6/Qt6 (xcb platform plugin)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libgl1 \
    libglx-mesa0 \
    libegl1 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxkbcommon-x11-0 \
    libxcb-icccm4 \
    libxcb-image0 \
    libxcb-keysyms1 \
    libxcb-randr0 \
    libxcb-render-util0 \
    libxcb-xinerama0 \
    libxcb-xfixes0 \
    libxcb-shape0 \
    libxcb-sync1 \
    libxcb-xkb1 \
    libxcb-cursor0 \
    libx11-xcb1 \
    libxext6 \
    libxrender1 \
    libxi6 \
    libxtst6 \
    libsm6 \
    libice6 \
    libglib2.0-0 \
    libfontconfig1 \
    fontconfig \
    fonts-noto-color-emoji \
    xauth \
    && rm -rf /var/lib/apt/lists/*

# Install Poetry (the lock file is copied and used as-is, so builds are
# reproducible and do not resolve dependencies at build time).
RUN pip install --no-cache-dir "poetry==2.5.2"

WORKDIR /app

COPY pyproject.toml poetry.lock ./
RUN poetry config virtualenvs.create false \
    && poetry install --only main --no-root --no-interaction --no-ansi

# Copy the application code
COPY . /app

# Persistent directories (mount points)
RUN mkdir -p /config /data/storage /data/mongita_data

VOLUME ["/config", "/data"]

CMD ["python", "main.py"]
