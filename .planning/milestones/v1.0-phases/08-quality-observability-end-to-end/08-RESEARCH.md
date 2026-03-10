# Phase 8: Quality, Observability & End-to-End - Research

**Researched:** 2026-03-10
**Domain:** Pipeline orchestration, SSE streaming, plausibility validation, structured logging
**Confidence:** HIGH

## Summary

Phase 8 ties the entire v2 pipeline together into a production-grade end-to-end flow with real-time progress visibility, result plausibility validation, and robust error reporting. The codebase already has substantial infrastructure for this: the v1 `job_store.py` provides background job execution with SSE streaming, `analyze.py` has SSE endpoints (`/analyze/stream/{job_id}`, `/analyze/status/{job_id}`), and the React frontend has a `useSSE` hook with polling fallback. The v2 `analyze_v2.py` router currently runs synchronously without job/SSE support.

The core work is: (1) wrap the v2 analyze endpoint in the existing job_store background execution model with granular stage-level progress events, (2) build a plausibility checker that validates completeness and consistency of final results, (3) add structured step-level logging throughout the pipeline, and (4) ensure AI service failures produce clear user-facing error messages rather than partial/degraded results.

**Primary recommendation:** Reuse the existing `job_store.py` + SSE infrastructure for the v2 pipeline, add a `PlausibilityChecker` service for post-analysis validation, and wire granular progress callbacks through each pipeline stage.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| QUAL-01 | Plausibility check after analysis (all positions covered, no duplicates, no suspicious patterns) | New `PlausibilityChecker` service with deterministic checks on final results |
| QUAL-02 | Every analysis step logged with detail (requirement, pass, result) | Structured logging via existing `logger_setup.py` JSON formatter + per-stage log context |
| QUAL-03 | Live progress in frontend (which step, which position) | Existing SSE/job_store infrastructure + granular `update_job()` calls from pipeline stages |
| QUAL-04 | Clear error message on AI failure instead of degraded results | V2Error exception hierarchy + fail-fast strategy with explicit error propagation |
| APII-02 | POST /api/analyze with SSE streaming for real-time progress | Wrap v2 pipeline in `run_in_background()` + reuse existing `/analyze/stream/{job_id}` |
| APII-03 | GET /api/analyze/status/{job_id} with position-level progress | Extend Job.to_dict() with stage-level progress data from pipeline schema |
</phase_requirements>

## Standard Stack

### Core (Already in Project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| FastAPI | existing | SSE endpoints via StreamingResponse | Already used for `/analyze/stream/{job_id}` |
| Python logging | stdlib | Structured step logging | Already configured with JSON formatter in `logger_setup.py` |
| Pydantic v2 | existing | Pipeline stage schemas, plausibility result models | Already used throughout v2 pipeline |
| asyncio.Queue | stdlib | SSE event delivery to subscribers | Already used in `job_store.py` subscriber pattern |

### Supporting (Already in Project)
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| threading | stdlib | Background job execution | Already used in `job_store.py` `run_in_background()` |
| uuid | stdlib | Job ID generation | Already used in `job_store.py` |
| anthropic SDK | >=0.84.0 | AI calls with structured output | Already used for messages.parse() |

### No New Dependencies Required

This phase requires zero new pip packages. Everything builds on existing infrastructure.

## Architecture Patterns

### Recommended Project Structure
```
backend/v2/
├── routers/
│   └── analyze_v2.py        # Modify: wrap in job_store, add SSE streaming
├── validation/
│   ├── __init__.py           # Already exists (empty)
│   └── plausibility.py       # NEW: PlausibilityChecker service
├── schemas/
│   └── pipeline.py           # Modify: extend StageProgress with position-level detail
└── extraction/
    └── pipeline.py           # Modify: accept progress_callback parameter
```

