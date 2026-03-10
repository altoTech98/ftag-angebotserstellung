# Milestones

## v1.0 FTAG KI-Angebotserstellung v2 Core Engine (Shipped: 2026-03-10)

**Phases completed:** 8 phases, 19 plans, 0 tasks

**Key accomplishments:**
- Robust document parsing (PDF/DOCX/XLSX) with 55-field Pydantic schemas and format auto-detection
- 3-pass extraction pipeline (structural + AI semantic + cross-reference validation) with deduplication
- Cross-document intelligence: position matching, enrichment, and AI conflict resolution across mixed file types
- TF-IDF + Claude AI product matching against 891-product catalog with multi-dimensional confidence scoring
- Adversarial FOR/AGAINST debate validation with triple-check ensemble for uncertain matches
- Gap analysis with severity ratings, dual suggestions, and alternative product search
- 4-sheet Excel output (Uebersicht, Details, Gap-Analyse, Executive Summary) with color coding and CoT reasoning
- End-to-end pipeline with plausibility checks, structured logging, SSE progress streaming

**Stats:** 8,686 lines v2 Python code, 7,212 lines tests, 187 commits, 8 days (2026-03-02 → 2026-03-10)

### Known Gaps

Accepted as tech debt (28/38 requirements fully satisfied, 10 partial):

| REQ-ID | Description | Issue |
|--------|-------------|-------|
| EXEL-01..06 | 4-sheet Excel output | Backend complete; frontend calls v1 offer endpoint instead of v2 |
| APII-04 | POST /api/offer/generate | Endpoint exists but no frontend caller |
| APII-05 | GET /api/offer/{id}/download | Never reached (APII-04 not called) |
| MATC-09 | Feedback integration | V2 feedback store works; frontend writes to v1 store |
| GAPA-05 | Alternative suggestions | Computed but not surfaced to user |

**Root cause:** Frontend-backend v2 wiring incomplete — folder workflow reads v1-shaped response keys and calls v1 offer generation endpoint.

---

