"""
Core project management module for GNU Mau CLI.

Provides CRUD operations for projects in the Mongita database,
including the nested info key-value store.
"""
import os
import json
from mongita import MongitaClientDisk
from bson.objectid import ObjectId


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _resolve_db_path(db_path=None):
    """Resolve the Mongita database directory.

    Priority:
    1. Explicitly passed *db_path*
    2. ``GNUMAU_DB_PATH`` environment variable
    3. ``./mongita_data`` relative to cwd
    """
    if db_path:
        return os.path.abspath(db_path)
    env = os.environ.get("GNUMAU_DB_PATH")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.getcwd(), "mongita_data")


def get_client(db_path=None):
    """Return a ``MongitaClientDisk`` instance."""
    path = _resolve_db_path(db_path)
    return MongitaClientDisk(path)


def get_db(db_path=None, db_name="projects_db"):
    """Return the Mongita database handle."""
    client = get_client(db_path)
    return client[db_name]


# ---------------------------------------------------------------------------
# Storage helpers
# ---------------------------------------------------------------------------

def _resolve_storage_path(storage_path=None):
    """Resolve the file storage directory.

    Priority:
    1. Explicitly passed *storage_path*
    2. ``GNUMAU_STORAGE_PATH`` environment variable
    3. ``./storage`` relative to cwd
    """
    if storage_path:
        return os.path.abspath(storage_path)
    env = os.environ.get("GNUMAU_STORAGE_PATH")
    if env:
        return os.path.abspath(env)
    return os.path.join(os.getcwd(), "storage")


def get_storage_dir(project_id, storage_path=None):
    """Return (and create if missing) the project's file storage directory."""
    base = _resolve_storage_path(storage_path)
    path = os.path.join(base, str(project_id))
    os.makedirs(path, exist_ok=True)
    return path


# ---------------------------------------------------------------------------
# Project CRUD
# ---------------------------------------------------------------------------

def list_projects(db_path=None):
    """Return a list of all projects as dicts (with stringified ``_id``)."""
    db = get_db(db_path)
    results = []
    for p in db.projects.find():
        p["_id"] = str(p["_id"])
        results.append(p)
    return results


def get_project(project_id, db_path=None):
    """Return a single project dict or ``None``."""
    db = get_db(db_path)
    oid = ObjectId(project_id) if isinstance(project_id, str) else project_id
    p = db.projects.find_one({"_id": oid})
    if p:
        p["_id"] = str(p["_id"])
    return p


def create_project(name, description="", icon_path=None, db_path=None):
    """Create a new project and return its dict with ``_id``."""
    db = get_db(db_path)
    doc = {
        "name": name,
        "description": description,
        "info": {},
        "icon_path": icon_path or "assets/project_images/default_icon.png",
    }
    result = db.projects.insert_one(doc)
    doc["_id"] = str(result.inserted_id)

    # Create on-disk storage folder
    get_storage_dir(doc["_id"])
    return doc


def update_project(project_id, name=None, description=None, icon_path=None,
                   db_path=None):
    """Update project metadata fields.  Only non-``None`` values are updated."""
    db = get_db(db_path)
    oid = ObjectId(project_id) if isinstance(project_id, str) else project_id
    updates = {}
    if name is not None:
        updates["name"] = name
    if description is not None:
        updates["description"] = description
    if icon_path is not None:
        updates["icon_path"] = icon_path
    if not updates:
        return get_project(project_id, db_path)
    db.projects.update_one({"_id": oid}, {"$set": updates})
    return get_project(project_id, db_path)


def delete_project(project_id, db_path=None):
    """Delete a project and its related todos from the database.

    Does **not** remove on-disk files (notes / diagrams).
    """
    db = get_db(db_path)
    oid = ObjectId(project_id) if isinstance(project_id, str) else project_id
    db.projects.delete_one({"_id": oid})
    # Delete related todos
    db.todos.delete_many({"project_id": str(project_id)})
    return {"deleted": str(project_id)}


# ---------------------------------------------------------------------------
# Info (key-value) CRUD
# ---------------------------------------------------------------------------

def list_info(project_id, db_path=None):
    """Return the info dict for a project."""
    p = get_project(project_id, db_path)
    if not p:
        return {}
    return p.get("info", {})


def add_info(project_id, key, value, action=None, category="", db_path=None):
    """Add or overwrite a key-value info entry on a project."""
    db = get_db(db_path)
    oid = ObjectId(project_id) if isinstance(project_id, str) else project_id
    info = list_info(project_id, db_path)
    info[key] = {"value": value, "action": action, "category": category}
    db.projects.update_one({"_id": oid}, {"$set": {"info": info}})
    return info[key]


def delete_info(project_id, key, db_path=None):
    """Delete a single info key from a project."""
    db = get_db(db_path)
    oid = ObjectId(project_id) if isinstance(project_id, str) else project_id
    info = list_info(project_id, db_path)
    removed = info.pop(key, None)
    db.projects.update_one({"_id": oid}, {"$set": {"info": info}})
    return {"deleted_key": key, "deleted_value": removed}
