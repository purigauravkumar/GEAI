from pathlib import Path
import json

FACTS_FILE = Path(r"D:\GEAI\memory\facts.json")


def load_facts():

    if not FACTS_FILE.exists():
        return {}

    try:
        with open(FACTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}


def save_facts(facts):

    with open(FACTS_FILE, "w", encoding="utf-8") as f:
        json.dump(facts, f, indent=2)


def remember_fact(topic, fact):

    facts = load_facts()

    topic = topic.lower()

    if topic not in facts:
        facts[topic] = []

    if fact not in facts[topic]:
        facts[topic].append(fact)

    save_facts(facts)

    return {
        "topic": topic,
        "fact": fact,
        "saved": True
    }


def ask_fact(topic):

    facts = load_facts()

    return {
        "topic": topic.lower(),
        "facts": facts.get(topic.lower(), [])
    }