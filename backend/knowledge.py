from backend.crawler import WORKSPACE
from backend.crawler import PAGES_DIR
from backend.crawler import *
from backend.memory import *
from backend.crawler import *
from pathlib import Path
from ollama import chat
import os

STOP_TOPICS = {
    "this",
    "that",
    "with",
    "from",
    "your",
    "what",
    "other",
    "more",
    "using",
    "about",
    "user",
    "status",
    "source",
    "into",
    "when",
    "where",
    "which",
    "their",
    "there",
    "have",
    "been",
    "will",
    "would",
    "could",
    "should"
    "2026",
    "2025",
    "2024",
    "page",
    "pages",
    "list",
    "information",
    "help",
    "started",
    "english",
    "open",
    "support",
    "event",
    "events",
    "documentation",
    "developer",
    "developers",
    "software",
    "tools"
    "email",
    "contact",
    "changes",
    "links",
    "newsletter",
    "subscribe",
    "type",
    "guide",
    "learn"
    "prev",
    "next",
    "posted",
    "have",
    "page",
    "pages",
    "article",
    "articles",
    "read",
    "reading",
    "view",
    "views"
}

STOP_RELATED = {
    "case",
    "shared",
    "short",
    "stylesheets",
    "socialize",
    "fulfil",
    "using",
    "other",
    "more",
    "this",
    "that",
    "with",
    "from",
    "about"
    "prev",
    "next",
    "posted",
    "have",
    "page",
    "pages",
    "article",
    "articles",
    "read",
    "reading",
    "view",
    "views"
}

def expand_query(query):
    
    aliases_file = MEMORY_FILE.parent / "aliases.txt"

    terms = {query.lower()}

    if aliases_file.exists():

        try:

            with open(aliases_file, "r", encoding="utf-8") as f:

                for line in f:

                    line = line.strip()

                    if "=" not in line:
                        continue

                    left, right = line.split("=", 1)

                    left = left.strip().lower()
                    right = right.strip().lower()

                    if query.lower() == left:
                        terms.add(right)

                    if query.lower() == right:
                        terms.add(left)

        except Exception:
            pass
        
    return list(terms)


def get_candidate_pages(search_terms):

    index = load_index()

    candidates = set()

    for term in search_terms:

        term = term.lower()

        if term in index:

            candidates.update(
                index[term]
            )

    return candidates


def expand_concepts(search_terms):

    concepts = load_concepts()

    expanded = set(search_terms)

    for term in search_terms:

        term = term.lower()

        if term in concepts:

            expanded.update(
                concepts[term][:10]
            )

    return list(expanded)

def ask_concept(concept):

    concepts = load_concepts()

    return {
        "concept": concept.lower(),
        "related": concepts.get(
            concept.lower(),
            []
        )
    }
    
    
def calculate_page_score(
    content,
    search_terms,
    freshness_score=0,
    fact_bonus=0,
    concept_bonus=0
):

    keyword_score = sum(
        content.lower().count(term.lower())
        for term in search_terms
    )

    total_score = (
        keyword_score
        + freshness_score
        + fact_bonus
        + concept_bonus
    )
    
    return {
        "keyword_score": keyword_score,
        "freshness_score": freshness_score,
        "fact_bonus": fact_bonus,
        "concept_bonus": concept_bonus,
        "total_score": total_score
    }
    
 
def calculate_fact_bonus(
    content,
    query
):

    facts = load_facts()

    query = query.lower()

    bonus = 0

    content_lower = content.lower()

    for fact in facts.get(query, []):

        words = [
            w.lower()
            for w in fact.split()
            if len(w) > 4
        ]

        matches = sum(
            1
            for word in words
            if word in content_lower
        )

        bonus += matches * 5

    return bonus


def calculate_concept_bonus(
    content,
    search_terms
):

    concepts = load_concepts()

    bonus = 0

    content_lower = content.lower()

    for term in search_terms:

        for concept in concepts.get(
            term.lower(),
            []
        )[:10]:

            if concept in content_lower:

                bonus += 5

    return bonus


def get_file_freshness(file_name):

    registry = load_url_registry()

    for data in registry.values():

        if data.get("file") == file_name:

            return data.get(
                "freshness_score",
                0
            )

    return 0
 
 
def freshness_debug(file_name):

    registry = load_url_registry()

    for url, data in registry.items():

        if data.get("file") == file_name:

            return {
                "file": file_name,
                "url": url,
                "freshness_score": data.get(
                    "freshness_score",
                    0
                ),
                "status": data.get(
                    "status"
                )
            }

    return {
        "file": file_name,
        "message": "not found in registry"
    }
 
    
