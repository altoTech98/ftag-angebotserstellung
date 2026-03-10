# Phase 4: Product Matching Engine - Research

**Researched:** 2026-03-10
**Domain:** TF-IDF pre-filtering + Claude AI multi-dimensional product matching
**Confidence:** HIGH

## Summary

Phase 4 transforms ExtractedDoorPosition objects (from Phase 2/3) into MatchResult objects by comparing each requirement against the FTAG product catalog (~891 products, ~318 columns). The architecture is two-stage: a scikit-learn TF-IDF pre-filter narrows candidates to 30-50 per requirement, then individual Claude Sonnet API calls score each match across 6 dimensions (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung). Feedback from past corrections is injected as few-shot examples.

The codebase already has significant infrastructure to build on: MatchResult/MatchCandidate/DimensionScore schemas in `backend/v2/schemas/matching.py`, the `messages.parse()` pattern from Phase 2, TF-IDF usage in `services/semantic_search.py`, domain knowledge in `services/fast_matcher.py` (fire class hierarchies, resistance ranks, category keywords), and the feedback store pattern in `services/feedback_store.py`. The v2 matching module stub exists at `backend/v2/matching/__init__.py`.

**Primary recommendation:** Build three new modules in `backend/v2/matching/` -- `tfidf_index.py` (weighted field indexing with category boost), `ai_matcher.py` (one-position-per-call Claude matching with structured output), and `feedback_v2.py` (TF-IDF-based feedback retrieval with v2 schemas) -- then wire them into the analyze_v2 router.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- TF-IDF index rebuilt from scratch using all 318 catalog columns with weighted field indexing (boost Brandschutzklasse, Schallschutz, Lichtmass, Material, Widerstandsklasse over administrative columns)
- Return top 30-50 candidates per requirement
- Category detection runs in parallel: TF-IDF searches all 891 products but boosts score for products in detected door category -- wider search with category signal, no hard category filtering
- One position per AI call -- each requirement gets its own Claude call with 30-50 candidates
- Model: Claude Sonnet for Phase 4 matching (Opus reserved for Phase 5 adversarial)
- Full relevant fields per candidate (~15-20 fields) sent per candidate product
- Structured output via messages.parse() returning MatchResult Pydantic model directly
- asyncio.to_thread wrapping for async compat (established pattern)
- Equal weight average across all 6 dimensions
- Hard fail on safety dimensions: if Brandschutz scores below 50%, cap gesamt_konfidenz at max 60%
- 95%+ = confirmed match, below 95% = flagged for Phase 5 adversarial validation or gap analysis
- Return best match + up to 3 alternative matches with full dimension breakdown and reasoning
- Few-shot examples injected into matching prompt from past corrections
- Feedback selection via TF-IDF similarity between current requirement and past corrections
- New v2 feedback store in backend/v2/ with v2 schemas (MatchResult references)
- POST /api/v2/feedback endpoint for saving corrections

### Claude's Discretion
- Exact TF-IDF field weights and boosting factors
- Prompt design for matching (German, domain-specific)
- Feedback example count per call (balancing relevance vs prompt size)
- Internal data structures for the new TF-IDF index
- Retry/error handling strategy for individual matching calls
- How to handle requirements with very few extracted fields

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| MATC-01 | System gleicht jede extrahierte Anforderung gegen den FTAG-Produktkatalog (~891 Produkte) ab | TF-IDF pre-filter + AI matching pipeline; CatalogIndex loading pattern exists |
| MATC-02 | System bewertet jedes Match multi-dimensional (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistungsdaten) | MatchDimension enum + DimensionScore schema already defined; AI prompt returns per-dimension scores |
| MATC-03 | System berechnet Konfidenz-Score (0-100%) pro Match mit Aufschluesselung nach Dimension | MatchCandidate.gesamt_konfidenz + dimension_scores list; equal-weight average with safety cap |
| MATC-04 | System setzt Match-Schwellenwert bei 95%+ Konfidenz | MatchResult.hat_match flag set when gesamt_konfidenz >= 0.95 |
| MATC-09 | System integriert Feedback/Korrekturen aus frueheren Analysen als Few-Shot-Examples | v2 feedback store with TF-IDF similarity retrieval; injected into matching prompt |
| APII-06 | POST /api/feedback speichert Matching-Korrekturen fuer zukuenftige Analysen | POST /api/v2/feedback endpoint in v2 routers |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| scikit-learn | >=1.6.0 | TF-IDF vectorization + cosine similarity | Already in requirements.txt; proven in v1 semantic_search.py |
| anthropic | >=0.49.0 | Claude Sonnet API via messages.parse() | Already in requirements.txt; messages.parse() pattern established in Phase 2 |
| pydantic | >=2.5.3 | Structured output schemas (MatchResult) | Already in requirements.txt; v2 schemas already defined |
| pandas | 2.2.3 | Catalog DataFrame loading and column access | Already in requirements.txt; CatalogIndex uses it |

