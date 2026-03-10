# Architecture

**Analysis Date:** 2026-03-10

## Pattern Overview

**Overall:** Layered N-tier architecture with FastAPI backend + React frontend, centered on asynchronous background job processing with in-memory caching.

**Key Characteristics:**
- Separation of concerns via FastAPI routers → services → data/persistence layers
- Asynchronous task execution (background jobs with SSE streaming)
- Multiple AI engine failover (Claude API → Ollama → Regex fallback)
- In-memory caching with TTL-based expiration (text, project, offer caches)
- Optional database persistence (SQLAlchemy) with migrations (Alembic)
- Middleware-based auth, compression, and CORS
- Static React SPA with client-side routing

## Layers

**Presentation Layer:**
- Purpose: User-facing React SPA and API endpoints
- Location: `frontend-react/src` (React components, hooks, context) and `backend/routers` (FastAPI endpoints)
- Contains: Pages, components, forms, API request handlers
- Depends on: Auth context, AppContext, API client library
- Used by: End users via browser

**API/Router Layer:**
- Purpose: HTTP endpoint definitions and request/response handling
- Location: `backend/routers/` (auth.py, upload.py, analyze.py, offer.py, feedback.py, history.py, catalog.py, erp.py)
- Contains: Endpoint definitions, request validation (Pydantic models), response formatting, background job orchestration
- Depends on: Services layer, Job store, database models
- Used by: Frontend, external clients

**Business Logic/Services Layer:**
- Purpose: Core application functionality independent of HTTP transport
- Location: `backend/services/`
- Contains: Document parsing, AI matching, offer generation, product indexing, authentication, caching, job management
- Key services: `ai_service.py`, `product_matcher.py`, `catalog_index.py`, `document_parser.py`, `result_generator.py`, `auth_service.py`, `memory_cache.py`, `job_store.py`
- Depends on: Data persistence, external APIs (Claude, Ollama, ERP), error handling
- Used by: Routers, other services

**Data/Persistence Layer:**
- Purpose: Database models and data access
- Location: `backend/db/` (engine.py, models.py) and `backend/models/` (data classes)
- Contains: SQLAlchemy ORM models (User, Project, ProjectFile, Analysis, Requirement, Feedback), async session management
- Depends on: SQLAlchemy, SQLite or PostgreSQL
- Used by: Services, routers (via FastAPI dependency injection)

**Configuration Layer:**
- Purpose: Centralized settings management
- Location: `backend/config.py`
- Contains: Environment variables, settings validation, hardcoded constants (VAT rates, company info)
- Depends on: Environment
- Used by: All layers

**Infrastructure Layer:**
- Purpose: Utilities and cross-cutting concerns
- Location: `backend/services/` (logger_setup.py, error_handler.py, exceptions.py, memory_cache.py, ollama_watchdog.py, availability_manager.py)
- Contains: Logging, error handling, caching, availability monitoring, background job tracking
- Depends on: Standard library, config
- Used by: All layers

## Data Flow

**Upload → Analysis → Matching → Offer Generation:**

1. **File Upload** (`POST /api/upload`)
   - Frontend sends file via FormData
   - Router validates file (size, type)
   - Service: `document_parser.py` → extracts text from PDF/Word/Excel/etc.
   - Text cached in `text_cache` (TTL: 1 hour)
   - Returns `file_id` to frontend

2. **Document Analysis** (`POST /api/analyze`)
   - Frontend submits `file_id`
   - Router creates background job via `job_store.create_job()`
   - Service: `document_parser.py` → retrieves cached text
   - Service: `ai_service.py` or `local_llm.py` → extracts structured requirements (JSON)
   - Service: `document_scanner.py` → enriches requirements with AI cross-checking
   - Results cached in `project_cache`
   - Frontend polls `/api/analyze/status/{job_id}` or SSE streams `/api/analyze/stream/{job_id}`
   - Returns `project_id`, structured requirements, file classification

3. **Product Matching** (within analysis or via `POST /api/feedback`)
   - Service: `product_matcher.py` → two-stage matching:
     - Stage 1: Keyword pre-filter narrows 884 FTAG products → ~25 candidates
     - Stage 2: `ai_service.py` (Claude) → semantic matching with feedback few-shot examples
   - Fallback: Legacy keyword-based matching if AI unavailable
   - Corrections stored in `feedback_store.py` (JSON) → injected as examples in next match
   - Returns matches grouped by status: `matched`, `partial`, `unmatched`

4. **Offer Generation** (`POST /api/offer/generate`)
   - Frontend submits requirements + matching results
   - Router creates background job
   - Service: `result_generator.py` → generates Excel with:
     - Sheet 1: "Tuermatrix-FTAG" (matched products + selections)
     - Sheet 2: "GAP-Report" (unmatched items with gaps)
   - Optional: `erp_connector.py` → fetches live pricing from ERP (Bohr system)
   - Excel bytes stored in `offer_cache` (TTL: 30 minutes)
   - Returns `offer_id` and download URL

5. **Download** (`GET /api/offer/{id}/download`)
   - Retrieves Excel bytes from cache
   - Returns as binary response with `Content-Disposition: attachment`
   - Cache cleanup: Files expire after TTL or manual deletion

**State Management:**

- **Frontend State:** React Context (AuthContext for user, AppContext for app-wide state)
- **Backend State:**
  - Memory caches: in-process dict with TTL (fast, volatile)
  - Optional Redis: for distributed caching if `REDIS_URL` set
  - Database: persistent user/project/feedback data (optional, SQLite or PostgreSQL)
  - Job store: in-process queue + event subscriptions for real-time updates
  - File system: Uploaded files in `uploads/`, generated Excel in memory

