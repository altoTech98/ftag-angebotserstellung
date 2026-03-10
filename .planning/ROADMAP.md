# Roadmap: FTAG KI-Angebotserstellung v2

## Overview

Rebuild the core analysis engine from document parsing through Excel output, replacing v1's single-pass approach with a multi-pass, adversarially-validated pipeline. The journey moves from robust document extraction (Phases 1-3), through AI-powered matching with adversarial validation (Phases 4-5), gap analysis (Phase 6), structured Excel output (Phase 7), and finally end-to-end quality assurance with live observability (Phase 8). Each phase delivers a verifiable capability that builds on the previous.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Document Parsing & Pipeline Schemas** - Robust per-format parsers (PDF/DOCX/XLSX) plus Pydantic data contracts for the entire pipeline (completed 2026-03-10)
- [x] **Phase 2: Multi-Pass Extraction** - Multi-file upload with structural + AI semantic + cross-reference validation passes (completed 2026-03-10)
- [ ] **Phase 3: Cross-Document Intelligence** - Merge requirements across document types and detect inter-document conflicts
- [ ] **Phase 4: Product Matching Engine** - TF-IDF pre-filter + AI matching with multi-dimensional confidence scores and feedback integration
- [ ] **Phase 5: Adversarial Validation** - Double-check and triple-check passes that actively challenge matches with chain-of-thought reasoning
- [ ] **Phase 6: Gap Analysis** - Categorized gap reports with severity ratings and alternative product suggestions
- [ ] **Phase 7: Excel Output Generation** - 4-sheet Excel with color-coding, reasoning columns, and executive summary
- [ ] **Phase 8: Quality, Observability & End-to-End** - Plausibility checks, step logging, live progress streaming, and full pipeline integration

## Phase Details

### Phase 1: Document Parsing & Pipeline Schemas
**Goal**: Every document format (PDF, DOCX, XLSX) is reliably parsed into structured text, and all Pydantic models for the entire pipeline are defined as data contracts between stages
**Depends on**: Nothing (first phase)
**Requirements**: DOKA-01, DOKA-02, DOKA-03
**Success Criteria** (what must be TRUE):
  1. User uploads a PDF containing tables and receives complete text with table structure preserved
  2. User uploads a DOCX file and receives text with formatting context intact
  3. User uploads an XLSX door list and the system automatically detects column structure without manual configuration
  4. All pipeline Pydantic schemas (ExtractedRequirement, MatchResult, AdversarialResult, GapReport) are defined and importable by downstream services
**Plans**: 2 plans

Plans:
- [ ] 01-01-PLAN.md — V2 project scaffolding, Pydantic schemas, exceptions, and test infrastructure
- [ ] 01-02-PLAN.md — PDF, DOCX, and XLSX parsers with format-detection router

### Phase 2: Multi-Pass Extraction
**Goal**: Users can upload multiple files per tender and get a complete, deduplicated list of every technical requirement extracted through multiple analysis passes
**Depends on**: Phase 1
**Requirements**: DOKA-04, DOKA-05, DOKA-06, APII-01
**Success Criteria** (what must be TRUE):
  1. User can upload a mixed set of PDF + Excel + DOCX files in a single analysis request
  2. System performs at least 3 passes per document (structural, AI semantic, cross-reference validation) and extracts requirements missed by any single pass
  3. Every technical requirement (dimensions, materials, fire ratings, certifications, performance data) is extracted as an individual data point with its source location
  4. Duplicate requirements from multiple passes are merged (e.g., "T1.01", "Tuer 1.01", "Position 1.01" resolve to one entry)
  5. POST /api/upload accepts multiple files per tender
**Plans**: 3 plans

Plans:
- [ ] 02-01-PLAN.md — Pass 1 structural extraction, page chunking, dedup module, and prompt templates
- [ ] 02-02-PLAN.md — V2 upload and analyze API endpoints with tender_id session management
- [ ] 02-03-PLAN.md — Pass 2 AI semantic, Pass 3 cross-reference validation, pipeline orchestrator, and API wiring

### Phase 3: Cross-Document Intelligence
**Goal**: Requirements are enriched with data from all uploaded documents, and contradictions between documents are surfaced before matching begins
**Depends on**: Phase 2
**Requirements**: DOKA-07, DOKA-08
**Success Criteria** (what must be TRUE):
  1. When a door position appears in both an Excel door list and a PDF specification, the system merges all attributes into one enriched requirement record
  2. When documents contain conflicting specifications (e.g., different fire ratings for the same position), the system flags the conflict with both values and their source documents
  3. Cross-document enrichment results are visible in the final output (user can see which data came from which document)
**Plans**: 3 plans

Plans:
- [ ] 03-01-PLAN.md — Schemas, cross-doc matcher, enrichment engine, conflict detector, and prompt templates
- [ ] 03-02-PLAN.md — Pipeline integration, API response extension, and end-to-end wiring
- [ ] 03-03-PLAN.md — Gap closure: wire AI conflict resolution in conflict_detector.py

