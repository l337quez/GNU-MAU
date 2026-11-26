<p align="center">
  <img src="desktop/assets/banner/mau_server_mcp.png" alt="GNU Mau Logo" width="400">
</p>

# Mau 😸🔧

![Python](https://img.shields.io/badge/python-3.11+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![Mongita](https://img.shields.io/badge/Mongita-Embedded_DB-4ea94b?style=for-the-badge&logo=mongodb&logoColor=white)
![PySide6](https://img.shields.io/badge/PySide6-Desktop-41CD52?style=for-the-badge&logo=qt&logoColor=white)

![Swagger](https://img.shields.io/badge/Swagger-Docs-%2385ea2d?logo=swagger&logoColor=black)
![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Status](https://img.shields.io/badge/status-active-brightgreen)

**Mau** *(Multipurpose Automation Utility)* is a powerful, open-source **Knowledge Management API Backend**. Designed to structure and centralize complex information, it acts as a semantic graph engine where your technical data and ideas live interconnectedly.

Rather than just storing flat data, GNU Mau organizes everything around **Projects**, providing a comprehensive ecosystem to manage architecture diagrams, task lists, credentials, and rich Markdown notes. It features native security, allowing users to **encrypt sensitive data** directly at the application layer.

Built on **FastAPI**, the backend leverages multi-model database architectures (**Mongita / MongoDB** for structured document storage, and **ArangoDB** for lightning-fast graph resolution and semantic knowledge relationships).

---

## 📑 Table of Contents

- [✨ Features](#-key-features)
- [🏗️ Architecture](#️-project-architecture)
- [⚡ Requirements](#-requirements)
- [📦 Installation](#-setup--installation)
- [🖥️ Desktop App](#️-desktop-app-pyside6)
- [⚡ Backend API](#-backend-api-fastapi)
- [📚 API Documentation](#-api-documentation--swagger)
- [🗂️ API Modules](#️-api-modules)
- [⚙️ Database](#️-configuration--database)
- [🛠️ Development](#️-internal-development)

---

## ✨ Key Features

### 📁 Project-Centric Organization

- **Unified Ecosystem**: Every piece of knowledge—from architecture diagrams to credentials—is grouped into logical Projects.
- **Data Encryption**: Native support for encrypting sensitive data directly via the API, ensuring credentials and private notes remain secure.
- **RESTful Architecture**: Clean, modular, and fully documented endpoints ready to be consumed by any frontend or AI agent.

### 📋 Information Modules

- **Diagrams**: Store and retrieve complete node/edge structures for architecture canvases.
- **Notes & Knowledge**: High-performance module that parses Markdown to build semantic knowledge graphs.
- **Tasks & TODOs**: Manage complex, structured task lists linked directly to your projects.
- **Snippets & Credentials**: Store raw information items (URLs, code snippets, secrets) with optional encryption.

### 🧠 Semantic Graph Engine

- **ArangoDB Powered**: Store notes and metadata in a high-performance multi-model graph database.
- **Bidirectional Linking**: Automatically extracts `[[links]]` and `#tags` to build a real-time knowledge network.
- **Vector-Search Ready**: Architecture designed from the ground up to support AI Embeddings and RAG.
- **Graph Traversals**: Native endpoints for backlinks and full graph rendering using AQL.

---

## 🏗️ Project Architecture

GNU Mau is organized as a **monorepo** with two independent projects:

| Folder | Description | Technology |
|--------|-------------|------------|
| `desktop/` | Desktop application | PySide6 + Poetry |
| `backend/` | REST API | FastAPI + Uvicorn + Mongita |

The backend follows a **strict layered architecture** per feature module:

```
backend/app/api/<module>/
├── model.py       ← Pydantic domain model (DB document structure)
├── schemas.py     ← DTOs: input (Create/Update) and output (Response)
├── service.py     ← Business logic layer (no HTTP, no SQL)
├── repository.py  ← Data access layer (Mongita CRUD)
└── router.py      ← HTTP controller (thin — only routes & DI)
```

---

## ⚡ Requirements

![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)
![Poetry](https://img.shields.io/badge/poetry-1.7+-60A5FA?logo=poetry&logoColor=white)

| Component | Version | Notes |
|-----------|---------|-------|
| **Python** | 3.11+ | Desktop |
| **Python** | 3.13+ | Backend API |
| **Poetry** | 1.7+ | Desktop dependency manager |
| **pip + venv** | — | Backend dependency manager |

---

## 📦 Setup & Installation

### Clone the repository

```bash
git clone https://github.com/l337quez/GNU-MAU.git
cd GNU-MAU
```

---

## 🖥️ Desktop App (PySide6)

The desktop app uses **Poetry** for dependency management.

### Run the app

```bash
# 1. Enter the desktop folder
cd desktop

# 2. Install dependencies
poetry install

# 3. Launch the application
poetry run python app/main.py
```

> [!TIP]
> You can also activate the virtual environment with `poetry shell` and then run `python app/main.py` directly.

---

## ⚡ Backend API (FastAPI)

The REST API runs in its own environment inside `backend/` managed by **Poetry**.

### Run the API

```bash
# 1. Enter the backend folder
cd backend

# 2. Install dependencies
poetry install

# 3. Start the server with auto-reload
poetry run uvicorn app.main:app --reload --port 9000
```

### Run with Docker Compose (Recommended for Servers & Production)

You can run the entire backend stack (FastAPI backend + MongoDB database) using Docker and Docker Compose. This is ideal for server deployment or containerized development:

```bash
# 1. From the project root, start the container stack:
docker compose up -d --build

# 2. Check the container logs:
docker compose logs -f

# 3. Stop the containers:
docker compose down
```

The database container stores its data persistently in a Docker volume called `mongodb_data`, and the API container enlazes automatically with it.

> [!CAUTION]
> Do **not** run the desktop app and the backend simultaneously if both are writing to the same Mongita collection, as this may cause conflicts.

---

## 📚 API Documentation & Swagger

Once the backend is running, access the interactive API documentation:

| Interface | URL | Description |
|-----------|-----|-------------|
| **Swagger UI** | [http://127.0.0.1:9000/docs](http://127.0.0.1:9000/docs) | Interactive API explorer |
| **ReDoc** | [http://127.0.0.1:9000/redoc](http://127.0.0.1:9000/redoc) | Clean reference documentation |
| **Health Check** | [http://127.0.0.1:9000/api/health](http://127.0.0.1:9000/api/health) | API status |

> [!NOTE]
> Swagger UI allows you to test every endpoint directly from the browser — no Postman needed.

---

## 🗂️ API Modules

### 📁 Projects — `/api/projects`

CRUD completo de proyectos. Soporta ícono personalizado e items de info embebidos.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/projects/` | List all projects |
| `GET` | `/api/projects/{id}` | Get project by ID |
| `POST` | `/api/projects/` | Create a new project |
| `PUT` | `/api/projects/{id}` | Update project fields |
| `PATCH` | `/api/projects/{id}/icon` | Update project icon |
| `PATCH` | `/api/projects/{id}/info` | Add or update an info item |
| `DELETE` | `/api/projects/{id}/info/{key}` | Delete an info item |
| `DELETE` | `/api/projects/{id}` | Delete a project |

---

### 📋 Information — `/api/information`

Items de información independientes (comandos, URLs, notas). Pueden vincularse opcionalmente a un proyecto.

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/information/` | List all items (filter by `?project_id=`) |
| `GET` | `/api/information/{id}` | Get item by ID |
| `POST` | `/api/information/` | Create a new information item |
| `PUT` | `/api/information/{id}` | Update item fields |
| `DELETE` | `/api/information/{id}` | Delete an item |

#### Information Item fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `title` | `str` | ✅ | Title of the item |
| `content` | `str` | ✅ | Content or value |
| `category` | `str` | ❌ | Free category (e.g. `git`, `docker`) |
| `action` | `str \| null` | ❌ | `"terminal"`, `"browser"`, or `null` |
| `project_id` | `str \| null` | ❌ | ID of the linked project |

---

## ⚙️ Configuration & Database

GNU Mau features a **dynamic database engine selection** system. You can choose to run with an embedded local database (no installation needed) or connect to a professional, dedicated MongoDB server.

### 🔌 Database Engines

| Engine (`DB_ENGINE`) | Type | Description | Best For |
|---|---|---|---|
| **`mongita`** (Default) | Embedded | Stores collections directly in local files. | Local development, isolated desktop app |
| **`mongodb`** | Server | Connects to a standard MongoDB server (local, Docker, Atlas). | Production, Docker environments, shared setups |

### 📂 Mongita Database Location
When using `mongita`, data is stored in the local directory:
```
desktop/app/mongita_data/
```

> [!IMPORTANT]
> When using `mongita`, both the desktop app and the backend API point to the **same database directory**. Avoid having both processes write to the same collection simultaneously to prevent file locks.

### ⚙️ Environment Variables (`.env`)

The backend reads its configuration from a `.env` file inside the `backend/` directory. Create a `.env` file based on [.env.example](file:///c:/Users/l337q/OneDrive/Desktop/PROYECTOS/GNU-MAU/backend/.env.example):

| Variable | Default | Allowed Values | Description |
|----------|---------|----------------|-------------|
| `DB_ENGINE` | `mongita` | `mongita`, `mongodb` | The database engine to load. |
| `MONGODB_URI` | `mongodb://localhost:27017` | Any valid MongoDB URI | MongoDB connection string (used only if `DB_ENGINE=mongodb`). |
| `MONGITA_DB_DIR` | `../desktop/app/mongita_data` | Filepath | Path to the Mongita database directory (used only if `DB_ENGINE=mongita`). |
| `DB_NAME` | `projects_db` | Any string | The name of the database. |
| `DEBUG` | `true` | `true`, `false` | Enable or disable debug mode. |

---

## 🛠️ Internal Development

### Desktop (Poetry)

```bash
# Add a package
poetry add <package>

# Remove a package
poetry remove <package>

# Update dependencies
poetry update
```

### Backend (Poetry)

```bash
# Add a package
poetry add <package>

# Remove a package
poetry remove <package>

# Update dependencies
poetry update
```

### Adding a new API module

Follow the layered structure for every new feature:

1. Create `app/api/<module>/model.py` — Pydantic domain model
2. Create `app/api/<module>/schemas.py` — Input/output DTOs
3. Create `app/api/<module>/service.py` — Business logic
4. Create `app/api/<module>/repository.py` — Mongita CRUD
5. Create `app/api/<module>/router.py` — HTTP routes
6. Create `app/api/<module>/__init__.py` — Module exports
7. Register the router in `app/api/routers.py`

---

## 📝 License

This project is licensed under the **Apache License 2.0**.
See [LICENSE](LICENSE) for full details.

---

_Designed with 🐾 for efficiency._