### Pattern 1: Progress Callback Threading
**What:** Each pipeline stage accepts an optional `on_progress` callback that reports granular progress through the job_store
**When to use:** Every stage of the v2 pipeline (extraction, matching, adversarial, gaps)
**Example:**
```python
# In extraction/pipeline.py
async def run_extraction_pipeline(
    parse_results: list[ParseResult],
    tender_id: str,
    client: Optional[anthropic.Anthropic] = None,
    on_progress: Optional[Callable[[str, str, float], None]] = None,
) -> ExtractionResult:
    """
    on_progress(stage: str, detail: str, percent: float)
    """
    if on_progress:
        on_progress("extraction", f"Pass 1 auf {pr.source_file}", 10.0)
    # ... existing logic
```

### Pattern 2: Job Store Stage Tracking
**What:** Extend job progress to include structured stage data, not just a flat string
**When to use:** When the frontend needs to display which pipeline stage is running and which position is being processed
**Example:**
```python
# Extended update_job call with structured stage data
update_job(job_id, progress=json.dumps({
    "message": "Matching Position 5 von 42",
    "stage": "matching",
    "stage_status": "running",
    "current_position": "T1.05",
    "positions_done": 4,
    "positions_total": 42,
    "percent": 12.0,
}))
```

### Pattern 3: Plausibility Check as Post-Processing
**What:** After the full pipeline completes, run deterministic checks on the results before returning to the user
**When to use:** Always, as the final step before marking a job as completed
**Example:**
```python
class PlausibilityChecker:
    def check(self, positions, match_results, adversarial_results, gap_reports):
        issues = []
        # Check 1: All positions have a match result or gap report
        # Check 2: No duplicate position numbers
        # Check 3: No suspicious patterns (all 100% matches, all 0% matches)
        # Check 4: Confidence distribution sanity
        return PlausibilityResult(issues=issues, passed=len(critical) == 0)
```

### Pattern 4: Fail-Fast on AI Errors
**What:** When the Claude API fails during any pipeline stage, immediately fail the entire job with a clear German error message instead of continuing with partial results
**When to use:** Any AI call (extraction, matching, adversarial, gap analysis)
**Example:**
```python
except anthropic.APIError as e:
    raise PipelineError(
        message=f"KI-Service nicht verfuegbar: {e}. Bitte spaeter erneut versuchen.",
        details={"stage": "matching", "api_error": str(e)},
    )
```

### Anti-Patterns to Avoid
- **Silent degradation:** Do NOT silently skip pipeline stages when AI fails. QUAL-04 requires clear error messages. Current v2 code has `matching_skipped`, `adversarial_skipped` flags - these must become hard failures for the end-to-end pipeline.
- **Flat progress strings only:** Don't just send "Matching laeuft..." - include structured data (stage, position, percentage) so the frontend can render rich progress UI.
- **Logging after the fact:** Don't log only at pipeline boundaries. Log each position processed within each pass for post-hoc debugging (QUAL-02).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Background job execution | Custom thread pool | Existing `job_store.py` `run_in_background()` | Already handles timeout, concurrency limits, SSE notifications |
| SSE event streaming | Custom WebSocket/polling | Existing `/analyze/stream/{job_id}` endpoint | Already handles keepalive, subscriber cleanup, error propagation |
| Structured logging | Custom log format | Existing `logger_setup.py` JSONFormatter | Already writes to `logs/structured.log` with timestamp, level, module |
| Exception hierarchy | New error classes | Existing `v2/exceptions.py` PipelineError | Already has code/message/details pattern |
| Job status polling | New polling endpoint | Existing `/analyze/status/{job_id}` | Already returns job status dict |

**Key insight:** Phase 8 is primarily a wiring/integration phase. Almost all infrastructure exists - the work is connecting the v2 pipeline to the v1 job infrastructure and adding the plausibility layer.

## Common Pitfalls

### Pitfall 1: Thread-to-Async Bridge
**What goes wrong:** The v2 pipeline uses async/await (extraction, matching use `asyncio.to_thread`), but `job_store.run_in_background()` runs in a plain thread with no event loop.
**Why it happens:** `run_in_background()` wraps a sync function in `threading.Thread`. The v2 pipeline functions are `async`.
**How to avoid:** Use `asyncio.run()` inside the background thread to create a new event loop, or use `asyncio.run_coroutine_threadsafe()` with the main loop.
**Warning signs:** "no current event loop" errors, coroutine never awaited warnings.
```python
def _run_v2_pipeline_sync(job_id, tender_id, ...):
    """Sync wrapper for async v2 pipeline, runs in background thread."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            _run_v2_pipeline_async(job_id, tender_id, ...)
        )
    finally:
        loop.close()
```

