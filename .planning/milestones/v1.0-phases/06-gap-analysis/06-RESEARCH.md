# Phase 6: Gap Analysis - Research

**Researched:** 2026-03-10
**Domain:** AI-driven gap analysis for door product specification deviations
**Confidence:** HIGH

## Summary

Phase 6 transforms the output of Phase 4 (MatchResult) and Phase 5 (AdversarialResult) into detailed gap reports for every position. The core work is: (1) expanding the existing gap schemas to support 6 dimensions, dual suggestion types, and cross-references, (2) building a gap analyzer that makes one Claude Opus call per position to identify specification deviations, (3) implementing gap-focused TF-IDF alternative search using the existing CatalogTfidfIndex with dynamically weighted fields, and (4) wiring it all into the analyze_v2.py router.

The codebase already has well-established patterns from Phase 5: `asyncio.to_thread` wrapping sync `client.messages.parse()` calls, `asyncio.Semaphore` for rate limiting Opus calls, German system prompts with domain knowledge, and Pydantic v2 structured output models. Phase 6 follows these patterns exactly. No new libraries are needed.

**Primary recommendation:** Mirror Phase 5's adversarial.py + adversarial_prompts.py structure. Create gap_analyzer.py (engine) + gap_prompts.py (German prompts) in backend/v2/gaps/. Expand existing schemas in gaps.py. Wire into analyze_v2.py with the same lazy-import pattern.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- ALL positions get gap analysis (bestaetigt, unsicher, AND abgelehnt)
- For bestaetigt: report gaps for any dimension scoring below 100%
- For unsicher: full gap report against best-effort match
- For abgelehnt: text summary only (no per-dimension breakdown)
- Dedicated Claude Opus call per position for gap identification (not derived from adversarial data)
- Phase 5 per-dimension CoT passed as input context to gap analysis call
- Expand GapDimension enum to 6+ dimensions: Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung
- Safety dimensions auto-escalate: Brandschutz gap = always Kritisch or Major (never Minor)
- Every gap includes side-by-side: anforderung_wert vs katalog_wert
- Each GapItem links to alternatives via gap_geschlossen_durch cross-reference
- Fresh TF-IDF search weighted toward gap dimensions for alternative search
- Up to 3 alternatives per position, ranked by gap coverage
- Abgelehnt alternatives filtered: only >30% gap coverage included
- Two suggestion types per gap: Kundenvorschlag (sales) AND Technischer Hinweis (technical)
- All suggestions in German
- zusammenfassung per position: full paragraph covering all gaps, alternatives, suggestions

### Claude's Discretion
- Exact prompt design for gap analysis Opus calls (German, domain-specific)
- Concurrency strategy (Semaphore limit for Opus calls)
- How to weight TF-IDF fields for gap-focused alternative search
- Internal GapItem cross-reference structure for gap_geschlossen_durch
- How to handle positions with no extractable fields for comparison

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| GAPA-01 | Detaillierte Gap-Analyse fuer jeden Nicht-Match (welche Eigenschaft weicht ab) | Schema expansion (6 dimensions, side-by-side values), Opus call per position with DimensionCoT context input |
| GAPA-02 | Gaps kategorisiert nach Dimension: Masse, Material, Norm, Zertifizierung, Leistung | GapDimension enum expansion to include Brandschutz and Schallschutz (6 total, 1:1 with Phase 4 MatchDimension) |
| GAPA-03 | Gap-Schweregrad: Kritisch, Major, Minor mit safety auto-escalation | GapSeverity enum already exists; safety auto-escalation logic mirrors Phase 4 safety cap pattern |
| GAPA-04 | AI-Vorschlag was sich aendern muesste damit ein Produkt passt | Dual suggestion types (Kundenvorschlag + Technischer Hinweis) via Opus structured output |
| GAPA-05 | Alternative Produkte die den Gap schliessen koennten | Gap-weighted TF-IDF search using CatalogTfidfIndex with dynamic field weights + per-gap breakdown |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| anthropic | >=0.84.0 | Claude Opus API calls with messages.parse() | Already used in Phase 4+5, structured output via Pydantic |
| pydantic | v2 | Schema definitions and structured output | Already used throughout v2 codebase |
| scikit-learn | existing | TF-IDF vectorizer for alternative search | Already used in CatalogTfidfIndex |
| asyncio | stdlib | Concurrency with Semaphore for rate limiting | Established pattern from Phase 5 |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | existing | Score computation for TF-IDF weighting | Already imported in tfidf_index.py |
| pandas | existing | Catalog DataFrame access | Already used for product data |

