# Codebase Concerns

**Analysis Date:** 2026-03-10

## Tech Debt

**Large monolithic service files:**
- Issue: Core services exceed 1000 lines (claude_client.py: 1153, excel_parser.py: 1097, local_llm.py: 954, result_generator.py: 933)
- Files: `backend/services/claude_client.py`, `backend/services/excel_parser.py`, `backend/services/local_llm.py`, `backend/services/result_generator.py`
- Impact: Difficult to test individual functions, high coupling, increased maintenance burden
- Fix approach: Extract helper functions into separate modules, split by domain (e.g., excel_parser → header_detection.py, column_mapping.py, value_normalization.py)

**Duplicate JSON repair logic:**
- Issue: _repair_json() duplicated in both claude_client.py and local_llm.py with identical implementation
- Files: `backend/services/claude_client.py` (lines 42-82), `backend/services/local_llm.py` (lines 52-84)
- Impact: Maintenance burden, potential divergence if one is fixed and other is not
- Fix approach: Extract to shared utility module `backend/services/json_repair.py`

**Root directory cluttered with debug/test scripts:**
- Issue: ~30+ analysis and debug scripts in project root (analyze_*.py, debug_*.py, compare_*.py)
- Files: `/analyze_fertige_all.py`, `/debug_parser.py`, `/compare_ko2.py`, etc.
- Impact: Clutters git status, confusing for developers, not version-controlled properly
- Fix approach: Move to `tests/experimental/` or delete if no longer needed; add `.gitignore` entry

**Unused claude_client.py module:**
- Issue: 1153-line module marked as "no longer actively used" but still maintained
- Files: `backend/services/claude_client.py` (header comment lines 1-7)
- Impact: Dead code, confusion about which AI interface to use (claude_client vs ai_service)
- Fix approach: Either fully remove and migrate remaining usages to ai_service.py, or make it a proper backward-compatibility wrapper with clear deprecation notice

**Inconsistent error handling with pass statements:**
- Issue: Multiple exception handlers swallow errors silently without logging in fallback paths
- Files: `backend/services/document_parser.py` (lines 184, 244, 251), `backend/services/excel_parser.py` (line 121), `backend/services/fast_matcher.py` (line 487)
- Impact: Silent failures make debugging difficult, errors go unnoticed in production
- Fix approach: Replace all `pass` statements with at least `logger.debug()` or `logger.warning()` calls

---

## Known Bugs

**Excel parser pandas Series ambiguity:**
- Symptoms: "Truth value of a Series is ambiguous" error when Excel files have merged cells or duplicate column names
- Files: `backend/services/excel_parser.py` (lines 27-37 has _to_scalar workaround, but only used in some places)
- Trigger: Upload Excel files with merged header rows or repeated column names (common in formatted templates)
- Workaround: Current code calls `_to_scalar()` in column combining (line 67-68) but not consistently in all cell access patterns
- Fix approach: Audit all DataFrame access, ensure _to_scalar() applied universally before any conditional checks

**JSON truncation recovery in LLM responses:**
- Symptoms: If Ollama/Claude response is truncated mid-JSON, repair heuristics may create invalid structures
- Files: `backend/services/local_llm.py` (lines 68-72, closing bracket logic), `backend/services/claude_client.py` (lines 66-72)
- Trigger: Very large LLM response (rare) or timeout during generation
- Workaround: _repair_json counts brackets naively and may add wrong number of closing brackets
- Fix approach: Use proper JSON parser state machine or validate repaired JSON schema matches expected structure

**Fallback from Claude to Ollama may lose context:**
- Symptoms: Switched AI engine mid-task may result in different extraction format or quality
- Files: `backend/services/ai_service.py` (lines 144-180 calls Claude, 181-220 calls Ollama)
- Trigger: Claude API key missing/invalid while Ollama available, or vice versa
- Impact: Offer generation may have inconsistent structure depending on which AI engine was used
- Fix approach: Validate response schema regardless of engine, or wrap both engines with consistent output validation

---

## Security Considerations

**Default admin password hardcoded as environment fallback:**
- Risk: "ChangeMeOnFirstLogin!" password used if DEFAULT_ADMIN_PASSWORD env var not set
- Files: `backend/services/auth_service.py` (line 36)
- Current mitigation: Settings allow override via environment variable, admin is warned at startup to change password (implicit in default message)
- Recommendations:
  - Reject default password on first login, force immediate change before any other operations
  - Generate random temporary password instead of using hardcoded string
  - Add audit log entry when default credentials used

