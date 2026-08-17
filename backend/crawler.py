from pathlib import Path
import hashlib
import ipaddress
import json
import re
import socket
from datetime import datetime, timedelta
from urllib.parse import urljoin, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup

from backend.memory import (
    GEAI_HOME,
    load_index,
    save_index,
    load_concepts,
    save_concepts,
)
from backend.facts import load_facts, save_facts

WORKSPACE = (GEAI_HOME / "workspace").resolve()
CRAWLER_DIR = WORKSPACE / "crawler"
PAGES_DIR = CRAWLER_DIR / "pages"
LINKS_FILE = CRAWLER_DIR / "links.txt"
CRAWLED_FILE = CRAWLER_DIR / "crawled.txt"
URL_REGISTRY_FILE = CRAWLER_DIR / "url_registry.json"

USER_AGENT = "GEAI-Crawler/3.0"
REQUEST_TIMEOUT = 10
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
MAX_REDIRECTS = 5
MAX_QUEUED_LINKS = 5000


def ensure_crawler_dirs():
    CRAWLER_DIR.mkdir(parents=True, exist_ok=True)
    PAGES_DIR.mkdir(parents=True, exist_ok=True)
    LINKS_FILE.touch(exist_ok=True)
    CRAWLED_FILE.touch(exist_ok=True)
    if not URL_REGISTRY_FILE.exists():
        URL_REGISTRY_FILE.write_text("{}", encoding="utf-8")


