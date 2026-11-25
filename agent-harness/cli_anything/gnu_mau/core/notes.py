"""
Notes management module for GNU Mau CLI.

Notes are stored as plain files on disk under ``storage/<project_id>/``.
Supported formats: Markdown (``.md``) and Rich Text (``.txt``).
"""
import os
from cli_anything.gnu_mau.core import get_storage_dir


def list_notes(project_id, storage_path=None):
    """Return a list of note metadata dicts for a project."""
    notes_dir = get_storage_dir(project_id, storage_path)
    results = []
    for f in os.listdir(notes_dir):
        if f.endswith((".md", ".txt")):
            full = os.path.join(notes_dir, f)
            results.append({
                "filename": f,
                "path": full,
                "size_bytes": os.path.getsize(full),
                "type": "markdown" if f.endswith(".md") else "richtext",
            })
    return results


def get_note(project_id, filename, storage_path=None):
    """Read and return the content of a note file."""
    notes_dir = get_storage_dir(project_id, storage_path)
    path = os.path.join(notes_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Note not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    return {
        "filename": filename,
        "path": path,
        "content": content,
        "size_bytes": os.path.getsize(path),
    }


def create_note(project_id, name, note_type="md", storage_path=None):
    """Create a new note file.  *note_type* is ``'md'`` or ``'txt'``."""
    ext = f".{note_type}" if not name.endswith(f".{note_type}") else ""
    filename = f"{name}{ext}"
    notes_dir = get_storage_dir(project_id, storage_path)
    path = os.path.join(notes_dir, filename)
    if os.path.exists(path):
        raise FileExistsError(f"Note already exists: {path}")
    if note_type == "txt":
        content = "<html><body><p>My rich note content...</p></body></html>"
    else:
        bare = name.replace(".md", "").replace(".txt", "")
        content = f"# {bare}\n\nWrite here..."
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {
        "filename": filename,
        "path": path,
        "content": content,
        "size_bytes": os.path.getsize(path),
    }


def update_note(project_id, filename, content, storage_path=None):
    """Overwrite a note's content."""
    notes_dir = get_storage_dir(project_id, storage_path)
    path = os.path.join(notes_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Note not found: {path}")
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return {
        "filename": filename,
        "path": path,
        "size_bytes": os.path.getsize(path),
    }


def delete_note(project_id, filename, storage_path=None):
    """Delete a note file from disk."""
    notes_dir = get_storage_dir(project_id, storage_path)
    path = os.path.join(notes_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Note not found: {path}")
    os.remove(path)
    return {"deleted": filename}


def rename_note(project_id, old_name, new_name, storage_path=None):
    """Rename a note file."""
    notes_dir = get_storage_dir(project_id, storage_path)
    old_path = os.path.join(notes_dir, old_name)
    new_path = os.path.join(notes_dir, new_name)
    if not os.path.exists(old_path):
        raise FileNotFoundError(f"Note not found: {old_path}")
    if os.path.exists(new_path):
        raise FileExistsError(f"Target already exists: {new_path}")
    os.rename(old_path, new_path)
    return {"old_name": old_name, "new_name": new_name, "path": new_path}
