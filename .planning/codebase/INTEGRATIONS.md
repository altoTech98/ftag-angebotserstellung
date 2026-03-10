# External Integrations

**Analysis Date:** 2026-03-10

## APIs & External Services

**Claude API (Anthropic):**
- Service: Claude AI models for document analysis, requirement extraction, offer generation
- SDK: `anthropic>=0.49.0`
- Auth: Environment variable `ANTHROPIC_API_KEY`
- Model: `claude-sonnet-4-6` (configurable via `CLAUDE_MODEL`)
- Features: Pydantic structured output parsing (messages.parse)
- Usage files: `backend/services/claude_client.py`, `backend/services/ai_service.py`
- Status: Primary AI engine (auto-selected if API key present)
- Fallback: Ollama or regex pattern matching if Claude unavailable

**Telegram Bot API:**
- Service: Telegram messaging and file processing
- SDK: `python-telegram-bot==21.10`
- Auth: Environment variable `TELEGRAM_BOT_TOKEN`
- Authorized Chat: Environment variable `TELEGRAM_CHAT_ID`
- Features: Command handlers, file upload/download, message streaming
- Usage file: `backend/services/telegram_bot.py`
- Status: Optional (enabled if TELEGRAM_BOT_TOKEN set)
- Endpoints: `/start`, `/status`, `/katalog`, `/history`, `/clear` and file handling
- Startup: Initialized in main.py lifespan if `settings.TELEGRAM_ENABLED`

**ERP Integration (Bohr System):**
- Service: Frank Türen AG's Bohr ERP system for pricing and availability
- Protocol: HTTP REST API
- Auth: Bearer token (preferred) or HTTP Basic Auth
- Base URL: Environment variable `ERP_BOHR_URL`
- Credentials:
  - `ERP_BOHR_API_KEY` (preferred authentication method)
  - `ERP_BOHR_USERNAME` + `ERP_BOHR_PASSWORD` (fallback)
- Features:
  - Product pricing (net/gross with VAT)
  - Stock availability and delivery times
  - Discount calculation
- Usage file: `backend/services/erp_connector.py`
- Status: Optional (enabled if `ERP_ENABLED=true` and credentials provided)
- Caching: Prices cached for 1 hour (configurable via `ERP_PRICE_CACHE_TTL_SECONDS`)
- Fallback: Estimated pricing if ERP unavailable and `ERP_FALLBACK_TO_ESTIMATE=true`
- Request timeout: 10 seconds (configurable via `ERP_REQUEST_TIMEOUT`)

## Data Storage

**Databases:**

**PostgreSQL (Production):**
- Provider: PostgreSQL 12+
- Connection: Via environment variable `DATABASE_URL` (e.g., `postgresql://user:pass@host/db`)
- Async Driver: `asyncpg>=0.29.0`
- Usage: User management, project history, feedback storage, job metadata
- Schema: Managed by Alembic migrations (`backend/alembic.ini`)
- Table models: `backend/db/models.py`
- Connection pool: SQLAlchemy with pre-ping enabled

**SQLite (Development/Testing):**
- Location: `data/frank_tueren.db`
- Async Driver: `aiosqlite>=0.20.0`
- Auto-created: Yes, on first run via `db/engine.py`
- Purpose: Local development without PostgreSQL setup
- Fallback: Used if `DATABASE_URL` not set

**File Storage:**
- Document uploads: `uploads/` directory (local filesystem)
- Generated offers/reports: `outputs/` directory (local filesystem)
- Product catalog: `data/produktuebersicht.xlsx` (local Excel file)
- Logs: `logs/` directory (app.log, structured.log)
- Feedback store: `data/matching_feedback.json` (user corrections for AI training)
- Users file: `data/users.json` (JSON fallback if database unavailable)
- JWT secret: `data/.jwt_secret` (auto-generated on first startup)

**Caching:**

**In-Memory Cache (Primary):**
- Implementation: Three separate cache objects (`text_cache`, `offer_cache`, `project_cache`)
- Max size: Configurable (default 2000MB via `CACHE_MAX_SIZE_MB`)
- TTL settings:
  - Text cache: 3600 seconds (1 hour)
  - Project cache: 1800 seconds (30 minutes)
  - Offer cache: 1800 seconds (30 minutes)
