# Phase 3: Cross-Document Intelligence - Research

**Researched:** 2026-03-10
**Domain:** Cross-document data merging, conflict detection, AI-assisted enrichment
**Confidence:** HIGH

## Summary

Phase 3 adds a post-pipeline cross-document intelligence layer on top of Phase 2's per-file 3-pass extraction. The core challenge is matching door positions across documents (XLSX door lists, PDF specifications, DOCX requirements), merging their attributes into enriched records, and detecting/resolving contradictions between documents. This is a data integration problem with AI-assisted entity resolution.

The existing codebase provides strong foundations: `dedup.py` already implements field-level merge with provenance tracking, `pipeline.py` has a clean orchestration pattern, and the `FieldSource` + `TrackedField` schemas already track per-field provenance. Phase 3 extends these patterns to cross-document boundaries rather than cross-pass boundaries.

**Primary recommendation:** Build three new modules (`cross_doc_matcher.py`, `enrichment.py`, `conflict_detector.py`) in `backend/v2/extraction/`, extend `ExtractionResult` with conflict and enrichment report schemas, and hook into `pipeline.py` as a post-pipeline step triggered automatically for multi-file tenders.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Dedicated cross-doc matcher module -- separate from Phase 2's intra-doc dedup. Different rules: also match by room+floor+door-type when positions_nr is missing in one document.
- Tiered confidence approach: auto-merge at 90%+ confidence, flag as 'possible match' at 60-90% for user review, ignore below 60%.
- General spec paragraphs (e.g., 'Alle Tueren im OG muessen T30 sein') are detected, scoped, and applied to all matching positions. Tagged with 'general spec' source.
- AI handles cross-doc position identifier normalization (e.g., 'Tuer 1.01' = 'Pos. 1.01' = 'Element E1.01'). Same approach as Phase 2 dedup but across document boundaries.
- AI resolution: Send both conflicting values + context to Claude to determine which is more likely correct based on document type, surrounding context, and domain knowledge.
- Full transparency: AI picks the best value but the rejected alternative is stored and visible. Output shows e.g. 'T90 (aus PDF-Spec, bestaetigt durch AI) -- Konflikt mit T30 aus Excel'.
- Detect both exact field contradictions AND semantic conflicts (e.g., 'Holzrahmen' in Excel but 'Stahlzarge' implied by PDF fire spec). AI should catch logical inconsistencies.
- Conflict severity: Critical (safety-relevant: fire rating, emergency exit), Major (spec-relevant: dimensions, material), Minor (cosmetic: color, surface). Matches Phase 6 Gap Analysis severity pattern.
- Fill gaps + upgrade low confidence: If a field is empty, fill from other doc. If a field has konfidenz <0.7 but another doc has a higher-confidence value, upgrade. FieldSource provenance preserved.
- Extract and apply implicit specs from general document sections (e.g., 'Alle Innenturen: Holzzarge, 40dB Schallschutz'). Apply to all matching positions with 'implicit spec' source and lower konfidenz (e.g., 0.7).
- Extend FieldSource with enrichment_source metadata -- explicitly mark 'this field was enriched from document X' beyond the existing dokument field.
- Generate enrichment report: per document, how many positions matched, how many fields enriched, how many conflicts found.
- Post-pipeline step: Run existing 3-pass pipeline per file first (Phase 2 code untouched), then run cross-doc intelligence as a separate layer over all results.
- Automatic when multi-file: If tender has 2+ files, cross-doc runs automatically after the 3-pass pipeline. Single file: skip.
- Same /api/v2/analyze response, extended with enrichment_report and conflicts fields.
- Separate Claude call(s) for cross-doc matching, enrichment, and conflict resolution. Dedicated prompts per task.

