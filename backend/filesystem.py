import os
from pathlib import Path

from backend.crawler import WORKSPACE


def safe_workspace_path(name: str) -> Path:
    """Resolve a user-supplied workspace path without allowing path traversal."""
    if not isinstance(name, str) or not name.strip():
        raise ValueError("path must not be empty")

    root = WORKSPACE.resolve()
    candidate = (root / name).resolve()

    try:
        candidate.relative_to(root)
    except ValueError as exc:
        raise ValueError("path must remain inside the GEAI workspace") from exc

    return candidate


def safe_project_path(project_name: str) -> Path:
    project_root = safe_workspace_path(Path("Projects") / project_name)
    if project_root == WORKSPACE.resolve() or project_root.name in {".", ".."}:
        raise ValueError("invalid project name")
    return project_root


def create_folder(folder_name):
    folder = safe_workspace_path(folder_name)
    folder.mkdir(parents=True, exist_ok=True)
    return {"action": "create_folder", "folder": str(folder)}


def create_file(file_name, content=""):
    file_path = safe_workspace_path(file_name)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)
    return {"action": "create_file", "created": str(file_path)}


def read_file(file_name):
    file_path = safe_workspace_path(file_name)
    if not file_path.exists() or not file_path.is_file():
        return {"error": "file not found"}
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    return {"action": "read_file", "content": content}


def list_workspace():
    items = [item.name for item in WORKSPACE.iterdir()]
    return {"action": "list_workspace", "workspace": items}


def list_projects():
    projects_folder = WORKSPACE / "Projects"
    if not projects_folder.exists():
        return {"action": "list_projects", "projects": []}
    projects = [item.name for item in projects_folder.iterdir() if item.is_dir()]
    return {"action": "list_projects", "projects": projects}


def show_project(project_name):
    project_root = safe_project_path(project_name)
    if not project_root.exists() or not project_root.is_dir():
        return {"error": "project not found"}

    result = {"project": project_name}
    for folder in ("docs", "notes", "tasks", "memory"):
        directory = project_root / folder
        result[folder] = os.listdir(directory) if directory.exists() else []
    return result