### Pitfall 2: SSE Progress Event Flooding
**What goes wrong:** Sending a progress event for every single position in every pass creates thousands of events that overwhelm the frontend and create backpressure in the asyncio.Queue.
**Why it happens:** Over-eager progress reporting.
**How to avoid:** Throttle progress events - report at most every 500ms or every 5th position, whichever is less frequent. The existing Queue has `maxsize=100` which silently drops on overflow.
**Warning signs:** Frontend lag, Queue full warnings in logs.

### Pitfall 3: Partial Results on AI Failure
**What goes wrong:** Current v2 code sets `matching_skipped=True` and returns partial results. QUAL-04 requires this to be a clear error instead.
**Why it happens:** v2 was designed for graceful degradation, but the requirements demand fail-fast.
**How to avoid:** Change the try/except blocks in the pipeline to re-raise as PipelineError with German user-facing messages.
**Warning signs:** Users see results with `matching_skipped` warnings instead of a clear error.

### Pitfall 4: Plausibility Check False Positives
**What goes wrong:** Plausibility checks flag valid results as suspicious (e.g., small tenders with all matches or all rejections).
**Why it happens:** Rigid thresholds that don't account for small sample sizes.
**How to avoid:** Scale thresholds by number of positions. A 3-position tender with 100% match rate is fine; a 50-position tender with 100% match rate is suspicious.
**Warning signs:** Users constantly see plausibility warnings on valid small tenders.

### Pitfall 5: Frontend Progress Parsing
**What goes wrong:** Frontend receives structured progress as a JSON string in the `progress` field but tries to display it as plain text.
**Why it happens:** The v1 frontend expects `progress` to be a display string, but v2 sends structured JSON.
**How to avoid:** Keep backward compatibility: always include a `message` field in the structured progress that can be displayed as-is. Frontend can optionally parse the structured data for richer UI.
**Warning signs:** Frontend shows `{"stage":"matching","percent":50}` as raw text.

## Code Examples

### 1. Wrapping V2 Pipeline in Job Store
```python
# In v2/routers/analyze_v2.py

from services.job_store import create_job, run_in_background, update_job

@router.post("/analyze")
async def analyze_tender(request: AnalyzeRequest):
    tender_id = request.tender_id
    # ... validation ...

    job = create_job()
    run_in_background(job, _run_v2_pipeline_sync, job.id, tender_id)
    return {"job_id": job.id, "status": "started"}


def _run_v2_pipeline_sync(job_id: str, tender_id: str) -> dict:
    """Sync wrapper that creates event loop for async v2 pipeline."""
    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(
            _run_v2_pipeline_async(job_id, tender_id)
        )
    finally:
        loop.close()


async def _run_v2_pipeline_async(job_id: str, tender_id: str) -> dict:
    """Full v2 pipeline with progress reporting."""
    def on_progress(stage, detail, percent):
        update_job(job_id, progress=json.dumps({
            "message": detail,
            "stage": stage,
            "percent": percent,
        }))

    # ... run extraction, matching, adversarial, gaps, plausibility ...
```