### Alternatives Considered
None -- all libraries are already in the codebase. No new dependencies needed.

**Installation:**
No new packages required.

## Architecture Patterns

### Recommended Project Structure
```
backend/v2/gaps/
  __init__.py           # Exports: analyze_gaps, analyze_single_position_gaps
  gap_analyzer.py       # Engine: Opus calls, TF-IDF search, assembly
  gap_prompts.py        # German system/user prompt templates
backend/v2/schemas/
  gaps.py               # EXPAND existing: GapDimension +1, GapItem +fields, AlternativeProduct +fields
```

### Pattern 1: Mirror Phase 5 Engine Structure
**What:** gap_analyzer.py follows the same structure as adversarial.py: single-position function + batch function with Semaphore
**When to use:** Always -- this is the established pattern
**Example:**
```python
# gap_analyzer.py mirrors adversarial.py structure
async def analyze_single_position_gaps(
    client: anthropic.Anthropic,
    match_result: MatchResult,
    adversarial_result: AdversarialResult,
    tfidf_index: CatalogTfidfIndex,
    semaphore: asyncio.Semaphore,
) -> GapReport:
    ...

async def analyze_gaps(
    client: anthropic.Anthropic,
    match_results: list[MatchResult],
    adversarial_results: list[AdversarialResult],
    tfidf_index: CatalogTfidfIndex,
) -> list[GapReport]:
    semaphore = asyncio.Semaphore(GAP_MAX_CONCURRENT)
    tasks = [analyze_single_position_gaps(...) for ...]
    return list(await asyncio.gather(*tasks))
```

### Pattern 2: Structured Output via messages.parse()
**What:** Use Pydantic model as output_format for Claude Opus call, get typed gap analysis back
**When to use:** For the Opus gap analysis call
**Example:**
```python
# Pydantic model for Opus structured output (internal, not the final GapReport)
class GapAnalysisResponse(BaseModel):
    gaps: list[GapItemResponse]
    zusammenfassung: str

response = await asyncio.to_thread(
    client.messages.parse,
    model="claude-opus-4-6",
    max_tokens=4096,
    system=GAP_SYSTEM_PROMPT,
    messages=[{"role": "user", "content": user_content}],
    output_format=GapAnalysisResponse,
)
parsed: GapAnalysisResponse = response.parsed
```

### Pattern 3: Lazy Import in analyze_v2.py
**What:** Guard imports with try/except, set _GAPS_AVAILABLE flag
**When to use:** When wiring gap analysis into the router
**Example:**
```python
try:
    from v2.gaps import analyze_gaps
    _GAPS_AVAILABLE = True
except ImportError as _gap_err:
    _GAPS_AVAILABLE = False
    logger.warning(f"[V2 Analyze] Gap modules not available: {_gap_err}")
```

### Pattern 4: Gap-Weighted TF-IDF Search
**What:** Dynamically boost TF-IDF field weights based on which dimensions have gaps
**When to use:** When searching for alternative products that close specific gaps
**Example:**
```python
def search_alternatives_for_gaps(
    position: ExtractedDoorPosition,
    gaps: list[GapItem],
    tfidf_index: CatalogTfidfIndex,
    top_k: int = 20,
) -> list[tuple[int, float]]:
    # Build query text with boosted weights for gap dimensions
    # e.g., if Brandschutz is a gap, repeat Brandschutz fields 8x instead of 4x
    gap_dims = {g.dimension for g in gaps}
    # Custom query with boosted gap-relevant fields
    ...
```