### Supporting
| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| numpy | >=2.4.0 | Array operations for TF-IDF similarity scores | Already imported by scikit-learn; use for score sorting |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| TF-IDF | Sentence-transformers embeddings | Out of scope per REQUIREMENTS.md ("Embedding-basierte Suche: TF-IDF ausreichend bei 891 Produkten") |
| One call per position | Batch multiple positions per call | Decision locked: one per call for maximum focus |

**Installation:** No new dependencies required. All libraries already in `backend/requirements.txt`.

## Architecture Patterns

### Recommended Project Structure
```
backend/v2/matching/
    __init__.py              # Already exists (stub)
    tfidf_index.py           # NEW: Weighted TF-IDF index over catalog
    ai_matcher.py            # NEW: Claude Sonnet one-position-per-call matching
    feedback_v2.py           # NEW: V2 feedback store + TF-IDF retrieval
    prompts.py               # NEW: German matching prompt templates
backend/v2/routers/
    feedback_v2.py           # NEW: POST /api/v2/feedback endpoint
    analyze_v2.py            # EXTEND: Add matching trigger after extraction
```

### Pattern 1: Weighted TF-IDF Index with Category Boost
**What:** Build a TF-IDF vectorizer over all 891 products using weighted text representations. Key matching fields (Brandschutzklasse, Schallschutz, Lichtmass, Material, Widerstandsklasse) are repeated/boosted in the text representation to increase their TF-IDF weight.
**When to use:** At startup (cached like CatalogIndex) and for each matching query.
**Example:**
```python
# Source: Pattern from services/semantic_search.py + services/catalog_index.py
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# Boost key fields by repeating them N times in the text representation
FIELD_WEIGHTS = {
    "brandschutzklasse": 4,     # Fire class: highest importance
    "widerstandsklasse": 3,     # RC class: safety-critical
    "schallschutz_db": 3,       # Sound: common filter criterion
    "lichtmass_max": 2,         # Dimensions: must fit
    "material": 2,              # Material: structural match
    "kategorie": 2,             # Category: structural match
}

def _build_weighted_text(row: pd.Series, col_names: list[str]) -> str:
    """Build weighted text for a catalog product row."""
    parts = []
    for col_idx, col_name in enumerate(col_names):
        val = _safe_str(row.iloc[col_idx])
        if not val:
            continue
        normalized_col = col_name.lower().replace(" ", "")
        weight = 1
        for key, w in FIELD_WEIGHTS.items():
            if key in normalized_col:
                weight = w
                break
        parts.extend([f"{col_name}:{val}"] * weight)
    return " ".join(parts)

# Build vectorizer once at startup
vectorizer = TfidfVectorizer(
    analyzer="word",
    token_pattern=r"(?u)\b[a-zA-ZaeoeueAeOeUess0-9]{2,}\b",
    max_features=5000,
    ngram_range=(1, 2),
    sublinear_tf=True,  # Apply log normalization to TF
)
tfidf_matrix = vectorizer.fit_transform(product_texts)

# Query: build text from ExtractedDoorPosition fields
def search(position: ExtractedDoorPosition, top_k: int = 50) -> list[tuple[int, float]]:
    query_text = _build_query_from_position(position)
    query_vec = vectorizer.transform([query_text])
    scores = cosine_similarity(query_vec, tfidf_matrix).flatten()
    # Category boost: multiply score by 1.3 for products in detected category
    # ... apply category_boost ...
    top_indices = scores.argsort()[::-1][:top_k]
    return [(idx, scores[idx]) for idx in top_indices if scores[idx] > 0.01]
```