def load_url_registry():
    if not URL_REGISTRY_FILE.exists():
        return {}
    try:
        with open(URL_REGISTRY_FILE, "r", encoding="utf-8") as f:
            value = json.load(f)
        return value if isinstance(value, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def save_url_registry(registry):
    temporary = URL_REGISTRY_FILE.with_suffix(".json.tmp")
    with open(temporary, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=2, ensure_ascii=False)
    temporary.replace(URL_REGISTRY_FILE)


def update_registry(url, status, file_name=None):
    registry = load_url_registry()
    entry = registry.get(url, {})
    now = datetime.utcnow()
    registry[url] = {
        "status": status,
        "crawl_count": entry.get("crawl_count", 0) + 1,
        "last_crawled": now.isoformat(),
        "next_recrawl": (now + timedelta(days=30)).isoformat(),
        "freshness_score": 100,
    }
    if file_name:
        registry[url]["file"] = file_name
    save_url_registry(registry)


def _is_blocked_ip(address):
    ip = ipaddress.ip_address(address)
    return any((
        ip.is_private,
        ip.is_loopback,
        ip.is_link_local,
        ip.is_multicast,
        ip.is_reserved,
        ip.is_unspecified,
    ))


def validate_url(url):
    """Validate a crawler target and reject local/private network destinations."""
    if not isinstance(url, str) or len(url) > 2048:
        raise ValueError("invalid URL")
    parts = urlsplit(url)
    if parts.scheme.lower() not in {"http", "https"}:
        raise ValueError("only http and https URLs are allowed")
    if not parts.hostname:
        raise ValueError("URL must contain a hostname")
    if parts.username or parts.password:
        raise ValueError("URLs with embedded credentials are not allowed")
    host = parts.hostname.rstrip(".").lower()
    if host in {"localhost", "localhost.localdomain"} or host.endswith(".local"):
        raise ValueError("local hostnames are not allowed")
    try:
        addresses = {item[4][0] for item in socket.getaddrinfo(host, parts.port or (443 if parts.scheme == "https" else 80), type=socket.SOCK_STREAM)}
    except socket.gaierror as exc:
        raise ValueError("hostname could not be resolved") from exc
    if not addresses or any(_is_blocked_ip(address) for address in addresses):
        raise ValueError("private or special-use network targets are not allowed")
    normalized = urlunsplit((parts.scheme.lower(), parts.netloc, parts.path or "/", parts.query, ""))
    return normalized


def _download(url):
    current = validate_url(url)
    session = requests.Session()
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html,application/xhtml+xml"}
    for _ in range(MAX_REDIRECTS + 1):
        response = session.get(
            current,
            timeout=REQUEST_TIMEOUT,
            headers=headers,
            allow_redirects=False,
            stream=True,
        )
        if response.is_redirect or response.is_permanent_redirect:
            location = response.headers.get("Location")
            response.close()
            if not location:
                raise ValueError("redirect response has no Location header")
            current = validate_url(urljoin(current, location))
            continue
        if response.status_code >= 400:
            response.close()
            raise ValueError(f"remote server returned HTTP {response.status_code}")
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > MAX_RESPONSE_BYTES:
            response.close()
            raise ValueError("response exceeds crawler size limit")
        chunks = []
        total = 0
        try:
            for chunk in response.iter_content(chunk_size=64 * 1024):
                if not chunk:
                    continue
                total += len(chunk)
                if total > MAX_RESPONSE_BYTES:
                    raise ValueError("response exceeds crawler size limit")
                chunks.append(chunk)
        finally:
            response.close()
        body = b"".join(chunks)
        content_type = response.headers.get("Content-Type", "")
        return current, body, content_type
    raise ValueError("too many redirects")


def extract_facts(text):
    facts = load_facts()
    for sentence in text.split("."):
        sentence = sentence.strip()
        if len(sentence) < 20 or " is " not in sentence:
            continue
        topic = sentence.split(" is ", 1)[0].strip().lower()[:50]
        if not 2 <= len(topic) <= 30 or len(topic.split()) > 5:
            continue
        if not re.fullmatch(r"[a-zA-Z0-9\s\-]+", topic):
            continue
        facts.setdefault(topic, [])
        if sentence not in facts[topic]:
            facts[topic].append(sentence)
    save_facts(facts)


def save_page_knowledge(page_text, page_file):
    words = set(re.findall(r"\w+", page_text.lower()))
    stop_words = {"this", "that", "with", "from", "have", "will", "your", "they", "them", "what", "when", "where", "why", "how"}
    index = load_index()
    for word in words:
        if len(word) < 3 or word in stop_words:
            continue
        index.setdefault(word, [])
        if page_file.name not in index[word]:
            index[word].append(page_file.name)
    save_index(index)

    stop_concepts = {"home", "main", "content", "dashboard", "docs", "browse", "feedback", "registered", "credits", "copyright", "javascript", "faqs", "login", "logout", "menu", "navigation", "privacy", "cookies", "terms", "search", "skip", "next", "previous"}
    concepts = load_concepts()
    useful = {word for word in words if len(word) >= 4 and word not in stop_concepts}
    for word in useful:
        concepts.setdefault(word, [])
        for related in list(useful - {word})[:20]:
            if related not in concepts[word]:
                concepts[word].append(related)
    save_concepts(concepts)


def process_page(url):
    try:
        requested_url = validate_url(url)
        final_url, body, content_type = _download(requested_url)
        if content_type and not any(value in content_type.lower() for value in ("text/html", "application/xhtml+xml", "text/plain")):
            return {"url": final_url, "message": "unsupported content type skipped"}
        soup = BeautifulSoup(body.decode("utf-8", errors="replace"), "html.parser")
        page_text = soup.get_text(separator=" ", strip=True)
        if len(page_text) < 50:
            update_registry(final_url, "skipped")
            return {"url": final_url, "message": "empty page skipped"}
        content_hash = hashlib.sha256(page_text.encode("utf-8")).hexdigest()
        page_file = PAGES_DIR / f"{content_hash}.txt"
        if page_file.exists():
            update_registry(final_url, "duplicate", page_file.name)
            return {"url": final_url, "message": "page already stored", "saved_as": page_file.name}
        page_file.write_text(page_text, encoding="utf-8")
        extract_facts(page_text)
        save_page_knowledge(page_text, page_file)
        update_registry(final_url, "success", page_file.name)
        return {"url": final_url, "saved_as": page_file.name, "characters": len(page_text)}
    except (ValueError, requests.RequestException) as exc:
        return {"error": str(exc)}


def crawl_website(url):
    ensure_crawler_dirs()
    try:
        requested_url = validate_url(url)
        final_url, body, content_type = _download(requested_url)
        if content_type and "html" not in content_type.lower() and "xhtml" not in content_type.lower():
            return {"url": final_url, "message": "non-HTML page cannot be used for link discovery"}
        soup = BeautifulSoup(body.decode("utf-8", errors="replace"), "html.parser")
        base = urlsplit(final_url)
        origin = (base.scheme, base.hostname, base.port or (443 if base.scheme == "https" else 80))
        links = set()
        for tag in soup.find_all("a", href=True):
            try:
                link = validate_url(urljoin(final_url, tag["href"]))
                parts = urlsplit(link)
                link_origin = (parts.scheme, parts.hostname, parts.port or (443 if parts.scheme == "https" else 80))
                if link_origin == origin:
                    links.add(link)
            except ValueError:
                continue
        existing = {line.strip() for line in LINKS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()}
        new_links = sorted(links - existing)[:MAX_QUEUED_LINKS]
        with LINKS_FILE.open("a", encoding="utf-8") as f:
            for link in new_links:
                f.write(link + "\n")
        return {"url": final_url, "links_found": len(new_links), "scope": "same-origin"}
    except (ValueError, requests.RequestException) as exc:
        return {"error": str(exc)}


def crawl_next():
    ensure_crawler_dirs()
    links = [line.strip() for line in LINKS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    crawled = {line.strip() for line in CRAWLED_FILE.read_text(encoding="utf-8").splitlines() if line.strip()}
    for url in links:
        if url in crawled:
            continue
        result = process_page(url)
        with CRAWLED_FILE.open("a", encoding="utf-8") as f:
            f.write(url + "\n")
        return result
    return {"message": "no uncrawled links"}


def crawl_batch(limit):
    try:
        limit = max(0, min(int(limit), 100))
    except (TypeError, ValueError):
        return {"error": "crawl limit must be an integer"}
    processed = errors = 0
    for _ in range(limit):
        result = crawl_next()
        if result.get("message") == "no uncrawled links":
            break
        if "error" in result:
            errors += 1
        else:
            processed += 1
    return {"requested": limit, "processed": processed, "errors": errors}


def crawler_stats():
    registry = load_url_registry()
    counts = {"success": 0, "duplicate": 0, "skipped": 0, "historic": 0}
    for item in registry.values():
        status = item.get("status")
        if status in counts:
            counts[status] += 1
    return {"known_urls": len(registry), "successful_pages": counts["success"], "duplicates": counts["duplicate"], "skipped": counts["skipped"], "stored_pages": len(list(PAGES_DIR.glob("*.txt"))), "historic": counts["historic"]}


def url_info(url):
    return load_url_registry().get(url, {"message": "url not found"})


def calculate_freshness(last_crawled):
    try:
        age_days = (datetime.utcnow() - datetime.fromisoformat(last_crawled)).days
    except (TypeError, ValueError):
        return 0
    if age_days <= 7: return 100
    if age_days <= 30: return 80
    if age_days <= 90: return 60
    if age_days <= 180: return 40
    return 20


def update_freshness_scores():
    registry = load_url_registry()
    updated = 0
    for data in registry.values():
        if data.get("last_crawled"):
            data["freshness_score"] = calculate_freshness(data["last_crawled"])
            updated += 1
    save_url_registry(registry)
    return {"updated_urls": updated}


def get_stale_urls():
    stale = [{"url": url, "score": data.get("freshness_score", 0)} for url, data in load_url_registry().items() if data.get("freshness_score", 0) <= 40]
    return {"count": len(stale), "urls": stale}


def rebuild_url_registry():
    ensure_crawler_dirs()
    urls = [line.strip() for line in CRAWLED_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]
    registry = {url: {"status": "historic", "crawl_count": 1} for url in urls}
    save_url_registry(registry)
    return {"rebuilt_urls": len(registry)}


def upgrade_registry():
    registry = load_url_registry()
    updated = 0
    for data in registry.values():
        data.setdefault("freshness_score", 100)
        if "next_recrawl" not in data and data.get("last_crawled"):
            try:
                data["next_recrawl"] = (datetime.fromisoformat(data["last_crawled"]) + timedelta(days=30)).isoformat()
            except ValueError:
                pass
        updated += 1
    save_url_registry(registry)
    return {"updated_urls": updated}


def recrawl_url(url):
    return process_page(url)


def recrawl_stale(limit=10):
    try:
        limit = max(0, min(int(limit), 100))
    except (TypeError, ValueError):
        limit = 10
    stale = get_stale_urls()["urls"][:limit]
    for item in stale:
        process_page(item["url"])
    return {"recrawled": len(stale)}


def knowledge_health():
    return {"pages": len(list(PAGES_DIR.glob("*.txt"))), "index_terms": len(load_index()), "concepts": len(load_concepts()), "facts": len(load_facts()), "registry_urls": len(load_url_registry()), "health": "good"}


def find_orphan_pages():
    registered = {data.get("file") for data in load_url_registry().values() if data.get("file")}
    orphan_pages = [page.name for page in PAGES_DIR.glob("*.txt") if page.name not in registered]
    return {"count": len(orphan_pages), "pages": orphan_pages[:50]}


def rebuild_index():
    index = {}
    processed = 0
    for page_file in PAGES_DIR.glob("*.txt"):
        try:
            words = set(re.findall(r"\w+", page_file.read_text(encoding="utf-8").lower()))
            for word in words:
                if len(word) >= 3:
                    index.setdefault(word, [])
                    if page_file.name not in index[word]: index[word].append(page_file.name)
            processed += 1
        except OSError:
            pass
    save_index(index)
    return {"processed_pages": processed, "index_terms": len(index)}


def rebuild_concepts():
    concepts = {}
    processed = 0
    stop = {"home", "main", "content", "dashboard", "docs", "browse", "feedback", "copyright", "javascript", "login", "logout", "menu", "navigation", "privacy", "cookies", "terms", "search", "skip", "next", "previous"}
    for page_file in PAGES_DIR.glob("*.txt"):
        try:
            words = {w for w in re.findall(r"\w+", page_file.read_text(encoding="utf-8").lower()) if len(w) >= 4 and w not in stop}
            for word in words:
                concepts.setdefault(word, [])
                for related in list(words - {word})[:20]:
                    if related not in concepts[word]: concepts[word].append(related)
            processed += 1
        except OSError:
            pass
    save_concepts(concepts)
    return {"processed_pages": processed, "concepts": len(concepts)}


def maintenance_report():
    stale = get_stale_urls()["count"]
    return {"knowledge": knowledge_health(), "crawler": crawler_stats(), "freshness": {"fresh_urls": max(0, len(load_url_registry()) - stale), "stale_urls": stale}, "orphans": find_orphan_pages()}


def registry_summary():
    summary = {}
    for data in load_url_registry().values():
        status = data.get("status", "unknown")
        summary[status] = summary.get(status, 0) + 1
    return {"registry_urls": sum(summary.values()), "statuses": summary}


def registry_health():
    registry = load_url_registry()
    return {"registry_urls": len(registry), "missing_file": sum(1 for d in registry.values() if d.get("status") != "historic" and "file" not in d), "missing_freshness": sum(1 for d in registry.values() if "freshness_score" not in d), "missing_next_recrawl": sum(1 for d in registry.values() if "next_recrawl" not in d)}


def repair_registry():
    registry = load_url_registry()
    repaired = 0
    for data in registry.values():
        if "freshness_score" not in data:
            data["freshness_score"] = 100; repaired += 1
        if "next_recrawl" not in data and data.get("last_crawled"):
            try:
                data["next_recrawl"] = (datetime.fromisoformat(data["last_crawled"]) + timedelta(days=30)).isoformat(); repaired += 1
            except ValueError:
                pass
    save_url_registry(registry)
    return {"registry_urls": len(registry), "repairs": repaired}