### 2. Plausibility Checker
```python
# In v2/validation/plausibility.py

from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class IssueSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"

class PlausibilityIssue(BaseModel):
    code: str
    severity: IssueSeverity
    message: str
    details: dict = Field(default_factory=dict)

class PlausibilityResult(BaseModel):
    passed: bool
    issues: list[PlausibilityIssue] = Field(default_factory=list)
    positions_total: int = 0
    positions_matched: int = 0
    positions_unmatched: int = 0
    duplicate_positions: list[str] = Field(default_factory=list)


def check_plausibility(
    positions: list,
    match_results: list,
    adversarial_results: list,
    gap_reports: list,
) -> PlausibilityResult:
    issues = []

    # 1. All positions covered
    pos_ids = {p.positions_nr for p in positions}
    matched_ids = {mr.positions_nr for mr in match_results}
    uncovered = pos_ids - matched_ids
    if uncovered:
        issues.append(PlausibilityIssue(
            code="UNCOVERED_POSITIONS",
            severity=IssueSeverity.ERROR,
            message=f"{len(uncovered)} Positionen ohne Match-Ergebnis",
            details={"positions": list(uncovered)},
        ))

    # 2. No duplicate position numbers
    seen = set()
    dupes = []
    for p in positions:
        if p.positions_nr in seen:
            dupes.append(p.positions_nr)
        seen.add(p.positions_nr)
    if dupes:
        issues.append(PlausibilityIssue(
            code="DUPLICATE_POSITIONS",
            severity=IssueSeverity.WARNING,
            message=f"{len(dupes)} doppelte Positionsnummern",
            details={"duplicates": dupes},
        ))

    # 3. Suspicious patterns (scaled by size)
    n = len(positions)
    if n > 10:
        match_rate = sum(1 for mr in match_results if mr.hat_match) / n
        if match_rate == 1.0:
            issues.append(PlausibilityIssue(
                code="ALL_MATCHED",
                severity=IssueSeverity.WARNING,
                message="Alle Positionen als Match - ungewoehnlich bei grosser Ausschreibung",
            ))
        if match_rate == 0.0:
            issues.append(PlausibilityIssue(
                code="NONE_MATCHED",
                severity=IssueSeverity.WARNING,
                message="Keine einzige Position matched - moeglicherweise falscher Katalog",
            ))

    # 4. Confidence distribution sanity
    confidences = [
        mr.bester_match.gesamt_konfidenz
        for mr in match_results
        if mr.bester_match
    ]
    if confidences and len(set(round(c, 2) for c in confidences)) == 1 and n > 5:
        issues.append(PlausibilityIssue(
            code="IDENTICAL_CONFIDENCES",
            severity=IssueSeverity.WARNING,
            message="Alle Konfidenzwerte identisch - moeglicherweise AI-Fehler",
        ))

    has_errors = any(i.severity == IssueSeverity.ERROR for i in issues)
    return PlausibilityResult(
        passed=not has_errors,
        issues=issues,
        positions_total=n,
        positions_matched=sum(1 for mr in match_results if mr.hat_match),
        positions_unmatched=sum(1 for mr in match_results if not mr.hat_match),
        duplicate_positions=dupes,
    )
```

### 3. Structured Step Logging
```python
# Logging pattern for QUAL-02
import logging

logger = logging.getLogger("v2.pipeline")

def log_step(tender_id: str, stage: str, position_nr: str,
             pass_num: int, result: str, details: dict = None):
    """Structured log entry for every pipeline step."""
    logger.info(
        f"[{tender_id}] {stage} | Position {position_nr} | "
        f"Pass {pass_num} | Result: {result}",
        extra={
            "tender_id": tender_id,
            "stage": stage,
            "position_nr": position_nr,
            "pass_num": pass_num,
            "result": result,
            **(details or {}),
        },
    )
```