### Pattern 2: One-Position-Per-Call AI Matching with Structured Output
**What:** Each ExtractedDoorPosition gets its own Claude Sonnet call with 30-50 TF-IDF candidates. The response is parsed directly into MatchResult via messages.parse().
**When to use:** For every position after TF-IDF pre-filtering.
**Example:**
```python
# Source: Established pattern from v2/extraction/pass2_semantic.py
import asyncio
import anthropic
from v2.schemas.matching import MatchResult

async def match_single_position(
    client: anthropic.Anthropic,
    position: ExtractedDoorPosition,
    candidates: list[dict],  # 30-50 candidate products with key fields
    feedback_examples: list[dict],
) -> MatchResult:
    """Match one position against candidates using Claude Sonnet."""
    system_prompt = MATCHING_SYSTEM_PROMPT  # German, domain-specific
    user_content = MATCHING_USER_TEMPLATE.format(
        position_json=position.model_dump_json(exclude_none=True),
        candidates_json=json.dumps(candidates, ensure_ascii=False),
        feedback_examples=_format_feedback(feedback_examples),
    )

    response = await asyncio.to_thread(
        client.messages.parse,
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
        output_format=MatchResult,
    )
    result = response.parsed
    # Apply safety cap: if Brandschutz < 50%, cap gesamt_konfidenz at 60%
    result = _apply_safety_caps(result)
    return result
```

### Pattern 3: Feedback V2 Store with TF-IDF Retrieval
**What:** New feedback store using JSON file (same pattern as v1) but with v2 schema references. Retrieval uses TF-IDF similarity between current requirement text and past correction texts.
**When to use:** When saving corrections (POST /api/v2/feedback) and retrieving relevant examples for matching prompts.
**Example:**
```python
# Source: Pattern from services/feedback_store.py
# Feedback entry structure for v2:
{
    "id": "fb_v2_abc123",
    "positions_nr": "1.01",
    "requirement_summary": "EI30 Rahmentuer 900x2100 Rw32dB",
    "original_match": {
        "produkt_id": "RT-001",
        "gesamt_konfidenz": 0.82,
    },
    "corrected_match": {
        "produkt_id": "RT-005",
        "produkt_name": "Prestige 51 EI30",
    },
    "correction_reason": "Original hatte falsche Fluegel-Anzahl",
    "timestamp": "2026-03-10T14:00:00Z",
}
```

### Anti-Patterns to Avoid
- **Hard category filtering:** Do NOT filter products by category before TF-IDF search. Use category as a boost signal, not a filter. Products may be miscategorized or cross-category requirements exist.
- **Batching multiple positions per AI call:** Decision locked -- one position per call. Cross-contamination between positions degrades match quality.
- **Reusing v1 CatalogIndex directly:** Build new TF-IDF index from scratch. v1 CatalogIndex uses compact_text (~25 tokens) which is too lossy for TF-IDF matching.
- **Sending all 318 columns per candidate to Claude:** Send only ~15-20 matching-relevant fields. Full column set would exceed context limits and add noise.
- **Ignoring safety dimension failures:** If Brandschutz scores below 50%, the match MUST be capped at 60% regardless of other scores. Safety mismatches can never be confirmed matches.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Text vectorization | Custom word frequency counter | `sklearn.feature_extraction.text.TfidfVectorizer` | Handles tokenization, IDF weighting, sparse matrices, German umlauts with proper token_pattern |
| Cosine similarity | Manual dot product | `sklearn.metrics.pairwise.cosine_similarity` | Optimized for sparse matrices, handles batches |
| Structured AI output parsing | JSON.loads + manual validation | `client.messages.parse(output_format=MatchResult)` | Type-safe Pydantic output, handles schema enforcement |
| Fire class hierarchy comparison | String comparison | Port v1's `FIRE_CLASS_RANK` dict + `_normalize_fire_class()` | Handles EI/T/F equivalences, legacy Swiss designations |
| Resistance class comparison | String comparison | Port v1's `RESISTANCE_RANK` dict + `_normalize_resistance()` | Handles RC/WK equivalences |
| Dimension parsing (mm) | Regex on each use | Port v1's `_normalize_dimension()` and `_parse_max_dimensions()` | Handles mm/cm/m conversion, plausibility checks |

**Key insight:** The v1 `fast_matcher.py` contains battle-tested Swiss door domain knowledge (fire class ranks, resistance ranks, category keywords, dimension parsing, product preference scoring) that MUST be ported to v2 rather than reimplemented. These encode real FTAG catalog semantics.

