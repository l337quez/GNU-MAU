<p align="center">
  <img src="assets/app/mau.png" alt="GNU Mau Logo" width="400">
</p>

# GNU Mau 😸🔧

**GNU Mau** (Multipurpose Automation Utility) is a specialized productivity tool designed for **Backend Engineers and DevOps Professionals**. It provides a centralized hub to organize projects, store critical commands, manage credentials, and keep track of daily tasks through a streamlined, themeable interface.

---

## ✨ Key Features

### 📁 Project Management

- **Centralized Info**: Store project-specific credentials, URLs, and documentation.
- **Embedded Terminal**: Execute project commands directly from the interface using quick-access terminal buttons.
- **Quick Copy**: One-click copying for sensitive data like API keys or server IPs.

### ✅ Advanced TODO Lists

- **Rich Text Support**: Bold formatting for important tasks.
- **Emoji Picker**: Personalize your lists with a built-in emoji selector.
- **Auto-Save**: Never lose progress with background saving.
- **Quick Copy**: Share your task lists instantly with the "Copy to Clipboard" feature.

### 📝 Markdown Notes

- **Live Preview**: Write in Markdown and see the rendered result instantly.
- **Theme-Aware**: Preview styles adjust automatically to your active theme (Dark/Light/Arctic).
- **Clean Formatting**: Use the "Sweep" tool to strip formatting and keep your notes tidy.
- **Emoji & Links**: Full support for emojis and clickable hyperlink insertion.

### 📊 Interactive Diagrams

- **Node-Based Editor**: Create architecture diagrams, database schemas, or flowcharts using an intuitive drag-and-drop interface.
- **Powered by `qtpynodeeditor`**: Built on a robust, native framework for offline node-graph editing in Python.
- **Customizable Components**: Add specialized nodes for text, database tables with column listings, and more.
- **Project-Linked**: Diagrams are automatically organized and saved as JSON within each project's storage.

### 🎨 Premium UI & Customization

- **Dynamic Themes**: Choose from **Arctic Mist**, **Amber Dusk**, **Dark**, or **Light** themes.
- **System Tray**: Keep Mau running in the background for quick access.
- **Responsive Design**: Elegant layouts built with PySide6 for a native desktop feel.

---

## 🚀 Setup & Installation

GNU Mau está organizado como un **monorepo** con dos proyectos independientes:

| Carpeta | Descripción | Tecnología |
|---------|-------------|------------|
| `desktop/` | Aplicación de escritorio | PySide6 + Poetry |
| `backend/` | API REST | FastAPI + uvicorn |

---

## 🖥️ Desktop App (PySide6)

La app de escritorio usa **Poetry** para la gestión de dependencias.

### Prerrequisitos

- Python 3.11+
- [Poetry](https://python-poetry.org/docs/#installation)

### Correr la aplicación

```bash
# 1. Entrar a la carpeta del desktop
cd desktop

# 2. Instalar dependencias
poetry install

# 3. Lanzar la aplicación
poetry run python app/main.py
```

> **Tip:** También puedes activar el entorno con `poetry shell` y luego correr `python app/main.py`.

---

## ⚡ Backend API (FastAPI)

La API REST corre en un entorno virtual propio dentro de `backend/`.

### Prerrequisitos

- Python 3.13+

### Correr la API

```bash
# 1. Entrar a la carpeta del backend
cd backend

# 2. Crear entorno virtual (solo la primera vez)
python -m venv venv

# 3. Instalar dependencias
#    En Git Bash / Linux / Mac:
venv/Scripts/pip install -r requirements.txt
#    En PowerShell / CMD:
venv\Scripts\pip install -r requirements.txt

# 4. Iniciar el servidor con recarga automática
#    En Git Bash / Linux / Mac:
venv/Scripts/uvicorn app.main:app --reload --port 8000
#    En PowerShell / CMD:
venv\Scripts\uvicorn app.main:app --reload --port 8000
```

### Endpoints disponibles

Una vez corriendo, accede a la documentación interactiva:

- **Swagger UI:** http://127.0.0.1:8000/docs
- **ReDoc:** http://127.0.0.1:8000/redoc
- **Health check:** http://127.0.0.1:8000/api/health

---

## 🛠️ Desarrollo Interno

### Desktop (Poetry)

- **Agregar paquete:** `poetry add <paquete>`
- **Eliminar paquete:** `poetry remove <paquete>`
- **Actualizar dependencias:** `poetry update`

### Backend (pip + venv)

- **Agregar paquete:** `venv/Scripts/pip install <paquete>` y luego actualizar `requirements.txt`

---

## ⚙️ Configuración & Base de Datos

GNU Mau usa **Mongita** (MongoDB embebido en Python) para almacenar los datos localmente. La base de datos se encuentra en:

```
desktop/app/mongita_data/
```

> ⚠️ La API backend apunta a esta misma base de datos. Asegúrate de no correr ambos procesos escribiendo simultáneamente en la misma colección para evitar conflictos.

---

_Designed with 🐾 for efficiency._
