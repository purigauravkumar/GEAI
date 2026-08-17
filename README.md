# GEAI

**GEAI (Gaurav Evolved Artificial Intelligence)** is a local-first personal AI workspace built around a local Ollama model. The project combines conversational AI with persistent memory, project workspaces, web crawling, a searchable knowledge index, concept relationships, facts, URL metadata, freshness scoring, and recrawling tools.

> **Project status:** Active personal project / experimental software. The repository is not yet production-ready for exposure to an untrusted network.

## What GEAI currently contains

- Local LLM chat through Ollama
- Persistent memory stored on the local machine
- Project-based workspace management
- Notes and project memory
- Web crawling and HTML text extraction
- SHA-256 content-based page deduplication
- URL registry and crawl metadata
- Freshness scoring and stale URL detection
- Knowledge indexing and concept relationships
- Fact storage and lookup
- CLI client for the local HTTP API
- Maintenance and knowledge-health commands

The current version history is recorded in `VERSION.txt` and the development plan is in `ROADMAP.md`.

## Architecture

```text
GEAI
├── backend/
│   ├── main.py          # FastAPI application and command router
│   ├── security.py      # HTTP API-key authentication middleware
│   ├── crawler.py       # Web crawling, URL registry and knowledge extraction
│   ├── filesystem.py    # Workspace and project filesystem operations
│   ├── memory.py        # Persistent memory, indexes and concepts
│   ├── facts.py         # Fact storage and lookup
│   ├── knowledge.py     # Knowledge/search functions
│   └── projects.py      # Project operations
├── brain/               # GEAI design, mission and architecture documents
├── config/              # Project configuration
├── specs/               # System specifications
├── workspace/           # Git-tracked placeholder; runtime data should stay local
├── cli.py               # Interactive CLI client
├── requirements.txt
├── ROADMAP.md
└── VERSION.txt
```

## Requirements

- Python 3.10+ recommended
- Ollama installed and running locally
- An Ollama model available locally; the current application defaults to `llama3:latest`
- Windows, Linux or macOS with a writable local data directory

## Installation

Clone the repository and create a virtual environment:

```bash
git clone https://github.com/purigauravkumar/GEAI.git
cd GEAI
python -m venv .venv
```

Activate it on Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

Or on Linux/macOS:

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Install Ollama separately, start the Ollama service, and make sure the configured model exists:

```bash
ollama pull llama3:latest
```

## Configuration

Copy `.env.example` to your local environment configuration and set a strong API key. The application reads environment variables directly; it does not automatically load a `.env` file.

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

Keep the API key secret and never commit it to Git.

### Local data directory

Older GEAI code used a hard-coded `D:\GEAI` location. The hardened storage modules now use the `GEAI_HOME` environment variable and default to `~/GEAI`.

Keeping runtime memory and crawler data outside the repository reduces the chance of accidentally committing personal data.

## Running GEAI

Start the FastAPI application from the repository root:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Use `127.0.0.1` for local-only operation.

The HTTP API now requires the `X-GEAI-API-Key` header for protected endpoints. The root status endpoint and API documentation remain publicly readable on the local server.

In another terminal, run the CLI after setting `GEAI_API_KEY`:

```bash
python cli.py
```

Then try:

```text
GEAI> Who are you?
GEAI> Remember I am building GEAI.
GEAI> What do you remember?
GEAI> List projects
```

## Example commands

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

## API authentication

Protected HTTP requests must include:

```http
X-GEAI-API-Key: <your-secret>
```

Example:

```bash
curl -H "X-GEAI-API-Key: $GEAI_API_KEY" "http://127.0.0.1:8000/memory"
```

If `GEAI_API_KEY` is not configured, protected endpoints return `503` instead of silently running without authentication.

## Security hardening included in this branch

The security-hardening branch addresses several concrete problems found during repository review:

1. **Workspace path traversal** — filesystem paths are resolved and checked to remain inside the GEAI workspace before file/folder operations.
2. **Portable storage** — memory and facts no longer depend on `D:\GEAI`; storage can be selected with `GEAI_HOME`.
3. **Safer JSON persistence** — memory/index/concept/fact writes use temporary files followed by replacement, reducing the chance of leaving partially written JSON after an interrupted write.
4. **Safer file handling** — reading a directory through a file endpoint is rejected instead of being treated as a normal file.
5. **API authentication** — protected HTTP endpoints require a configured `GEAI_API_KEY`, supplied through the `X-GEAI-API-Key` header.
6. **Repository hygiene** — runtime memory, crawler output and project data remain ignored by Git.

## Important security limitations

The API authentication layer is an important boundary, but it does **not** make GEAI production-secure by itself. Before exposing GEAI to untrusted networks, the following work remains:

- Several state-changing operations are still exposed as HTTP `GET` endpoints and should be migrated to appropriate `POST`/`PUT`/`DELETE` methods.
- The crawler accepts arbitrary HTTP/HTTPS targets and should have SSRF protections, DNS/IP validation, response-size limits and redirect controls.
- The crawler still contains a legacy hard-coded workspace path in `backend/crawler.py`; this should be migrated to the same `GEAI_HOME` configuration used by the memory and filesystem modules.
- The single shared API key is suitable for a personal/local tool, not a multi-user identity and authorization system.
- Dependencies are not pinned to known versions.
- There are no automated tests or CI checks covering the API, filesystem boundaries and crawler behavior.
- Ollama availability/model errors are not currently converted into user-friendly API errors.
- Rate limiting, HTTPS, CORS policy and structured security logging should be added before public deployment.

These limitations are intentionally documented rather than claiming that GEAI is production-secure.

## Safe deployment guidance

For personal use, keep GEAI bound to `127.0.0.1` and place its data directory outside the Git repository. If you later want remote access, add at minimum:

- Strong API authentication and authorization
- HTTPS behind a reverse proxy
- Rate limiting
- Appropriate CORS policy
- SSRF protection for crawler targets
- Request and response size limits
- Dependency pinning and automated security checks
- Automated tests for path traversal and crawler restrictions
- Non-secret structured logging

## Privacy

GEAI stores memory, facts, crawler output and project information locally. Treat the generated memory and crawler directories as potentially sensitive personal data. Do not commit them to a public repository.

## Development roadmap

See `ROADMAP.md` for planned work. The next engineering phase should focus on crawler SSRF protection, HTTP method cleanup, automated security tests, dependency pinning and then expansion of the AI/tool architecture.

## Disclaimer

GEAI is an experimental personal AI project. It is not a security product, autonomous security system, or production-grade enterprise platform. Review and test changes before using GEAI with important or sensitive data.

## License

No license is currently declared in this repository. Until a license is added, assume that the source is **not** granted general permission for redistribution or commercial reuse beyond rights provided by applicable law.