- Usage file: `backend/services/memory_cache.py`
- Stats endpoint: GET `/api/health` returns cache statistics in debug mode

**Redis (Optional Distributed Cache):**
- Service: Redis 5.0+
- Connection: Environment variable `REDIS_URL` (e.g., `redis://localhost:6379/0`)
- Status: Auto-detected; used if available, falls back to in-memory
- Purpose: Multi-instance cache sharing in production
- Implementation: Falls back to in-memory if REDIS_URL not set or Redis unavailable
- Usage: ERP price cache, semantic search index cache

## Authentication & Identity

**Auth Provider:**
- Implementation: Custom JWT-based (not OAuth/external)
- Token type: Bearer tokens (HS256 algorithm)
- Storage: SQLAlchemy ORM (Users table) with JSON fallback
- Token generation: `backend/services/auth_service.py`
- Token verification: Middleware in `backend/main.py` (auth_middleware)
- Token expiration: 24 hours (configurable via `ACCESS_TOKEN_EXPIRE_HOURS`)
- JWT secret: Auto-generated or provided via `JWT_SECRET` environment variable

**Password Management:**
- Hashing: bcrypt with salt (passlib[bcrypt] 1.7.4)
- Admin setup: Environment variables `DEFAULT_ADMIN_EMAIL` and `DEFAULT_ADMIN_PASSWORD`
- Default credentials: admin@franktueren.ch / ChangeMeOnFirstLogin! (override via env vars)
- First-time admin creation: Triggered in main.py lifespan via `init_admin_user()`

**Protected Routes:**
- All `/api/*` routes require valid Bearer token (except whitelist)
- Whitelist: `/api/auth/login`, `/api/auth/logout`, `/health`, `/api/health`, `/`, `/docs`, `/redoc`
- Token extraction: HTTP Authorization header (`Bearer <token>`) or query param (for SSE)

## Monitoring & Observability

**Error Tracking:**
- Method: Structured logging to JSON files
- Library: `python-json-logger==2.0.7`
- Log files: `logs/app.log` (combined), `logs/structured.log` (JSON)
- Log levels: DEBUG (dev), INFO (prod) - configurable via `LOG_LEVEL` env var
- Custom exceptions: `backend/services/exceptions.py` (FrankTuerenError)

**Logging:**
- Framework: Python logging module
- Setup: `backend/services/logger_setup.py`
- Format: JSON for structured logging, human-readable for console
- Request logging: FastAPI access logs enabled
- Middleware logging: Request/response in error_and_cache_middleware

**Health Checks:**
- Endpoint: GET `/health` (public, no auth required)
- Response: JSON with status of all services (Claude, Ollama, catalog, cache, DB)
- Components checked:
  - AI service availability (Claude vs Ollama)
  - Ollama status and models
  - Product catalog (main_products count, all_profiles count)
  - Caching system status
  - Database connectivity
  - Telegram bot (if enabled)
  - ERP system (if enabled)

**Detailed Status Endpoints:**
- `/api/health` - Alias for `/health` with auth requirement removed
- `/api/availability/status` - Detailed service status and uptime statistics
- `/api/ollama/status` - Ollama watchdog and health details
- `/info` - Application version and settings (debug mode only)

**Metrics:**
- Library: `prometheus-client==0.19.0`
- Metrics types: Counters, gauges, histograms for performance monitoring
- Endpoint: Prometheus-compatible metrics endpoint (if implemented)

**Service Monitoring:**
- Availability Manager: `backend/services/availability_manager.py`
  - 24/7 monitoring of all services
  - Auto-healing on failure detection
  - Service uptime statistics
  - Health check interval: 30 seconds

- Ollama Watchdog: `backend/services/ollama_watchdog.py`
  - Dedicated monitoring for Ollama LLM service
  - Auto-restart on failure
  - Windows Task Scheduler integration (production)
  - Max restart attempts: 5 with exponential backoff
  - Health check interval: Configurable (default in watchdog)

