from itertools import count
from urllib.parse import urljoin
from fastapi import FastAPI
from ollama import chat
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import json
import os
import re
from backend.memory import *
from backend.crawler import *
from backend.knowledge import *
from backend.projects import *
from backend.filesystem import *
from backend.facts import *

app = FastAPI()


def create_project_tool(project_name):

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


@app.get("/")
def root():
    return {"status": "GEAI ONLINE", "model": "llama3:latest"}


@app.get("/remember")
def remember(text: str):

    memory = load_memory()

    if text not in memory:
        memory.append(text)

    save_memory(memory)

    return {"saved": text}


@app.get("/memory")
def memory():
    return {"memory": load_memory()}


@app.get("/chat")
def geai_chat(prompt: str):

    memory = load_memory()

    memory_text = "\n".join([f"- {item}" for item in memory])

    system_prompt = f"""
You are GEAI.

You have persistent memory.

Current memory:

{memory_text}

Use memory when answering.
"""

    response = chat(
        model="llama3:latest",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": prompt},
        ],
    )

    return {"response": response["message"]["content"]}


@app.get("/create_folder")
def create_folder(name: str):

    folder = WORKSPACE / name

    folder.mkdir(parents=True, exist_ok=True)

    return {"created": str(folder)}


@app.get("/create_file")
def create_file(name: str, content: str = ""):

    file_path = WORKSPACE / name

    with open(file_path, "w", encoding="utf-8") as f:
        f.write(content)

    return {"created": str(file_path)}


@app.get("/read_file")
def read_file(name: str):

    file_path = WORKSPACE / name

    if not file_path.exists():
        return {"error": "file not found"}

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    return {"content": content}


@app.get("/list_workspace")
def list_workspace():

    items = []

    for item in WORKSPACE.iterdir():
        items.append(item.name)

    return {"workspace": items}


