---
phase: 03-cross-document-intelligence
verified: 2026-03-10T15:35:00Z
status: human_needed
score: 8/8 must-haves verified
re_verification: true
  previous_status: gaps_found
  previous_score: 7/8
  gaps_closed:
    - "AI resolves conflicts with transparent reasoning, rejected value preserved"
  gaps_remaining: []
  regressions: []
human_verification:
  - test: "Upload two files (Excel door list + PDF specification) with the same position 1.01 in both, where the PDF has a different fire rating than the Excel"
    expected: "API response includes conflicts list with the fire rating conflict, severity=critical, both values visible, and resolved_by='ai' if ANTHROPIC_API_KEY is set"
    why_human: "Requires live API call with real file parsing and actual Anthropic API key for full end-to-end behavior"
  - test: "Upload one XLSX door list and one PDF specification for the same tender via POST /api/v2/analyze"
    expected: "API response shows enrichment_report.positionen_matched_cross_doc >= 1, enrichment_report.felder_enriched >= 1, and enrichment_source on enriched fields"
    why_human: "Requires live Anthropic API key for Pass 2/3 semantic extraction, real file upload, and actual cross-doc triggering in the full pipeline"
---

# Phase 3: Cross-Document Intelligence Verification Report

**Phase Goal:** Requirements are enriched with data from all uploaded documents, and contradictions between documents are surfaced before matching begins
**Verified:** 2026-03-10T15:35:00Z
**Status:** human_needed
**Re-verification:** Yes — after gap closure (Plan 03-03 executed to wire AI conflict resolution)

## Re-Verification Summary

Previous verification (2026-03-10T14:46:58Z) found 1 gap: `_resolve_conflicts_with_ai()` accepted an Anthropic client parameter but never called it — all resolutions were rule-based with `resolved_by` hardcoded to `"rule"`.

Plan 03-03 closed this gap. This re-verification confirms the gap is resolved.

**Gap closed:** AI conflict resolution is now wired. `_resolve_conflicts_with_ai()` calls `client.messages.parse` via `asyncio.to_thread` using `CROSSDOC_CONFLICT_SYSTEM_PROMPT` and `CROSSDOC_CONFLICT_USER_TEMPLATE`, sets `resolved_by="ai"` on success, applies 3x retry with exponential backoff, and falls back to rule-based resolution when client is None or all retries fail.

**Regressions:** None. All 36 crossdoc tests pass (31 original + 5 new AI resolution tests).

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Positions from different documents with the same position number are identified as matches | VERIFIED | `cross_doc_matcher.py` Tier 1: exact positions_nr comparison at confidence 1.0, auto_merge=True |
| 2 | Positions with normalized IDs (Tuer 1.01 = Pos. 1.01) are matched across documents | VERIFIED | `_normalize_position_id()` strips Swiss prefixes via regex; Tier 2 match at confidence 0.92 |
| 3 | Empty fields are filled from other documents with enrichment_source provenance | VERIFIED | `enrich_positions()` gap-fill branch sets FieldSource.enrichment_source + enrichment_type="gap_fill" |
| 4 | Low-confidence fields (<0.7) are upgraded when another document has higher confidence | VERIFIED | `_enrich_one_from_other()` confidence_upgrade branch; test_no_downgrade verifies high-conf fields never overwritten |
| 5 | General specs (e.g. 'Alle Innenturen T30') are detected and applied to matching positions | VERIFIED | `_apply_general_spec()` with `_match_scope()` scope filter; only fills empty fields; general_spec_no_override test passes |
| 6 | Conflicting field values between documents are detected with severity classification | VERIFIED | `detect_and_resolve_conflicts()` with deterministic SAFETY_FIELDS/MAJOR_FIELDS sets; _classify_severity tested for CRITICAL/MAJOR/MINOR |
| 7 | AI resolves conflicts with transparent reasoning, rejected value preserved | VERIFIED | `_resolve_conflicts_with_ai()` calls `asyncio.to_thread(client.messages.parse, ..., output_format=ConflictResolutionResult)`; `resolved_by="ai"` on success; 3x retry + rule-based fallback wired |
| 8 | Enrichment report summarizes cross-doc statistics per document | VERIFIED | `EnrichmentReport` returned from `enrich_positions()` with felder_enriched, konflikte_*, general_specs_applied, zusammenfassung |

**Score:** 8/8 truths verified

### Required Artifacts