### 4. Frontend Progress Display Enhancement
```javascript
// In useSSE.js or AnalysePage.jsx - parse structured progress
es.onmessage = (e) => {
  const data = JSON.parse(e.data)
  if (data.progress) {
    let progressInfo
    try {
      progressInfo = JSON.parse(data.progress)
      // Structured: { message, stage, percent, current_position, positions_done, positions_total }
      onProgress(progressInfo.message, progressInfo)
    } catch {
      // Fallback: plain string (backward compatible)
      onProgress(data.progress)
    }
  }
}
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| v2 analyze runs synchronously | Needs to run via job_store background thread | Phase 8 | Enables SSE streaming + prevents HTTP timeout |
| Graceful degradation on AI failure | Fail-fast with clear error messages | Phase 8 (QUAL-04) | Users never see partial results |
| Flat `progress: str` in job events | Structured progress with stage/position/percent | Phase 8 (QUAL-03) | Rich frontend progress display |
| No post-analysis validation | PlausibilityChecker runs after pipeline | Phase 8 (QUAL-01) | Catches missing positions, duplicates, suspicious patterns |

**Key architectural change:** The v2 `analyze_v2.py` router currently returns results synchronously (the full pipeline blocks the HTTP request). Phase 8 must convert this to background job execution with SSE streaming, matching the pattern already established in v1's `analyze.py`.

## Open Questions

1. **Progress throttling threshold**
   - What we know: SSE Queue maxsize is 100, positions can number 50-200+
   - What's unclear: Optimal throttle interval (every N positions vs every M milliseconds)
   - Recommendation: Start with every 500ms minimum interval, adjust based on testing

2. **Plausibility check scope for adversarial results**
   - What we know: Need to check all positions covered and no duplicates
   - What's unclear: Should plausibility also validate adversarial confidence distribution?
   - Recommendation: Yes - check that adversarial results exist for all matched positions (not just match_results)

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (existing) |
| Config file | backend/pytest.ini or pyproject.toml (existing) |
| Quick run command | `python -m pytest tests/test_plausibility.py -x` |
| Full suite command | `python -m pytest tests/ -x --timeout=60` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| QUAL-01 | Plausibility check detects uncovered positions, duplicates, suspicious patterns | unit | `python -m pytest tests/test_plausibility.py -x` | No - Wave 0 |
| QUAL-02 | Pipeline logs each step with tender_id, stage, position, pass, result | unit | `python -m pytest tests/test_pipeline_logging.py -x` | No - Wave 0 |
| QUAL-03 | SSE events contain structured stage/position progress | integration | `python -m pytest tests/test_sse_progress.py -x` | No - Wave 0 |
| QUAL-04 | AI failure raises PipelineError with German message, no partial results | unit | `python -m pytest tests/test_error_handling.py -x` | No - Wave 0 |
| APII-02 | POST /api/v2/analyze returns job_id and starts background processing | integration | `python -m pytest tests/test_analyze_v2_endpoint.py -x` | No - Wave 0 |
| APII-03 | GET /api/analyze/status/{job_id} returns stage-level progress | integration | `python -m pytest tests/test_job_status.py -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `python -m pytest tests/test_plausibility.py tests/test_pipeline_logging.py -x`
- **Per wave merge:** `python -m pytest tests/ -x --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_plausibility.py` -- covers QUAL-01
- [ ] `tests/test_pipeline_logging.py` -- covers QUAL-02
- [ ] `tests/test_sse_progress.py` -- covers QUAL-03, APII-02
- [ ] `tests/test_error_handling.py` -- covers QUAL-04

## Sources

### Primary (HIGH confidence)
- Codebase analysis of `backend/services/job_store.py` -- existing SSE/background job infrastructure
- Codebase analysis of `backend/routers/analyze.py` -- existing SSE streaming endpoints
- Codebase analysis of `backend/v2/routers/analyze_v2.py` -- current synchronous v2 pipeline
- Codebase analysis of `backend/v2/extraction/pipeline.py` -- pipeline structure and logging patterns
- Codebase analysis of `backend/v2/schemas/pipeline.py` -- existing StageProgress/AnalysisJob schemas
- Codebase analysis of `frontend-react/src/hooks/useSSE.js` -- existing SSE client with polling fallback
- [FastAPI SSE docs](https://fastapi.tiangolo.com/tutorial/server-sent-events/) -- SSE best practices

### Secondary (MEDIUM confidence)
- [sse-starlette PyPI](https://pypi.org/project/sse-starlette/) -- production SSE library (not needed, existing StreamingResponse suffices)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in project, no new dependencies
- Architecture: HIGH - patterns directly derived from existing v1 infrastructure
- Pitfalls: HIGH - identified from actual codebase analysis (thread/async bridge, partial results pattern)

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable - internal integration work, no external dependency changes)