## Key Abstractions

**AIService (Abstraction over LLM engines):**
- Purpose: Unified interface to multiple AI backends
- Examples: `services/ai_service.py`
- Pattern: Singleton with automatic failover
  - Tries Claude API first (if API key set)
  - Falls back to Ollama (local model)
  - Final fallback: returns None (caller uses regex)
- Methods: `call(prompt, system="")`, `get_status()`, `get_context_usage()`

**JobStore (Abstraction over background task tracking):**
- Purpose: Track async job progress and enable real-time streaming
- Examples: `services/job_store.py`
- Pattern: In-process task queue with asyncio event channels
- Methods: `create_job()`, `get_job(id)`, `update_job(id, status, result)`, `subscribe_job(id)` (returns asyncio.Queue)

**CatalogIndex (Product catalog preprocessing):**
- Purpose: Efficient product lookup and compact text summaries for Claude
- Examples: `services/catalog_index.py`
- Pattern: Singleton, loaded on startup, cached in memory
- Partitions 884 FTAG products into main products vs. accessories (ZZ)
- Provides compact "profiles" (~25-30 tokens each) for efficient API calls

**DocumentParser (Polymorphic file format handling):**
- Purpose: Unified parsing interface for PDF, Word, Excel, Text, GAEB, IFC
- Examples: `services/document_parser.py`
- Pattern: Format detection + format-specific parsing logic
- Methods: `parse_document_bytes(content, ext)`, `get_format(filename)`, `is_supported(filename)`

**AuthService (User/token management):**
- Purpose: JWT token generation, verification, role-based access control
- Examples: `services/auth_service.py`
- Pattern: Synchronous service with database dependency
- Creates admin user on startup if not exists
- Validates Bearer tokens in middleware before routing

## Entry Points

**Backend Entry Point:**
- Location: `backend/main.py`
- Triggers: `uvicorn main:app` command
- Responsibilities:
  - FastAPI app initialization
  - Middleware registration (CORS, auth, compression, error handling)
  - Lifespan management (startup/shutdown hooks)
  - Router registration
  - Static file serving (React SPA or vanilla frontend)
  - Health/info endpoints

**Frontend Entry Point:**
- Location: `frontend-react/src/main.jsx`
- Triggers: Browser navigation to `/`
- Responsibilities:
  - React DOM rendering
  - AuthProvider wrapper (session restoration from localStorage)
  - App component initialization
  - Client-side routing via React Router

**Startup Sequence (main.py lifespan):**
1. Initialize database (create tables)
2. Initialize auth (create admin user if needed)
3. Start Ollama watchdog (24/7 auto-restart monitoring)
4. Start availability manager (background health monitoring)
5. Pre-load catalog index
6. Build semantic search index
7. Initialize AI service (probe Claude + Ollama)
8. Start Telegram bot (if enabled)
9. Start periodic file cleanup (every 6 hours)

## Error Handling

**Strategy:** Layered exception handling with structured error responses

**Patterns:**

1. **Custom Exception Hierarchy** (`services/exceptions.py`):
   - `FrankTuerenError` (base class)
   - `FileUploadError`, `FileParsingError`, `AnalysisError`, `MatchingError`, `OfferGenerationError`, `LLMError`, `ValidationError`
   - Each includes `error_code`, `status_code`, `details`

2. **Error Handler Middleware** (`main.py`):
   - `@app.exception_handler(FrankTuerenError)` → structured JSON response
   - `@app.exception_handler(RequestValidationError)` → Pydantic validation errors
   - `@app.exception_handler(Exception)` → catchall with debug-aware messages

3. **Service-Level Error Handling** (`services/error_handler.py`):
   - `handle_exceptions()` decorator for automatic logging and error conversion
   - Preserves stack traces in debug mode only
   - Custom error codes for different failure domains

4. **AI Engine Failover** (`services/ai_service.py`):
   - Claude call fails → automatically tries Ollama
   - Ollama fails → returns None (caller implements regex fallback)
   - Logged but not fatal

5. **Validation** (`backend/validators.py`):
   - Input validation at router layer (Pydantic models)
   - Business logic validation in services
   - Min/max thresholds checked before processing

## Cross-Cutting Concerns

**Logging:**
- Centralized setup via `services/logger_setup.py`
- Structured logging with context (request IDs, job IDs)
- Different log levels by environment (DEBUG in dev, INFO in prod)
- Log files in `logs/` directory

**Validation:**
- Pydantic models at API boundary (routers)
- Custom validators in `backend/validators.py`
- File type/size validation before processing
- Settings validation on app startup

**Authentication:**
- JWT tokens stored in localStorage (frontend)
- Bearer token validation in auth middleware (backend)
- Role-based access control (user vs. admin)
- Token expires after set TTL, forces re-login
- Optional: token refresh endpoint

**Caching:**
- In-process LRU cache with TTL (Memory backends: `text_cache`, `project_cache`, `offer_cache`)
- Optional Redis backend if `REDIS_URL` environment variable set
- Cache invalidation: TTL expiration or manual deletion
- No cache for auth/sensitive endpoints

**Monitoring & Observability:**
- Health check endpoints: `/health`, `/api/health`, `/api/availability/status`, `/api/ollama/status`
- Uptime statistics per service
- Ollama watchdog auto-restart tracking
- Error tracking and logging to files

---

*Architecture analysis: 2026-03-10*