## CI/CD & Deployment

**Hosting:**
- Docker container (primary recommendation)
- Dockerfile: `backend/Dockerfile` (Python 3.12-slim)
- Health check: Docker HEALTHCHECK defined (30s interval, 10s timeout, 40s startup grace)

**CI Pipeline:**
- Not detected - no `.github/workflows/`, `.gitlab-ci.yml`, or `circleci/` found
- Testing: Test framework configured (`pytest`, `pytest-cov`)
- Linting/Formatting: Configured (ruff, black, mypy) but not CI-integrated

**Local Development:**
- Startup: `start.bat` (Windows) or `backend/main.py` with `python -m uvicorn`
- Setup: `setup.bat` creates venv and installs dependencies
- Dev mode: Reload enabled, debug endpoint documentation exposed (/docs, /redoc)

**Production Deployment:**
- Container: `docker build -t frank-tueren:latest .`
- Server: Uvicorn or Gunicorn on port 8000
- Environment: Set all required env vars before startup
- Frontend: React build included in container at `frontend-react-dist/`
- Health check: Curl-based in Docker (GET /api/health)

## Environment Configuration

**Required Environment Variables:**
- `ANTHROPIC_API_KEY` - Claude API authentication (required if using Claude engine)
- For ERP integration:
  - `ERP_ENABLED=true`
  - `ERP_BOHR_URL` - ERP endpoint
  - `ERP_BOHR_API_KEY` or `ERP_BOHR_USERNAME`/`ERP_BOHR_PASSWORD`
- For Telegram bot:
  - `TELEGRAM_BOT_TOKEN` - Telegram bot token
  - `TELEGRAM_CHAT_ID` - Authorized chat ID

**Recommended Environment Variables:**
- `ENVIRONMENT=production` - Set to "production" for deployment
- `DATABASE_URL` - PostgreSQL connection (defaults to SQLite if not set)
- `REDIS_URL` - Redis cache endpoint (optional, enables distributed caching)
- `OLLAMA_URL` - Ollama endpoint (default: http://localhost:11434)
- `OLLAMA_MODEL` - Ollama model (default: llama3.2)
- `HOST=0.0.0.0` - Server host
- `PORT=8000` - Server port
- `LOG_LEVEL=INFO` - Logging verbosity
- `JWT_SECRET` - JWT signing key (auto-generated if not set)
- `DEFAULT_ADMIN_EMAIL` - Admin user email
- `DEFAULT_ADMIN_PASSWORD` - Admin user password (MUST change on first login)

**Secrets Location:**
- Environment variables: Primary (production)
- `.env` file: Development only (loaded via python-dotenv)
- `data/.jwt_secret` - Generated JWT secret (created at first run)
- Database: User passwords hashed with bcrypt
- ERP credentials: Stored in environment only (never in code)
- API keys: Environment variables only

## Webhooks & Callbacks

**Incoming Webhooks:**
- Not detected

**Outgoing Webhooks:**
- None configured
- ERP integration uses polling/request model, not webhooks
- Telegram bot uses polling model via telegram-bot-api

**Event Streaming:**
- Server-Sent Events (SSE): No SSE endpoints detected
- WebSockets: Not implemented

**Asynchronous Tasks:**
- Background job support: `MAX_CONCURRENT_JOBS` config (default: 10)
- Job timeout: 7200 seconds (2 hours) for large PDF processing
- Background tasks: File cleanup (every 6 hours), Telegram message processing
- Task implementation: asyncio.create_task() in lifespan

## API Client Libraries

**HTTP Clients:**
- `httpx==0.28.1` - Async HTTP (primary for Ollama, Claude fallback detection)
- `requests==2.32.3` - Sync HTTP (ERP connector)

**API Integration Files:**
- Ollama: `backend/services/ollama_client.py` (circuit breaker, retry logic)
- Claude: `backend/services/claude_client.py` (deprecated, kept for backward compatibility)
- ERP: `backend/services/erp_connector.py` (with caching and fallback)
- AI abstraction: `backend/services/ai_service.py` (unified 3-tier failover)

---

*Integration audit: 2026-03-10*