### Pattern 5: Three-Track Processing Based on ValidationStatus
**What:** Different gap analysis depth based on bestaetigt/unsicher/abgelehnt
**When to use:** In analyze_single_position_gaps
**Example:**
```python
if adversarial_result.validation_status == ValidationStatus.BESTAETIGT:
    # Only gaps for dimensions scoring < 1.0
    # Opus call to identify non-perfect dimensions
elif adversarial_result.validation_status == ValidationStatus.UNSICHER:
    # Full gap report against best-effort match
    # All dimensions analyzed
else:  # ABGELEHNT
    # Text summary only (no per-dimension breakdown)
    # Alternative search with >30% coverage filter
```

### Anti-Patterns to Avoid
- **Re-deriving dimension scores from scratch:** Phase 5 already has per-dimension CoT with scores. Pass this as context to the gap Opus call, don't ask Claude to re-score.
- **Calling Opus for abgelehnt dimension breakdown:** CONTEXT.md explicitly says "text summary only" for abgelehnt. Don't waste Opus calls on per-dimension analysis for positions with no viable match.
- **Using the same TF-IDF weights for alternative search as for initial matching:** Gap-focused search MUST dynamically boost fields relevant to the identified gaps.
- **Building GapReport inside the Opus output schema:** Keep the Opus output schema lean (gap items + summary). Assembly of the full GapReport (with alternatives, cross-references) happens in Python after the Opus call and TF-IDF search.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Fire class severity assessment | Custom ranking logic | domain_knowledge.FIRE_CLASS_RANK + normalize_fire_class() | Battle-tested hierarchy already handles EI30/60/90/120 |
| Resistance class comparison | Custom comparator | domain_knowledge.RESISTANCE_RANK + normalize_resistance() | Already handles RC/WK normalization |
| Product catalog search | Custom search | CatalogTfidfIndex.search() + extract_candidate_fields() | Already built, tested, handles German tokenization |
| Structured AI output parsing | Manual JSON parsing | client.messages.parse() with Pydantic output_format | Established pattern, handles validation automatically |
| Concurrent API rate limiting | Custom threading | asyncio.Semaphore + asyncio.to_thread + asyncio.gather | Same pattern as Phase 5 adversarial.py |

**Key insight:** This phase reuses almost all infrastructure from Phases 4-5. The only new code is the gap analysis logic, prompts, and schema expansions.

## Common Pitfalls

### Pitfall 1: Safety Dimension Severity Downgrade
**What goes wrong:** Brandschutz gap rated as "minor" when a fire class is missing
**Why it happens:** AI might see small numerical difference (EI60 vs EI90) as minor
**How to avoid:** Post-process Opus output: any Brandschutz or Schallschutz gap MUST be Kritisch or Major. Apply deterministic override after Opus call, like Phase 4's safety cap.
**Warning signs:** GapItem with dimension=Brandschutz and schweregrad=MINOR

### Pitfall 2: Empty katalog_wert for Abgelehnt Positions
**What goes wrong:** Trying to compare against a product that doesn't exist for abgelehnt positions
**Why it happens:** Abgelehnt positions have no viable match, so there's no product to compare against
**How to avoid:** For abgelehnt: skip per-dimension comparison entirely, generate text summary only, focus on alternative search
**Warning signs:** AttributeError or None access on bester_match for abgelehnt positions

### Pitfall 3: Alternative Product Overlap with Best Match
**What goes wrong:** Alternative search returns the same product that was already matched
**Why it happens:** TF-IDF search naturally returns the best-matching product first
**How to avoid:** Filter out the already-matched product_id from alternative search results
**Warning signs:** Alternative with same produkt_id as bester_match

### Pitfall 4: Oversized Opus Prompts
**What goes wrong:** Prompt exceeds token limits when position has many fields + full catalog candidate data
**Why it happens:** Including raw catalog rows in the prompt
**How to avoid:** Send only the matched product's relevant fields (using extract_candidate_fields()), not full catalog rows. Keep alternative candidate data minimal.
**Warning signs:** API errors about context length

### Pitfall 5: Cross-Reference Integrity (gap_geschlossen_durch)
**What goes wrong:** GapItem references an alternative product that doesn't exist in the alternativen list
**Why it happens:** Building gap items and alternatives independently without cross-linking
**How to avoid:** Build GapItems first, then search alternatives, then cross-reference by checking which gaps each alternative closes. Update gap_geschlossen_durch after alternatives are determined.
**Warning signs:** gap_geschlossen_durch contains produkt_ids not in alternativen list