## Common Pitfalls

### Pitfall 1: TF-IDF Token Pattern for German Text
**What goes wrong:** Default TfidfVectorizer token pattern strips umlauts, breaking German terms like "Tuerblatt", "Schallschutz"
**Why it happens:** Default regex is `r"(?u)\b\w\w+\b"` which works but custom patterns might inadvertently exclude German characters
**How to avoid:** Use token pattern `r"(?u)\b[a-zA-ZaeoeueAeOeUess0-9]{2,}\b"` as established in `services/feedback_store.py` and `services/semantic_search.py`
**Warning signs:** Low TF-IDF similarity scores for obvious matches

### Pitfall 2: Catalog Header Row Offset
**What goes wrong:** Loading product catalog with wrong header row, getting column names from data rows
**Why it happens:** FTAG catalog has header at row 6 (0-indexed), not row 0
**How to avoid:** Use `CATALOG_HEADER_ROW = 6` constant from `services/catalog_index.py`. Reuse `_load_catalog_df()` or replicate its logic
**Warning signs:** Column names like "Rahmentüre" instead of "Produktegruppen"

### Pitfall 3: Claude API Token Limits with 50 Candidates
**What goes wrong:** Sending 50 candidates with 20 fields each exceeds reasonable prompt size, leading to truncation or high costs
**Why it happens:** 50 candidates x 20 fields x ~30 chars = ~30,000 chars of candidate data, plus position data and feedback
**How to avoid:** Keep candidate field representation compact. Use key-value format, not full JSON. Monitor token usage. Consider reducing to 30 candidates if prompts exceed ~8000 tokens
**Warning signs:** Response truncation (stop_reason == "max_tokens"), high API costs per position

### Pitfall 4: Safety Cap Not Applied Post-Parse
**What goes wrong:** Claude returns a gesamt_konfidenz of 0.92 but Brandschutz dimension is 0.3 -- without the safety cap, this could appear as a near-confirmed match
**Why it happens:** Claude calculates the average honestly but doesn't know about the business rule
**How to avoid:** Apply safety cap AFTER parsing the MatchResult: if any Brandschutz DimensionScore < 0.5, set gesamt_konfidenz = min(gesamt_konfidenz, 0.6)
**Warning signs:** Confirmed matches with low fire protection scores

### Pitfall 5: Empty/Sparse ExtractedDoorPosition
**What goes wrong:** Some positions have only positions_nr and maybe breite_mm -- TF-IDF query is too sparse to find relevant candidates
**Why it happens:** Tender documents sometimes list positions with minimal details
**How to avoid:** Build query text from all available fields; if fewer than 3 fields are populated, use broader TF-IDF search (lower min_score threshold) and include position description text
**Warning signs:** All candidates scoring near-zero similarity

### Pitfall 6: Async Wrapping of Synchronous Anthropic Client
**What goes wrong:** Using `await client.messages.parse()` directly fails because `messages.parse()` is only available on the synchronous Anthropic client
**Why it happens:** The async Anthropic client may not expose `messages.parse()`
**How to avoid:** Use established pattern: `await asyncio.to_thread(client.messages.parse, ...)` as done in Phase 2
**Warning signs:** AttributeError on AsyncAnthropic client

## Code Examples

### Building Query Text from ExtractedDoorPosition
```python
# Source: Derived from v2/schemas/extraction.py field structure
def _build_query_from_position(pos: ExtractedDoorPosition) -> str:
    """Build TF-IDF query text from an extracted door position."""
    parts = []
    if pos.brandschutz_klasse:
        parts.extend([f"Brandschutz:{pos.brandschutz_klasse.value}"] * 4)
    if pos.brandschutz_freitext:
        parts.append(pos.brandschutz_freitext)
    if pos.schallschutz_db:
        parts.extend([f"Schallschutz:Rw{pos.schallschutz_db}dB"] * 3)
    if pos.schallschutz_klasse:
        parts.append(pos.schallschutz_klasse.value)
    if pos.breite_mm and pos.hoehe_mm:
        parts.extend([f"Masse:{pos.breite_mm}x{pos.hoehe_mm}mm"] * 2)
    if pos.material_blatt:
        parts.extend([f"Material:{pos.material_blatt.value}"] * 2)
    if pos.einbruchschutz_klasse:
        parts.extend([f"Widerstand:{pos.einbruchschutz_klasse}"] * 3)
    if pos.oeffnungsart:
        parts.append(f"Oeffnungsart:{pos.oeffnungsart.value}")
    if pos.anzahl_fluegel:
        parts.append(f"Fluegel:{pos.anzahl_fluegel}")
    if pos.glasausschnitt:
        parts.append("Glasausschnitt:ja")
    if pos.positions_bezeichnung:
        parts.append(pos.positions_bezeichnung)
    if pos.tuerblatt_ausfuehrung:
        parts.append(pos.tuerblatt_ausfuehrung)
    if pos.bemerkungen:
        parts.append(pos.bemerkungen)
    return " ".join(parts) if parts else "Tuer"
```

