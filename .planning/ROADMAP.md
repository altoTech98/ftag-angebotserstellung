# Roadmap: FTAG KI-Angebotserstellung v2

## Milestones

- ✅ **v1.0 KI-Angebotserstellung v2 Pipeline** — Phases 1-9 (shipped 2026-03-10)
- ✅ **v2.0 AI Tender Matcher — Web-Oberflaeche & Platform** — Phases 10-18 (shipped 2026-03-11)
- 🚧 **v2.1 Analyse-Pipeline Stabilisierung** — Phases 19-21 (in progress)

## Phases

<details>
<summary>✅ v1.0 KI-Angebotserstellung v2 Pipeline (Phases 1-9) — SHIPPED 2026-03-10</summary>

- [x] Phase 1: Document Parsing & Pipeline Schemas (2/2 plans) — completed 2026-03-10
- [x] Phase 2: Multi-Pass Extraction (3/3 plans) — completed 2026-03-10
- [x] Phase 3: Cross-Document Intelligence (3/3 plans) — completed 2026-03-10
- [x] Phase 4: Product Matching Engine (2/2 plans) — completed 2026-03-10
- [x] Phase 5: Adversarial Validation (2/2 plans) — completed 2026-03-10
- [x] Phase 6: Gap Analysis (2/2 plans) — completed 2026-03-10
- [x] Phase 7: Excel Output Generation (2/2 plans) — completed 2026-03-10
- [x] Phase 8: Quality, Observability & End-to-End (3/3 plans) — completed 2026-03-10
- [x] Phase 9: Frontend V2 Offer & Feedback Wiring (2/2 plans) — completed 2026-03-10

Full details: `.planning/milestones/v1.0-ROADMAP.md`

</details>

<details>
<summary>✅ v2.0 AI Tender Matcher — Web-Oberflaeche & Platform (Phases 10-18) — SHIPPED 2026-03-11</summary>

- [x] Phase 10: Foundation — Auth + Database + Design System (6/6 plans) — completed 2026-03-11
- [x] Phase 11: Python Backend Integration — BFF + Service Auth (3/3 plans) — completed 2026-03-11
- [x] Phase 12: File Handling + Project Management (3/3 plans) — completed 2026-03-11
- [x] Phase 13: Analysis Wizard + Results View (4/4 plans) — completed 2026-03-11
- [x] Phase 14: Catalog Management (3/3 plans) — completed 2026-03-11
- [x] Phase 15: Admin + Dashboard + Polish (4/4 plans) — completed 2026-03-11
- [x] Phase 16: Fix Analysis-to-Python File Bridge (1/1 plan) — completed 2026-03-11
- [x] Phase 17: Fix Dashboard & Email Data Access (1/1 plan) — completed 2026-03-11
- [x] Phase 18: Fix Cross-Phase Integration Gaps (1/1 plan) — completed 2026-03-11

Full details: `.planning/milestones/v2.0-ROADMAP.md`

</details>

### 🚧 v2.1 Analyse-Pipeline Stabilisierung (In Progress)

**Milestone Goal:** Fix the three interconnected bugs that prevent project analyses from completing and delivering results to the frontend. The bugs form a failure chain: slow PDF parsing causes long analysis times, long analyses exceed SSE connection lifetimes, and when SSE drops the polling fallback does not work.

- [x] **Phase 19: PDF Performance Fix** — Replace pdfplumber text extraction with PyMuPDF, fix max_chars=0 bug, resolve pydantic compatibility (completed 2026-03-12)
- [ ] **Phase 20: SSE Reliability + Job History** — W3C-compliant SSE with sse-starlette, event history ring buffer, reconnection replay
- [ ] **Phase 21: Result Delivery + Polling Fallback** — Missing BFF proxy route, working polling fallback, end-to-end result delivery

## Phase Details

### Phase 19: PDF Performance Fix
**Goal**: PDF text extraction completes in seconds instead of minutes, unblocking the entire analysis pipeline
**Depends on**: Phase 18 (v2.0 complete)
**Requirements**: PDF-01, PDF-02, PDF-03, PDF-04, INT-02
**Success Criteria** (what must be TRUE):
  1. A 286-page tender PDF completes text extraction in under 30 seconds (not 10 minutes)
  2. Table extraction from PDFs still works correctly (pdfplumber retained for tables)
  3. Uploading a PDF with max_chars=0 extracts all text without truncation
  4. Per-page progress appears in backend logs during PDF parsing
  5. No pydantic/anthropic SDK by_alias errors occur during analysis
