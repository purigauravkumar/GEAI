from pathlib import Path
import re
from urllib.parse import urljoin
from datetime import datetime, timedelta

import requests
from bs4 import BeautifulSoup
import hashlib
import json


from backend.memory import (
    load_index,
    save_index,
    load_concepts,
    save_concepts,
)

from backend.facts import (
    load_facts,
    save_facts,
)

WORKSPACE = Path(r"D:\GEAI\workspace")

CRAWLER_DIR = WORKSPACE / "crawler"
PAGES_DIR = CRAWLER_DIR / "pages"

LINKS_FILE = CRAWLER_DIR / "links.txt"
CRAWLED_FILE = CRAWLER_DIR / "crawled.txt"
URL_REGISTRY_FILE = CRAWLER_DIR / "url_registry.json"

def ensure_crawler_dirs():
    
    CRAWLER_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)

    LINKS_FILE.touch(exist_ok=True)
    CRAWLED_FILE.touch(exist_ok=True)
    URL_REGISTRY_FILE.touch(exist_ok=True)
    
    if not URL_REGISTRY_FILE.exists():

        with open(
        URL_REGISTRY_FILE,
        "w",
        encoding="utf-8"
        ) as f:

            json.dump({}, f)
    

def load_url_registry():

    if not URL_REGISTRY_FILE.exists():
        return {}

    try:

        with open(
            URL_REGISTRY_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return json.load(f)

    except Exception:

        return {}
    
def save_url_registry(registry):

    with open(
        URL_REGISTRY_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            registry,
            f,
            indent=2
        )
        
def update_registry(
    url,
    status,
    file_name=None
):

    registry = load_url_registry()

    entry = registry.get(url, {})

    now = datetime.utcnow()

    registry[url] = {
        "status": status,
        "crawl_count": entry.get("crawl_count", 0) + 1,
        "last_crawled": now.isoformat(),
        "next_recrawl": (
            now + timedelta(days=30)
        ).isoformat(),
        "freshness_score": 100
    }

    if file_name:
        registry[url]["file"] = file_name

    save_url_registry(registry)
        
def extract_facts(text):

    facts = load_facts()

    sentences = text.split(".")

    for sentence in sentences:

        sentence = sentence.strip()

        if len(sentence) < 20:
            continue

        if " is " not in sentence:
            continue

        parts = sentence.split(" is ", 1)

        topic = parts[0].strip().lower()

        topic = topic[:50]

        topic_words = topic.split()

        if len(topic_words) > 5:
            continue

        if not re.match(r"^[a-zA-Z0-9\s\-]+$", topic):
            continue

        if len(topic) < 2:
            continue

        if len(topic) > 30:
            continue

        if len(topic) > 40:
            continue

        if topic not in facts:
            facts[topic] = []

        if sentence not in facts[topic]:
            facts[topic].append(sentence)

    save_facts(facts)

def save_page_knowledge(page_text, page_file):
    
        index = load_index()

        words = re.findall(r"\w+", page_text.lower())

        unique_words = set(words)

        for word in unique_words:
            if len(word) < 3:
                continue

            stop_words = {
                "this",
                "that",
                "with",
                "from",
                "have",
                "will",
                "your",
                "they",
                "them",
                "what",
                "when",
                "where",
                "why",
                "how",
            }

            if word in stop_words:
                continue

            if word not in index:
                index[word] = []

            if page_file.name not in index[word]:
                index[word].append(page_file.name)

        save_index(index)

        concepts = load_concepts()

        words = re.findall(r"\w+", page_text.lower())
        unique_words = set(words)

        stop_concepts = {
            "home",
            "main",
            "content",
            "dashboard",
            "docs",
            "browse",
            "feedback",
            "registered",
            "credits",
            "copyright",
            "javascript",
            "faqs",
            "operational",
            "login",
            "logout",
            "menu",
            "navigation",
            "privacy",
            "cookies",
            "terms",
            "search",
            "skip",
            "next",
            "previous",
        }

        for word in unique_words:
            if len(word) < 4 or word in stop_concepts:
                continue

            if word not in concepts:
                concepts[word] = []

            related = [
                item
                for item in unique_words
                if item != word and len(item) >= 4 and item not in stop_concepts
            ][:20]

            for item in related:
                if item not in concepts[word]:
                    concepts[word].append(item)

        save_concepts(concepts)


def process_page(url):

    if not url.startswith(("http://", "https://")):
            return {"error": f"invalid url: {url}"}

    try:

        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "GEAI-Crawler/2.0"}
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        page_text = soup.get_text(
            separator=" ",
            strip=True
        )
        
        if len(page_text.strip()) < 50:
            
            update_registry(
                url,
                "skipped"
            )
            
            return {
                "url": url,
                "message": "empty page skipped"
            }
        
        content_hash = hashlib.sha256(page_text.encode("utf-8")).hexdigest()

        page_file = PAGES_DIR / f"{content_hash}.txt"
        
        if page_file.exists():
            
            update_registry(
                url,
                "duplicate",
                page_file.name
            )

            return {
                "url": url,
                "message": "page already stored",
                "saved_as": page_file.name
            }
            
        with open(page_file,"w", encoding="utf-8") as f:

            f.write(page_text)

        extract_facts(page_text)

        save_page_knowledge(
            page_text,
            page_file
        )
        
        update_registry(
            url,
            "success",
            page_file.name
        )
        
        return {
            "url": url,
            "saved_as": page_file.name,
            "characters": len(page_text)
        }

    except Exception as e:

        return {
            "error": str(e)
        }
        