def rank_knowledge(query):

        search_terms = expand_concepts(expand_query(query))

        pages_folder = WORKSPACE / "crawler" / "pages"

        results = []

        candidate_pages = get_candidate_pages(search_terms)

        for page_name in candidate_pages:
            page = pages_folder / page_name

            if not page.exists() or not page.is_file():
                continue

            try:
                with open(page, "r", encoding="utf-8") as f:
                    content = f.read()

                fact_bonus = calculate_fact_bonus(
                    content,
                    query
                )
                
                concept_bonus = calculate_concept_bonus(
                    content,
                    search_terms
                )
                
                freshness_score = get_file_freshness(
                    page.name
                )

                scores = calculate_page_score(
                    content,
                    search_terms,
                    freshness_score=freshness_score,
                    fact_bonus=fact_bonus,
                    concept_bonus=concept_bonus
)
                
                score = scores["total_score"]

                if score > 0:
                    results.append({
                        "file": page.name,
                        "score": score,
                        "keyword_score": scores["keyword_score"],
                        "freshness_score": scores["freshness_score"],
                        "fact_bonus": scores["fact_bonus"],
                        "concept_bonus": scores["concept_bonus"]
                    })
            except Exception:
                pass

        results.sort(key=lambda x: x["score"], reverse=True)

        return {
            "query": query,
            "search_terms": search_terms,
            "candidate_pages": list(candidate_pages),
            "results": results[:20],
        }
        
        
def search_report(query):

    ranked = rank_knowledge(query)

    return {
        "query": query,
        "search_terms": ranked["search_terms"],
        "candidate_pages": len(
            ranked.get(
                "candidate_pages",
                []
            )
        ),
        "ranked_pages": len(
            ranked["results"]
        ),
        "top_score": (
            ranked["results"][0]["score"]
            if ranked["results"]
            else 0
        )
    }
        

def knowledge_coverage(topic):

    ranking = rank_knowledge(topic)

    concepts = load_concepts()

    facts = load_facts()

    return {
        "topic": topic,
        "pages": len(
            ranking["results"]
        ),
        "concepts": len(
            concepts.get(
                topic.lower(),
                []
            )
        ),
        "facts": len(
            facts.get(
                topic.lower(),
                []
            )
        )
    }


def explain_ranking(query):

    ranking = rank_knowledge(query)

    if not ranking["results"]:

        return {
            "message": "no results"
        }

    top = ranking["results"][0]

    return {
        "query": query,
        "top_file": top["file"],
        "keyword_score": top["keyword_score"],
        "freshness_score": top["freshness_score"],
        "fact_bonus": top["fact_bonus"],
        "concept_bonus": top["concept_bonus"],
        "total_score": top["score"]
    }


def ranking_breakdown(query):

    ranking = explain_ranking(query)

    total = ranking.get(
        "total_score",
        0
    )

    if total == 0:

        return {
            "query": query,
            "message": "no results"
        }

    return {
        "query": query,
        "keyword_percent": round(
            ranking["keyword_score"]
            * 100 / total,
            2
        ),
        "fact_percent": round(
            ranking["fact_bonus"]
            * 100 / total,
            2
        ),
        "concept_percent": round(
            ranking["concept_bonus"]
            * 100 / total,
            2
        ),
        "freshness_percent": round(
            ranking["freshness_score"]
            * 100 / total,
            2
        )
    }


def ranking_health():

    pages = list(
        PAGES_DIR.glob("*.txt")
    )

    mapped = 0

    registry = load_url_registry()

    for data in registry.values():

        if data.get("file"):

            mapped += 1

    return {
        "pages": len(pages),
        "mapped_pages": mapped,
        "unmapped_pages": (
            len(pages) - mapped
        ),
        "freshness_enabled": (
            mapped > 0
        )
    }


def search_quality_report(query):

    coverage = knowledge_coverage(query)

    ranking = search_report(query)

    return {
        "query": query,
        "pages_found": coverage["pages"],
        "concepts_found": coverage["concepts"],
        "facts_found": coverage["facts"],
        "candidate_pages": ranking["candidate_pages"],
        "ranked_pages": ranking["ranked_pages"],
        "top_score": ranking["top_score"]
    }
    
    
