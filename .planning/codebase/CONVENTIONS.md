# Coding Conventions

**Analysis Date:** 2026-03-10

## Naming Patterns

### Files

**Python backend:**
- Modules: `snake_case.py` (e.g., `document_parser.py`, `ai_service.py`)
- Test files: `test_*.py` (e.g., `test_document_parser.py`)
- Class files match purpose (e.g., `ProductMatcher` in `product_matcher.py`)

**JavaScript frontend (React):**
- Components: `PascalCase.jsx` (e.g., `FileUpload.jsx`, `AuthContext.jsx`)
- Hooks: `use*.js` (e.g., `useSSE.js`)
- Utilities/services: `camelCase.js` (e.g., `api.js`)
- CSS modules: `*.module.css` (e.g., `FileUpload.module.css`)

### Functions and Variables

**Python:**
- Functions: `snake_case` (e.g., `parse_document_bytes`, `get_ai_service`)
- Private functions: prefix with `_` (e.g., `_get_claude_client`, `_build_requirement_text`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `MAX_TEXT_LENGTH`, `SUPPORTED_FORMATS`)
- Local/internal constants: `UPPER_CASE` with `_` prefix for private (e.g., `_PROBE_TTL`)

**JavaScript:**
- Functions: `camelCase` (e.g., `getToken`, `handleDrop`, `processFiles`)
- Private helpers: prefix with `_` (e.g., `_getExt`, `_getIcon`)
- Constants: `UPPER_SNAKE_CASE` (e.g., `ALLOWED_EXTS`, `API_BASE`, `FILE_ICONS`)

### Types

**Python:**
- Classes: `PascalCase` (e.g., `DocumentParser`, `ErrorCode`, `AIService`)
- Enums: `PascalCase` (e.g., `Environment`, `ErrorCode`)
- Exception classes: `PascalCase` ending with `Error` (e.g., `FileError`, `ProcessingError`, `ValidationError`)

**JavaScript/React:**
- Components: `PascalCase` (e.g., `FileUpload`, `StatusBadge`, `Toast`)
- Context: `*Context.jsx` (e.g., `AuthContext.jsx`, `AppContext.jsx`)

## Code Style

### Formatting

**Python:**
- Line length: 120 characters (observed in codebase)
- Indentation: 4 spaces
- Import ordering: standard library → third-party → local imports
- No automatic formatter detected (no black/autopep8 config)

**JavaScript:**
- Line length: no strict limit observed
- Indentation: 2 spaces
- Semicolons: optional (used inconsistently)
- Template literals preferred for multi-line strings

### Linting

**Python:**
- No `.flake8`, `.pylintrc`, or similar detected
- Follows PEP 8 conventions generally
- Type hints used in function signatures (e.g., `def func(x: str) -> int:`)

**JavaScript:**
- ESLint config: `frontend-react/eslint.config.js`
- Rules enforced:
  - `no-unused-vars`: error (with pattern `^[A-Z_]` for unused uppercase/underscore)
  - `react-hooks` recommendations enabled
  - `react-refresh` plugin enabled
  - ES2020 support, JSX enabled

## Import Organization

### Python

**Order observed:**
1. Standard library (`os`, `sys`, `logging`, `asyncio`)
2. Third-party (`fastapi`, `pydantic`, `pandas`, `openpyxl`)
3. Local services (`from config import settings`, `from services.xxx import yyy`)
4. Relative imports avoided in favor of absolute

**Examples:**
```python
# services/document_parser.py
import hashlib
import io
import logging
from pathlib import Path
from typing import Optional, Tuple

from services.error_handler import FileError, ProcessingError, ErrorCode

logger = logging.getLogger(__name__)
```

### JavaScript

**Order observed:**
1. React imports
2. Context/providers
3. Component imports
4. Style imports
5. Service imports (api.js)

**Examples:**
```javascript
// FileUpload.jsx
import { useState, useRef, useCallback } from 'react'
import styles from '../styles/FileUpload.module.css'

const ALLOWED_EXTS = ['xlsx', 'pdf', ...]
```

### Path Aliases

**Python:**
- Absolute imports from project root: `from services.xxx import yyy`
- Config imports: `from config import settings`

**JavaScript:**
- Relative paths used: `'../services/api'`, `'../styles/FileUpload.module.css'`
- No path aliases configured (no jsconfig.json/tsconfig.json)

## Error Handling

### Python Patterns

**Custom exception hierarchy:**
```python
# Base exception in services/exceptions.py
class FrankTuerenError(Exception):
    def __init__(self, message: str, error_code: str, status_code: int, details: dict = None):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}

# Specialized exceptions
class FileError(FrankTuerenError)
class ProcessingError(FrankTuerenError)
class ValidationError(FrankTuerenError)
class AnalysisError(FrankTuerenError)
```

