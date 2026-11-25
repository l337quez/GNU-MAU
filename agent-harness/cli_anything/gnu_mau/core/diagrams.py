"""
Diagram management module for GNU Mau CLI.

Diagrams are stored as JSON files in ``storage/<project_id>/``.
This module handles pure file-based CRUD for the diagram JSON files.
It does NOT require qtpynodeeditor to be installed — it reads/writes
the serialized JSON representation directly.
"""
import os
import json
from cli_anything.gnu_mau.core import get_storage_dir


def list_diagrams(project_id, storage_path=None):
    """Return metadata for all diagram JSON files of a project."""
    d = get_storage_dir(project_id, storage_path)
    results = []
    for f in os.listdir(d):
        if f.endswith(".json"):
            full = os.path.join(d, f)
            try:
                with open(full, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                nodes_count = len(data.get("nodes", []))
                conns_count = len(data.get("connections", []))
            except (json.JSONDecodeError, KeyError):
                nodes_count = 0
                conns_count = 0
            results.append({
                "filename": f,
                "path": full,
                "size_bytes": os.path.getsize(full),
                "nodes": nodes_count,
                "connections": conns_count,
            })
    return results


def get_diagram(project_id, filename, storage_path=None):
    """Load and return a diagram's full JSON content."""
    d = get_storage_dir(project_id, storage_path)
    path = os.path.join(d, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Diagram not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return {
        "filename": filename,
        "path": path,
        "data": data,
    }


def create_diagram(project_id, name, storage_path=None):
    """Create an empty diagram JSON file."""
    if not name.endswith(".json"):
        name += ".json"
    d = get_storage_dir(project_id, storage_path)
    path = os.path.join(d, name)
    if os.path.exists(path):
        raise FileExistsError(f"Diagram already exists: {path}")
    data = {"nodes": [], "connections": []}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return {
        "filename": name,
        "path": path,
        "data": data,
    }


def add_node(project_id, diagram_filename, node_type="TextNode",
             name="New Node", x=0.0, y=0.0, model_data=None,
             storage_path=None):
    """Add a node to an existing diagram file."""
    diag = get_diagram(project_id, diagram_filename, storage_path)
    data = diag["data"]

    # Generate a simple unique id
    existing_ids = {n.get("id", "") for n in data.get("nodes", [])}
    idx = len(existing_ids)
    while str(idx) in existing_ids:
        idx += 1
    node_id = str(idx)

    node = {
        "id": node_id,
        "name": node_type,
        "position": {"x": x, "y": y},
        "model_data": model_data or {"text": name},
    }
    data["nodes"].append(node)

    path = diag["path"]
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    return node


def delete_diagram(project_id, filename, storage_path=None):
    """Delete a diagram JSON file."""
    d = get_storage_dir(project_id, storage_path)
    path = os.path.join(d, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Diagram not found: {path}")
    os.remove(path)
    return {"deleted": filename}