**JWT secret generation stored in plaintext:**
- Risk: JWT_SECRET saved to disk at `data/.jwt_secret` without encryption if not in environment
- Files: `backend/services/auth_service.py` (lines 59-64)
- Current mitigation: File stored in data/ directory (assumed restricted), can be overridden by JWT_SECRET env var
- Recommendations:
  - Always require JWT_SECRET as environment variable in production (fail startup if missing)
  - Remove on-disk generation except in development
  - Document this as required production setup step

**CORS headers allow all origins in development:**
- Risk: `CORS_ORIGINS = ["*"]` when ENVIRONMENT != production (line 253 in main.py)
- Files: `backend/main.py` (lines 252-261)
- Impact: Any website can make requests to your API in dev/staging
- Current mitigation: Explicit production CORS list exists (franktueren.ch domains)
- Recommendations:
  - In staging, use explicit list of allowed origins rather than wildcard
  - Add warning in logs when wildcard CORS detected

**Database password in connection string:**
- Risk: ERP connector stores credentials in environment variables (ERP_BOHR_PASSWORD, ERP_BOHR_API_KEY)
- Files: `backend/config.py` (lines 97-99), `backend/services/erp_connector.py` (lines 30-35)
- Current mitigation: Environment-based, not hardcoded
- Recommendations:
  - Never log or expose these credentials in error messages
  - Audit erp_connector.py for credential leakage in exception handling

**Debug mode exposes full stack traces:**
- Risk: When DEBUG=true, error responses include full exception text instead of generic message
- Files: `backend/main.py` (lines 355, 395, 525, 531, 555, 561-566)
- Impact: Stack traces reveal internal structure, file paths, installed packages to clients
- Current mitigation: Only in debug mode (development), not in production
- Recommendations:
  - Ensure DEBUG never true in production (validate at startup)
  - Consider stricter error sanitization even in debug mode for APIs

---

## Performance Bottlenecks

**No pagination on large catalog searches:**
- Problem: GET /api/products returns all 891 products at once without pagination
- Files: `backend/routers/analyze.py` (lines 616-627, get_products endpoint)
- Cause: JSON serialization of entire catalog, bandwidth/memory on client
- Improvement path: Add limit/offset or cursor-based pagination (default 50, max 200 items)

**Semantic search index rebuilt on every startup:**
- Problem: get_semantic_index() rebuilds full index from 891 products on app startup
- Files: `backend/main.py` (lines 108-110), `backend/services/semantic_search.py`
- Cause: No persistent index cache, TF-IDF vectorization runs for every restart
- Impact: 5-10 second startup delay on large catalogs
- Improvement path: Serialize sklearn vectorizer and feature matrix to disk, load on startup

**Memory cache uses in-memory storage only (no Redis by default):**
- Problem: Cache lost on restart, no sharing across workers in production
- Files: `backend/services/memory_cache.py` (lines 31-47, Redis fallback optional)
- Cause: REDIS_URL must be manually configured, defaults to in-memory
- Impact: Cache thrashing in multi-worker deployments, poor hit rates
- Improvement path: Make Redis required in production, or implement simple file-based cache as fallback

**Large PDF parsing blocks request thread:**
- Problem: parse_document_bytes() for large PDFs (>50MB) can take 30+ seconds, blocks async handler
- Files: `backend/services/document_parser.py` (lines 59-100), used in POST /api/analyze
- Cause: Synchronous extraction (pdfplumber, PyMuPDF) in event loop
- Impact: Request timeout, poor UX, no progress feedback while parsing
- Improvement path: Move parsing to thread pool or background task, stream progress to client via SSE

**Product matching loops through all 891 products:**
- Problem: fast_matcher.py score_requirement() applies regex/TF-IDF to entire catalog for each requirement
- Files: `backend/services/fast_matcher.py` (entire module, 781 lines)
- Cause: Pre-filter logic has high algorithmic complexity for large catalogs
- Impact: Slowness with 891 products, linear scalability (N*M for N requirements × M products)
- Improvement path: Implement hierarchical matching (category → subcategory filter before scoring)

---

## Fragile Areas