def crawl_website(url):

    ensure_crawler_dirs()

    try:

        response = requests.get(
            url,
            timeout=10,
            headers={"User-Agent": "GEAI-Crawler/2.0"}
        )

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        links = set()

        for tag in soup.find_all("a", href=True):

            link = urljoin(
                url,
                tag["href"]
            )

            if link.startswith("http"):
                links.add(link)
                

        for link in sorted(list(links))[:20]:
                print(link)

        existing = set()

        with open(
            LINKS_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            existing = {
                line.strip()
                for line in f
                if line.strip()
            }

        new_links = links - existing

        with open(
            LINKS_FILE,
            "a",
            encoding="utf-8"
        ) as f:

            for link in sorted(new_links):
                f.write(link + "\n")

        return {
            "url": url,
            "links_found": len(new_links)
        }

    except Exception as e:

        return {"error": str(e)}
    
def crawl_next():

    ensure_crawler_dirs()

    with open(
        LINKS_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        links = [
            line.strip()
            for line in f
            if line.strip()
        ]

    with open(
        CRAWLED_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        crawled = {
            line.strip()
            for line in f
            if line.strip()
        }
        

    for url in links:
        
        if not url.startswith(("http://", "https://")):
            continue

        if url not in crawled:

            result = process_page(url)

            with open(CRAWLED_FILE, "a", encoding="utf-8") as f:
                    f.write(url + "\n")

            return result

    return {
        "message": "no uncrawled links"
    }
    
def crawl_batch(limit):

    processed = 0
    errors = 0

    for _ in range(limit):

        result = crawl_next()

        if result.get("message") == "no uncrawled links":
            break

        if "error" in result:
            errors += 1
        else:
            processed += 1

    return {
        "requested": limit,
        "processed": processed,
        "errors": errors
    }
    
def crawler_stats():

    registry = load_url_registry()

    success = 0
    duplicate = 0
    skipped = 0
    historic = 0
    
    for item in registry.values():

        status = item.get("status")

        if status == "success":
            success += 1

        elif status == "duplicate":
            duplicate += 1

        elif status == "skipped":
            skipped += 1
            
        elif status == "historic":
            historic += 1

    return {
        "known_urls": len(registry),
        "successful_pages": success,
        "duplicates": duplicate,
        "skipped": skipped,
        "stored_pages": len(
            list(PAGES_DIR.glob("*.txt"))
        ),
        "historic": historic,   
    }
    
def url_info(url):

    registry = load_url_registry()

    return registry.get(
        url,
        {"message": "url not found"}
    )
    
def calculate_freshness(last_crawled):

    try:

        crawl_time = datetime.fromisoformat(
            last_crawled
        )

    except Exception:

        return 0

    age_days = (
        datetime.utcnow() - crawl_time
    ).days

    if age_days <= 7:
        return 100

    if age_days <= 30:
        return 80

    if age_days <= 90:
        return 60

    if age_days <= 180:
        return 40

    return 20

def update_freshness_scores():

    registry = load_url_registry()

    updated = 0

    for url, data in registry.items():

        last_crawled = data.get(
            "last_crawled"
        )

        if not last_crawled:
            continue

        score = calculate_freshness(
            last_crawled
        )

        data["freshness_score"] = score

        updated += 1

    save_url_registry(registry)

    return {
        "updated_urls": updated
    }

def get_stale_urls():

    registry = load_url_registry()

    stale = []

    for url, data in registry.items():

        score = data.get(
            "freshness_score",
            0
        )

        if score <= 40:

            stale.append(
                {
                    "url": url,
                    "score": score
                }
            )

    return {
        "count": len(stale),
        "urls": stale
    }

def rebuild_url_registry():

    registry = {}

    if not CRAWLED_FILE.exists():
        return {
            "message": "no crawled file"
        }

    with open(
        CRAWLED_FILE,
        "r",
        encoding="utf-8"
    ) as f:

        urls = [
            line.strip()
            for line in f
            if line.strip()
        ]

    for url in urls:

        registry[url] = {
            "status": "historic",
            "crawl_count": 1
        }

    save_url_registry(registry)

    return {
        "rebuilt_urls": len(registry)
    }
    
def upgrade_registry():

    registry = load_url_registry()

    updated = 0

    for url, data in registry.items():

        if "freshness_score" not in data:

            data["freshness_score"] = 100

        if "next_recrawl" not in data:

            try:

                last = datetime.fromisoformat(
                    data["last_crawled"]
                )

                data["next_recrawl"] = (
                    last + timedelta(days=30)
                ).isoformat()

            except Exception:

                continue

        updated += 1

    save_url_registry(registry)

    return {
        "updated_urls": updated
    }
    
def recrawl_url(url):

    return process_page(url)

def recrawl_stale(limit=10):

    stale = get_stale_urls()["urls"]

    processed = 0

    for item in stale[:limit]:

        process_page(item["url"])

        processed += 1

    return {
        "recrawled": processed
    }
    
def knowledge_health():

    index = load_index()

    concepts = load_concepts()

    facts = load_facts()

    registry = load_url_registry()

    pages = list(
        PAGES_DIR.glob("*.txt")
    )

    return {
        "pages": len(pages),
        "index_terms": len(index),
        "concepts": len(concepts),
        "facts": len(facts),
        "registry_urls": len(registry),
        "health": "good"
    }
    
def find_orphan_pages():

    registry = load_url_registry()

    registered_files = set()

    for data in registry.values():

        file_name = data.get("file")

        if file_name:
            registered_files.add(file_name)

    orphan_pages = []

    for page in PAGES_DIR.glob("*.txt"):

        if page.name not in registered_files:

            orphan_pages.append(page.name)

    return {
        "count": len(orphan_pages),
        "pages": orphan_pages[:50]
    }
    
def rebuild_index():

    index = {}

    pages = list(
        PAGES_DIR.glob("*.txt")
    )

    processed = 0

    for page_file in pages:

        try:

            with open(
                page_file,
                "r",
                encoding="utf-8"
            ) as f:

                page_text = f.read()

            words = re.findall(
                r"\w+",
                page_text.lower()
            )

            unique_words = set(words)

            for word in unique_words:

                if len(word) < 3:
                    continue

                if word not in index:
                    index[word] = []

                if page_file.name not in index[word]:
                    index[word].append(
                        page_file.name
                    )

            processed += 1

        except Exception:
            pass

    save_index(index)

    return {
        "processed_pages": processed,
        "index_terms": len(index)
    }
    
def rebuild_concepts():

    concepts = {}

    pages = list(
        PAGES_DIR.glob("*.txt")
    )

    processed = 0

    stop_concepts = {
        "home",
        "main",
        "content",
        "dashboard",
        "docs",
        "browse",
        "feedback",
        "registered",
        "credits",
        "copyright",
        "javascript",
        "faqs",
        "operational",
        "login",
        "logout",
        "menu",
        "navigation",
        "privacy",
        "cookies",
        "terms",
        "search",
        "skip",
        "next",
        "previous",
    }

    for page_file in pages:

        try:

            with open(
                page_file,
                "r",
                encoding="utf-8"
            ) as f:

                page_text = f.read()

            words = re.findall(
                r"\w+",
                page_text.lower()
            )

            unique_words = set(words)

            for word in unique_words:

                if len(word) < 4:
                    continue

                if word in stop_concepts:
                    continue

                if word not in concepts:
                    concepts[word] = []

                related = [
                    item
                    for item in unique_words
                    if item != word
                    and len(item) >= 4
                    and item not in stop_concepts
                ][:20]

                for item in related:

                    if item not in concepts[word]:
                        concepts[word].append(item)

            processed += 1

        except Exception:
            pass

    save_concepts(concepts)

    return {
        "processed_pages": processed,
        "concepts": len(concepts)
    }
    
def maintenance_report():

    health = knowledge_health()

    crawler = crawler_stats()

    freshness = {
        "fresh_urls": (
            len(load_url_registry())
            - get_stale_urls()["count"]
        ),
        "stale_urls": get_stale_urls()["count"]
    }

    orphan = find_orphan_pages()

    return {
        "knowledge": health,
        "crawler": crawler,
        "freshness": freshness,
        "orphans": orphan
    }
    
def registry_summary():

    registry = load_url_registry()

    summary = {}

    for data in registry.values():

        status = data.get(
            "status",
            "unknown"
        )

        summary[status] = (
            summary.get(status, 0) + 1
        )

    return {
        "registry_urls": len(registry),
        "statuses": summary
    }
    
def registry_health():

    registry = load_url_registry()

    missing_file = 0

    missing_freshness = 0

    missing_recrawl = 0

    for data in registry.values():

        if (
            data.get("status")
            != "historic"
        ):

            if "file" not in data:
                missing_file += 1

        if "freshness_score" not in data:
            missing_freshness += 1

        if "next_recrawl" not in data:
            missing_recrawl += 1

    return {
        "registry_urls": len(registry),
        "missing_file": missing_file,
        "missing_freshness": missing_freshness,
        "missing_next_recrawl": missing_recrawl
    }

def repair_registry():

    registry = load_url_registry()

    repaired = 0

    for url, data in registry.items():

        if "freshness_score" not in data:

            data["freshness_score"] = 100

            repaired += 1

        if "next_recrawl" not in data:

            try:

                last = datetime.fromisoformat(
                    data["last_crawled"]
                )

                data["next_recrawl"] = (
                    last + timedelta(days=30)
                ).isoformat()

                repaired += 1

            except Exception:
                pass

    save_url_registry(registry)

    return {
        "registry_urls": len(registry),
        "repairs": repaired
    }