### Claude's Discretion
- Exact prompt design for cross-doc matching, enrichment, and conflict resolution
- Batching strategy for AI calls (how many positions per call)
- enrichment_source schema extension details
- Enrichment report format and structure
- Internal data structures for cross-doc matching

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| DOKA-07 | System enriches positions with data from different documents (Cross-Document Enrichment: Excel door list + PDF specification + DOCX requirements) | Cross-doc matcher identifies same positions across files; enrichment module fills gaps and upgrades low-confidence fields; FieldSource extended with enrichment_source for provenance |
| DOKA-08 | System detects and reports conflicts between documents (e.g., different fire protection classes in different files) | Conflict detector identifies exact field contradictions and semantic conflicts; AI resolves with transparency; severity classification (Critical/Major/Minor) |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.84.0 | AI calls for cross-doc matching, enrichment, conflict resolution | Already in use; messages.parse() for structured output |
| pydantic | v2 | Schema definitions for conflicts, enrichment report | Already in use for all v2 schemas |
| asyncio | stdlib | Async wrapping of sync Anthropic calls | Established pattern with asyncio.to_thread |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| difflib | stdlib | SequenceMatcher for position ID fuzzy matching (pre-filter before AI) | Initial candidate identification before AI call |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| AI-only matching | Pure string similarity | Too fragile for Swiss tender ID variations; AI needed for semantic normalization |
| Custom conflict resolution | Rule-based only | Misses semantic conflicts like material-firerating incompatibility |

**Installation:**
No new dependencies needed. All required libraries already installed.

## Architecture Patterns

### Recommended Project Structure
```
backend/v2/extraction/
├── cross_doc_matcher.py    # Position matching across documents
├── enrichment.py           # Field-level gap filling + confidence upgrade
├── conflict_detector.py    # Conflict detection + AI resolution
├── prompts.py              # Extended with cross-doc prompt templates
├── pipeline.py             # Extended with post-pipeline hook
├── dedup.py                # Unchanged (intra-doc dedup)
├── pass1_structural.py     # Unchanged
├── pass2_semantic.py       # Unchanged
├── pass3_validation.py     # Unchanged
└── chunking.py             # Unchanged

backend/v2/schemas/
├── common.py               # FieldSource extended with enrichment_source
├── extraction.py           # ExtractionResult extended with enrichment_report, conflicts
└── ...                     # Other schemas unchanged
```

### Pattern 1: Post-Pipeline Hook
**What:** Cross-doc intelligence runs as a separate step after the existing 3-pass pipeline, only when 2+ files are present.
**When to use:** Always for multi-file tenders. Skip for single-file.
**Example:**
```python
# In pipeline.py - after existing Pass 3:
async def run_extraction_pipeline(parse_results, tender_id, client=None):
    # ... existing Pass 1+2+3 code unchanged ...

    # Phase 3: Cross-document intelligence (only for multi-file tenders)
    if len(sorted_results) >= 2:
        logger.info(f"Pipeline [{tender_id}]: Cross-document intelligence on {len(all_positions)} positions")
        cross_doc_result = await run_cross_doc_intelligence(
            all_positions, sorted_results, client=client
        )
        all_positions = cross_doc_result.positionen
        enrichment_report = cross_doc_result.enrichment_report
        conflicts = cross_doc_result.conflicts

    return ExtractionResult(
        positionen=all_positions,
        # ... existing fields ...
        enrichment_report=enrichment_report,  # NEW
        conflicts=conflicts,                   # NEW
    )
```

### Pattern 2: Tiered Confidence Matching
**What:** Three-tier approach for cross-document position matching. Pre-filter with string similarity, then AI for ambiguous cases.
**When to use:** For every cross-document matching decision.
**Example:**
```python
# Tier 1: Exact positions_nr match (auto-merge, confidence 1.0)
# Tier 2: Normalized ID match ("Tuer 1.01" == "Pos. 1.01") via regex + AI (confidence 0.9+)
# Tier 3: Room+floor+type fallback when no position_nr in one doc (confidence 0.6-0.9)

class CrossDocMatch(BaseModel):
    """A match between positions from different documents."""
    position_a_index: int
    position_b_index: int
    confidence: float  # 0.0-1.0
    match_method: str  # "exact_id", "normalized_id", "room_floor_type", "ai_semantic"
    auto_merge: bool   # True if confidence >= 0.9
```

