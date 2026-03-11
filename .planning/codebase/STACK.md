# Technology Stack

**Analysis Date:** 2026-03-10

## Languages

**Primary:**
- Python 3.12+ - Backend API and all business logic
- JavaScript (ES6+/Module) - React frontend
- HTML5 - SPA template
- CSS3 - Frontend styling

**Secondary:**
- SQL - Database queries (SQLAlchemy ORM translates to PostgreSQL/SQLite)
- Batch scripting - Windows setup and startup scripts

## Runtime

**Backend Environment:**
- Python 3.12 (production Dockerfile: `FROM python:3.12-slim`)
- Virtual environment: `backend/.venv/`
- Activation: `backend\.venv\Scripts\activate.bat` (Windows)

**Frontend Environment:**
- Node.js runtime via Vite
- Package manager: npm (via `frontend-react/package.json`)

## Package Manager

**Backend:**
- pip (Python Package Installer)
- Requirements file: `backend/requirements.txt` (83 packages specified)
- Lock mechanism: Not detected (pip uses requirements.txt with pinned versions)

**Frontend:**
- npm
- Manifest: `frontend-react/package.json`
- Production build: Vite build output to `frontend-react-dist/`

## Frameworks

**Core Web Framework:**
- FastAPI 0.115.0+ - REST API framework
- Uvicorn 0.32.0+ (with `[standard]`) - ASGI server

**Frontend:**
- React 19.2.0 - UI library
- React Router DOM 7.13.1 - Client-side routing
- Vite 7.3.1 - Build tool and dev server

**Data Processing:**
- pandas 2.2.3 - Excel/CSV analysis
- openpyxl 3.1.5 - Excel file creation/manipulation
- xlsxwriter 3.2.0 - Excel styling and generation
- SQLAlchemy 2.0.25 - ORM and database abstraction
- Alembic 1.13.1 - Database schema migrations

**AI & Document Processing:**
- anthropic 0.49.0+ - Claude API SDK (messages.parse for Pydantic structured outputs)
- scikit-learn 1.6.0+ - TF-IDF vectorization and cosine similarity for semantic search
- pdfplumber 0.11.4 - PDF text extraction
- PyMuPDF 1.24.0+ - Fast PDF text extraction (10-100x faster than pdfplumber)
- pymupdf4llm 0.0.17 - Markdown output with tables from PDFs
- python-docx 1.1.2 - Word document parsing
- Pillow 10.2.0 - Image processing for OCR
- pytesseract 0.3.10 - Tesseract OCR integration
- unstructured[all-docs] 0.16.0+ (optional) - Universal document parser with layout detection
- ifcopenshell 0.7.0 (optional) - IFC/BIM file support

**Local LLM:**
- Ollama (external service at `http://localhost:11434`)
- Default model: llama3.2 (configurable via `OLLAMA_MODEL`)

**Testing:**
- pytest 7.4.4 - Test runner
- pytest-asyncio 0.23.3 - Async test support
- pytest-cov 4.1.0 - Coverage reporting
- black 23.12.1 - Code formatter
- ruff 0.1.14 - Linter
- mypy 1.7.1 - Type checker

**Security & Authentication:**
- cryptography 41.0.7 - Cryptographic operations
- python-jose[cryptography] 3.3.0 - JWT token handling
- passlib[bcrypt] 1.7.4 - Password hashing
- slowapi 0.1.9+ - Rate limiting middleware (optional, defaults to RATE_LIMIT_ENABLED=false unless production)

**Validation & Config:**
- pydantic 2.5.3+ - Data validation and settings management
- pydantic-settings 2.1.0 - Environment variable management
- python-dotenv 1.0.1 - .env file loading

**Async & Networking:**
- aiofiles 24.1.0 - Async file I/O
- httpx 0.28.1 - Async HTTP client
- requests 2.32.3 - Sync HTTP client (for ERP integration)
- asyncpg 0.29.0 - Async PostgreSQL driver (production database)
- aiosqlite 0.20.0 - Async SQLite driver (dev/testing)
- python-multipart 0.0.20 - File upload handling (FastAPI dependency)

**Monitoring & Observability:**
- python-json-logger 2.0.7 - Structured JSON logging
- prometheus-client 0.19.0 - Metrics collection and exposure

**Optional Integrations:**
- python-telegram-bot 21.10 - Telegram bot integration (enabled if TELEGRAM_BOT_TOKEN set)
- redis 5.0.0 (optional) - Redis cache backend (enabled if REDIS_URL set)
- gunicorn 23.0.0 - Production WSGI server (alternative to Uvicorn)
- psycopg2-binary 2.9.9 - PostgreSQL adapter (optional, required if using PostgreSQL)

**Database Drivers:**
- asyncpg 0.29.0 - Async PostgreSQL (production)
- aiosqlite 0.20.0 - Async SQLite (development/testing)
- sqlalchemy (includes both via SQLAlchemy dialects)

## Configuration