**Error handling decorator:**
```python
# services/error_handler.py
@handle_exceptions(error_code=ErrorCode.INTERNAL_ERROR, log_traceback=True)
async def async_function():
    try:
        return await func(*args, **kwargs)
    except FrankTuerenError:
        raise  # Re-raise custom errors
    except Exception as e:
        # Wrap in ProcessingError
        raise ProcessingError(message=str(e), operation=func.__name__, original_error=e)
```

**Validation pattern:**
```python
# services/error_handler.py
def validate_file_extension(filename: str, allowed_extensions: list[str]) -> bool:
    if not filename:
        raise ValidationError("Dateiname ist erforderlich", field="filename")
    ext = filename.split('.')[-1].lower()
    if ext not in allowed_extensions:
        raise ValidationError(f"Dateiendung nicht erlaubt", field="filename")
    return True
```

**Global exception handlers:**
```python
# main.py
@app.exception_handler(FrankTuerenError)
async def frank_tueren_error_handler(request: Request, exc: FrankTuerenError):
    logger.warning(f"{exc.error_code}: {exc.message}")
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(status_code=422, content={"error": "VALIDATION_ERROR", ...})

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(status_code=500, content={"error": "INTERNAL_SERVER_ERROR"})
```

### JavaScript Patterns

**Custom ApiError class:**
```javascript
// services/api.js
class ApiError extends Error {
  constructor(message, status) {
    super(message)
    this.status = status
  }
}
```

**Error handling in API calls:**
```javascript
async function request(path, opts = {}) {
  let res
  try {
    res = await fetch(url, opts)
  } catch {
    throw new ApiError('Server nicht erreichbar', 0)
  }

  if (res.status === 401) {
    localStorage.removeItem('auth_token')
    window.dispatchEvent(new Event('auth:logout'))
    throw new ApiError('Sitzung abgelaufen', 401)
  }

  if (!res.ok) {
    let msg = `HTTP ${res.status}`
    try {
      const body = await res.json()
      msg = body.detail || body.message || msg
    } catch {}
    throw new ApiError(msg, res.status)
  }

  try {
    return await res.json()
  } catch {
    throw new ApiError('Ungueltige Server-Antwort', 0)
  }
}
```

## Logging

### Framework

**Python:**
- Uses standard `logging` module
- Logger instantiation: `logger = logging.getLogger(__name__)`
- Setup: `services/logger_setup.py` configures structured JSON logging via `python-json-logger`

**JavaScript:**
- Browser `console` (no logging library observed)
- Structured logs would go via API calls for server-side tracking

### Patterns

**Python (in main.py and services):**
```python
logger.info("[OK] Database initialized")
logger.error(f"[ERROR] Database initialization failed: {e}")
logger.warning(f"[WARN] Catalog pre-load failed: {e}")
logger.exception(f"Unhandled exception: {exc}")

# Structured logging with context
logger.info(
    "AI Service init",
    extra={"engine": engine, "model": model, "available": True}
)

# Error logging with details
logger.error(f"{exc.error_code}: {exc.message}", extra={"details": exc.details})
```

**When to log:**
- Service startup/shutdown events
- Critical failures (with level ERROR)
- Warnings for degraded but operational states (level WARNING)
- Info for normal operational milestones (level INFO)
- Debug only in development (config-controlled)

## Comments

### When to Comment

**Document complex algorithms:**
```python
# Two-stage matching:
# Stage 1: Keyword scoring narrows products
# Stage 2: Claude AI sends candidates to verify

def match_products(requirement: str):
    # Pre-filter via keyword scoring
    candidates = keyword_score(requirement)
    # AI verification with feedback loop
    return ai_match(requirement, candidates)
```

**Explain why, not what:**
```python
# GOOD: Explains business logic
# EI30 and T30 are equivalent in Swiss fire protection standards
if fire_rating in ["EI30", "T30"]:
    ...

# BAD: Restates the code
# Check if fire_rating is EI30 or T30
if fire_rating in ["EI30", "T30"]:
    ...
```

**Mark temporary/experimental code:**
```python
# TODO: Migrate to sentence-transformers for multilingual embeddings
# FIXME: This regex is brittle, needs proper parser
# XXX: Performance bottleneck here (N^2 algorithm)
```

### JSDoc/DocString

**Python docstrings (observed style):**
```python
def parse_document_bytes(content: bytes, ext: str) -> str:
    """
    Parst Dokument aus Bytes und gibt Text zurück.

    Args:
        content: Datei-Bytes
        ext: Dateiendung (z.B. ".pdf")

    Returns:
        Extrahierter Text

    Raises:
        FileError: Wenn Format nicht unterstützt oder Parsing fehlschlägt
    """
```