@app.get("/command")
def command(text: str):

    text_lower = text.lower()

    if text_lower.startswith("test concepts "):

        query = text[14:].strip()

        search_terms = expand_query(query)

        expanded = expand_concepts(
            search_terms
        )

        return {
            "query": query,
            "search_terms": search_terms,
            "expanded_terms": expanded
        }

    if text_lower == "alias list":

        aliases_file = MEMORY_FILE.parent / "aliases.txt"

        if not aliases_file.exists():

            return {"message": "no aliases"}

        with open(aliases_file, "r", encoding="utf-8") as f:

            aliases = f.read()

        return {"aliases": aliases}

    if text_lower.startswith("create project "):

        project_name = text[15:].strip()

        return create_project(project_name)

    if text_lower.startswith("create folder "):

        folder_name = text[14:].strip()

        return create_folder(folder_name)

    if text_lower.startswith("create file "):

        remainder = text[12:]

        parts = remainder.split(" with content ", 1)

        file_name = parts[0].strip()

        content = ""

        if len(parts) > 1:
            content = parts[1]

        return create_file(file_name, content)

    if text_lower.startswith("crawl website "):

        url = text[14:].strip()

        return crawl_website(url)

    if text_lower.startswith("crawl next"):

        return crawl_next()
    
    if text_lower.startswith("crawl "):
        
        try:

            count = int(text[6:].strip())
            return crawl_batch(count)
        
        except ValueError:
            return {"error": "use: Crawl 10"}
        
    if text_lower == "rebuild url registry":

        return rebuild_url_registry()
    
    if text_lower == "upgrade registry":

        return upgrade_registry()
    
    if text_lower.startswith("recrawl url "):

        url = text[12:].strip()

        return recrawl_url(url)

    if text_lower == "recrawl stale":

        return recrawl_stale()
        
    if text_lower == "crawler stats":

        return crawler_stats()
    
    if text_lower == "update freshness":

        return update_freshness_scores()
    
    if text_lower == "list stale urls":

        return get_stale_urls()
    
    if text_lower == "freshness report":

        stale = get_stale_urls()

        registry = load_url_registry()

        fresh = len(registry) - stale["count"]

        avg = 0

        if registry:

            scores = [
                item.get("freshness_score", 0)
                for item in registry.values()
            ]   

            avg = sum(scores) / len(scores)

        return {
            "known_urls": len(registry),
            "fresh_urls": fresh,
            "stale_urls": stale["count"],
            "average_freshness": round(avg, 2)
        }
        
    if text_lower == "knowledge health":

        return knowledge_health()
    
    if text_lower == "find orphan pages":

        return find_orphan_pages()
    
    if text_lower == "rebuild index":

        return rebuild_index()
    
    if text_lower == "rebuild concepts":

        return rebuild_concepts()
    
    if text_lower == "maintenance report":

        return maintenance_report()
    
    if text_lower == "registry summary":

        return registry_summary()

    if text_lower == "registry health":

        return registry_health()

    if text_lower == "repair registry":

        return repair_registry()
    
    if text_lower.startswith("url info "):

        url = text[9:].strip()

        return url_info(url)
    
    if text_lower.startswith("search report "):

        query = text[14:].strip()

        return search_report(query)
    
    if text_lower.startswith("knowledge coverage "):

        topic = text[19:].strip()

        return knowledge_coverage(topic)
    
    if text_lower.startswith("freshness debug "):

        file_name = text[17:].strip()

        return freshness_debug(file_name)
    
    if text_lower.startswith("explain ranking "):

        query = text[16:].strip()

        return explain_ranking(query)
    
    if text_lower.startswith("ranking breakdown "):

        query = text[18:].strip()

        return ranking_breakdown(query)
    
    if text_lower == "ranking health":

        return ranking_health()
    
    if text_lower.startswith("search quality "):

        query = text[15:].strip()

        return search_quality_report(query)

    if text_lower.startswith("rank knowledge "):

        query = text[15:].strip()

        return rank_knowledge(query)
        

    if text_lower.startswith("ask concept "):

        concept = text[12:].strip()

        return ask_concept(concept)

    if text_lower.startswith("ask knowledge "):

        query = text[14:].strip()

        return ask_knowledge(query)

    if text_lower.startswith("read "):

        file_name = text[5:].strip()

        return read_file(file_name)
    
    if text_lower.startswith("list workspace"):

        return list_workspace()

    if text_lower.startswith("list projects"):

       return list_projects()

    if text_lower.startswith("show project "):

        project_name = text[13:].strip()

        return show_project(project_name)
    
    if text_lower.startswith("create note "):

        remainder = text[12:]

        parts = remainder.split(" in project ", 1)

        if len(parts) < 2:
            return {"error": "use: Create note filename in project ProjectName"}

        file_name = parts[0].strip()

        project_name = parts[1].strip()

        return create_note(project_name, file_name)

    if text_lower.startswith("write note "):

        remainder = text[11:]

        parts = remainder.split(" in project ", 1)

        if len(parts) < 2:
            return {
            "error": "use: Write note file.txt in project ProjectName with content ..."
        }

        file_name = parts[0].strip()

        project_part = parts[1]

        project_parts = project_part.split(" with content ", 1)

        if len(project_parts) < 2:
            return {"error": "missing content"}

        project_name = project_parts[0].strip()

        content = project_parts[1]

        return write_note(
        project_name,
        file_name,
        content
    )

    if text_lower.startswith("remember in project "):

        remainder = text[len("Remember in project "):]

        words = remainder.split()

        if len(words) < 2:
            return {
            "error": "use: Remember in project ProjectName MemoryText"
        }

        project_name = words[0]

        memory_text = " ".join(words[1:])

        return remember_in_project(
        project_name,
        memory_text
    )
        
    if text_lower.startswith("show memory for project "):

        project_name = text[24:].strip()

        return show_project_memory(
        project_name
    )

    if text_lower.startswith("search project "):

        project_name = text[15:].strip()

        return search_project(
        project_name
    )

    if text_lower.startswith("ask project "):

        remainder = text[12:]

        parts = remainder.split(" ", 1)

        if len(parts) < 2:
            return {
            "error": "use: Ask project ProjectName Question"
        }

        project_name = parts[0].strip()

        question = parts[1].strip()

        return ask_project(
        project_name,
        question
    )

    if text_lower.startswith("search "):

        query = text[7:].strip().lower()
        
        return search_all_projects(query)
    
    if text_lower.startswith("remember fact "):

            remainder = text[14:]

            parts = remainder.split(" = ", 1)

            if len(parts) < 2:
        
                return {"error": "use: Remember fact Topic = Fact"}

            topic = parts[0].strip()

            fact = parts[1].strip()

            return remember_fact(topic, fact)

    if text_lower.startswith("remember "):

        memory_item = text[9:].strip()

        memory = load_memory()

        if memory_item not in memory:
            memory.append(memory_item)

        save_memory(memory)

        return {"action": "remember", "saved": memory_item}

    if text_lower.startswith("ask fact "):

        topic = text[9:].strip()

        return ask_fact(topic)

    return {"action": "unknown", "message": "command not recognized"}


def route_prompt(prompt: str):

    response = chat(
        model="llama3:latest",
        messages=[
            {
                "role": "system",
                "content": """
You are a router.

Reply with ONLY ONE WORD.

CHAT
MEMORY
PROJECT

Examples:

What is our roadmap? -> PROJECT
What do we know about GEAI? -> PROJECT
Search memory -> MEMORY
Remember this -> MEMORY
Tell me a joke -> CHAT
Who are you? -> CHAT
""",
            },
            {"role": "user", "content": prompt},
        ],
    )

    return response["message"]["content"].strip().upper()
   

@app.get("/ask")
def ask(prompt: str):

    route = route_prompt(prompt)

    if route == "PROJECT":
        return command("Ask project GEAI " + prompt)

    if route == "MEMORY":
        return memory()

    return geai_chat(prompt)
