# Retrospective

## Milestone: v1.0 — KI-Angebotserstellung v2 Pipeline

**Shipped:** 2026-03-10
**Phases:** 9 | **Plans:** 21

### What Was Built
- Multi-format document parsing (PDF/DOCX/XLSX) with Pydantic pipeline schemas
- 3-pass extraction (structural + AI semantic + cross-reference validation) with deduplication
- Cross-document intelligence with enrichment and AI conflict resolution
- TF-IDF + Claude AI product matching against 891-product catalog (6 dimensions)
- Adversarial FOR/AGAINST debate with triple-check ensemble
- Categorized gap analysis with severity ratings and alternative suggestions
- Professional 4-sheet Excel output with color coding and chain-of-thought reasoning
- End-to-end pipeline with plausibility checks, SSE streaming, and React frontend

### What Worked
- Phase-by-phase approach allowed verifiable incremental progress
- Pydantic schemas defined upfront (Phase 1) prevented integration issues later
- Adversarial validation architecture caught real false positives
- German-language prompts matched domain language, improving extraction quality
- Safety-critical dimension weighting (Brandschutz 2x) prevented dangerous false confirms
- TF-IDF pre-filter kept API costs manageable while maintaining recall

### What Was Inefficient
- Phase 9 (frontend wiring) was essentially gap closure for v1.0 audit — should have been planned from the start
- Phase 3 human verification items remain pending (need live API key testing)
- SSE cross-thread issue discovered late in integration — caught by audit, not by phase verification
- ROADMAP.md plan checkboxes not consistently updated by executors (cosmetic issue)

### Patterns Established
- Enum+Freitext pattern for all domain classifications
- Safety cap pipeline: apply_safety_caps → set_hat_match → limit_alternatives
- Three-track processing: bestaetigt (filtered), unsicher (full), abgelehnt (text only)
- Deterministic resolution via weighted average instead of additional AI calls
- Lazy try/except imports for optional dependencies (graceful degradation)
- 500ms progress throttle to prevent SSE flooding

### Key Lessons
- Define frontend wiring as explicit phase in initial roadmap (not gap closure)
- asyncio.Queue is not thread-safe for cross-thread communication — use loop.call_soon_threadsafe
- messages.parse() structured output eliminates manual JSON parsing but requires Pydantic v2 compatibility
- TF-IDF top_k=50 is sufficient for 891-product catalog; top_k=80 for triple-check wider pool

### Cost Observations
- Model mix: Opus for adversarial debate only, Sonnet for all other AI calls
- Sessions: 9 execution sessions + 2 gap closure + 1 audit
- Notable: Deterministic adversarial resolution saved ~33% on Opus calls vs. third-call approach

---

## Cross-Milestone Trends

| Metric | v1.0 |
|--------|------|
| Phases | 9 |
| Plans | 21 |
| Timeline | 8 days |
| Requirements | 38/38 |
| Gap closures | 2 phases (03, 08) |
| Audit status | tech_debt |
