# Codebase Structure

**Analysis Date:** 2026-03-10

## Directory Layout

```
ClaudeCodeTest/
├── backend/                          # FastAPI Python backend
│   ├── main.py                       # FastAPI app entry point, lifespan, middleware, routers
│   ├── config.py                     # Centralized settings (env vars, defaults, validation)
│   ├── requirements.txt              # Python dependencies
│   ├── routers/                      # FastAPI endpoint handlers
│   │   ├── auth.py                   # POST /api/auth/login, GET /api/auth/me, user management
│   │   ├── upload.py                 # POST /api/upload, folder upload
│   │   ├── analyze.py                # POST /api/analyze, /api/analyze/project, streaming
│   │   ├── offer.py                  # POST /api/result/generate, file downloads
│   │   ├── feedback.py               # POST /api/feedback, correction storage, search
│   │   ├── history.py                # GET /api/history, project listing
│   │   ├── catalog.py                # GET /api/products, browsing
│   │   └── erp.py                    # ERP integration endpoints (if enabled)
│   ├── services/                     # Business logic layer
│   │   ├── ai_service.py             # Claude/Ollama abstraction with failover
│   │   ├── product_matcher.py        # Two-stage AI+keyword product matching
│   │   ├── catalog_index.py          # Preprocessed product catalog (singleton)
│   │   ├── document_parser.py        # PDF/Word/Excel/Text/GAEB/IFC parsing
│   │   ├── document_scanner.py       # Document enrichment and analysis
│   │   ├── excel_parser.py           # Excel-specific parsing (tuerlisten)
│   │   ├── result_generator.py       # Excel offer + gap report generation
│   │   ├── semantic_search.py        # Vector-based product search (embeddings)
│   │   ├── memory_cache.py           # In-process LRU cache with TTL
│   │   ├── auth_service.py           # JWT token generation/verification, user CRUD
│   │   ├── feedback_store.py         # JSON-based correction storage
│   │   ├── history_store.py          # Project/analysis history
│   │   ├── project_store.py          # Project state management
│   │   ├── job_store.py              # Background job tracking + SSE streaming
│   │   ├── file_cleanup.py           # Periodic cleanup of old uploads
│   │   ├── error_handler.py          # Error utilities and decorators
│   │   ├── exceptions.py             # Custom exception classes
│   │   ├── validators.py             # Input validation utilities
│   │   ├── logger_setup.py           # Structured logging configuration
│   │   ├── availability_manager.py   # 24/7 service health monitoring
│   │   ├── ollama_watchdog.py        # Ollama auto-restart monitoring
│   │   ├── local_llm.py              # Ollama API client (extraction, matching)
│   │   ├── claude_client.py          # Claude API helpers (legacy)
│   │   ├── ollama_client.py          # Ollama API client (legacy)
│   │   ├── erp_connector.py          # ERP (Bohr) system integration
│   │   ├── telegram_bot.py           # Telegram notifications (optional)
│   │   ├── full_agent.py             # Agentic AI loop (experimental)
│   │   ├── code_agent.py             # Code generation agent (experimental)
│   │   ├── agent_brain.py            # Agent reasoning engine (experimental)
│   │   ├── vision_parser.py          # Vision-based document parsing (experimental)
│   │   ├── embedding_index.py        # Vector embeddings for semantic search
│   │   ├── ifc_parser.py             # IFC/BIM format parsing
│   │   ├── gaeb_parser.py            # GAEB construction tender parsing
│   │   ├── unstructured_parser.py    # Unstructured document parsing
│   │   ├── file_classifier.py        # Document type classification
│   │   ├── fast_matcher.py           # High-performance keyword matching
│   │   └── __init__.py               # Service exports
│   ├── db/                           # Database layer
│   │   ├── engine.py                 # SQLAlchemy engine, session factory, init/close
│   │   ├── models.py                 # ORM models (User, Project, ProjectFile, Analysis, Requirement, Feedback)
│   │   ├── migrate_json.py           # Migration utilities (JSON → DB)
│   │   └── __init__.py
│   ├── models/                       # Pydantic/data models
│   │   ├── erp_models.py             # ERP-specific data structures
│   │   └── __init__.py
│   ├── alembic/                      # Database migrations (Alembic)
│   │   ├── env.py                    # Migration environment
│   │   ├── script.py.mako            # Migration template
│   │   ├── versions/                 # Migration scripts
│   │   └── alembic.ini               # Alembic configuration
│   ├── uploads/                      # Uploaded file storage (runtime)
│   ├── outputs/                      # Generated Excel files (runtime, in-memory preference)
│   ├── logs/                         # Application logs (app.log, structured.log)
│   ├── data/                         # Data directory
│   │   ├── produktuebersicht.xlsx    # FTAG product catalog (884 products, 318 columns)
│   │   ├── matching_feedback.json    # Stored product matching corrections
│   │   └── frank_tueren.db           # SQLite database (if using SQLite)
│   ├── tests/                        # Unit and integration tests
│   │   ├── conftest.py               # Pytest configuration
│   │   ├── test_upload.py
│   │   ├── test_analyze.py
│   │   ├── test_product_matcher.py
│   │   ├── test_document_parser.py
│   │   ├── test_excel_parser.py
│   │   ├── test_offer.py
│   │   ├── test_validators.py
│   │   ├── test_vision_parser.py
│   │   ├── test_ko_integration.py    # Kostenkontrolle integration tests
│   │   └── data/                     # Test fixtures and sample files
│   ├── erp_config_example.py         # ERP configuration template
│   ├── test_ollama.py                # Ollama connectivity test
│   ├── .venv/ or venv/               # Python virtual environment
│   └── __init__.py
│
├── frontend/                         # Legacy vanilla JavaScript frontend (fallback)
│   ├── index.html                    # Main HTML
│   ├── app.js                        # Vanilla JS application logic
│   ├── style.css                     # Styling
│   └── lib/                          # Helper libraries
│
├── frontend-react/                   # React SPA (production)
│   ├── src/
│   │   ├── main.jsx                  # React app entry point
│   │   ├── App.jsx                   # Root component with routing
│   │   ├── pages/
│   │   │   ├── AnalysePage.jsx       # Main analysis interface
│   │   │   ├── KatalogPage.jsx       # Product catalog browser
│   │   │   ├── HistoriePage.jsx      # Project history and results
│   │   │   ├── BenutzerPage.jsx      # User management (admin only)
│   │   │   └── LoginForm.jsx         # Login page (in components/)
│   │   ├── components/
│   │   │   ├── Header.jsx            # Navigation bar
│   │   │   ├── FileUpload.jsx        # File upload interface
│   │   │   ├── CorrectionModal.jsx   # Product match correction dialog
│   │   │   ├── StatusBadge.jsx       # Status display component
│   │   │   ├── Toast.jsx             # Toast notifications
│   │   │   └── LoginForm.jsx         # Login form
│   │   ├── context/
│   │   │   ├── AuthContext.jsx       # User authentication state
│   │   │   └── AppContext.jsx        # Global app state (projects, results)
│   │   ├── hooks/
│   │   │   └── useSSE.js             # Server-Sent Events (streaming) hook
│   │   ├── services/
│   │   │   └── api.js                # API client (all endpoints)
│   │   └── styles/
│   │       └── global.css            # Global React styling
│   ├── public/                       # Static assets
│   ├── dist/                         # Built output (generated)
│   ├── node_modules/                 # Dependencies
│   ├── package.json                  # npm dependencies and scripts
│   ├── package-lock.json
│   ├── vite.config.js                # Vite build configuration
│   ├── eslint.config.js              # ESLint configuration
│   └── README.md
│
├── frontend-react-dist/              # Built React SPA (served by FastAPI)
│   ├── index.html
│   └── assets/                       # JS/CSS bundles (from Vite build)
│
├── data/                             # Shared data directory (root level)
│   ├── produktuebersicht.xlsx        # Master product catalog
│   ├── matching_feedback.json        # Shared feedback storage
│   ├── frank_tueren.db               # Shared SQLite database
│   └── tessdata/                     # OCR language data (Tesseract)
│
├── logs/                             # Application logs (root level)
│   ├── app.log                       # Main application log
│   └── structured.log                # Structured JSON logs
│
├── .planning/                        # GSD planning documents
│   └── codebase/
│       ├── ARCHITECTURE.md           # This project's architectural layers
│       ├── STRUCTURE.md              # This file
│       ├── STACK.md                  # Technology stack
│       ├── INTEGRATIONS.md           # External service integrations
│       ├── CONVENTIONS.md            # Coding conventions
│       ├── TESTING.md                # Testing patterns
│       └── CONCERNS.md               # Technical debt and issues
│
├── .github/                          # GitHub Actions workflows
│   └── workflows/                    # CI/CD pipelines
│
├── docs/                             # Documentation
│   └── plans/                        # Design documents (markdown)
│
├── .env.example                      # Environment variable template
├── .gitignore                        # Git ignore rules
├── DEPLOYMENT_GUIDE.md               # Production deployment steps
├── setup.bat                         # Windows setup script (creates venv, installs deps)
├── start.bat                         # Windows startup script (runs uvicorn)
├── CHECK_OLLAMA_STATUS.ps1           # Windows PowerShell script to check Ollama
│
└── Various analysis scripts (root):  # Development/debugging scripts
    ├── analyze_fertige_all.py
    ├── analyze_ko4.py
    ├── compare_ko_detailed.py
    ├── debug_parser.py
    └── [etc...]
```