#### Plan 03-01 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/v2/schemas/common.py` | FieldSource with enrichment_source and enrichment_type | VERIFIED | Both Optional[str] fields present, default None, backward compatible |
| `backend/v2/schemas/extraction.py` | ConflictSeverity, FieldConflict, GeneralSpec, EnrichmentReport, CrossDocMatch schemas; ExtractionResult extended | VERIFIED | All 6 new schemas present; ExtractionResult has enrichment_report=None and conflicts=[] defaults |
| `backend/v2/extraction/cross_doc_matcher.py` | match_positions_across_docs() with tiered confidence | VERIFIED | Three tiers implemented (exact_id/normalized_id/room_floor_type), fully substantive |
| `backend/v2/extraction/enrichment.py` | enrich_positions() gap-fill + confidence upgrade + general spec application | VERIFIED | 319 lines, all three enrichment modes implemented with provenance tracking |
| `backend/v2/extraction/conflict_detector.py` | detect_and_resolve_conflicts() with AI resolution + severity | VERIFIED | AI resolution wired via asyncio.to_thread; ConflictResolutionItem/Result Pydantic models; 3x retry; resolved_by="ai" on success; rule fallback confirmed |
| `backend/v2/extraction/prompts.py` | German prompt templates including CROSSDOC_MATCHING_SYSTEM_PROMPT | VERIFIED | CROSSDOC_MATCHING_SYSTEM_PROMPT, CROSSDOC_CONFLICT_SYSTEM_PROMPT, CROSSDOC_ENRICHMENT_SYSTEM_PROMPT all present and > 100 chars |
| `backend/tests/test_v2_crossdoc.py` | Unit tests for matcher, enrichment, conflict detector (min 150 lines) | VERIFIED | 36 tests (31 original + 5 new AI resolution tests); covers AI path, no-client fallback, retry exhaustion, prompt formatting, async behavior |

#### Plan 03-02 Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/v2/extraction/pipeline.py` | Post-pipeline cross-doc hook triggered for multi-file tenders | VERIFIED | `run_cross_doc_intelligence()` and conditional `len(sorted_results) >= 2` hook present; `await detect_and_resolve_conflicts(...)` confirmed on line 124 |
| `backend/v2/extraction/__init__.py` | Updated exports including cross-doc modules | VERIFIED | cross_doc_matcher, enrichment, conflict_detector all exported in `__all__` |
| `backend/v2/routers/analyze_v2.py` | Extended response with enrichment_report and conflicts | VERIFIED | Response dict includes enrichment_report, conflicts, total_conflicts with None/[] defaults for backward compat |

#### Plan 03-03 Artifacts (Gap Closure)

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `backend/v2/extraction/conflict_detector.py` | AI call via asyncio.to_thread + resolved_by="ai" + 3x retry | VERIFIED | Lines 144-151: `await asyncio.to_thread(client.messages.parse, ..., output_format=ConflictResolutionResult)` confirmed; `resolved_by="ai"` set at line 169; backoff loop at lines 142-196 |
| `backend/tests/test_v2_crossdoc.py` | Tests for AI resolution path (test_ai_resolution*) | VERIFIED | `test_ai_resolution_called_when_client_provided`, `test_rule_fallback_when_no_client`, `test_rule_fallback_on_ai_failure`, `test_ai_receives_formatted_prompt` all present |

### Key Link Verification

#### Plan 03-01 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `cross_doc_matcher.py` | `extraction.py` | CrossDocMatch schema | WIRED | `from v2.schemas.extraction import ConflictSeverity, CrossDocMatch, ExtractedDoorPosition` |
| `enrichment.py` | `common.py` | FieldSource enrichment_source field | WIRED | `from v2.schemas.common import BrandschutzKlasse, FieldSource, SchallschutzKlasse`; enrichment_source set in gap_fill and confidence_upgrade branches |
| `conflict_detector.py` | `extraction.py` | FieldConflict + ConflictSeverity | WIRED | `from v2.schemas.extraction import ConflictSeverity, CrossDocMatch, ExtractedDoorPosition, FieldConflict` |

#### Plan 03-02 Key Links

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `pipeline.py` | `cross_doc_matcher.py` | import match_positions_across_docs | WIRED | `from v2.extraction.cross_doc_matcher import match_positions_across_docs` |
| `pipeline.py` | `enrichment.py` | import enrich_positions | WIRED | `from v2.extraction.enrichment import enrich_positions` |
| `pipeline.py` | `conflict_detector.py` | import + await detect_and_resolve_conflicts | WIRED | Line 13: import confirmed; line 124: `conflicts = await detect_and_resolve_conflicts(...)` |
| `analyze_v2.py` | ExtractionResult | enrichment_report and conflicts in response dict | WIRED | enrichment_report and conflicts serialized in response |

