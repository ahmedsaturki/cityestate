# CityEstate Architecture

## System Overview

CityEstate is a multi-layered Egyptian real estate automation platform. The architecture follows a **modular monolith** pattern with clear separation of concerns across AI agents, API services, browser automation, and data pipelines.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Client Layer                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────────────────┐ │
│  │ Chrome        │  │ Streamlit    │  │ External Integrations       │ │
│  │ Extension     │  │ Dashboard    │  │ (Webhooks, APIs, Email)     │ │
│  │ (WhatsApp +   │  │ (1698 lines) │  │                             │ │
│  │  Facebook)    │  │              │  │                             │ │
│  └──────┬───────┘  └──────┬───────┘  └─────────────┬───────────────┘ │
│         │                 │                         │                  │
├─────────┼─────────────────┼─────────────────────────┼──────────────────┤
│         │                 │                         │                  │
│  ┌──────▼─────────────────▼─────────────────────────▼───────────────┐  │
│  │                    FastAPI Application Layer                      │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  Routes: auth | automation | content | dashboard | data    │  │  │
│  │  │  routes: leads | properties | requests | scheduler |       │  │  │
│  │  │  skills | webhooks | websocket                             │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  Middleware: CORS | Auth (JWT) | Error Handling | Logging  │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    AI Agent Layer (CrewAI)                       │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  CityEstateCrew — Orchestrator                              │  │  │
│  │  │  ├── Lead Qualifier Agent (Facebook Radar)                  │  │  │
│  │  │  ├── Sales Rep Agent (Personalized Outreach)                │  │  │
│  │  │  ├── Copywriter Agent (Marketing Content)                   │  │  │
│  │  │  ├── Data Collector Agent (Web Scraping)                    │  │  │
│  │  │  ├── Data Enricher Agent (Lead Enrichment)                  │  │  │
│  │  │  ├── Lead Analyst Agent (Scoring & Analysis)                │  │  │
│  │  │  ├── Property Expert Agent (Matching)                       │  │  │
│  │  │  ├── Market Researcher Agent (Intelligence)                 │  │  │
│  │  │  ├── Buyer Researcher Agent (Intent Detection)              │  │  │
│  │  │  ├── Personalized Writer Agent (Message Generation)         │  │  │
│  │  │  └── Message Reviewer Agent (Quality Assurance)             │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Skills Layer (18 Skills)                      │  │
│  │  ComputerUse | GoogleSearch | WebScraper | GoogleMaps | Email   │  │
│  │  DocumentProc | ImageAnalysis | VoiceSpeech | TaskManager       │  │
│  │  GoalTracker | Checklist | DecisionMatrix | Kanban | TimeTracker│  │
│  │  ReportGenerator | Notes | Translator | WhatsAppWeb | LeadScore │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Automation Layer                              │  │
│  │  ┌─────────────────────────────────────────────────────────────┐  │  │
│  │  │  Browser Automation (Playwright)                            │  │  │
│  │  │  ├── WhatsApp Expert (14K lines)                           │  │  │
│  │  │  ├── Facebook Expert                                       │  │  │
│  │  │  ├── Phone Expert                                          │  │  │
│  │  │  ├── Writer Expert                                         │  │  │
│  │  │  └── Classifier Expert                                     │  │  │
│  │  └─────────────────────────────────────────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Data & Storage Layer                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │  │
│  │  │ SQLAlchemy    │  │ SQLite/Postgres│  │ Alembic Migrations    │ │  │
│  │  │ ORM           │  │ (dev/prod)     │  │ (versioned schema)    │ │  │
│  │  └──────────────┘  └──────────────┘  └───────────────────────┘ │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │  │
│  │  │ Session Vault │  │ Encrypted    │  │ File-based JSON stores│ │  │
│  │  │ (Fernet)      │  │ Backups      │  │ (goals, kanban, etc.) │ │  │
│  │  └──────────────┘  └──────────────┘  └───────────────────────┘ │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    Infrastructure Layer                          │  │
│  │  Docker Compose | APScheduler | WebSocket | Webhooks | MCP      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Module Dependency Graph

