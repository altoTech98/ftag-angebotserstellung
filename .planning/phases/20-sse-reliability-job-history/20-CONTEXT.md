# Phase 20: SSE Reliability + Job History - Context

**Gathered:** 2026-03-12
**Status:** Ready for planning

<domain>
## Phase Boundary

SSE connections survive long-running analyses with automatic reconnection and event replay. Replace raw StreamingResponse with sse-starlette for W3C compliance. Add event history ring buffer for reconnection replay via Last-Event-ID. Frontend handles disconnects gracefully without marking analysis as failed.

</domain>

<decisions>
## Implementation Decisions

### Reconnection UX
- Silent retry on SSE disconnect — progress bar freezes at last known state, no visible indicator
- Fully silent fallback to polling — user never knows the transport changed
- On reconnect, jump to current progress instantly — no animation through missed steps
- Keep current error behavior for real backend failures (onFailed callback, no distinction between disconnect and failure in UI)

### SSE Protocol (from STATE.md decisions)
- sse-starlette replaces raw StreamingResponse for W3C SSE compliance
- In-memory ring buffer for event history (no Redis/SQLite) — ~100 events per job
- Events get unique IDs, retry directives, and keepalive pings
- Last-Event-ID header support for reconnection replay

### Claude's Discretion
- Ring buffer implementation details (data structure, eviction strategy)
- Keepalive ping interval and timeout thresholds
- Event ID format (sequential integer vs UUID vs timestamp-based)
- sse-starlette configuration details
- How to handle Last-Event-ID for events that have already been evicted from buffer

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/services/job_store.py`: Already has subscribe/unsubscribe with asyncio.Queue, notification system. Needs ring buffer addition.
- `frontend/src/lib/sse-client.ts`: Has 10-retry backoff logic and polling fallback. Needs Last-Event-ID header support.
- `frontend/src/components/analysis/step-progress.tsx`: Handles events via connectToAnalysis callback. No changes needed for silent retry.

### Established Patterns
- Job lifecycle: pending -> running -> completed | failed (job_store.py)
- SSE auth: Token-based via `/api/backend/sse-token` BFF route
- Background jobs run in threads, notify via asyncio.Queue to SSE subscribers

### Integration Points
- `backend/routers/analyze.py:50-89`: SSE endpoint — replace StreamingResponse with sse-starlette EventSourceResponse
- `backend/services/job_store.py:83-91`: _notify_subscribers — add event to ring buffer here
- `frontend/src/lib/sse-client.ts:76`: EventSource construction — add Last-Event-ID support
- `backend/services/sse_token_validator.py`: Token validation stays as-is

</code_context>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 20-sse-reliability-job-history*
*Context gathered: 2026-03-12*
