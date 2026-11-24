"""
Session management with undo/redo for GNU Mau CLI.

Tracks the "active project" across commands and keeps an undo/redo stack
for project-level mutations.
"""
import os
import json
import copy

_SESSION_FILE = os.path.join(os.path.expanduser("~"), ".myapp", "cli_session.json")


def _load_session():
    if os.path.exists(_SESSION_FILE):
        with open(_SESSION_FILE, "r") as f:
            return json.load(f)
    return {"active_project_id": None, "undo_stack": [], "redo_stack": []}


def _save_session(session):
    os.makedirs(os.path.dirname(_SESSION_FILE), exist_ok=True)
    with open(_SESSION_FILE, "w") as f:
        json.dump(session, f, indent=2)


def get_active_project():
    """Return the currently active project id (or None)."""
    return _load_session().get("active_project_id")


def set_active_project(project_id):
    """Set the active project and clear undo/redo stacks."""
    session = _load_session()
    session["active_project_id"] = str(project_id) if project_id else None
    session["undo_stack"] = []
    session["redo_stack"] = []
    _save_session(session)
    return session


def push_undo(action_name, snapshot):
    """Push a state snapshot onto the undo stack."""
    session = _load_session()
    session["undo_stack"].append({"action": action_name, "snapshot": snapshot})
    session["redo_stack"] = []  # Clear redo on new action
    # Keep max 50 undo entries
    session["undo_stack"] = session["undo_stack"][-50:]
    _save_session(session)


def undo():
    """Pop and return the last undo entry (or None)."""
    session = _load_session()
    if not session["undo_stack"]:
        return None
    entry = session["undo_stack"].pop()
    session["redo_stack"].append(entry)
    _save_session(session)
    return entry


def redo():
    """Pop and return the last redo entry (or None)."""
    session = _load_session()
    if not session["redo_stack"]:
        return None
    entry = session["redo_stack"].pop()
    session["undo_stack"].append(entry)
    _save_session(session)
    return entry


def get_session_status():
    """Return full session status."""
    session = _load_session()
    return {
        "active_project_id": session.get("active_project_id"),
        "undo_depth": len(session.get("undo_stack", [])),
        "redo_depth": len(session.get("redo_stack", [])),
    }