#### Plan 03-03 Key Links (Gap Closure)

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `conflict_detector.py` | `prompts.py` | CROSSDOC_CONFLICT_SYSTEM_PROMPT, CROSSDOC_CONFLICT_USER_TEMPLATE | WIRED | Lines 17-19: both prompt constants imported and used at lines 137 and 148 |
| `conflict_detector.py` | anthropic client | asyncio.to_thread(client.messages.parse, ...) | WIRED | Line 144-151: `await asyncio.to_thread(client.messages.parse, model=..., system=CROSSDOC_CONFLICT_SYSTEM_PROMPT, ..., output_format=ConflictResolutionResult)` |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DOKA-07 | 03-01, 03-02 | System enriches positions with data from different documents (Excel door list + PDF spec + DOCX requirements) | SATISFIED | enrich_positions() gap-fill + confidence upgrade + general spec; pipeline hook triggers for 2+ files; API response shows enrichment_report |
| DOKA-08 | 03-01, 03-02, 03-03 | System detects and reports conflicts between documents (e.g. different fire protection classes) | SATISFIED | Conflict detection with CRITICAL/MAJOR/MINOR severity classification; AI resolution via Claude when client provided; rule-based fallback; conflicts surfaced in API response |

Both DOKA-07 and DOKA-08 are mapped to Phase 3 in REQUIREMENTS.md traceability table. No orphaned requirements found for Phase 3.

### Anti-Patterns Found

No anti-patterns found in Phase 3 files. No TODO/FIXME/placeholder comments. No `return null`/`return {}` stubs. No empty implementations. The previous warning-level anti-pattern (AI resolution stub) is resolved.

### Human Verification Required

#### 1. End-to-End Multi-Document Cross-Doc Enrichment

**Test:** Upload one XLSX door list and one PDF specification for the same tender via POST /api/v2/analyze (upload both files, then call /api/v2/analyze). The XLSX has position 1.01 with dimensions but no fire rating; the PDF has "Pos. 1.01" with fire rating T30.
**Expected:** API response shows enrichment_report.positionen_matched_cross_doc >= 1, enrichment_report.felder_enriched >= 1, and the position in positionen has brandschutz_klasse populated with enrichment_source pointing to the PDF.
**Why human:** Requires live Anthropic API key for Pass 2/3 semantic extraction, real file upload, and actual cross-doc triggering in the full pipeline.

#### 2. AI Conflict Resolution in Live Response

**Test:** Upload two files for the same tender where position 1.01 appears in both with conflicting fire ratings (T30 in XLSX, T90 in PDF).
**Expected:** API response includes conflicts list with at least one entry for brandschutz_klasse at severity=critical, with both wert_a and wert_b visible, resolution set to the winning value, and resolved_by="ai" (when ANTHROPIC_API_KEY is set).
**Why human:** Requires real documents with extractable position data; cannot be verified without live API and actual parser output. The AI resolution path (resolved_by="ai") is now wired but only exercisable with a real API key.

### Gaps Summary

No gaps remain. Phase 3 delivers all structural and behavioral components for cross-document intelligence:

- Position matching across documents using three confidence tiers (exact ID, normalized ID, room/floor/type)
- Enrichment engine fills gaps and upgrades low-confidence fields with full provenance tracking
- Conflict detector surfaces field-level contradictions with deterministic CRITICAL/MAJOR/MINOR severity
- AI conflict resolution calls Claude via asyncio.to_thread with CROSSDOC_CONFLICT prompts and structured Pydantic output; 3x retry with exponential backoff; rule-based fallback preserved
- Pipeline triggers cross-doc intelligence for multi-file tenders and exposes enrichment_report + conflicts in the API response
- 36 tests cover all paths including AI resolution, no-client fallback, and retry exhaustion

The sole remaining items are human-verification only: live end-to-end testing with real documents and a valid API key to confirm the full pipeline fires correctly in production conditions.

---

_Verified: 2026-03-10T15:35:00Z_
_Verifier: Claude (gsd-verifier)_
_Re-verification: Yes (gap closure after Plan 03-03)_