```
main.py
  ├── src.api.main (FastAPI app)
  │     ├── src.api.routes.* (12 route modules)
  │     │     ├── src.api.auth (JWT + bcrypt)
  │     │     ├── src.api.deps (SessionLocal, engine)
  │     │     ├── src.database.models (User, Property, ClientRequest, MessageLog)
  │     │     ├── src.database.ingester (Lead model, Base)
  │     │     ├── src.ai_crew.crew (CityEstateCrew)
  │     │     │     ├── src.ai_crew.agents (agent definitions)
  │     │     │     ├── src.ai_crew.tasks (task definitions)
  │     │     │     ├── src.ai_crew.tools (tool definitions)
  │     │     │     ├── src.ai_crew.llm_config (LLM provider)
  │     │     │     ├── src.ai_crew.outreach_agents
  │     │     │     └── src.ai_crew.outreach_tasks
  │     │     ├── src.skills.* (18 skills)
  │     │     ├── src.automation.* (browser automation)
  │     │     │     └── src.automation.experts.* (WhatsApp, Facebook, Phone, Writer)
  │     │     ├── src.outreach.* (campaign engine)
  │     │     ├── src.matching.* (lead-property matching)
  │     │     ├── src.scheduler.* (job scheduling)
  │     │     ├── src.services.* (WhatsApp services)
  │     │     ├── src.session_vault.* (encrypted sessions)
  │     │     ├── src.data.* (crawler, enricher, extractor, quality)
  │     │     ├── src.mcp.* (MCP server)
  │     │     ├── src.backup.* (encrypted backup)
  │     │     └── src.config.* (YAML config loader)
  │     ├── src.api.websocket_manager
  │     └── src.api.bridge_handler
  ├── src.scheduler.engine (APScheduler)
  ├── src.scheduler.jobs (scheduled job definitions)
  └── scripts.* (utility scripts)
```

## Data Flow

### Lead Qualification Flow
```
Facebook Group Post
  → src.automation.experts.facebook (scrape post)
  → src.ai_crew.crew.qualify_leads() (CrewAI agent)
  → src.ai_crew.tools (web search, scraper, maps)
  → Qualified Lead (score, type, budget, area, urgency)
  → src.database.ingester (store in DB)
  → src.matching.engine (match to properties)
  → src.outreach.dispatcher (send notification)
```

### Outreach Flow
```
Client Request (matched)
  → src.outreach.intent_parser (parse intent)
  → src.outreach.llm_generator (generate personalized message)
  → src.outreach.content_generator (create content)
  → src.outreach.dispatcher (send via WhatsApp/Facebook)
  → src.outreach.campaign_log (log campaign activity)
  → src.outreach.rate_limiter (respect rate limits)
```

### Notification Flow
```
Scheduled Job (main.py --notify)
  → src.database.models.ClientRequest (find matched + not notified)
  → src.matching.notifier.send_match_notification()
  → src.services.whatsapp_web (send via WhatsApp Web)
  → src.database.models.MessageLog (record status)
```

## Database Schema

### Tables
- **users** — Authentication (id, username, password_hash, full_name, role, is_active)
- **properties** — Property inventory (id, title, description, property_type, status, area, city, district, price, bedrooms, bathrooms, size, images, contact_phone, contact_email, created_at)
- **client_requests** — Client property requests (id, client_name, phone, email, budget_min, budget_max, area, property_type, status, matched_property_id, notified_at, notification_channel)
- **message_logs** — Message delivery logs (id, client_request_id, channel, message, status, sent_at)
- **leads** — CRM leads from CSV ingestion (id, title, url, source, lead_type, budget, area, interest, urgency, phone, email, status, score, tags)

## Security Architecture

```
Client Request
  │
  ├── CORS Check (ALLOWED_ORIGINS)
  ├── JWT Token Validation (src.api.auth.get_current_user)
  ├── Password Hash Verification (bcrypt)
  ├── Session Vault Decryption (Fernet)
  ├── Webhook HMAC Verification (HMAC-SHA256)
  │
  └── Business Logic
        │
        ├── Input Sanitization
        ├── Rate Limiting (outreach.rate_limiter)
        ├── Encryption at Rest (session_vault)
        └── Audit Logging
```

## Deployment Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  API        │     │  Dashboard  │     │  Scheduler  │
│  :8000      │     │  :8501      │     │  (background)│
│  (FastAPI)  │     │  (Streamlit)│     │  (APScheduler)│
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────▼──────┐
                    │  SQLite /   │
                    │  PostgreSQL │
                    │  (output/)  │
                    └─────────────┘
```

## Key Design Decisions

1. **Modular Monolith** — All modules in a single codebase with clear boundaries, avoiding microservices complexity while maintaining separation of concerns.

2. **CrewAI for AI Agents** — Chosen for its structured agent/task/tool pattern, making it easy to add new agents and manage LLM interactions.

3. **Playwright for Browser Automation** — Provides reliable browser control for WhatsApp Web and Facebook automation with intelligent waiting.

4. **Fernet Encryption for Session Vault** — AES-128-CBC encryption for storing browser session cookies and sensitive data at rest.

5. **SQLite for Development, PostgreSQL for Production** — Easy local development with SQLite, scalable production with PostgreSQL via SQLAlchemy ORM.

6. **Streamlit for Dashboard** — Rapid prototyping of interactive dashboards with minimal code, connected to the FastAPI backend via HTTP.

7. **YAML Configuration** — `agents.yaml` and `tasks.yaml` provide declarative agent and task configuration, making it easy to modify behavior without code changes.

8. **Chrome Extensions** — Two variants (extension + standalone) for different deployment scenarios, sharing core automation logic.