**Python class docstrings:**
```python
class DocumentParser:
    """Hauptklasse für Dokumentenanalyse"""

    SUPPORTED_FORMATS = { ... }
    MAX_TEXT_LENGTH = 100000
```

**No JSDoc observed in frontend** - Comments used minimally, code is self-documenting

## Function Design

### Size

**Python:**
- Small service functions: 10-20 lines
- Complex functions: documented with multi-line docstrings
- Long functions (100+ lines) are rare and occur in `main.py` startup (intentional complexity)

**JavaScript:**
- Arrow functions for inline callbacks (1-5 lines)
- Named functions for logic (10-20 lines)
- Async functions split to avoid callback nesting

### Parameters

**Python:**
- Prefer explicit parameters over *args/**kwargs
- Use type hints: `def func(x: str, y: int = 5) -> bool:`
- Dataclass/Pydantic models for complex inputs: `class AnalyzeRequest(BaseModel):`

**JavaScript:**
- Objects for multiple parameters (destructuring):
  ```javascript
  const processFiles = useCallback(({ files, onReady }) => {
    // implementation
  }, [onReady])
  ```
- Avoid positional parameters beyond 2-3

### Return Values

**Python:**
- Explicit return types in annotations
- Return structured data (dicts, dataclasses) not tuples
- Return `None` for side-effect functions, declare as `-> None`

**JavaScript:**
- Promises for async: `async function() -> Promise<T>`
- `null` for missing values (not `undefined`)
- Objects for multiple returns:
  ```javascript
  return { type: 'single', file: valid[0] }
  ```

## Module Design

### Exports

**Python:**
- No `__all__` observed
- Functions imported directly: `from services.xxx import function_name`
- Classes imported directly: `from services.xxx import ClassName`

**JavaScript:**
- Named exports: `export const getToken = () => { ... }`
- Default exports for components: `export default function FileUpload() { ... }`

### Barrel Files

**Not used** - No `index.js` re-export pattern observed in frontend

**Python structure:**
- `services/xxx.py` contains single service class or related functions
- `routers/xxx.py` contains router registration
- Import by full path, not via barrel files

## Code Organization Patterns

### Service Architecture (Python)

**Pattern: Singleton service classes with lazy initialization**
```python
# services/ai_service.py
class AIService:
    _instance = None

    def __init__(self):
        # Initialize with config
        self._claude_client = None  # Lazy init
        self._ollama_available = None  # Cached probe results

# Global accessor
def get_ai_service():
    global _ai_service_instance
    if not _ai_service_instance:
        _ai_service_instance = AIService()
    return _ai_service_instance
```

**Pattern: Failover chains**
```python
# Try Claude first, fallback to Ollama, then None
def call(self, prompt, system=""):
    if self._preferred_engine == ENGINE_CLAUDE:
        result = self._call_claude(prompt, system)
        if result:
            return result

    # Fallback to Ollama
    result = self._call_ollama(prompt, system)
    if result:
        return result

    # No AI engine available
    return None
```

### Router Pattern (Python/FastAPI)

**Pattern: Router registration with tags**
```python
# routers/analyze.py
router = APIRouter()

@router.post("/analyze")
async def analyze_document(request: AnalyzeRequest):
    """Start single-file analysis as background job."""
    job = create_job()
    run_in_background(job_id, _analyze_task)
    return job.to_dict()

# main.py
app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
```

### Component Pattern (React)

**Pattern: Hooks + Context for state**
```javascript
// contexts/AuthContext.jsx
export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(true)

  const login = useCallback(async (email, password) => { ... }, [])

  return <AuthContext.Provider value={{ user, loading, login, logout }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
```

**Pattern: Component composition**
```javascript
// pages/AnalysePage.jsx
export default function AnalysePage() {
  const { file, status } = useContext(AppContext)

  return (
    <>
      <FileUpload onFilesReady={handleFiles} />
      <StatusBadge status={status} />
      <Toast message={message} />
    </>
  )
}
```

## Language-Specific Notes

### Python

**Async/await usage:**
- FastAPI routes use `async def`
- Services use `async def` for I/O-bound operations
- Event loop management in `main.py` lifespan context manager

**Type hints:**
- Used throughout for function signatures
- Pydantic models for request/response validation
- Optional types for nullable values: `Optional[str]`

### JavaScript

**React 19 features:**
- Hooks: `useState`, `useContext`, `useCallback`, `useRef`, `useEffect`
- Context API for global state (AuthContext, AppContext)
- No Redux/state management library
- CSS modules for scoped styling

**Modern JS:**
- Arrow functions: `() => {}`
- Template literals: `` `text ${var}` ``
- Destructuring: `const { x, y } = obj`
- Async/await: `await fetch()`, `async function`
- Error boundary via try/catch in handlers

---

*Convention analysis: 2026-03-10*