### Pattern 3: Conflict with Resolution
**What:** Conflict detection stores both values, AI picks winner, rejected value preserved.
**When to use:** When same field has different non-None values across documents for matched positions.
**Example:**
```python
class ConflictSeverity(str, Enum):
    CRITICAL = "critical"   # Safety: fire rating, emergency exit
    MAJOR = "major"         # Spec: dimensions, material
    MINOR = "minor"         # Cosmetic: color, surface

class FieldConflict(BaseModel):
    """A detected conflict between two document sources for the same field."""
    positions_nr: str
    field_name: str
    wert_a: str
    quelle_a: FieldSource
    wert_b: str
    quelle_b: FieldSource
    severity: ConflictSeverity
    resolution: str           # Which value was chosen
    resolution_reason: str    # AI's reasoning
    resolved_by: str          # "ai" or "rule"
```

### Pattern 4: General Spec Detection and Application
**What:** AI identifies general specification paragraphs (e.g., "All interior doors: wood frame, 40dB sound protection") and applies them to all matching positions.
**When to use:** During enrichment phase, specifically for PDF/DOCX documents that contain blanket specifications.
**Example:**
```python
class GeneralSpec(BaseModel):
    """A general specification that applies to multiple positions."""
    beschreibung: str           # The spec text
    scope: str                  # e.g., "Alle Innenturen OG", "Fluchtwege"
    affected_fields: dict[str, str]  # field_name -> value to apply
    source: FieldSource
    konfidenz: float = 0.7      # Lower confidence for implicit specs
```

### Anti-Patterns to Avoid
- **Modifying Phase 2 dedup logic:** Cross-doc matching is fundamentally different from intra-doc pass merging. Do not try to reuse `merge_positions()` for cross-doc matching. The matching criteria differ (room+floor+type vs exact ID only).
- **Monolithic AI call:** Do not send all positions from all documents in a single massive prompt. Batch by document pairs and use dedicated prompts per task (matching, enrichment, conflict resolution).
- **Silent enrichment:** Never enrich a field without updating `quellen` provenance. Every field change must be traceable.
- **Overwriting high-confidence with low-confidence:** The enrichment rule is fill-gaps + upgrade-low-confidence, never downgrade.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Position ID normalization | Custom regex for every Swiss ID format | AI prompt with examples of Swiss tender ID patterns | Endless edge cases: "Tuer 1.01", "Pos. 1.01", "Element E1.01", "T-1.01", "Nr. 1.01" |
| Semantic conflict detection | Rule-based incompatibility checker | AI prompt with domain knowledge | Material-firerating incompatibilities require building construction domain knowledge |
| Conflict severity classification | Manual field-to-severity mapping | Enum-based mapping with safety-field list | `SAFETY_FIELDS = {"brandschutz_klasse", "rauchschutz", "einbruchschutz_klasse"}` is straightforward enough to hand-code |
| Field-level merge with provenance | Custom merge logic | Extend existing `_merge_two_positions()` pattern | The pattern already exists in dedup.py, adapt it for cross-doc context |

**Key insight:** Position matching across documents is the hardest sub-problem because Swiss tenders lack standardized position numbering. AI is essential for this, not optional. But conflict severity classification is a simple domain mapping that does not need AI.

## Common Pitfalls

### Pitfall 1: Context Window Overflow
**What goes wrong:** Sending full text from multiple documents plus all positions in a single AI call exceeds context limits.
**Why it happens:** A tender might have 100+ positions across 3 documents with 200+ pages total.
**How to avoid:** Batch positions (25 per batch, matching existing pattern). Send only compact position summaries to matching prompts. Truncate document text to relevant sections only.
**Warning signs:** API errors with "max_tokens" or response truncation.

### Pitfall 2: Circular Enrichment
**What goes wrong:** Position A enriches Position B, then B enriches A back, creating feedback loops or overwriting original data.
**Why it happens:** Bidirectional merging without tracking what was already enriched.
**How to avoid:** Process enrichment in a single pass per matched group. Mark enriched fields with `enrichment_source` in FieldSource. Never re-enrich an already-enriched field.
**Warning signs:** Fields with `enrichment_source` being overwritten by another enrichment.