**Excel file format detection relies on heuristics:**
- Files: `backend/services/excel_parser.py` (header detection lines 86-143)
- Why fragile: Detects header row by scanning for non-null density, fails on unusual layouts (e.g., title rows, metadata blocks above data)
- Safe modification: Add explicit header_row parameter to upload API, allow user to specify; log actual detected header row
- Test coverage: No specific test cases for unusual Excel layouts (frozen panes, multiple header levels)

**Product matching feedback system has no versioning:**
- Files: `backend/services/feedback_store.py` (JSON-based feedback storage)
- Why fragile: Feedback correcting products stored as dict snapshots; if product catalog evolves, feedback becomes stale/invalid
- Safe modification: Store feedback by row_index and product_name combo, not by entire product dict; validate feedback references still exist
- Test coverage: No tests for handling deleted/renamed products after feedback stored

**Ollama watchdog restart logic may loop on repeated failures:**
- Files: `backend/services/ollama_watchdog.py` (auto-restart with exponential backoff)
- Why fragile: If Ollama crashes due to corrupted model file, watchdog will keep restarting indefinitely without investigating root cause
- Safe modification: Add failure reason analysis (Is port taken? Corrupt files? Memory exhausted?), escalate after N failures
- Test coverage: No tests for watchdog behavior under sustained failure conditions

**AI engine fallback chain may not preserve output format:**
- Files: `backend/services/ai_service.py` (Claude → Ollama → None), `backend/services/local_llm.py` (callers must handle None)
- Why fragile: When Claude unavailable and Ollama used, JSON response format may differ (e.g., different field order, omitted optional fields)
- Safe modification: Normalize all AI responses through Pydantic model validation before returning to callers
- Test coverage: No tests exercising Claude→Ollama switch; test suite likely runs against one engine only

**Multiprocessing in document_parser may leak resources:**
- Files: `backend/services/document_parser.py` (multiprocessing.queues used, lines 12-13, 179-200)
- Why fragile: Process pool created but cleanup unclear if exception occurs mid-extraction
- Safe modification: Use context managers or explicit pool.close()/pool.join(), test with timeout
- Test coverage: No tests for cleanup under exception/timeout scenarios

---

## Scaling Limits

**Single-file processing limited to 100k characters:**
- Current capacity: MAX_TEXT_LENGTH = 100,000 chars (config.py line 45)
- Limit: Large PDFs (500+ pages) may be truncated before analysis
- Scaling path: Implement chunking + parallel processing (100k chunks processed independently, merged results)
- Files: `backend/services/document_parser.py` (line 45)

**Background job queue is in-memory (job_store.py):**
- Current capacity: ~1000 concurrent jobs before memory stress
- Limit: No persistence to disk/DB, jobs lost on restart
- Scaling path: Migrate job_store to database (already have SQLAlchemy Job model)
- Files: `backend/services/job_store.py`

**Catalog index loaded entirely in memory:**
- Current capacity: 891 products × ~10KB per product = ~9MB in memory
- Limit: Would struggle with 100,000+ product catalogs
- Scaling path: Implement lazy loading or database-backed index, cache only top 1000 frequently matched products
- Files: `backend/services/catalog_index.py`

---

## Dependencies at Risk

**pdfplumber 0.11.4 (pinned, EOL risk):**
- Risk: Version 0.11.4 released May 2024, no recent updates; project may be stagnating
- Impact: Security vulnerabilities not patched, compatibility with future PDF standards
- Migration plan: Monitor upstream, consider PyMuPDF (already installed) as primary, pdfplumber as fallback

**unstructured[all-docs] (optional, heavy dependency):**
- Risk: Pulls 50+ transitive dependencies (detectron2, PIL, torch), takes minutes to install
- Impact: Optional feature but in requirements.txt as fallback; adds bloat even if not used
- Migration plan: Make truly optional (not in requirements.txt), require manual pip install for users who need it

**scikit-learn 1.6.0 (TF-IDF vectorizer):**
- Risk: Large library for simple TF-IDF; duplicated from sentence-transformers if embeddings enabled
- Impact: ~200MB download, memory overhead
- Migration plan: Consider lightweight alternative (gensim, spacy) or implement custom TF-IDF

**anthropic SDK version constraint:**
- Risk: anthropic>=0.49.0 (loose lower bound), SDK breaking changes common
- Impact: New installations may get SDK with incompatible API
- Migration plan: Pin to tested version (e.g., anthropic==0.50.0) in production, test before upgrade

