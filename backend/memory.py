from pathlib import Path
import json

MEMORY_FILE = Path(r"D:\GEAI\memory\memory.json")
INDEX_FILE = Path(r"D:\GEAI\memory\memory_index.json")
CONCEPTS_FILE = Path(r"D:\GEAI\memory\concepts.json")

ALIASES_FILE = MEMORY_FILE.parent / "aliases.txt"


def load_memory():
    if not MEMORY_FILE.exists():
        return []

    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return []


def save_memory(memory):
    with open(MEMORY_FILE, "w", encoding="utf-8") as f:
        json.dump(memory, f, indent=2)

def load_index():

    if not INDEX_FILE.exists():
        return {}

    try:

        with open(
            INDEX_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}


def save_index(index):

    with open(
        INDEX_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            index,
            f,
            indent=2
        )

def load_concepts():

    if not CONCEPTS_FILE.exists():
        return {}

    try:

        with open(
            CONCEPTS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:
        return {}


def save_concepts(concepts):

    with open(
        CONCEPTS_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            concepts,
            f,
            indent=2
        )
