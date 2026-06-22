import os
from pathlib import Path

from backend.crawler import WORKSPACE

def create_folder(folder_name):
    
    folder = WORKSPACE / folder_name

    folder.mkdir(
        parents=True,
        exist_ok=True
    )

    return {
        "action": "create_folder",
        "folder": str(folder)
    }

def create_file(file_name, content=""):

    file_path = WORKSPACE / file_name

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "action": "create_file",
        "created": str(file_path)
    }

def read_file(file_name):
        
        file_path = WORKSPACE / file_name

        if not file_path.exists():
            return {"error": "file not found"}

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        return {"action": "read_file", "content": content}

def list_workspace():
    
        items = []

        for item in WORKSPACE.iterdir():
            items.append(item.name)

        return {"action": "list_workspace", "workspace": items}

def list_projects():
     
        projects_folder = WORKSPACE / "Projects"

        if not projects_folder.exists():
            return {"action": "list_projects", "projects": []}

        projects = []

        for item in projects_folder.iterdir():

            if item.is_dir():
                projects.append(item.name)

        return {"action": "list_projects", "projects": projects}
    
def show_project(project_name):
    
        project_root = WORKSPACE / "Projects" / project_name

        if not project_root.exists():
            return {"error": "project not found"}

        return {
            "project": project_name,
            "docs": os.listdir(project_root / "docs"),
            "notes": os.listdir(project_root / "notes"),
            "tasks": os.listdir(project_root / "tasks"),
            "memory": os.listdir(project_root / "memory"),
        }