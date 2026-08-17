import json
from backend.memory import MEMORY_DIR

FACTS_FILE = MEMORY_DIR / "facts.json"


def load_facts():
    if not FACTS_FILE.exists():
        return {}
    try:
        with open(FACTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def save_facts(facts):
    FACTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    temporary = FACTS_FILE.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=2, ensure_ascii=False)
    temporary.replace(FACTS_FILE)


def remember_fact(topic, fact):
    facts = load_facts()
    topic = topic.lower().strip()
    if topic not in facts:
        facts[topic] = []
    if fact not in facts[topic]:
        facts[topic].append(fact)
    save_facts(facts)
    return {"topic": topic, "fact": fact, "saved": True}


def ask_fact(topic):
    facts = load_facts()
    return {"topic": topic.lower(), "facts": facts.get(topic.lower(), [])}