## Directory Purposes

**backend/**
- Purpose: FastAPI Python backend (REST API, business logic)
- Contains: Routers (endpoints), services (logic), database models, configuration
- Key dependency: `requirements.txt` lists Python packages
- Runtime directories: `uploads/`, `outputs/`, `logs/`, `data/`

**frontend-react/**
- Purpose: Modern React SPA (production frontend)
- Contains: React components, hooks, context, services, styling
- Build output: `dist/` (created by `npm run build`)
- Key files: `package.json` (dependencies), `vite.config.js` (build config)

**frontend-react-dist/**
- Purpose: Built React SPA served by FastAPI at `/`
- Contains: `index.html`, `assets/` (bundled JS/CSS)
- Generated by: `cd frontend-react && npm run build`
- Served by: `main.py` via `StaticFiles` mounting and React SPA fallback routing

**frontend/**
- Purpose: Legacy vanilla JavaScript frontend (fallback if React dist not found)
- Contains: Plain HTML, CSS, JavaScript (no build step)
- Served by: `main.py` if `frontend-react-dist/` not found

**backend/routers/**
- Purpose: FastAPI endpoint definitions
- Naming: One router file per major feature (auth, upload, analyze, offer, feedback, history, catalog, erp)
- Pattern: Router imported in `main.py` with `app.include_router(router, prefix="/api")`

**backend/services/**
- Purpose: Business logic, independent of HTTP layer
- Naming: Service files named by responsibility (ai_service, product_matcher, document_parser, etc.)
- Pattern: Most services are singletons (lazy-initialized, cached in module-level variable)
- No HTTP dependencies (services take plain dicts/bytes, return results)

**backend/db/**
- Purpose: Database abstraction layer
- Contains: SQLAlchemy engine, async session factory, ORM models
- Supports: PostgreSQL (production) or SQLite (development)
- Alembic: Migrations in `alembic/versions/` (run via `alembic upgrade head`)

**data/**
- Purpose: Data and configuration files
- `produktuebersicht.xlsx`: Master product catalog (read-only, 884 products)
- `matching_feedback.json`: User corrections to product matches (read-write)
- `frank_tueren.db`: SQLite database (if not using PostgreSQL)

**logs/**
- Purpose: Application logs
- `app.log`: Rotating main log file
- `structured.log`: JSON-formatted structured logs
- Cleaned up periodically by `file_cleanup.py`

## Key File Locations

**Entry Points:**
- `backend/main.py`: FastAPI application initialization and routing
- `frontend-react/src/main.jsx`: React DOM rendering
- `frontend-react/index.html`: HTML template
- `setup.bat`, `start.bat`: Windows setup and startup scripts

**Configuration:**
- `backend/config.py`: All settings (environment vars, defaults, validation)
- `.env.example`: Template for environment variables
- `backend/alembic/alembic.ini`: Database migration configuration
- `frontend-react/vite.config.js`: Frontend build configuration

**Core Logic:**
- `backend/services/ai_service.py`: Claude/Ollama abstraction
- `backend/services/product_matcher.py`: Product matching logic
- `backend/services/catalog_index.py`: Product catalog preprocessing
- `backend/services/document_parser.py`: Document parsing (PDF, Word, Excel, etc.)
- `backend/services/result_generator.py`: Excel offer generation

**Testing:**
- `backend/tests/conftest.py`: Pytest fixtures and configuration
- `backend/tests/test_*.py`: Unit and integration tests
- `backend/tests/data/`: Sample test files

**Database:**
- `backend/db/models.py`: SQLAlchemy ORM models
- `backend/db/engine.py`: Database engine and session management
- `backend/alembic/versions/`: Migration scripts

## Naming Conventions

**Files:**

- Python backend files: `snake_case.py`
  - Example: `ai_service.py`, `product_matcher.py`, `document_parser.py`
- React components: `PascalCase.jsx`
  - Example: `FileUpload.jsx`, `CorrectionModal.jsx`, `AnalysePage.jsx`
- React hooks: `useHookName.js`
  - Example: `useSSE.js`
- React context: `NameContext.jsx`
  - Example: `AuthContext.jsx`, `AppContext.jsx`
- API routes: kebab-case endpoints
  - Example: `/api/analyze`, `/api/upload/folder`, `/api/offer/generate`

**Directories:**

- Python packages (backend): `snake_case/` (routers, services, db, models, tests)
  - Example: `backend/routers/`, `backend/services/`
- React pages: `PascalCase/` or files in `pages/`
  - Example: `frontend-react/src/pages/AnalysePage.jsx`
- React components: `PascalCase/` or files in `components/`
  - Example: `frontend-react/src/components/FileUpload.jsx`

**Environment Variables:**

- Uppercase with underscores
  - Example: `ANTHROPIC_API_KEY`, `OLLAMA_URL`, `ENVIRONMENT`, `DATABASE_URL`
- Feature flags: `FEATURE_NAME_ENABLED`
  - Example: `OLLAMA_FALLBACK_ENABLED`, `TELEGRAM_ENABLED`, `ERP_ENABLED`

## Where to Add New Code

**New Feature (e.g., new analysis type):**
- Primary code: `backend/services/new_feature_service.py`
- Router endpoint: `backend/routers/analyze.py` (or new router file)
- Frontend page: `frontend-react/src/pages/NewFeaturePage.jsx`
- Tests: `backend/tests/test_new_feature_service.py`
- Database model (if needed): `backend/db/models.py`

**New Component/Module:**
- Implementation: `backend/services/component_name.py`
- Import in: `backend/routers/` (for router endpoints) or other services (for service composition)
- Tests: `backend/tests/test_component_name.py`
- Configuration: Add to `backend/config.py` if new env vars needed

**Utilities:**
- Shared helpers: `backend/services/` (specific service file or new utility module)
- Validators: `backend/validators.py`
- Error handling: `backend/services/error_handler.py` and `backend/services/exceptions.py`
- Logging: Imported from `services/logger_setup.py`, use `logger = logging.getLogger(__name__)`

**Frontend Pages:**
- Location: `frontend-react/src/pages/PageName.jsx`
- Route: Add to `frontend-react/src/App.jsx` in `<Routes>`
- Context: Use `useAuth()` from AuthContext, `useApp()` from AppContext
- API calls: Import from `frontend-react/src/services/api.js`

**Database Models:**
- Location: `backend/db/models.py`
- Pattern: Inherit from `Base`, use SQLAlchemy mapped columns
- Migration: Run `alembic revision --autogenerate -m "Add new model"`, then edit and run `alembic upgrade head`

## Special Directories

**backend/uploads/**
- Purpose: Temporary storage of uploaded files during processing
- Generated: Yes (created at runtime)
- Committed: No (in `.gitignore`)
- Cleanup: `file_cleanup.py` deletes files older than `UPLOAD_CLEANUP_HOURS` (default 24h)

**backend/outputs/**
- Purpose: Generated Excel files (optional; in-memory caching preferred)
- Generated: Yes (if file system storage used)
- Committed: No (in `.gitignore`)
- Cleanup: `file_cleanup.py` cleans periodically

**backend/logs/**
- Purpose: Application log files
- Generated: Yes (created at startup)
- Committed: No (in `.gitignore`)
- Key files: `app.log` (main), `structured.log` (JSON)

**frontend-react/node_modules/**
- Purpose: npm package dependencies
- Generated: Yes (created by `npm install`)
- Committed: No (in `.gitignore`)

**frontend-react/dist/ and frontend-react-dist/**
- Purpose: Built React bundles
- Generated: Yes (by `npm run build` or `vite build`)
- Committed: `frontend-react-dist/` is committed; `dist/` is not
- FastAPI serves: `frontend-react-dist/` if it exists, else fallback to `frontend/`

**backend/.venv/ or backend/venv/**
- Purpose: Python virtual environment
- Generated: Yes (by `python -m venv venv`)
- Committed: No (in `.gitignore`)
- Setup: Run `setup.bat` (Windows) or `python -m venv venv && venv\Scripts\activate`

**backend/alembic/**
- Purpose: Database migrations (Alembic)
- Migration scripts: `alembic/versions/*.py`
- Run migrations: `alembic upgrade head`
- Create new migration: `alembic revision --autogenerate -m "Description"`

**data/**
- Purpose: Persistent data files
- `produktuebersicht.xlsx`: Read-only product catalog (required)
- `matching_feedback.json`: User-provided corrections (created at runtime)
- `frank_tueren.db`: SQLite database (if using SQLite)
- `tessdata/`: OCR language data

---

*Structure analysis: 2026-03-10*
