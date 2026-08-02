# CityEstate — Egyptian Real Estate Multi-Agent System

CityEstate is an AI-powered real estate automation platform for the Egyptian market. It combines CrewAI multi-agent orchestration, FastAPI REST endpoints, Streamlit dashboards, and Chrome browser extensions to automate lead qualification, property matching, WhatsApp/Facebook outreach, and market research.

## Features

- **AI Lead Qualification** — CrewAI agents qualify Facebook leads using LLM-powered analysis
- **Property Matching Engine** — Matches client requests to available properties with scoring
- **WhatsApp Automation** — Browser-based WhatsApp Web automation for inbound/outbound messaging
- **Facebook Automation** — Automated Facebook group monitoring and lead extraction
- **Multi-Agent AI System** — 14+ specialized agents for research, outreach, and analysis
- **Notification Dispatch** — Multi-channel notification system (WhatsApp, SMS, Email)
- **Webhook Integration** — HMAC-SHA256 signed webhooks for Google Forms, Tally, Typeform
- **Dashboard** — Streamlit-based real-time dashboard with metrics and monitoring
- **Chrome Extensions** — Bridge extension (backend-connected) and standalone extension (local AI)

## Project Structure

```
cityestate/
├── src/
│   ├── api/                  # FastAPI REST API
│   │   ├── main.py           # App factory with CORS, security, rate limiting
│   │   ├── auth.py           # JWT auth + bcrypt + brute-force protection
│   │   ├── routes/           # API route modules
│   │   ├── models.py         # Pydantic models with XSS sanitization
│   │   └── deps.py           # Database and auth dependencies
│   ├── ai_crew/              # CrewAI multi-agent system
│   │   ├── crew/             # Crew orchestrator package
│   │   ├── tools/            # Modularized tools (9 domain modules)
│   │   ├── agents.py         # Agent definitions
│   │   ├── tasks.py          # Task definitions
│   │   └── llm_config.py     # LLM provider configuration
│   ├── messaging/            # Notification dispatch system
│   ├── cache_utils.py        # TTL in-memory cache
│   ├── skills/               # 18 AI skills
│   ├── matching/             # Lead-property matching engine
│   ├── scheduler/            # APScheduler job orchestration
│   ├── database/             # SQLAlchemy models + data ingester
│   ├── automation/           # Browser automation (WhatsApp, Facebook, Phone)
│   ├── session_vault/        # Encrypted session/cookie management
│   ├── error_handling.py     # Circuit breakers, retry logic, error responses
│   └── logging_config.py     # Structured logging + metrics
├── cityestate-extension/     # Chrome extension (backend bridge)
├── cityestate-standalone/    # Chrome extension (standalone AI)
├── cityestate-common/        # Shared assets for both extensions
├── tests/                    # Test suite
├── scripts/                  # Utility scripts
└── alembic/                  # Database migrations
```

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your API keys and secrets
python scripts/bootstrap_env.py
```

### 3. Start the API server

```bash
python main.py --serve
```

### 4. Start the dashboard

```bash
streamlit run src/dashboard/app.py
```

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `/api/v1/auth/token` | JWT authentication |
| `/api/v1/auth/register` | User registration (admin only) |
| `/api/v1/leads` | Lead CRUD operations |
| `/api/v1/properties` | Property search and listing |
| `/api/v1/requests` | Client request management |
| `/api/v1/webhooks/form` | HMAC-signed webhook intake |
| `/health` | Health check |
| `/metrics` | System metrics |
| `/cache/keys` | List cached entries |
| `/cache/clear` | Clear all caches |

## Security

- JWT tokens (HS256) for API authentication
- bcrypt for password hashing
- Fernet (AES-128-CBC) for session vault encryption
- HMAC-SHA256 for webhook signature verification
- CORS lockdown via `ALLOWED_ORIGINS` env var
- Rate limiting (120 req/min per IP)
- Request size limiting (1MB default)
- Security headers (HSTS, X-Frame-Options, X-Content-Type-Options)
- Brute-force protection for login (5 attempts / 5 min)
- XSS sanitization on all user-facing text fields

## Testing

```bash
# Run all tests
pytest tests/ -v

# Run specific test files
pytest tests/test_messaging.py tests/test_auth.py -v

# Run with coverage
pytest tests/ -v --cov=src --cov-report=html
```

## Docker

```bash
docker compose up -d
docker compose down
```

## Configuration

Key environment variables:

| Variable | Description | Required |
|----------|-------------|----------|
| `JWT_SECRET` | HS256 signing key | Yes |
| `DATABASE_URL` | SQLite or PostgreSQL URL | No (defaults to SQLite) |
| `ALLOWED_ORIGINS` | Comma-separated CORS origins | No |
| `ROUTER_API_KEY` | OpenRouter API key | For LLM features |
| `ADMIN_PASSWORD` | Initial admin password | Yes (first run) |
| `MAX_REQUEST_SIZE` | Request body size limit (bytes) | No (default 1MB) |

## Architecture

CityEstate uses a multi-layered architecture:

1. **API Layer** — FastAPI with dependency injection, middleware for auth/rate-limiting/security
2. **Agent Layer** — CrewAI multi-agent system with specialized agents for each domain
3. **Tool Layer** — Modularized tools for database, WhatsApp, web, properties, data, content, phone, market
4. **Automation Layer** — Playwright-based browser automation for WhatsApp and Facebook
5. **Extension Layer** — Chrome extensions for browser-integrated AI features
6. **Dashboard Layer** — Streamlit for real-time monitoring and management

## License

Proprietary — CityEstate