### Extracting Candidate Fields for Claude Prompt
```python
# Source: Derived from services/catalog_index.py get_product_extended()
MATCHING_FIELDS = [
    "Produktegruppen", "Brandschutzklasse", "VKF.Nr",
    "Lichtmass max. B x H in mm", "Tuerflaece max. in m2",
    "Anzahl Fluegel", "Tuerblatt / Verglasungsart / Rollkasten",
    "Tuerblattausfuehrung", "Glasausschnitt",
    "Tuerrohling (dB)", "Widerstandsklasse",
    "Bleigleichwert (2mm)", "VKF.Nr / Klasse S200",
    "Umfassung Materialisierung",
    "Giessharzbeschichtung Orsopal", "Oberflaechenfolie Senosan",
]

def extract_candidate_fields(df: pd.DataFrame, row_idx: int) -> dict:
    """Extract matching-relevant fields for a catalog product."""
    row = df.iloc[row_idx]
    fields = {"row_index": row_idx}
    for col in MATCHING_FIELDS:
        if col in df.columns:
            val = row.get(col)
            if pd.notna(val) and str(val).strip() not in ("", "-", "nan"):
                fields[col] = str(val).strip()
    # Add Kostentraeger as product ID
    if "Kostentraeger" in df.columns:
        kt = row.get("Kostentraeger")
        if pd.notna(kt):
            fields["Kostentraeger"] = str(kt).strip()
    return fields
```

### Domain Knowledge to Port from V1
```python
# Source: services/fast_matcher.py -- MUST be ported to v2
# Fire class hierarchy (higher fulfills lower)
FIRE_CLASS_RANK = {
    "ohne": 0, "keine": 0, "": 0,
    "ei30": 1, "t30": 1, "f30": 1,
    "ei60": 2, "t60": 2, "f60": 2,
    "ei90": 3, "t90": 3, "f90": 3,
    "ei120": 4, "t120": 4, "f120": 4,
}

RESISTANCE_RANK = {
    "": 0, "ohne": 0, "keine": 0,
    "rc1": 1, "wk1": 1,
    "rc2": 2, "wk2": 2,
    "rc3": 3, "wk3": 3,
    "rc4": 4, "wk4": 4,
}

# Category detection keywords (proven with FTAG data)
CATEGORY_KEYWORDS = {
    "Rahmentuere": ["rahmen", "fluegel", "innentuer", "standardtuer"],
    "Zargentuere": ["zargen"],
    "Futtertuere": ["futter"],
    "Schiebetuere": ["schiebe", "sliding"],
    "Brandschutztor": ["tor", "sektional", "schnelllauf", "rolltor"],
    "Brandschutzvorhang": ["vorhang", "rollkasten"],
    "Festverglasung": ["festverglas"],
    "Ganzglas Tuer": ["ganzglas", "glastuer"],
    "Pendeltuere": ["pendel"],
    "Vollwand": ["vollwand", "trennwand"],
    "Steigzonen/Elektrofronten": ["steigzone", "elektrofront", "revision"],
}
```

## State of the Art

| Old Approach (v1) | Current Approach (v2 Phase 4) | Impact |
|---|---|---|
| Category-first filtering, then rule-based scoring | TF-IDF all-products search with category boost | Eliminates category misclassification as failure mode |
| Single overall score (0-100) | 6-dimension breakdown (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung) | Transparency into why matches fail/succeed |
| Rule-based scoring only (no AI) | TF-IDF pre-filter + Claude Sonnet AI evaluation | Better semantic understanding of requirements |
| 60% threshold for "matched" | 95% threshold for "confirmed" | Higher quality bar, more goes to adversarial validation |
| v1 feedback with keyword matching | v2 feedback with TF-IDF similarity retrieval | More relevant few-shot examples |

