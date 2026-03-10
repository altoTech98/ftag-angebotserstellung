# Phase 5: Adversarial Validation - Context

**Gathered:** 2026-03-10
**Status:** Ready for planning

<domain>
## Phase Boundary

Every product match from Phase 4 is challenged by an independent adversarial AI pass using a debate format (FOR/AGAINST arguments), with transparent chain-of-thought reasoning for all decisions. Matches that fail adversarial review trigger a triple-check ensemble. All candidates are listed with individual scores and reasoning.

</domain>

<decisions>
## Implementation Decisions

### Adversarial Pass Strategy
- Debate format: two separate Opus API calls per position — one argues FOR the match, one argues AGAINST
- A third lightweight resolution step determines the final verdict with adjusted confidence
- Input: same candidates + Phase 4 match result (no fresh TF-IDF search)
- Scope: ALL positions go through adversarial validation (per MATC-05: "every match")
- Model: Claude Opus for both FOR and AGAINST calls
- Full adversarial debate on best match AND up to 3 alternatives — each candidate gets its own FOR/AGAINST reasoning (per MATC-08)

### Triple-Check Trigger & Approach
- Trigger: post-adversarial confidence drops below 95%
- Strategy: ensemble of BOTH approaches — wider candidate pool (top 80 instead of 30-50 via relaxed TF-IDF) AND inverted prompt (requirement-centric instead of product-centric)
- Model: Opus for both ensemble passes
- Take the higher-confidence result from the two approaches
- If still below 95% after triple-check: flag as 'unsicher' (uncertain match), keep best match found across all passes, include all reasoning from all passes — goes to gap analysis in Phase 6

### Chain-of-Thought Presentation
- Language: German (consistent with all prompts and domain vocabulary)
- Structure: per-dimension reasoning step + final summary synthesis
- Verbosity: adaptive — brief (1 sentence) for high-confidence dimensions (>90%), detailed (2-3 sentences) for low-confidence or mismatched dimensions
- Adversarial debate reasoning (FOR/AGAINST arguments) fully stored and visible in output — maximum transparency per MATC-07

### Schema & Pipeline Wiring
- Separate AdversarialResult schema linked to MatchResult by positions_nr (MatchResult stays untouched)
- AdversarialResult contains: debate arguments (FOR/AGAINST), per-dimension CoT, final verdict, adjusted confidence, validation_status
- Pipeline position: inline after Phase 4 matching in analyze endpoint — single call returns fully validated results
- Concurrency: asyncio.Semaphore pattern (like Phase 4) for parallel Opus calls across positions

### Claude's Discretion
- Exact prompt design for FOR/AGAINST debate calls
- Resolution logic for combining FOR/AGAINST into final verdict
- Semaphore limit for Opus calls (likely lower than Phase 4's 5 due to Opus rate limits)
- Exact TF-IDF relaxation parameters for wider-pool triple-check
- Internal data structures for AdversarialResult schema
- How to structure the inverted (requirement-centric) prompt for triple-check

</decisions>

<code_context>
## Existing Code Insights

### Reusable Assets
- `backend/v2/matching/ai_matcher.py`: match_single_position + match_positions with asyncio.Semaphore(5) pattern — same concurrent pattern for adversarial calls
- `backend/v2/matching/prompts.py`: MATCHING_SYSTEM_PROMPT + MATCHING_USER_TEMPLATE — base for adversarial prompt design
- `backend/v2/schemas/matching.py`: MatchResult, MatchCandidate, DimensionScore, MatchDimension — Phase 4 output that feeds adversarial input
- `backend/v2/matching/tfidf_index.py`: CatalogTfidfIndex.search() — reuse for wider-pool triple-check with relaxed top_n
- `backend/v2/matching/domain_knowledge.py`: FIRE_CLASS_RANK, RESISTANCE_RANK — domain knowledge for adversarial reasoning

### Established Patterns
- `messages.parse()` with Pydantic v2 for structured AI outputs (Phases 1-4)
- `asyncio.to_thread` wrapping sync Anthropic calls (Phase 2+4)
- German prompts matching domain language (all phases)
- Safety cap pipeline: apply_safety_caps -> set_hat_match -> limit_alternatives (Phase 4)

### Integration Points
- `backend/v2/matching/` — new modules: adversarial.py, adversarial_prompts.py
- `backend/v2/schemas/` — new: adversarial.py (AdversarialResult schema)
- `backend/v2/routers/analyze_v2.py` — extend to run adversarial after matching, before returning results
- Phase 4 MatchResult (input) -> Phase 5 AdversarialResult (output) is the core transformation

</code_context>

<specifics>
## Specific Ideas

- Adversarial debate is expensive: 2 Opus calls per position for main debate + potentially 2 more for triple-check ensemble — design for cost visibility (log API call counts)
- Phase 4's Brandschutz safety cap (< 50% -> max 60%) still applies before adversarial — adversarial validates the post-cap result
- The FOR argument should reference specific catalog fields; the AGAINST should actively look for specification mismatches, overlooked candidates, and dimensional gaps
- 'unsicher' flag should be distinct from 'kein_match' — it means "best effort match exists but couldn't confirm at 95%"

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 05-adversarial-validation*
*Context gathered: 2026-03-10*
