# Requirements: v2.1 Analyse-Pipeline Stabilisierung

**Defined:** 2026-03-12
**Core Value:** 100% korrekte Zuordnung jeder Anforderung zum richtigen Produkt — oder eine explizite, begruendete Gap-Meldung.

## v2.1 Requirements

### PDF Performance

- [x] **PDF-01**: PDF text extraction uses PyMuPDF (fitz) instead of pdfplumber for spec text, completing 286-page PDF in under 30 seconds (not 10 minutes)
- [x] **PDF-02**: pdfplumber retained exclusively for table extraction where PyMuPDF is insufficient
- [x] **PDF-03**: max_chars=0 treated as unlimited consistently across all PDF parsing paths
- [x] **PDF-04**: Per-page progress logging emitted during PDF parsing for observability

### SSE Reliability

- [ ] **SSE-01**: SSE streaming uses sse-starlette EventSourceResponse with W3C-compliant event IDs, retry directives, and keepalive pings
- [ ] **SSE-02**: Job store maintains event history ring buffer (last ~100 events per job) for reconnection replay
- [ ] **SSE-03**: Reconnecting SSE clients receive missed events via Last-Event-ID header support
- [ ] **SSE-04**: SSE connection drops do not mark analysis as failed in the frontend

### Result Delivery

- [ ] **RES-01**: Missing BFF proxy route `/api/backend/analyze/status/[jobId]` created in Next.js API routes
- [ ] **RES-02**: Polling fallback in sse-client.ts actually fires and retrieves job status when SSE is unavailable
- [ ] **RES-03**: Analysis results display in frontend after backend completion, even if SSE was disconnected
- [ ] **RES-04**: Page refresh during running analysis reconnects to the active job (jobId persisted in sessionStorage or URL)

### Integration

- [ ] **INT-01**: End-to-end analysis with multi-file upload (PDF + Excel + DOCX) completes and shows results in frontend
- [x] **INT-02**: No by_alias pydantic/anthropic SDK errors (pydantic >=2.7.0 verified)

## Out of Scope

| Feature | Reason |
|---------|--------|
| SQLite job persistence | In-memory store sufficient for single-server deployment; restart during analysis is rare |
| Redis event queue | Over-engineering for single-server; ring buffer in memory is sufficient |
| Cancel analysis endpoint | No backend cancel API exists; closing SSE is sufficient for now |
| PyMuPDF table extraction | pdfplumber table extraction is proven; PyMuPDF find_tables() less mature |
| SSE token mechanism changes | Current token flow works correctly |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| PDF-01 | Phase 19 | Complete |
| PDF-02 | Phase 19 | Complete |
| PDF-03 | Phase 19 | Complete |
| PDF-04 | Phase 19 | Complete |
| SSE-01 | Phase 20 | Pending |
| SSE-02 | Phase 20 | Pending |
| SSE-03 | Phase 20 | Pending |
| SSE-04 | Phase 20 | Pending |
| RES-01 | Phase 21 | Pending |
| RES-02 | Phase 21 | Pending |
| RES-03 | Phase 21 | Pending |
| RES-04 | Phase 21 | Pending |
| INT-01 | Phase 21 | Pending |
| INT-02 | Phase 19 | Complete |

**Coverage:**
- v2.1 requirements: 14 total
- Mapped to phases: 14
- Unmapped: 0

---
*Requirements defined: 2026-03-12*
*Last updated: 2026-03-12 after research synthesis*
