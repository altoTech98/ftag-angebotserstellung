# Phase 6: Gap Analysis - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Every position (bestaetigt, unsicher, abgelehnt) gets a gap analysis report identifying specification deviations between tender requirements and matched/closest products. Gaps are categorized by dimension with severity ratings, accompanied by actionable suggestions for the sales team and alternative product proposals. The Excel output of gap reports is Phase 7.

</domain>

<decisions>
## Implementation Decisions

### Gap Trigger Scope
- ALL positions get gap analysis — bestaetigt, unsicher, AND abgelehnt
- For bestaetigt positions: report gaps for any dimension scoring below 100% (all non-perfect dimensions)
- For unsicher positions: full gap report against best-effort match
- For abgelehnt positions: text summary only (no per-dimension breakdown against a product since no viable match exists)
- Dedicated AI call (Claude Opus) per position for gap identification — not derived from existing adversarial data
- Phase 5 per-dimension CoT passed as input context to the gap analysis call

### Dimension Mapping
- Expand GapDimension enum to 6+ dimensions: Masse, Brandschutz, Schallschutz, Material, Zertifizierung, Leistung (1:1 with Phase 4 matching dimensions)
- Update existing GapDimension enum in schemas/gaps.py
- Safety dimensions auto-escalate severity: Brandschutz gap = always Kritisch or Major (never Minor), consistent with Phase 4's safety cap logic
- Every gap includes side-by-side values: anforderung_wert (required) vs katalog_wert (catalog) — always shown, for both quantitative and qualitative fields
- Each GapItem links to which AlternativeProduct(s) could close it via a 'gap_geschlossen_durch' cross-reference field

### Alternative Search Strategy
- Fresh TF-IDF search weighted toward gap dimensions (e.g., if Brandschutz is the gap, boost Brandschutz fields in search). Uses existing CatalogTfidfIndex
- Up to 3 alternative products per position, ranked by gap coverage
- Each alternative shows per-gap breakdown: which gaps it closes and which remain (verbleibende_gaps)
- For abgelehnt positions: search for alternatives but only include those with >30% gap coverage (filter out noise)
- For bestaetigt/unsicher: alternatives that specifically close the identified gaps

### Suggestion Specificity
- Two suggestion types per gap: sales-oriented (Kundenvorschlag) AND technical (Technischer Hinweis)
- Sales suggestions: actionable for offer creation (e.g., "Kunde verlangt EI90, nächstes FTAG-Produkt ist EI60. Vorschlag: Kunde fragen ob EI60 mit Brandschutzverkleidung akzeptabel")
- Technical suggestions: engineering insights (e.g., "Produkt X könnte mit Y-Material modifiziert werden")
- All suggestions in German (consistent with all prompts and domain vocabulary)
- zusammenfassung per position: full paragraph covering all gaps, alternatives, and suggestions

### Claude's Discretion
- Exact prompt design for gap analysis Opus calls (German, domain-specific)
- Concurrency strategy (Semaphore limit for Opus calls)
- How to weight TF-IDF fields for gap-focused alternative search
- Internal GapItem cross-reference structure for gap_geschlossen_durch
- How to handle positions with no extractable fields for comparison

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/v2/schemas/gaps.py`: GapSeverity, GapDimension, GapItem, AlternativeProduct, GapReport already defined — need expansion (dimensions, cross-reference field, suggestion types)
- `backend/v2/gaps/__init__.py`: Empty module ready for implementation
- `backend/v2/schemas/adversarial.py`: AdversarialResult with per-dimension CoT (DimensionCoT) — input to gap analysis
- `backend/v2/schemas/matching.py`: MatchResult, MatchCandidate, DimensionScore — input data
- `backend/v2/matching/tfidf_index.py`: CatalogTfidfIndex.search() — reusable for gap-focused alternative search
- `backend/v2/matching/domain_knowledge.py`: FIRE_CLASS_RANK, RESISTANCE_RANK — domain knowledge for severity assessment

### Established Patterns
- `messages.parse()` with Pydantic v2 for structured AI outputs (all phases)
- `asyncio.to_thread` wrapping sync Anthropic calls (Phase 2+4+5)
- German prompts matching domain language (all phases)
- Safety-critical dimension weighting (Phase 4: Brandschutz cap, Phase 5: safety weights)
- Lazy imports with _AVAILABLE guard for graceful degradation (Phase 4+5 pattern in analyze_v2.py)

### Integration Points
- `backend/v2/gaps/` — new modules: gap_analyzer.py, gap_prompts.py
- `backend/v2/schemas/gaps.py` — expand existing schemas (add dimensions, cross-reference, suggestion types)
- `backend/v2/routers/analyze_v2.py` — extend to run gap analysis after adversarial validation
- Phase 5 AdversarialResult + Phase 4 MatchResult (input) -> Phase 6 GapReport (output) is the core transformation

</code_context>

<specifics>
## Specific Ideas

- Phase 5's AdversarialResult already has per-dimension CoT with scores — gap analysis should leverage this as context, not re-derive it
- Safety dimension auto-escalation mirrors Phase 4's Brandschutz safety cap pattern (< 50% -> max 60%)
- Sales team creates offers directly from gap reports — suggestions must be concrete enough to copy into customer communication
- Gap-focused TF-IDF search should use the same CatalogTfidfIndex but with dynamically adjusted field weights based on which dimensions have gaps

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-gap-analysis*
*Context gathered: 2026-03-10*