def topic_authority(topic):

    coverage = knowledge_coverage(topic)

    authority_score = (
        coverage["pages"]
        + coverage["facts"] * 10
        + coverage["concepts"]
    )

    return {
        "topic": topic,
        "authority_score": authority_score,
        "pages": coverage["pages"],
        "facts": coverage["facts"],
        "concepts": coverage["concepts"]
    }
    
    
def topic_profile(topic):

    coverage = knowledge_coverage(topic)

    authority = topic_authority(topic)

    concepts = load_concepts()

    related = [
        item
        for item in concepts.get(
            topic.lower(),
            []
        )
        if item.lower() not in STOP_RELATED
    ][:10]

    return {
        "topic": topic,
        "authority": authority[
            "authority_score"
        ],
        "pages": coverage["pages"],
        "facts": coverage["facts"],
        "concepts": coverage["concepts"],
        "coverage": (
            "strong"
            if authority[
                "authority_score"
            ] > 200
            else "weak"
        ),
        "related": related
    }

       
def coverage_gaps(topic):

    coverage = knowledge_coverage(topic)

    missing = []

    if coverage["pages"] < 5:
        missing.append("pages")

    if coverage["facts"] < 3:
        missing.append("facts")

    if coverage["concepts"] < 20:
        missing.append("concepts")

    return {
        "topic": topic,
        "coverage": (
            "good"
            if not missing
            else "weak"
        ),
        "missing": missing
    }


def top_topics(limit=20):

    concepts = load_concepts()

    facts = load_facts()

    topics = []

    for topic in concepts:
        
        if topic.lower() in STOP_TOPICS:
            continue
        
        if topic.isdigit():
            continue

        concept_count = len(
            concepts.get(topic, [])
        )

        fact_count = len(
            facts.get(topic, [])
        )

        authority = (
            concept_count
            + fact_count * 10
        )

        topics.append({
            "topic": topic,
            "authority": authority,
            "concepts": concept_count,
            "facts": fact_count
        })

    topics.sort(
        key=lambda x: x["authority"],
        reverse=True
    )

    return topics[:limit]
       
        
def ask_knowledge(query):
    
    
        search_terms = expand_concepts(expand_query(query))

        pages_folder = PAGES_DIR

        results = []

        candidate_pages = get_candidate_pages(search_terms)

        for page_name in candidate_pages:
            page = pages_folder / page_name

            if not page.exists() or not page.is_file():
                continue

            try:
                with open(page, "r", encoding="utf-8") as f:
                    content = f.read()

                score = sum(
                    content.lower().count(term.lower())
                    for term in search_terms
                )

                if score > 0:
                    results.append(
                        {"file": page.name, "score": score, "content": content}
                    )
            except Exception:
                pass

        if not results:
            return {"message": "no knowledge found"}

        results.sort(key=lambda x: x["score"], reverse=True)

        knowledge = "\n\n".join(
            [
                f"FILE: {item['file']}\nSCORE: {item['score']}\n{item['content'][:3000]}"
                for item in results[:5]
            ]
        )

        response = chat(
            model="llama3:latest",
            messages=[
                {
                    "role": "system",
                    "content": f"""
You are GEAI.

Use ONLY the knowledge below.

If the user provides a topic such as:
AI
Python
Machine Learning

then explain that topic using the available knowledge.

Do not ask for clarification unless absolutely necessary.

Knowledge:

{knowledge}
""",
                },
                {"role": "user", "content": f"Explain: {query}"},
            ],
        )

        return {
            "query": query,
            "search_terms": search_terms,
            "sources": [{"file": r["file"], "score": r["score"]} for r in results[:5]],
            "answer": response["message"]["content"],
        }

def search_all_projects(query):
    
        projects_root = WORKSPACE / "Projects"

        results = []

        if projects_root.exists():

            for project in projects_root.iterdir():

                if not project.is_dir():
                    continue

                project_name = project.name

                memory_file = project / "memory" / "memory.txt"

                if memory_file.exists():

                    with open(memory_file, "r", encoding="utf-8") as f:

                        for line in f:

                            if query in line.lower():

                                results.append(
                                    {
                                        "project": project_name,
                                        "type": "memory",
                                        "match": line.strip(),
                                    }
                                )

                notes_folder = project / "notes"

                if notes_folder.exists():

                    for note in notes_folder.iterdir():

                        if note.is_file():

                            try:

                                with open(note, "r", encoding="utf-8") as f:

                                    content = f.read()

                                if query in content.lower():

                                    results.append(
                                        {
                                            "project": project_name,
                                            "type": "note",
                                            "file": note.name,
                                        }
                                    )

                            except Exception:
                                pass

        return {"query": query, "results": results}        