from ollama import chat

from backend.filesystem import safe_project_path
from backend.memory import load_memory


def _project_root(project_name):
    try:
        return safe_project_path(project_name)
    except ValueError as exc:
        return None, str(exc)


def create_project(project_name):
    project_root, error = _project_root(project_name)
    if error:
        return {"error": error}
    project_root.mkdir(parents=True, exist_ok=True)
    for folder in ("docs", "notes", "tasks", "memory"):
        (project_root / folder).mkdir(exist_ok=True)
    return {"action": "create_project", "project": project_name, "path": str(project_root)}


def create_note(project_name, file_name):
    project_root, error = _project_root(project_name)
    if error:
        return {"error": error}
    if not project_root.exists():
        return {"error": "project not found"}
    try:
        note_file = (project_root / "notes" / file_name).resolve()
        note_file.relative_to((project_root / "notes").resolve())
    except (ValueError, OSError):
        return {"error": "invalid note path"}
    note_file.parent.mkdir(parents=True, exist_ok=True)
    note_file.write_text("", encoding="utf-8")
    return {"action": "create_note", "project": project_name, "file": str(note_file)}


def write_note(project_name, file_name, content):
    project_root, error = _project_root(project_name)
    if error:
        return {"error": error}
    if not project_root.exists():
        return {"error": "project not found"}
    try:
        note_file = (project_root / "notes" / file_name).resolve()
        note_file.relative_to((project_root / "notes").resolve())
    except (ValueError, OSError):
        return {"error": "invalid note path"}
    note_file.write_text(content, encoding="utf-8")
    return {"action": "write_note", "project": project_name, "file": str(note_file)}


def remember_in_project(project_name, memory_text):
    project_root, error = _project_root(project_name)
    if error:
        return {"error": error}
    if not project_root.exists():
        return {"error": "project not found"}
    memory_file = project_root / "memory" / "memory.txt"
    memory_file.parent.mkdir(parents=True, exist_ok=True)
    with memory_file.open("a", encoding="utf-8") as f:
        f.write(memory_text + "\n")
    return {"action": "project_memory_saved", "project": project_name, "memory": memory_text}


def show_project_memory(project_name):
    project_root, error = _project_root(project_name)
    if error:
        return {"error": error}
    if not project_root.exists():
        return {"error": "project not found"}
    memory_file = project_root / "memory" / "memory.txt"
    if not memory_file.exists():
        return {"project": project_name, "memory": []}
    memories = [line.strip() for line in memory_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    return {"project": project_name, "memory": memories}


def search_project(project_name):
    project_root, error = _project_root(project_name)
    if error:
        return {"error": error}
    if not project_root.exists():
        return {"error": "project not found"}
    notes_folder = project_root / "notes"
    memory_file = project_root / "memory" / "memory.txt"
    notes = [item.name for item in notes_folder.iterdir() if item.is_file()] if notes_folder.exists() else []
    memories = [line.strip() for line in memory_file.read_text(encoding="utf-8").splitlines() if line.strip()] if memory_file.exists() else []
    return {"project": project_name, "notes": notes, "memories": memories}


def ask_project(project_name, question):
    project_root, error = _project_root(project_name)
    if error:
        return {"error": error}
    if not project_root.exists():
        return {"error": "project not found"}
    notes_folder = project_root / "notes"
    memory_file = project_root / "memory" / "memory.txt"
    notes = []
    if notes_folder.exists():
        for note in notes_folder.iterdir():
            if note.is_file():
                try:
                    notes.append({"name": note.name, "content": note.read_text(encoding="utf-8")})
                except OSError:
                    notes.append({"name": note.name, "content": "[could not read]"})
    memories = [line.strip() for line in memory_file.read_text(encoding="utf-8").splitlines() if line.strip()] if memory_file.exists() else []
    project_context = f"Global Memory:\n{load_memory()}\n\nProject:\n{project_name}\n\nProject Notes:\n{notes}\n\nProject Memories:\n{memories}"
    response = chat(model="llama3:latest", messages=[
        {"role": "system", "content": f"You are GEAI. Use the project information below when answering.\n\n{project_context}"},
        {"role": "user", "content": question},
    ])
    return {"project": project_name, "answer": response["message"]["content"]}