### Pitfall 3: False Position Matches
**What goes wrong:** AI matches two different physical doors because they share room number and floor but are actually distinct (e.g., two doors in the same room).
**Why it happens:** Room+floor+type matching is inherently ambiguous when a room has multiple doors.
**How to avoid:** The tiered confidence system handles this: room+floor+type matches get 60-90% confidence and are flagged for review, not auto-merged. Add "possible match" to response for user confirmation.
**Warning signs:** Positions being merged that have very different dimensions or conflicting attributes.

### Pitfall 4: General Spec Misapplication
**What goes wrong:** A general specification like "all doors in OG must be T30" gets applied to doors that already have a higher fire rating (e.g., T90 in a specific spec).
**Why it happens:** General specs should only fill gaps, not override specific specs.
**How to avoid:** General specs apply with konfidenz=0.7. Specific per-position specs from any document always win (higher konfidenz). Only fill empty fields from general specs.
**Warning signs:** Positions losing their specific fire ratings after enrichment.

### Pitfall 5: Document Type Assumptions
**What goes wrong:** Assuming all XLSX files are door lists and all PDFs are specifications.
**Why it happens:** Hard-coding document type roles instead of detecting content.
**How to avoid:** The file classifier from Phase 1 already identifies document content. Use that classification, not file extension, to determine document roles.
**Warning signs:** PDF door lists being treated as specification documents.

## Code Examples

Verified patterns from existing codebase:

### Extending FieldSource with Enrichment Source
```python
# In common.py - extend FieldSource
class FieldSource(BaseModel):
    """Provenance tracking for a single extracted field value."""
    dokument: str = Field(description="Source document filename")
    seite: Optional[int] = Field(None, description="Page number (PDF) or None")
    zeile: Optional[int] = Field(None, description="Row number (Excel) or None")
    zelle: Optional[str] = Field(None, description="Cell reference e.g. 'B15' (Excel)")
    sheet: Optional[str] = Field(None, description="Sheet name (Excel) or None")
    konfidenz: float = Field(1.0, description="Extraction confidence between 0.0 and 1.0")
    # NEW Phase 3 fields:
    enrichment_source: Optional[str] = Field(
        None, description="Document that provided this value via cross-doc enrichment"
    )
    enrichment_type: Optional[str] = Field(
        None, description="Type of enrichment: 'gap_fill', 'confidence_upgrade', 'general_spec', 'conflict_resolution'"
    )
```

### Extending ExtractionResult with Cross-Doc Fields
```python
# In extraction.py - extend ExtractionResult
class ExtractionResult(BaseModel):
    positionen: list[ExtractedDoorPosition] = Field(...)
    dokument_zusammenfassung: str = Field(...)
    warnungen: list[str] = Field(default_factory=list, ...)
    dokument_typ: DokumentTyp = Field(...)
    # NEW Phase 3 fields (Optional for backward compat):
    enrichment_report: Optional[EnrichmentReport] = Field(
        None, description="Cross-document enrichment statistics"
    )
    conflicts: list[FieldConflict] = Field(
        default_factory=list, description="Detected cross-document conflicts"
    )
```

### asyncio.to_thread Pattern (from existing Pass 3)
```python
# Source: backend/v2/extraction/pass3_validation.py
response = await asyncio.to_thread(
    client.messages.parse,
    model="claude-sonnet-4-20250514",
    max_tokens=16384,
    system=CROSSDOC_MATCHING_SYSTEM_PROMPT,
    messages=messages,
    output_format=CrossDocMatchResult,  # Pydantic model for structured output
)
```