### Phase 4: Product Matching Engine
**Goal**: Every extracted requirement is matched against the FTAG product catalog with multi-dimensional confidence scoring and learning from past corrections
**Depends on**: Phase 2
**Requirements**: MATC-01, MATC-02, MATC-03, MATC-04, MATC-09, APII-06
**Success Criteria** (what must be TRUE):
  1. Every extracted requirement is compared against the full FTAG catalog (~891 products) using TF-IDF pre-filtering followed by AI evaluation
  2. Each match includes a confidence score (0-100%) broken down by dimension (dimensions, fire protection, sound insulation, material, certification, performance)
  3. Matches scoring 95%+ are flagged as confirmed; below 95% are flagged for further validation or gap analysis
  4. Previous matching corrections (feedback) are injected as few-shot examples in AI matching calls
  5. POST /api/feedback saves corrections that improve future analyses
**Plans**: TBD

Plans:
- [ ] 04-01: TBD
- [ ] 04-02: TBD

### Phase 5: Adversarial Validation
**Goal**: Every match is challenged by an independent AI pass that actively tries to disprove it, with transparent chain-of-thought reasoning for all decisions
**Depends on**: Phase 4
**Requirements**: MATC-05, MATC-06, MATC-07, MATC-08
**Success Criteria** (what must be TRUE):
  1. Every match undergoes a second AI call (adversarial pass) that attempts to find reasons the match is wrong
  2. Matches with post-adversarial confidence below 95% trigger a third AI call with an alternative prompt strategy
  3. Every match decision includes step-by-step chain-of-thought reasoning explaining why the product was selected
  4. When multiple products could match a requirement, all candidates are listed with individual confidence scores and reasoning
**Plans**: TBD

Plans:
- [ ] 05-01: TBD
- [ ] 05-02: TBD

### Phase 6: Gap Analysis
**Goal**: Every non-match or partial match gets a detailed, categorized gap report with severity and actionable suggestions
**Depends on**: Phase 5
**Requirements**: GAPA-01, GAPA-02, GAPA-03, GAPA-04, GAPA-05
**Success Criteria** (what must be TRUE):
  1. Every non-match includes a detailed analysis of which specific properties deviate from the requirement
  2. Gaps are categorized by dimension (dimensions, material, norm, certification, performance)
  3. Each gap has a severity rating: Critical (no solution exists), Major (significant deviation), Minor (close to matching)
  4. System generates a suggestion for what would need to change for a product to match the requirement
  5. Alternative products that could partially close the gap are suggested with explanation of remaining deviations
**Plans**: TBD

Plans:
- [ ] 06-01: TBD
- [ ] 06-02: TBD

### Phase 7: Excel Output Generation
**Goal**: The complete analysis (matches, gaps, reasoning) is exported as a professional 4-sheet Excel file that the sales team can use directly for customer offers
**Depends on**: Phase 6
**Requirements**: EXEL-01, EXEL-02, EXEL-03, EXEL-04, EXEL-05, EXEL-06, APII-04, APII-05
**Success Criteria** (what must be TRUE):
  1. Generated Excel contains Sheet 1 "Uebersicht" with all requirements and their match status at a glance
  2. Generated Excel contains Sheet 2 "Details" with requirement-to-product mapping, confidence scores, dimensional breakdown, and reasoning
  3. Generated Excel contains Sheet 3 "Gap-Analyse" with all non-matches, gap reasons, deviations, severity, and alternative suggestions
  4. Generated Excel contains Sheet 4 "Executive Summary" with statistics, overall assessment, and recommendations
  5. Cells are color-coded: green (95%+ match), yellow (60-95% partial), red (<60% no match) and every decision cell explains WHY
**Plans**: TBD

Plans:
- [ ] 07-01: TBD
- [ ] 07-02: TBD

### Phase 8: Quality, Observability & End-to-End
**Goal**: The full pipeline runs reliably end-to-end with real-time progress visibility, plausibility validation, and clear error reporting
**Depends on**: Phase 7
**Requirements**: QUAL-01, QUAL-02, QUAL-03, QUAL-04, APII-02, APII-03
**Success Criteria** (what must be TRUE):
  1. After analysis completes, a plausibility check validates that all positions are covered, no duplicates exist, and no suspicious patterns are present
  2. Every analysis step is logged with detail (which requirement, which pass, which result) for post-hoc debugging
  3. User sees live progress in the frontend showing which step is running and which position is being processed
  4. If the AI service fails, the user receives a clear error message instead of partial or degraded results
  5. POST /api/analyze triggers the full pipeline with SSE streaming for real-time progress, and GET /api/analyze/status/{job_id} returns detailed position-level progress
**Plans**: TBD

Plans:
- [ ] 08-01: TBD
- [ ] 08-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Document Parsing & Pipeline Schemas | 2/2 | Complete   | 2026-03-10 |
| 2. Multi-Pass Extraction | 3/3 | Complete   | 2026-03-10 |
| 3. Cross-Document Intelligence | 2/3 | In Progress|  |
| 4. Product Matching Engine | 0/2 | Not started | - |
| 5. Adversarial Validation | 0/2 | Not started | - |
| 6. Gap Analysis | 0/2 | Not started | - |
| 7. Excel Output Generation | 0/2 | Not started | - |
| 8. Quality, Observability & End-to-End | 0/2 | Not started | - |
