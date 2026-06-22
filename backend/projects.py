from backend.memory import *
from backend.crawler import *
from pathlib import Path
import os
from ollama import chat

def create_project(project_name):

    project_root = WORKSPACE / "Projects" / project_name

    (project_root / "docs").mkdir(parents=True, exist_ok=True)
    (project_root / "notes").mkdir(parents=True, exist_ok=True)
    (project_root / "tasks").mkdir(parents=True, exist_ok=True)
    (project_root / "memory").mkdir(parents=True, exist_ok=True)

    return {
        "action": "create_project",
        "project": project_name,
        "path": str(project_root),
    }

def create_note(project_name, file_name):

    project_root = WORKSPACE / "Projects" / project_name

    if not project_root.exists():
        return {"error": "project not found"}

    note_file = project_root / "notes" / file_name

    with open(note_file, "w", encoding="utf-8") as f:
        f.write("")

    return {
        "action": "create_note",
        "project": project_name,
        "file": str(note_file),
    }

def write_note(project_name, file_name, content):

    project_root = WORKSPACE / "Projects" / project_name

    if not project_root.exists():
        return {"error": "project not found"}

    note_file = project_root / "notes" / file_name

    with open(note_file, "w", encoding="utf-8") as f:
        f.write(content)

    return {
        "action": "write_note",
        "project": project_name,
        "file": str(note_file)
    }

def remember_in_project(project_name, memory_text):

    project_root = WORKSPACE / "Projects" / project_name

    if not project_root.exists():
        return {"error": "project not found"}

    memory_file = project_root / "memory" / "memory.txt"

    with open(memory_file, "a", encoding="utf-8") as f:
        f.write(memory_text + "\n")

    return {
        "action": "project_memory_saved",
        "project": project_name,
        "memory": memory_text,
    }

def show_project_memory(project_name):

    project_root = WORKSPACE / "Projects" / project_name

    if not project_root.exists():
        return {"error": "project not found"}

    memory_file = project_root / "memory" / "memory.txt"

    if not memory_file.exists():
        return {
            "project": project_name,
            "memory": []
        }

    with open(memory_file, "r", encoding="utf-8") as f:
        memories = f.readlines()

    memories = [
        m.strip()
        for m in memories
        if m.strip()
    ]

    return {
        "project": project_name,
        "memory": memories
    }

def search_project(project_name):

    project_root = WORKSPACE / "Projects" / project_name

    if not project_root.exists():
        return {"error": "project not found"}

    notes_folder = project_root / "notes"
    memory_file = project_root / "memory" / "memory.txt"

    notes = []
    memories = []

    if notes_folder.exists():

        for note in notes_folder.iterdir():

            if note.is_file():

                notes.append(note.name)

    if memory_file.exists():

        with open(memory_file, "r", encoding="utf-8") as f:

            memories = [
                line.strip()
                for line in f.readlines()
                if line.strip()
            ]

    return {
        "project": project_name,
        "notes": notes,
        "memories": memories
    }

def ask_project(project_name, question):

        project_root = WORKSPACE / "Projects" / project_name

        if not project_root.exists():
            return {"error": "project not found"}

        notes_folder = project_root / "notes"
        memory_file = project_root / "memory" / "memory.txt"
        notes = []
        memories = []

        if notes_folder.exists():
            for note in notes_folder.iterdir():
                if note.is_file():
                    try:
                        with open(note, "r", encoding="utf-8") as f:
                            content = f.read()

                        notes.append({"name": note.name, "content": content})
                    except Exception:
                        notes.append({"name": note.name, "content": "[could not read]"})

        if memory_file.exists():
            with open(memory_file, "r", encoding="utf-8") as f:
                memories = [line.strip() for line in f.readlines() if line.strip()]

        global_memory = load_memory()

        project_context = f"""

Global Memory:
{global_memory}

Project:
{project_name}

Project Notes:
{notes}

Project Memories:
{memories}
"""

        response = chat(
            model="llama3:latest",
            messages=[
                {
                    "role": "system",
                    "content": f"""
You are GEAI.

Use the project information below when answering.

{project_context}
""",
                },
                {"role": "user", "content": question},
            ],
        )

        return {"project": project_name, "answer": response["message"]["content"]}