### Cross-Doc Matching Prompt Design (Recommended)
```python
CROSSDOC_MATCHING_SYSTEM_PROMPT = """\
Du bist ein Experte fuer die Zuordnung von Tuerpositionen aus verschiedenen \
Ausschreibungsdokumenten. Deine Aufgabe: Finde Positionen die dieselbe physische \
Tuer beschreiben, auch wenn sie unterschiedliche Bezeichnungen haben.

## Matching-Regeln

1. **Exakte Positionsnummer**: "1.01" = "1.01" -> Sicherer Match (Konfidenz 1.0)
2. **Normalisierte ID**: "Tuer 1.01" = "Pos. 1.01" = "Element E1.01" -> Hohe Konfidenz (0.9+)
3. **Raum+Geschoss+Typ**: Gleicher Raum, gleiches Geschoss, aehnlicher Tuertyp -> Mittlere Konfidenz (0.6-0.9)
4. **Keine Uebereinstimmung**: Verschiedene Tueren -> Konfidenz < 0.6

## Kontext: Schweizer Ausschreibungen

- XLSX Tuerliste: Positionen + Basisdaten (Masse, Anzahl)
- PDF Bauphysik/Brandschutz: Detailspezifikationen pro Bereich
- DOCX Pflichtenheft: Allgemeine Anforderungen

Antworte im JSON-Format.
"""

CROSSDOC_CONFLICT_SYSTEM_PROMPT = """\
Du bist ein Experte fuer Bauphysik und Tuertechnik. Deine Aufgabe: Analysiere \
Konflikte zwischen verschiedenen Dokumenten fuer dieselbe Tuerposition.

## Konfliktanalyse

Fuer jeden Konflikt:
1. Bestimme welcher Wert wahrscheinlich korrekt ist basierend auf:
   - Dokumenttyp (PDF-Spezifikation > XLSX-Tuerliste fuer technische Details)
   - Kontext (spezifische Angabe > allgemeine Angabe)
   - Fachlogik (z.B. T90 erfordert Stahlzarge, nicht Holzzarge)
2. Begruende deine Entscheidung
3. Klassifiziere den Schweregrad:
   - CRITICAL: Sicherheitsrelevant (Brandschutz, Rauchschutz, Fluchtweg)
   - MAJOR: Spezifikationsrelevant (Masse, Material, Schallschutz)
   - MINOR: Kosmetisch (Farbe, Oberflaeche)

Antworte im JSON-Format.
"""
```