### Pitfall 6: Inconsistent Dimension Names
**What goes wrong:** Opus returns "Brandschutzklasse" instead of "Brandschutz" as dimension name
**Why it happens:** Free-text dimension names in Opus output don't match GapDimension enum values
**How to avoid:** Use structured Pydantic output with GapDimension enum, not free text. Or normalize dimension names deterministically after Opus call.
**Warning signs:** GapItems with dimension values not in GapDimension enum

## Code Examples

### Schema Expansion (gaps.py)
```python
# Expand GapDimension to match Phase 4's MatchDimension (6 dimensions)
class GapDimension(str, Enum):
    MASSE = "Masse"
    BRANDSCHUTZ = "Brandschutz"      # NEW
    SCHALLSCHUTZ = "Schallschutz"    # NEW
    MATERIAL = "Material"
    ZERTIFIZIERUNG = "Zertifizierung"  # Was "Norm"
    LEISTUNG = "Leistung"

# Expand GapItem with dual suggestions and cross-reference
class GapItem(BaseModel):
    dimension: GapDimension
    schweregrad: GapSeverity
    anforderung_wert: str
    katalog_wert: Optional[str] = None
    abweichung_beschreibung: str
    kundenvorschlag: Optional[str] = None       # NEW: sales suggestion
    technischer_hinweis: Optional[str] = None   # NEW: technical suggestion
    gap_geschlossen_durch: list[str] = Field(   # NEW: cross-ref to alternatives
        default_factory=list,
        description="produkt_ids of alternatives that close this gap"
    )

# Expand AlternativeProduct with per-gap breakdown
class AlternativeProduct(BaseModel):
    produkt_id: str
    produkt_name: str
    teilweise_deckung: float  # 0.0-1.0
    verbleibende_gaps: list[str]          # gaps NOT closed
    geschlossene_gaps: list[str] = Field( # NEW: gaps closed
        default_factory=list,
    )
```

### Safety Auto-Escalation (deterministic post-processing)
```python
SAFETY_DIMENSIONS = {GapDimension.BRANDSCHUTZ, GapDimension.SCHALLSCHUTZ}

def apply_safety_escalation(gaps: list[GapItem]) -> list[GapItem]:
    """Ensure safety-critical gaps are never rated MINOR."""
    for gap in gaps:
        if gap.dimension in SAFETY_DIMENSIONS and gap.schweregrad == GapSeverity.MINOR:
            gap.schweregrad = GapSeverity.MAJOR
    return gaps
```

### Gap-Weighted Alternative Search
```python
# Dynamic weight boosting based on gap dimensions
GAP_BOOST_MULTIPLIER = 2.0  # Double the normal weight for gap fields

DIMENSION_TO_TFIDF_FIELDS = {
    GapDimension.BRANDSCHUTZ: ["brandschutzklasse"],
    GapDimension.SCHALLSCHUTZ: ["schallschutz", "tuerrohling"],
    GapDimension.MASSE: ["lichtmass"],
    GapDimension.MATERIAL: ["material"],
    GapDimension.ZERTIFIZIERUNG: ["widerstandsklasse"],
    GapDimension.LEISTUNG: ["kategorie", "produktegruppen"],
}

def build_gap_weighted_query(position, gaps):
    """Build TF-IDF query with boosted weights for gap dimensions."""
    gap_dims = {g.dimension for g in gaps}
    boosted_fields = set()
    for dim in gap_dims:
        boosted_fields.update(DIMENSION_TO_TFIDF_FIELDS.get(dim, []))
    # Build query text with double repetitions for boosted fields
    ...
```

