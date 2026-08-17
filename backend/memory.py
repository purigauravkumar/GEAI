import json
import os
from pathlib import Path

# Keep user data outside the source tree by default. Override with GEAI_HOME.
GEAI_HOME = Path(os.getenv("GEAI_HOME", Path.home() / "GEAI")).expanduser().resolve()
MEMORY_DIR = GEAI_HOME / "memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

MEMORY_FILE = MEMORY_DIR / "memory.json"
INDEX_FILE = MEMORY_DIR / "memory_index.json"
CONCEPTS_FILE = MEMORY_DIR / "concepts.json"
ALIASES_FILE = MEMORY_DIR / "aliases.txt"


def _load_json(path, default):
    if not path.exists():
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            value = json.load(f)
        return value
    except (OSError, json.JSONDecodeError):
        return default


def _save_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(value, f, indent=2, ensure_ascii=False)
    os.replace(temporary, path)


def load_memory():
    return _load_json(MEMORY_FILE, [])


def save_memory(memory):
    _save_json(MEMORY_FILE, memory)


def load_index():
    return _load_json(INDEX_FILE, {})


def save_index(index):
    _save_json(INDEX_FILE, index)


def load_concepts():
    return _load_json(CONCEPTS_FILE, {})


def save_concepts(concepts):
    _save_json(CONCEPTS_FILE, concepts)
