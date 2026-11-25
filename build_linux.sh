#!/usr/bin/env bash
set -e

echo "🔨 Compilando binario de Linux con PyInstaller en Podman..."

podman run --rm \
    -v "$PWD":/app:z \
    -w /app \
    localhost/gnu-mau-app:latest \
    pyinstaller setup_linux.spec --clean --noconfirm

echo ""
echo "✅ ¡Compilación exitosa!"
echo "📦 El ejecutable está listo en: dist/gnu-mau"
echo "👉 Puedes ejecutarlo directamente en Fedora con: ./dist/gnu-mau"
