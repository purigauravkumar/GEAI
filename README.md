# GEAI

**GEAI (General Effective Artificial Intelligence)** is a local-first personal AI workspace built around a local Ollama model. It combines conversational AI with persistent memory, project workspaces, web crawling, a searchable knowledge index, concept relationships, facts, URL metadata, freshness scoring, and recrawling tools.

> **Status:** Active personal project / experimental software. Keep the current API on localhost unless you understand and implement the remaining production-security requirements.

## Features

- Local LLM chat through Ollama
- Persistent local memory, facts, concepts, and indexes
- Project workspaces, notes, and project memory
- Web crawling and HTML text extraction
- SHA-256 content-based page deduplication
- URL registry and crawl metadata
- Freshness scoring and stale URL detection
- Knowledge indexing and concept relationships
- CLI client for the local HTTP API
- API-key authentication
- Path-traversal protections for workspace/project operations
- Crawler SSRF protections, redirect validation, DNS/IP checks, and response-size limits
- Same-origin link discovery to limit crawler expansion
- Security tests for authentication and crawler URL validation

## Architecture

```text
GEAI
├── backend/
│   ├── main.py          # FastAPI application and command router
│   ├── security.py      # HTTP API-key authentication middleware
│   ├── crawler.py       # Secure web crawler and crawl metadata
│   ├── filesystem.py    # Workspace/project filesystem operations
│   ├── memory.py        # Persistent memory, indexes and concepts
│   ├── facts.py         # Fact storage and lookup
│   ├── knowledge.py     # Knowledge/search and ranking functions
│   └── projects.py      # Project operations
├── brain/               # GEAI design and architecture documents
├── specs/               # System specifications
├── tests/               # Security tests
├── cli.py               # Interactive CLI client
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── ROADMAP.md
└── VERSION.txt
```

Runtime data is intentionally stored outside the repository under `GEAI_HOME`.

## Requirements

- Python 3.10+ recommended
- Ollama installed and running locally
- An Ollama model available locally; the application currently defaults to `llama3:latest`
- Windows, Linux, or macOS

## Installation

```bash
git clone https://github.com/purigauravkumar/GEAI.git
cd GEAI
python -m venv .venv
```

Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install runtime dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

For development and tests:

```bash
pip install -r requirements-dev.txt
```

Install Ollama separately, start it, and download the configured model:

```bash
ollama pull llama3:latest
```

## Configuration

The application reads environment variables directly; it does not automatically load `.env` files.

PowerShell:

```powershell
$env:GEAI_HOME = "$HOME\GEAI"
$env:GEAI_API_KEY = "replace-with-a-long-random-secret"
```

Linux/macOS:

```bash
export GEAI_HOME="$HOME/GEAI"
export GEAI_API_KEY="replace-with-a-long-random-secret"
```

`GEAI_HOME` defaults to `~/GEAI` when it is not set. Keep this directory outside the Git repository because it contains personal memory, facts, crawler output, and project data.

Never commit a real API key.

## Run GEAI

Start the API from the repository root:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Use `127.0.0.1` for local-only operation. Do not bind the current application to `0.0.0.0` or expose it directly to the Internet.

In another terminal:

```bash
python cli.py
```

Example:

```text
GEAI> Who are you?
GEAI> Remember I am building GEAI.
GEAI> What do you remember?
GEAI> List projects
```

## API authentication

Protected endpoints require:

```http
X-GEAI-API-Key: <your-secret>
```

Example:

```bash
curl -H "X-GEAI-API-Key: $GEAI_API_KEY" "http://127.0.0.1:8000/memory"
```

If `GEAI_API_KEY` is missing, protected endpoints return `503`. An incorrect key returns `401`.

The root status endpoint and FastAPI documentation routes are intentionally public on the local server.

## Commands

The command router currently supports functionality including:

