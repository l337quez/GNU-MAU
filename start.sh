#!/usr/bin/env bash
# Start GNU Mau in a Podman/Docker container with a persistent data volume.
set -euo pipefail

cd "$(dirname "$0")"

export DISPLAY="${DISPLAY:-:0}"

# Allow local X11/Xwayland connections from the container.
if command -v xhost >/dev/null 2>&1; then
    xhost +local: >/dev/null 2>&1 || true
fi

if command -v podman >/dev/null 2>&1; then
    if podman compose version >/dev/null 2>&1; then
        COMPOSE=(podman compose)
    elif command -v podman-compose >/dev/null 2>&1; then
        COMPOSE=(podman-compose)
    else
        echo "Error: 'podman compose' or 'podman-compose' is required." >&2
        exit 1
    fi
elif command -v docker >/dev/null 2>&1; then
    COMPOSE=(docker compose)
else
    echo "Error: Podman or Docker is required." >&2
    exit 1
fi

# Ensure default persistent directories exist
mkdir -p "${GNU_MAU_CONFIG_PATH:-/mnt/ronal_disk/contenedores/gnu_mau_config}" \
         "${GNU_MAU_DATA_PATH:-/mnt/ronal_disk/contenedores/gnu_mau_data}" 2>/dev/null || \
mkdir -p .docker-data/config .docker-data/data

# Build when needed and start in the background.
"${COMPOSE[@]}" up -d --build "$@"
"${COMPOSE[@]}" ps
