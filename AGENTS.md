# CityEstate — Agent Context

## Build Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Start API server
python main.py --serve

# Start dashboard
streamlit run src/dashboard/app.py

# Run all scheduled jobs
python main.py --all

# Run specific job
python main.py --match
python main.py --notify
python main.py --backup
python main.py --vault-check

# Seed database
python scripts/seed_data.py

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html

# Lint
ruff check src/ tests/ || flake8 src/ tests/

# Docker
docker compose up -d
docker compose down

## Windows Docker Workaround
Docker Desktop on Windows often has broken port forwarding for localhost.
If `localhost:8000` is not accessible from the host/browser:
- Run the API directly instead of Docker: `python main.py --serve`
- Run scheduler: `python main.py --all`
- The Chrome Extension connects to `http://localhost:8000` by default

## Chrome Extension Auto-Configuration
The CityEstate Bridge extension auto-configures its `extensionSecret` on first run.
The `DEFAULT_EXTENSION_SECRET` is set in `service-worker.js` and auto-saved to `chrome.storage.local`.
No manual popup configuration is needed for initial setup.
```

## Project Structure

- `src/api/` — FastAPI REST API (12 route modules)
  - `main.py` — FastAPI app factory with CORS, security headers, rate limiting, request size limiting
  - `auth.py` — JWT auth + bcrypt password hashing + brute-force protection
  - `routes/` — API route modules (auth, leads, properties, requests, automation, dashboard, scheduler, webhooks, content, data, skills, websocket)
- `src/ai_crew/` — CrewAI multi-agent system
  - `crew/` — Modularized crew package (`__init__.py` with CityEstateCrew)
  - `tools/` — Modularized tools package (database, whatsapp, web, properties, data, content, phone, market)
  - `agents.py` — Agent definitions
  - `tasks.py` — Task definitions
- `src/messaging/` — Notification dispatch system (MessageDispatcher)
- `src/cache_utils.py` — TTL in-memory cache with decorator
- `src/automation/` — Browser automation (WhatsApp, Facebook, Phone)
- `src/skills/` — 18 AI skills (search, scrape, maps, email, voice, etc.)
- `src/outreach/` — Campaign engine, content generation, dispatch
- `src/matching/` — Lead-property matching engine
- `src/scheduler/` — APScheduler job orchestration
- `src/database/` — SQLAlchemy models + data ingester
- `src/services/` — WhatsApp Web/Cloud services
- `src/session_vault/` — Encrypted session/cookie management
- `src/data/` — Data pipeline (crawler, enricher, extractor, quality)
- `src/mcp/` — MCP server for WhatsApp
- `src/backup/` — Encrypted backup system
- `src/config/` — YAML configuration (agents.yaml, tasks.yaml)
- `src/dashboard/` — Streamlit dashboard (app.py, 1698 lines)
- `cityestate-extension/` — Chrome extension (WhatsApp + Facebook bridge)
- `cityestate-standalone/` — Standalone extension (auto-reply + lead scorer)
- `cityestate-common/` — Shared assets for both extensions (icons, templates)
- `tests/` — 30+ test files
- `scripts/` — Utility scripts (bootstrap, seed, campaign orchestrator)
- `alembic/` — Database migrations

## Key Files

| File | Purpose |
|------|---------|
| `README.md` | Project documentation and quick start guide |
| `main.py` | CLI entry point — match, notify, backup, serve |
| `src/api/main.py` | FastAPI app factory with security middleware |
| `src/api/auth.py` | JWT auth + bcrypt + brute-force protection |
| `src/api/routes/skills.py` | Skills API endpoints |
| `src/ai_crew/crew/__init__.py` | CityEstateCrew orchestrator (563 lines) |
| `src/ai_crew/agents.py` | Agent definitions (14.8K lines) |
| `src/ai_crew/tools/` | Modularized tools package (9 domain modules) |
| `src/ai_crew/tools/__init__.py` | Tools package entry point + get_all_tools |
| `src/messaging/__init__.py` | MessageDispatcher notification system |
| `src/cache_utils.py` | TTL in-memory cache with decorator |
| `src/api/models.py` | Pydantic models with XSS sanitization |
| `src/dashboard/app.py` | Streamlit dashboard (1698 lines) |
| `src/matching/engine.py` | Matching algorithm with area aliases |
| `src/database/ingester.py` | CSV lead ingester (740 lines) |
| `src/database/models.py` | SQLAlchemy models (329 lines) |
| `src/dashboard/app.py` | Streamlit dashboard (1698 lines) |
| `src/matching/engine.py` | Matching algorithm with area aliases (428 lines) |
| `src/database/ingester.py` | CSV lead ingester (740 lines) |
| `src/database/models.py` | SQLAlchemy models (329 lines) |
| `src/automation/experts/whatsapp.py` | WhatsApp automation expert (14K lines) |
| `src/session_vault/vault.py` | Session vault management |
| `src/session_vault/encryption.py` | Fernet encryption manager |

## Code Style

- Python 3.12+ with type hints
- Follow PEP 8 conventions
- Use `logging` module for all logging (not print)
- All public functions must have docstrings
- Use SQLAlchemy ORM for all database operations (no raw SQL)
- Use Pydantic models for request/response validation
- Use FastAPI `Depends()` for dependency injection
- Use `async`/`await` for I/O-bound operations

## Testing

- Test framework: pytest + pytest-asyncio
- Test directory: `tests/`
- Run all tests: `pytest tests/ -v`
- Run with coverage: `pytest tests/ -v --cov=src`
- Test naming: `test_<module_name>.py`
- Each test file should have a corresponding module test

## Security

- JWT tokens for API authentication (HS256)
- bcrypt for password hashing
- Fernet (AES-128-CBC) for session vault encryption
- HMAC-SHA256 for webhook signature verification
- CORS lockdown via `ALLOWED_ORIGINS` env var
- No secrets in code — all secrets via `.env` file
- `.env` is gitignored; `.env.example` is the template

## Known Issues / TODOs

1. No CI/CD pipeline configured (GitHub Actions workflow exists but needs expansion)
2. SQLite default — not production-ready without PostgreSQL migration
3. Dashboard `app.py` (1698 lines) may have performance issues with unnecessary re-renders
4. Type safety: some functions in `src/api/routes/` still missing return type hints (50+ fixed, remaining are minor)
8. Dashboard `app.py` (1698 lines) may have performance issues with unnecessary re-renders