**Plans**: 1 plan

Plans:
- [ ] 19-01: Replace pdfplumber text extraction with PyMuPDF and fix parsing edge cases

### Phase 20: SSE Reliability + Job History
**Goal**: SSE connections survive long-running analyses with automatic reconnection and event replay
**Depends on**: Phase 19
**Requirements**: SSE-01, SSE-02, SSE-03, SSE-04
**Success Criteria** (what must be TRUE):
  1. SSE stream sends W3C-compliant events with unique IDs, retry directives, and keepalive pings
  2. Disconnecting and reconnecting mid-analysis resumes from the last received event (no missed progress updates)
  3. An SSE connection drop during analysis does not mark the analysis as failed in the frontend
  4. Job store retains last ~100 events per job for reconnection replay
**Plans**: 1-2 plans

Plans:
- [ ] 20-01: Replace StreamingResponse with sse-starlette and add event history ring buffer

### Phase 21: Result Delivery + Polling Fallback
**Goal**: Analysis results always reach the frontend, regardless of SSE connection state
**Depends on**: Phase 20
**Requirements**: RES-01, RES-02, RES-03, RES-04, INT-01
**Success Criteria** (what must be TRUE):
  1. The BFF proxy route `/api/backend/analyze/status/[jobId]` exists and returns job status from the Python backend
  2. When SSE is unavailable, the polling fallback in sse-client.ts fires and retrieves job status via the BFF route
  3. After backend analysis completes, results display in the frontend even if SSE was disconnected during the run
  4. Refreshing the browser during a running analysis reconnects to the active job and shows current progress
  5. A multi-file upload (PDF + Excel + DOCX) completes end-to-end and shows results in the frontend
**Plans**: 1 plan

Plans:
- [ ] 21-01: Create BFF proxy route, fix polling fallback, verify end-to-end result delivery

## Progress

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Document Parsing & Pipeline Schemas | v1.0 | 2/2 | Complete | 2026-03-10 |
| 2. Multi-Pass Extraction | v1.0 | 3/3 | Complete | 2026-03-10 |
| 3. Cross-Document Intelligence | v1.0 | 3/3 | Complete | 2026-03-10 |
| 4. Product Matching Engine | v1.0 | 2/2 | Complete | 2026-03-10 |
| 5. Adversarial Validation | v1.0 | 2/2 | Complete | 2026-03-10 |
| 6. Gap Analysis | v1.0 | 2/2 | Complete | 2026-03-10 |
| 7. Excel Output Generation | v1.0 | 2/2 | Complete | 2026-03-10 |
| 8. Quality, Observability & End-to-End | v1.0 | 3/3 | Complete | 2026-03-10 |
| 9. Frontend V2 Offer & Feedback Wiring | v1.0 | 2/2 | Complete | 2026-03-10 |
| 10. Foundation | v2.0 | 6/6 | Complete | 2026-03-11 |
| 11. Python Backend Integration | v2.0 | 3/3 | Complete | 2026-03-11 |
| 12. File Handling + Projects | v2.0 | 3/3 | Complete | 2026-03-11 |
| 13. Analysis Wizard + Results | v2.0 | 4/4 | Complete | 2026-03-11 |
| 14. Catalog Management | v2.0 | 3/3 | Complete | 2026-03-11 |
| 15. Admin + Dashboard + Polish | v2.0 | 4/4 | Complete | 2026-03-11 |
| 16. Fix Analysis-Python Bridge | v2.0 | 1/1 | Complete | 2026-03-11 |
| 17. Fix Dashboard & Email Data | v2.0 | 1/1 | Complete | 2026-03-11 |
| 18. Fix Cross-Phase Integration | v2.0 | 1/1 | Complete | 2026-03-11 |
| 19. PDF Performance Fix | 1/1 | Complete   | 2026-03-12 | - |
| 20. SSE Reliability + Job History | v2.1 | 0/1 | Not started | - |
| 21. Result Delivery + Polling Fallback | v2.1 | 0/1 | Not started | - |
