# Phase 4: Product Matching Engine - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Every extracted requirement (ExtractedDoorPosition from Phase 2/3) is matched against the FTAG product catalog (~891 products) using TF-IDF pre-filtering followed by AI evaluation with Claude Sonnet. Each match includes multi-dimensional confidence scoring (6 dimensions) and learning from past corrections via feedback integration. The adversarial double-check is Phase 5.

</domain>

<decisions>
## Implementation Decisions

### TF-IDF Pre-filter Strategy
- Rebuild TF-IDF index from scratch using all 318 catalog columns (not reusing v1 CatalogIndex)
- Weighted field indexing: boost key matching fields (Brandschutzklasse, Schallschutz, Lichtmass, Material, Widerstandsklasse) over administrative columns
- Return top 30-50 candidates per requirement
- Category detection runs in parallel: TF-IDF searches all 891 products but boosts score for products in the detected door category (Rahmentüre, Schiebetüre, etc.) — wider search with category signal, no hard category filtering

### AI Matching Approach
- One position per AI call — each requirement gets its own Claude call with its 30-50 candidates. Maximum focus, no cross-contamination between positions
- Model: Claude Sonnet for Phase 4 matching (Opus reserved for Phase 5 adversarial)
- Full relevant fields per candidate: send all matching-relevant fields (~15-20 fields: Brandschutz, Schallschutz, Masse, Material, Zertifizierung, Leistung) per candidate product
- Structured output via messages.parse() returning MatchResult Pydantic model directly — type-safe, no post-processing. Consistent with Phase 2 pattern
- asyncio.to_thread wrapping for async compat (established pattern)

### Confidence Scoring
- Equal weight average across all 6 dimensions (Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung)
- Hard fail on safety dimensions: if Brandschutz scores below 50%, cap gesamt_konfidenz at max 60% regardless of other scores. Safety mismatch = never a confirmed match
- 95%+ = confirmed match, below 95% = flagged for Phase 5 adversarial validation or gap analysis
- Return best match + up to 3 alternative matches, all with full dimension breakdown and reasoning

### Feedback Integration
- Few-shot examples injected into matching prompt: past corrections included as "For requirement X, correct product was Y (not Z)"
- Feedback selection: TF-IDF similarity between current requirement and past corrections — reuses same TF-IDF infrastructure
- Number of feedback examples per call: Claude's discretion (balance prompt size budget and relevance scores)
- New v2 feedback store in backend/v2/ with v2 schemas (MatchResult references) — not reusing v1 feedback_store.py
- POST /api/v2/feedback endpoint for saving corrections

### Claude's Discretion
- Exact TF-IDF field weights and boosting factors
- Prompt design for matching (German, domain-specific)
- Feedback example count per call (balancing relevance vs prompt size)
- Internal data structures for the new TF-IDF index
- Retry/error handling strategy for individual matching calls
- How to handle requirements with very few extracted fields

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/v2/schemas/matching.py`: MatchResult, MatchCandidate, DimensionScore, MatchDimension already defined — ready for messages.parse()
- `backend/v2/schemas/extraction.py`: ExtractedDoorPosition (55 fields) — input to matching
- `backend/services/catalog_index.py`: CatalogIndex/ProductProfile pattern as reference (not reusing directly, but architecture inspiration)
- `backend/services/fast_matcher.py`: FIRE_CLASS_RANK, RESISTANCE_RANK hierarchies, CATEGORY_KEYWORDS — domain knowledge to port
- `backend/services/feedback_store.py`: find_relevant_feedback() pattern as reference for v2 feedback selection

### Established Patterns
- `messages.parse()` with Pydantic v2 for structured AI outputs (Phase 1+2)
- `asyncio.to_thread` wrapping sync Anthropic calls (Phase 2)
- German prompts matching domain language (Phase 2)
- v2 code lives in `backend/v2/` with own exception hierarchy

### Integration Points
- `backend/v2/matching/` — new modules: tfidf_index.py, ai_matcher.py, feedback_v2.py
- `backend/v2/routers/` — extend analyze_v2 to trigger matching after extraction, or new matching endpoint
- ExtractedDoorPosition (Phase 2/3 output) → MatchResult (Phase 4 output) is the core transformation
- Product catalog (`data/produktuebersicht.xlsx`) loaded and indexed at startup

</code_context>

<specifics>
## Specific Ideas

- Product catalog has ~318 columns and ~891 products — TF-IDF must handle this scale with smart field weighting
- v1's FIRE_CLASS_RANK and RESISTANCE_RANK hierarchies encode real Swiss door domain knowledge — must be ported to v2
- Category detection keywords from v1 (CATEGORY_KEYWORDS) are proven with real FTAG data — use as starting point for category boost
- Matching prompts should be in German to match domain vocabulary in catalog and requirements

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 04-product-matching-engine*
*Context gathered: 2026-03-10*