```text
remember <text>
remember fact <topic> = <fact>
ask fact <topic>
create project <name>
create folder <name>
create file <name> with content <text>
read <name>
list workspace
list projects
show project <name>
create note <file> in project <project>
write note <file> in project <project> with content <text>
remember in project <project> <memory>
show memory for project <project>
search project <project>
ask project <project> <question>
crawl website <url>
crawl next
crawl <number>
crawler stats
url info <url>
update freshness
list stale urls
recrawl url <url>
recrawl stale
knowledge health
maintenance report
registry health
repair registry
rebuild index
rebuild concepts
```

## Crawler security

The crawler was hardened against common server-side request forgery and resource-abuse problems.

### URL validation

Before a request is made, GEAI:

- accepts only `http` and `https`
- rejects URLs containing embedded credentials
- rejects malformed or excessively long URLs
- resolves the hostname and rejects private, loopback, link-local, multicast, reserved, and unspecified IP addresses
- rejects `localhost` and `.local` hostnames
- validates every redirect target using the same rules

### Redirect protection

The crawler does not follow redirects automatically. Redirects are inspected and revalidated, with a maximum redirect count.

### Response limits

Responses are streamed and capped at 2 MiB. Oversized responses are rejected instead of being loaded without a bound into memory.

### Crawl scope

`crawl website <url>` discovers links only on the same origin as the starting URL. This limits uncontrolled crawler expansion.

> **Note:** DNS/IP validation reduces SSRF risk but does not by itself provide a perfect defense against every possible DNS-rebinding or network-layer attack. Keep GEAI on localhost unless stronger network isolation is added.

## Security hardening implemented

The security-hardening branch now includes:

1. Workspace path traversal protection.
2. Project and note path validation.
3. Portable storage through `GEAI_HOME`.
4. Safer atomic JSON persistence.
5. API-key authentication.
6. CLI authentication support.
7. SSRF-oriented crawler URL validation.
8. Private/special-use IP blocking.
9. Redirect validation and redirect limits.
10. Response-size limits.
11. Same-origin crawler link discovery.
12. Security tests for authentication and crawler validation.
13. Removal of the obsolete hard-coded `config/settings.json` file.
14. Removal of the obsolete repository `workspace/.gitkeep` runtime placeholder.

## Testing

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the test suite:

```bash
pytest -q
```

The current tests cover the API-key middleware and crawler URL validation. More integration tests should be added as the API evolves.

## Current limitations

GEAI is **not yet production-ready for untrusted network exposure**. Remaining engineering work includes:

- Convert state-changing HTTP `GET` endpoints to appropriate `POST`/`PUT`/`DELETE` methods.
- Add request rate limiting.
- Add a stronger multi-user authorization model if remote access is required.
- Add HTTPS through a reverse proxy for remote deployments.
- Define a strict CORS policy for any browser client.
- Pin runtime dependencies to tested versions.
- Add CI for tests, linting, dependency/security checks, and syntax validation.
- Improve Ollama error handling and health checks.
- Add stronger network isolation if the crawler will ever run against untrusted input.

## Safe deployment recommendation

For personal use, run GEAI locally:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

If remote access is eventually required, place GEAI behind a properly configured reverse proxy and implement authentication, authorization, HTTPS, rate limiting, CORS, logging, and network controls before exposing it to untrusted users.

## Privacy

GEAI stores memory, facts, crawler output, and project information locally. Treat the `GEAI_HOME` directory as sensitive personal data and protect it with normal operating-system permissions and backups.

## Project documentation

- `ROADMAP.md` — development roadmap
- `VERSION.txt` — version history
- `brain/` — project architecture, mission, principles, decisions, and tool documentation
- `specs/` — system specifications

## Disclaimer

GEAI is an experimental personal AI project. It is not a security product, autonomous security system, or production-grade enterprise platform. Review and test changes before using GEAI with important or sensitive data.

## License

No license is currently declared in this repository. Until a license is added, assume that the source is **not** granted general permission for redistribution or commercial reuse beyond rights provided by applicable law.