### Router Integration
```python
# In analyze_v2.py, after adversarial validation block:
if _GAPS_AVAILABLE and adversarial_results:
    try:
        gap_results = await analyze_gaps(
            client=client,
            match_results=match_results,
            adversarial_results=adversarial_results,
            tfidf_index=tfidf_idx,
        )
        response["gap_results"] = [gr.model_dump() for gr in gap_results]
        response["total_gaps"] = sum(len(gr.gaps) for gr in gap_results)
    except Exception as e:
        response["gaps_skipped"] = True
        response["gaps_warning"] = f"Gap analysis failed: {str(e)}"
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Single aenderungsvorschlag field | Dual: kundenvorschlag + technischer_hinweis | Phase 6 (new) | Sales team gets actionable copy-paste suggestions |
| 5 gap dimensions (no Brandschutz/Schallschutz) | 6 gap dimensions (1:1 with MatchDimension) | Phase 6 (new) | Full alignment between matching and gap analysis |
| Simple verbleibende_gaps strings | Cross-referenced gap_geschlossen_durch on GapItem | Phase 6 (new) | Bidirectional: gap knows which alternative closes it |

## Open Questions

1. **Opus Concurrency Limit**
   - What we know: Phase 5 uses Semaphore(3) for Opus calls
   - What's unclear: Whether Phase 6 Opus calls should share the same semaphore or use separate
   - Recommendation: Use Semaphore(3) for gap analysis (separate from adversarial since they run sequentially in the pipeline, not concurrently)

2. **Positions with No Extractable Fields**
   - What we know: Some positions may have minimal data (just a position number and description)
   - What's unclear: How to generate meaningful gaps when there's nothing specific to compare
   - Recommendation: If position has fewer than 2 technical fields populated, generate a summary-only gap report noting "Unzureichende Spezifikationsdaten fuer detaillierte Gap-Analyse"

3. **Alternative Search Result Quality**
   - What we know: CatalogTfidfIndex searches work well for initial matching
   - What's unclear: Whether gap-weighted search will produce meaningfully different results from initial search
   - Recommendation: Implement and validate empirically. If boosted search returns same products as initial match, the alternatives are genuinely the closest options.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest |
| Config file | None (run from backend/ directory) |
| Quick run command | `cd backend && python -m pytest tests/test_v2_gaps.py -x -v` |
| Full suite command | `cd backend && python -m pytest tests/ -x -v` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| GAPA-01 | Gap analysis for every non-match identifies deviating properties | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestGapAnalysis -x` | No - Wave 0 |
| GAPA-02 | Gaps categorized by 6 dimensions (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung) | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestGapDimensions -x` | No - Wave 0 |
| GAPA-03 | Gap severity: Kritisch/Major/Minor with safety auto-escalation | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestSeverityEscalation -x` | No - Wave 0 |
| GAPA-04 | AI suggestions (Kundenvorschlag + Technischer Hinweis) per gap | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestSuggestions -x` | No - Wave 0 |
| GAPA-05 | Alternative products with gap coverage and remaining deviations | unit | `cd backend && python -m pytest tests/test_v2_gaps.py::TestAlternativeSearch -x` | No - Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_v2_gaps.py -x -v`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x -v`
- **Phase gate:** Full suite green before /gsd:verify-work

### Wave 0 Gaps
- [ ] `tests/test_v2_gaps.py` -- covers GAPA-01 through GAPA-05
- [ ] Framework install: None needed (pytest already installed)

## Sources

### Primary (HIGH confidence)
- Codebase inspection: backend/v2/schemas/gaps.py (existing schema)
- Codebase inspection: backend/v2/schemas/adversarial.py (input data model)
- Codebase inspection: backend/v2/schemas/matching.py (input data model)
- Codebase inspection: backend/v2/matching/adversarial.py (established patterns for Opus calls, semaphore, structured output)
- Codebase inspection: backend/v2/matching/tfidf_index.py (reusable search with field weights)
- Codebase inspection: backend/v2/matching/domain_knowledge.py (FIRE_CLASS_RANK, RESISTANCE_RANK)
- Codebase inspection: backend/v2/routers/analyze_v2.py (integration point, lazy import pattern)

### Secondary (MEDIUM confidence)
- CONTEXT.md decisions (user-locked implementation choices)

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - all libraries already in codebase, no new dependencies
- Architecture: HIGH - direct mirror of Phase 5 patterns (adversarial.py structure)
- Pitfalls: HIGH - derived from codebase inspection of existing edge cases and patterns

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, no external dependency changes expected)