## Open Questions

1. **Optimal number of feedback examples per call**
   - What we know: More examples = better few-shot learning, but increases prompt size and cost
   - What's unclear: Sweet spot between 3-8 examples given ~30-50 candidates already in prompt
   - Recommendation: Start with 5 most similar, measure token usage, adjust. Cap at 8 based on v1 pattern (find_relevant_feedback limit=8)

2. **Handling ZZ accessory products in matching**
   - What we know: Catalog has main products + ZZ (Schloss, Glas, Schliessblech) accessories. Phase 4 scope focuses on main product matching
   - What's unclear: Whether requirements reference accessories directly
   - Recommendation: Match main products only in Phase 4. Accessories are a Phase 6/7 concern for complete offer generation

3. **Concurrency for multiple position matching**
   - What we know: Each position = separate Claude API call. 20 positions = 20 API calls
   - What's unclear: Rate limiting behavior with concurrent asyncio.to_thread calls
   - Recommendation: Use asyncio.Semaphore(5) to limit concurrent API calls, matching the pattern established in Phase 2

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 7.4.4 + pytest-asyncio 0.23.3 |
| Config file | Backend uses pytest discovery from `backend/tests/` |
| Quick run command | `cd backend && python -m pytest tests/test_v2_matching.py -x` |
| Full suite command | `cd backend && python -m pytest tests/ -x --timeout=60` |

### Phase Requirements to Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MATC-01 | Every position matched against catalog | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_tfidf_returns_candidates -x` | No -- Wave 0 |
| MATC-02 | Multi-dimensional scoring (6 dimensions) | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_dimension_scores_all_present -x` | No -- Wave 0 |
| MATC-03 | Confidence 0-100% with dimension breakdown | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_confidence_calculation -x` | No -- Wave 0 |
| MATC-04 | 95%+ threshold for confirmed match | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_threshold_95_confirmed -x` | No -- Wave 0 |
| MATC-09 | Feedback injected as few-shot examples | unit | `cd backend && python -m pytest tests/test_v2_matching.py::test_feedback_injection -x` | No -- Wave 0 |
| APII-06 | POST /api/v2/feedback saves corrections | integration | `cd backend && python -m pytest tests/test_v2_matching.py::test_feedback_endpoint -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `cd backend && python -m pytest tests/test_v2_matching.py -x`
- **Per wave merge:** `cd backend && python -m pytest tests/ -x --timeout=60`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `backend/tests/test_v2_matching.py` -- covers MATC-01 through MATC-04, MATC-09, APII-06
- [ ] Fixtures: sample ExtractedDoorPosition objects (reuse from conftest_v2.py), mock catalog DataFrame, mock Anthropic client
- [ ] No new framework install needed -- pytest + pytest-asyncio already in requirements.txt

## Sources

### Primary (HIGH confidence)
- `backend/v2/schemas/matching.py` -- MatchResult, MatchCandidate, DimensionScore schemas already defined
- `backend/v2/schemas/extraction.py` -- ExtractedDoorPosition (55 fields) input schema
- `backend/services/catalog_index.py` -- Catalog loading pattern, CATALOG_HEADER_ROW=6, ProductProfile structure
- `backend/services/fast_matcher.py` -- FIRE_CLASS_RANK, RESISTANCE_RANK, CATEGORY_KEYWORDS, dimension parsing utilities
- `backend/services/feedback_store.py` -- Feedback store pattern, find_relevant_feedback(), TF-IDF similarity usage
- `backend/services/semantic_search.py` -- TfidfVectorizer configuration, German token pattern, synonym dictionaries
- `backend/v2/extraction/pass2_semantic.py` -- messages.parse() + asyncio.to_thread pattern
- `backend/requirements.txt` -- scikit-learn>=1.6.0, anthropic>=0.49.0 confirmed

### Secondary (MEDIUM confidence)
- scikit-learn TfidfVectorizer API -- well-known, stable API; confirmed by existing usage in codebase

### Tertiary (LOW confidence)
- None -- all findings verified against existing codebase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all libraries already in requirements.txt and used in codebase
- Architecture: HIGH -- patterns established in Phases 1-3, schemas already defined
- Pitfalls: HIGH -- derived from actual v1 code and existing v2 patterns

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (stable domain, no external API changes expected)