### Enrichment Report Schema (Recommended)
```python
class DocumentEnrichmentStats(BaseModel):
    """Enrichment statistics for a single source document."""
    dokument: str
    positionen_matched: int
    felder_enriched: int
    konflikte_gefunden: int

class EnrichmentReport(BaseModel):
    """Overall cross-document enrichment report."""
    total_positionen: int
    positionen_matched_cross_doc: int
    felder_enriched: int
    konflikte_total: int
    konflikte_critical: int
    konflikte_major: int
    konflikte_minor: int
    general_specs_applied: int
    dokument_stats: list[DocumentEnrichmentStats]
    zusammenfassung: str  # Human-readable summary for sales team
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flat field merge (pass wins all) | Field-level merge with provenance | Phase 2 (current) | Foundation for cross-doc merge |
| Single-doc extraction | Multi-file pipeline (Pass 1+2 per file, Pass 3 across) | Phase 2 (current) | Cross-doc layer hooks into this |
| No conflict tracking | FieldSource per field | Phase 2 (current) | Extended with enrichment_source |

**Current codebase patterns to preserve:**
- `_merge_two_positions()` in dedup.py: field-level merge pattern with quellen tracking
- `_summarize_positions()` in pass3_validation.py: compact position summaries for AI prompts
- `_validate_batch_with_retry()`: 3x retry with exponential backoff for AI calls
- Position batching at 25 per batch for context limits

## Open Questions

1. **How to handle positions without any position number?**
   - What we know: PDF specs sometimes describe door requirements by area ("all doors in fire zone 2") without specific position numbers
   - What's unclear: Should these become synthetic positions or general specs?
   - Recommendation: Treat as general specs with scope detection. Apply to all positions matching the scope criteria.

2. **Optimal batching for cross-doc matching**
   - What we know: Pass 3 uses 25 positions per batch. Cross-doc matching sends position pairs.
   - What's unclear: For N documents with M positions each, is it better to batch by document pairs or by position groups?
   - Recommendation: Start with document-pair batching (positions from Doc A vs Doc B), which gives clearer context per AI call. Fall back to 25-position batches within each pair.

3. **How to present "possible matches" (60-90% confidence) to user?**
   - What we know: Auto-merge at 90%+, flag at 60-90%, ignore below 60%
   - What's unclear: The API response format for possible matches that need user confirmation
   - Recommendation: Include `possible_matches` list in the enrichment report. Each entry has both positions + confidence + reason. Frontend can display these later; for now they appear in the API response.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest (already installed) |
| Config file | backend/tests/conftest.py + conftest_v2.py |
| Quick run command | `cd backend && python -m pytest tests/test_v2_crossdoc.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| DOKA-07 | Cross-doc position matching by exact ID | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestCrossDocMatcher::test_exact_id_match -x` | Wave 0 |
| DOKA-07 | Cross-doc position matching by normalized ID | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestCrossDocMatcher::test_normalized_id_match -x` | Wave 0 |
| DOKA-07 | Cross-doc position matching by room+floor+type | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestCrossDocMatcher::test_room_floor_type_match -x` | Wave 0 |
| DOKA-07 | Gap filling from other document | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestEnrichment::test_gap_fill -x` | Wave 0 |
| DOKA-07 | Low confidence upgrade | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestEnrichment::test_confidence_upgrade -x` | Wave 0 |
| DOKA-07 | General spec detection and application | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestEnrichment::test_general_spec_application -x` | Wave 0 |
| DOKA-07 | Enrichment provenance tracking | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestEnrichment::test_enrichment_provenance -x` | Wave 0 |
| DOKA-07 | Enrichment report generation | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestEnrichmentReport::test_report_stats -x` | Wave 0 |
| DOKA-08 | Exact field contradiction detection | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestConflictDetector::test_exact_conflict -x` | Wave 0 |
| DOKA-08 | Semantic conflict detection | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestConflictDetector::test_semantic_conflict -x` | Wave 0 |
| DOKA-08 | Conflict severity classification | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestConflictDetector::test_severity_classification -x` | Wave 0 |
| DOKA-08 | Conflict resolution with transparency | unit | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestConflictDetector::test_resolution_transparency -x` | Wave 0 |
| DOKA-07+08 | Pipeline integration for multi-file | integration | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestPipelineIntegration::test_multi_file_triggers_crossdoc -x` | Wave 0 |
| DOKA-07+08 | Single-file skips cross-doc | integration | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestPipelineIntegration::test_single_file_skips_crossdoc -x` | Wave 0 |
| DOKA-07+08 | API response includes enrichment_report and conflicts | integration | `cd backend && python -m pytest tests/test_v2_crossdoc.py::TestPipelineIntegration::test_api_response_extended -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_v2_crossdoc.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_v2_crossdoc.py` -- covers DOKA-07, DOKA-08 (all tests listed above)
- [ ] Extend `backend/tests/conftest_v2.py` -- add fixtures for multi-document position sets (positions from different documents with overlapping/conflicting data)

## Sources

### Primary (HIGH confidence)
- `backend/v2/extraction/dedup.py` -- field-level merge pattern, provenance tracking
- `backend/v2/extraction/pipeline.py` -- orchestration pattern, format priority, post-Pass-3 hook point
- `backend/v2/extraction/pass3_validation.py` -- asyncio.to_thread pattern, batching (25/batch), retry logic
- `backend/v2/schemas/common.py` -- FieldSource schema (extend with enrichment_source)
- `backend/v2/schemas/extraction.py` -- ExtractedDoorPosition (55 fields), ExtractionResult (extend)
- `backend/v2/extraction/prompts.py` -- German prompt template patterns
- `backend/v2/routers/analyze_v2.py` -- API response structure to extend

### Secondary (MEDIUM confidence)
- `.planning/phases/03-cross-document-intelligence/03-CONTEXT.md` -- user decisions constraining implementation

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, extends existing patterns
- Architecture: HIGH -- clear post-pipeline hook point, existing merge pattern to follow
- Pitfalls: HIGH -- based on direct codebase analysis and domain understanding
- Cross-doc matching: MEDIUM -- AI prompt design for Swiss tender ID normalization needs empirical testing

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, no external dependency changes expected)
