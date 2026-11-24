#!/usr/bin/env bash
set -e

# Permitir conexiones locales a X11/Xwayland desde contenedores
xhost +local: > /dev/null 2>&1 || true

# Exportar DISPLAY por defecto si no está definido
export DISPLAY="${DISPLAY:-:0}"

# Iniciar la aplicación con podman compose
podman compose up -d