**Environment Management:**
- `config.py` - Centralized settings class with environment variable loading
- Environment variables via OS environment (production) or `.env` file (development)
- Base directory: `backend/config.py` sets BASE_DIR from file location
- Data directories auto-created: `data/`, `uploads/`, `outputs/`, `logs/`

**Key Configuration Files:**
- `backend/config.py` - Core settings (171 lines, comprehensive validation)
- `backend/requirements.txt` - All Python dependencies
- `frontend-react/package.json` - Frontend dependencies and build scripts
- `Dockerfile` - Container image specification (Python 3.12-slim based)
- `backend/alembic.ini` - Database migration configuration
- `backend/pytest.ini` - Test configuration

**Environment Variables (Production):**
- `ENVIRONMENT` - "development"|"staging"|"production" (default: "development")
- `ANTHROPIC_API_KEY` - Claude API authentication (required for Claude engine)
- `OLLAMA_URL` - Ollama endpoint (default: "http://localhost:11434")
- `OLLAMA_MODEL` - Ollama model name (default: "llama3.2")
- `AI_PREFERRED_ENGINE` - "auto"|"claude"|"ollama" (default: "auto")
- `DATABASE_URL` - PostgreSQL connection string (defaults to SQLite at `data/frank_tueren.db`)
- `REDIS_URL` - Optional Redis endpoint for distributed caching
- `TELEGRAM_BOT_TOKEN` - Telegram bot token (if TELEGRAM_ENABLED)
- `TELEGRAM_CHAT_ID` - Authorized Telegram chat ID
- `ERP_ENABLED` - Enable Bohr ERP integration
- `ERP_BOHR_URL` - ERP system endpoint
- `ERP_BOHR_API_KEY` - ERP API authentication
- `ERP_BOHR_USERNAME` / `ERP_BOHR_PASSWORD` - ERP basic auth (fallback)
- `HOST` - Server host (default: "0.0.0.0")
- `PORT` - Server port (default: 8000)
- `MAX_FILE_SIZE_MB` - Upload limit (default: 500)
- `CACHE_MAX_SIZE_MB` - In-memory cache size (default: 2000)
- `LOG_LEVEL` - "DEBUG"|"INFO"|"WARNING"|"ERROR" (auto: DEBUG if dev, INFO if prod)
- `JWT_SECRET` - JWT signing key (auto-generated and persisted to `data/.jwt_secret` if not set)
- `DEFAULT_ADMIN_EMAIL` - Initial admin email (default: "admin@franktueren.ch")
- `DEFAULT_ADMIN_PASSWORD` - Initial admin password (default: "ChangeMeOnFirstLogin!")

**Secrets Storage (Not in Version Control):**
- `.env` file (local development only)
- Environment variables (production)
- `data/.jwt_secret` - Generated JWT secret (created at first run)
- `data/users.json` - JSON-based user store (fallback when DB unavailable)

## Platform Requirements

**Development:**
- Python 3.12+ (enforced at startup via `setup.bat`)
- Windows (batch scripts use `.bat` syntax) or WSL/Linux/Mac with bash
- Virtual environment support (`python -m venv`)
- pip available
- Optional: Ollama running at `http://localhost:11434` for local LLM
- Optional: PostgreSQL 12+ if using production database
- Optional: Redis if using distributed cache

**Production:**
- Docker 20.10+ (Dockerfile provided)
- Container orchestration (Kubernetes, Docker Compose, etc.)
- 2GB+ RAM (for Ollama models if self-hosted)
- PostgreSQL 12+ (recommended)
- Ollama service accessible (local or remote)
- Python 3.12+ if not containerized

**Build & Deployment:**
- Docker: `docker build -t frank-tueren:latest .`
- Frontend build: `npm run build` (outputs to `frontend-react-dist/`)
- Backend: `uvicorn main:app --host 0.0.0.0 --port 8000` (or gunicorn for production)
- Health check endpoint: GET `/health` returns JSON with service status

**Networking:**
- Outbound HTTPS for Claude API (api.anthropic.com)
- Local HTTP for Ollama API (default: localhost:11434)
- Optional: ERP system connectivity (configurable URL)
- Optional: Telegram API (api.telegram.org)
- Optional: Redis connectivity

## Performance Optimizations

**Caching Strategy:**
- Three-tier in-memory cache: text cache, offer cache, project cache
- Optional Redis backend (REDIS_URL) for distributed caching
- TTL defaults: 1h (text), 30m (offer/project), 1h (ERP prices)
- Cache max size: configurable (default 2000MB)

**Compression:**
- GZIP compression enabled by default for responses >1000 bytes
- Controlled by `ENABLE_COMPRESSION` and `COMPRESSION_MIN_SIZE_BYTES`

**Database Optimization:**
- Connection pooling (SQLAlchemy default)
- Async drivers for I/O-bound operations (asyncpg, aiosqlite)
- Pre-ping enabled to detect stale connections

**Document Processing:**
- PyMuPDF used for fast PDF extraction (10-100x faster than pdfplumber)
- Semantic search index pre-built at startup
- TF-IDF vectorization with cosine similarity for product matching

---

*Stack analysis: 2026-03-10*
