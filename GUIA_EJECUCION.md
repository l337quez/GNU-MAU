# Guía de Ejecución y Compilación: Windows y Linux (Fedora)

Esta guía explica detalladamente cómo ejecutar y generar binarios independientes de **GNU Mau** tanto en **Linux** como en **Windows**.

---

## 🐧 Linux (Fedora y otras distribuciones)

Tienes dos formas de utilizar la aplicación en Linux:

### Opción 1: Ejecución con Podman (Contenedor)

Esta opción es ideal para desarrollo y ejecución aislada sin tener que instalar dependencias ni versiones específicas de Python en tu sistema anfitrión.

1. **Permitir acceso gráfico local a X11/Xwayland:**
   ```bash
   xhost +local:
   ```

2. **Iniciar la aplicación:**
   Puedes usar el script preparado:
   ```bash
   ./start.sh
   ```
   *O manualmente con Podman Compose:*
   ```bash
   podman compose up -d
   ```

3. **Detener el contenedor:**
   ```bash
   podman compose down
   ```

4. **Reconstruir la imagen (si cambias dependencias o fuentes):**
   ```bash
   podman compose build
   ```

---

### Opción 2: Compilación y Ejecución de Binario Nativo (Sin Podman)

Genera un único archivo ejecutable (`.bin` / ELF) que corre directamente en Fedora sin necesidad de tener Python ni Podman activos al usarlo.

1. **Compilar el binario:**
   Ejecuta el script automatizado (usa PyInstaller con `setup_linux.spec` dentro del entorno aislado):
   ```bash
   ./build_linux.sh
   ```

2. **Ubicación del ejecutable:**
   El binario generado se guardará en:
   ```bash
   dist/gnu-mau
   ```

3. **Ejecutar la aplicación nativa:**
   ```bash
   ./dist/gnu-mau
   ```

4. **(Opcional) Integración en el menú de aplicaciones de Fedora (GNOME / KDE):**
   Crea el archivo `.desktop`:
   ```bash
   cat << 'EOF' > ~/.local/share/applications/gnu-mau.desktop
   [Desktop Entry]
   Name=GNU Mau
   Comment=Multipurpose Automation Utility
   Exec=/home/ronal/Proyectos/GNU\ Mau-\ usando\ db\ mongita/dist/gnu-mau
   Icon=/home/ronal/Proyectos/GNU\ Mau-\ usando\ db\ mongita/assets/app/mau.png
   Terminal=false
   Type=Application
   Categories=Utility;Office;
   EOF

   update-desktop-database ~/.local/share/applications/
   ```

---

## 🪟 Windows

En Windows puedes ejecutar el código directamente con Poetry o generar el ejecutable `.exe` portable.

### Requisitos previos en Windows
* Python 3.11 instalado y añadido al PATH.
* Poetry instalado:
  ```powershell
  (Invoke-WebRequest -Uri https://install.python-poetry.org -UseBasicParsing).Content | py -
  ```

---

### Opción 1: Ejecutar en Modo Desarrollo

1. **Instalar dependencias:**
   ```powershell
   poetry install
   ```

2. **Ejecutar la aplicación:**
   ```powershell
   poetry run python main.py
   ```

---

### Opción 2: Compilar el Ejecutable `.exe`

Para Windows se utiliza el archivo de especificación original **`setup.spec`**.

1. **Compilar con PyInstaller:**
   Asegúrate de tener PyInstaller instalado en el entorno de Poetry y ejecuta:
   ```powershell
   poetry run pyinstaller setup.spec --clean
   ```

2. **Ubicación del ejecutable:**
   El archivo `.exe` se generará en la carpeta:
   ```text
   dist\GNU Mau\GNU Mau.exe
   ```
   (o en un solo archivo `dist\GNU Mau.exe` según la configuración del `.spec`).

---

## 📋 Resumen de Archivos Clave

| Archivo | Plataforma | Propósito |
| :--- | :--- | :--- |
| `start.sh` | Linux | Habilita `xhost` y levanta el contenedor en Podman. |
| `docker-compose.yml` | Linux | Configuración de volúmenes persistentes y pantalla X11. |
| `setup_linux.spec` | Linux | Configuración de PyInstaller para compilar binario ELF de Linux. |
| `build_linux.sh` | Linux | Compila el binario de Linux en `dist/gnu-mau`. |
| `setup.spec` | Windows | Configuración original de PyInstaller para Windows (`.exe` e icono `.ico`). |
| `pyproject.toml` | Ambas | Definición de dependencias de Python y versiones. |