---

## Missing Critical Features

**No rate limiting by user/IP in production:**
- Problem: Rate limiting disabled in development (config.py line 137); requires slowapi (optional dependency)
- Blocks: Can't prevent abuse/DoS on public endpoints
- Files: `backend/main.py` (lines 244-250)
- Fix: Make rate limiting mandatory in production, remove optional dependency flag

**No audit logging for data modifications:**
- Problem: CRUD operations on projects/analyses not logged for compliance
- Blocks: Cannot trace who changed what, when (regulatory requirements)
- Files: Database models exist (AuditLog table in db/models.py line 208) but never used
- Fix: Implement middleware that logs all DELETE/PUT/PATCH operations with user + timestamp

**No data retention/cleanup policy:**
- Problem: Uploaded files and projects kept indefinitely, no GDPR data deletion
- Blocks: Cannot comply with GDPR article 17 (right to be forgotten)
- Files: UPLOAD_CLEANUP_HOURS = 24 configured (config.py line 78) but cleanup task may fail silently
- Fix: Implement enforced data purge after retention period, log all deletions for audit

**No backup/restore mechanism:**
- Problem: No way to backup SQLAlchemy database state or project history
- Blocks: Data loss unrecoverable (no snapshots, no export)
- Fix: Add admin endpoints for database export (PostgreSQL dump), version control for offer files

---

## Test Coverage Gaps

**No integration tests for AI engine switching:**
- What's not tested: Fallback from Claude to Ollama, response format consistency
- Files: `backend/services/ai_service.py`, `backend/services/local_llm.py`
- Risk: Silent format divergence when switching engines undetected
- Priority: High (occurs in production when API key invalid)

**No tests for large file handling (>100MB):**
- What's not tested: PDF/Excel parsing at MAX_FILE_SIZE_MB limit, multiprocessing cleanup
- Files: `backend/services/document_parser.py`
- Risk: Memory leaks, process hangs on large files
- Priority: High (affects primary use case)

**No tests for concurrent job processing:**
- What's not tested: Race conditions in job_store.py when multiple workers process same job
- Files: `backend/services/job_store.py`
- Risk: Duplicate job runs, lost status updates
- Priority: Medium (only occurs with multiple worker processes)

**No tests for Excel parser edge cases:**
- What's not tested: Merged cells, duplicate column names, unusual header layouts, non-standard encodings
- Files: `backend/services/excel_parser.py`
- Risk: Crashes on customer documents with non-standard formatting
- Priority: High (primary input format)

**No tests for product matcher with small/empty catalogs:**
- What's not tested: Behavior when product catalog is unavailable, <10 products, or empty
- Files: `backend/services/fast_matcher.py`, `backend/services/catalog_index.py`
- Risk: Crashes or falls back to regex with poor matches
- Priority: Medium (rare but critical failure mode)

**No tests for auth service with database unavailable:**
- What's not tested: Graceful degradation when PostgreSQL down, fallback to JSON file
- Files: `backend/services/auth_service.py` (lines 83-97, DB fallback exists but untested)
- Risk: Silent auth failures, users locked out
- Priority: High (affects production availability)

---

## Deployment & Infrastructure Concerns

**Database migrations not documented:**
- Risk: No clear procedure for running alembic migrations in production
- Files: `backend/alembic/` directory exists but no README or deployment docs
- Impact: Database schema mismatches between releases
- Fix: Document migration process, test on staging before production

**No health check for database connectivity:**
- Risk: /health endpoint doesn't verify database is writable (only checks AI engines)
- Files: `backend/main.py` (lines 423-496, health_check endpoint)
- Impact: Can't detect database issues from outside
- Fix: Add database connectivity test to health endpoint

**No configuration for running with gunicorn in production:**
- Risk: Uvicorn run with single worker by default (settings.py line 57: WORKERS=1)
- Files: `backend/config.py`, `backend/main.py` (uvicorn.run lacks worker config)
- Impact: Single-threaded bottleneck, no load distribution
- Fix: Document multi-worker setup with gunicorn, load testing

**No Docker containerization:**
- Risk: Deployment varies across environments, no reproducible builds
- Impact: "Works on my machine" problems, dependency version conflicts
- Fix: Add Dockerfile with pinned Python version, tested in CI

---

*Concerns audit: 2026-03-10*
