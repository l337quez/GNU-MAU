"""
TODO management module for GNU Mau CLI.

Provides CRUD operations for TODO lists stored in the Mongita database.
"""
from bson.objectid import ObjectId
from cli_anything.gnu_mau.core import get_db


def list_todos(project_id, db_path=None):
    """Return all TODOs for a given project as a list of dicts."""
    db = get_db(db_path)
    results = []
    for t in db.todos.find({"project_id": str(project_id)}):
        t["_id"] = str(t["_id"])
        results.append(t)
    return results


def get_todo(todo_id, db_path=None):
    """Return a single TODO dict or ``None``."""
    db = get_db(db_path)
    oid = ObjectId(todo_id) if isinstance(todo_id, str) else todo_id
    t = db.todos.find_one({"_id": oid})
    if t:
        t["_id"] = str(t["_id"])
    return t


def create_todo(project_id, title="New TODO", content="☐ My first task",
                db_path=None):
    """Create a new TODO linked to *project_id*."""
    db = get_db(db_path)
    doc = {
        "title": title,
        "content": content,
        "project_id": str(project_id),
    }
    result = db.todos.insert_one(doc)
    doc["_id"] = str(result.inserted_id)
    return doc


def update_todo(todo_id, title=None, content=None, db_path=None):
    """Update a TODO.  Only non-``None`` fields are changed."""
    db = get_db(db_path)
    oid = ObjectId(todo_id) if isinstance(todo_id, str) else todo_id
    updates = {}
    if title is not None:
        updates["title"] = title
    if content is not None:
        updates["content"] = content
    if not updates:
        return get_todo(todo_id, db_path)
    db.todos.update_one({"_id": oid}, {"$set": updates})
    return get_todo(todo_id, db_path)


def delete_todo(todo_id, db_path=None):
    """Delete a TODO by its id."""
    db = get_db(db_path)
    oid = ObjectId(todo_id) if isinstance(todo_id, str) else todo_id
    db.todos.delete_one({"_id": oid})
    return {"deleted": str(todo_id)}
