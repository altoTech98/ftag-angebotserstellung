# Project Research Summary

**Project:** FTAG KI-Angebotserstellung v2 (Multi-Pass Validation)
**Domain:** AI-powered construction tender analysis with product catalog matching (door industry, Swiss/German market)
**Researched:** 2026-03-10
**Confidence:** HIGH

## Executive Summary

This project upgrades an existing AI-assisted offer-creation tool for Frank Türen AG from a single-pass extraction system to a multi-pass validation pipeline. The v1 system proved the concept but had a critical flaw: single-pass document parsing missed 10-30% of door positions, which directly translates to lost revenue and compliance failures in the construction tendering context. The v2 approach resolves this by introducing a two-stage extraction (structural column parsing + Claude AI semantic pass), followed by AI product matching with an adversarial double-check pass and optional triple-check for low-confidence results. The entire system already exists in skeleton form; v2 is a focused upgrade of the AI pipeline and output format, not a rewrite.

The recommended implementation keeps the existing FastAPI + Python stack with targeted dependency upgrades: `anthropic` SDK from 0.49 to 0.84+ to unlock grammar-enforced structured outputs via `messages.parse()`, and `pymupdf4llm` from 0.0.17 to 0.3.4 for improved table detection in construction tender PDFs. The core architectural pattern is Pydantic-first: every Claude API call returns a validated Pydantic model, eliminating JSON parsing failures and retry logic. Batching 5-10 requirements per API call reduces the 500-position worst case from 500 sequential calls to 50-100 batched calls, cutting analysis time from over 16 minutes to 2-4 minutes.

The key risks are concentrated in two areas: (1) structured output schema design — making fields too rigid forces Claude to hallucinate values when source documents don't contain the information, so all extraction fields except `position` and `beschreibung` must be Optional; and (2) adversarial pass calibration — the second AI call that challenges matches must be tuned against known v1 data to hit a 15-30% rejection rate, otherwise it either rubber-stamps everything or blocks the pipeline entirely. Both risks are addressable through prompt engineering and empirical validation against existing v1 output data before deploying to production.

## Key Findings

### Recommended Stack

The v1 tech stack is sound and requires only targeted upgrades. The core runtime (Python 3.12+, FastAPI, uvicorn, Pydantic 2.x) stays unchanged. The critical upgrade is `anthropic>=0.84.0`, which enables `messages.parse()` — grammar-enforced structured outputs that make the model physically unable to produce invalid JSON. This eliminates the retry/parsing failure class of bugs that affected v1 AI calls. `pymupdf4llm>=0.3.4` provides materially better table detection for the construction tender PDFs that dominate the input format. For pre-filtering 891 catalog products to ~25 candidates before AI matching, `scikit-learn` TF-IDF is fast, sufficient, and already in the codebase. Technologies to explicitly avoid: LangChain/LlamaIndex (unnecessary abstraction for a 891-product catalog), sentence-transformers (GPU overhead, TF-IDF sufficient at current catalog size), Celery+Redis (overkill for 1-5 tenders/day), and Ollama (explicitly out of scope — Claude-only per project constraints).

**Core technologies:**
- `anthropic>=0.84.0`: Claude API SDK — `messages.parse()` provides grammar-enforced Pydantic output, eliminates parsing failures
- `pymupdf4llm>=0.3.4`: PDF-to-Markdown — major table detection improvement critical for construction tender formats
- `pdfplumber>=0.11.9`: Table extraction fallback — best-in-class geometry-based table detection for edge cases
- `scikit-learn>=1.6.0`: TF-IDF pre-filter — narrows 891 products to ~25 candidates per requirement before AI matching
- `openpyxl==3.1.5`: Excel read + write — dual-purpose: reads product catalog AND generates 4-sheet output
- `sse-starlette>=2.0.0`: SSE streaming — real-time progress during 2-10 minute analyses
- `Claude Sonnet 4.6`: Primary model — extraction and initial matching passes (price/performance)
- `Claude Opus 4.6`: Adversarial validator only — higher reasoning for the challenge pass; cost irrelevant per project constraints

### Expected Features

The feature set has a clear three-tier structure. Foundation features address v1's critical weaknesses (missed positions, opaque matches). Validation layer features are the v2 differentiator (adversarial AI checking). Polish features complete the user experience but are not blocking.

**Must have (table stakes):**
- Multi-pass document analysis (minimum 2 passes: structural + AI semantic) — this is the core v1 fix; single-pass misses 10-30% of positions
- Complete requirement extraction with zero missed positions — one missed door position = lost revenue or compliance failure
- Multi-dimensional product matching with explicit confidence scores (0-100%) — sales team cannot trust opaque AI decisions
- Match traceability (chain-of-thought reasoning per match) — exported to Excel "Hinweise" column; audit trail for compliance
- Categorized gap analysis (Masse/Material/Norm/Zertifizierung/Leistung) — sales team needs to know exactly WHY a product fails
- 4-sheet Excel output (Overview, Details, Gap Analysis, Executive Summary) — replaces existing 2-sheet format
- SSE real-time progress streaming — analyses take 2-10 minutes, users abandon without progress feedback

**Should have (competitive differentiators):**
- Adversarial double-check (second Claude Opus call that actively tries to disprove each match) — the primary v2 innovation, reduces false positives by an estimated 15-30%
- Triple-check for low-confidence (<95%) matches — majority voting between three AI perspectives
- Gap severity categorization (Critical/Major/Minor) — "no fire-rated product exists" vs "5mm too narrow" require different escalation paths
- Alternative product suggestions for gaps — "Product X matches except fire rating is EI30 instead of required EI60"
- Cross-document enrichment — merge specs from multiple files (Excel door list + PDF spec + Word requirements) into unified position data
- Plausibility check — post-analysis sanity check (all positions accounted for, no suspicious duplicates, no anomalous match patterns)

**Defer indefinitely:**
- Embedding-based semantic search — TF-IDF sufficient at 891 products; revisit at 10K+
- Frontend redesign — minimal React frontend is acceptable per project scope; no dashboards or charts
- Automatic pricing — too much implicit business logic; wrong prices create legal liability
- User authentication — out of scope per PROJECT.md; internal team only
- Local LLM / Ollama fallback — explicitly out of scope; Claude-only

### Architecture Approach

The recommended architecture is a linear pipeline with 8 discrete stages, each consuming and producing typed Pydantic models. A coordinator class (`AnalysisPipeline`) orchestrates stages and emits SSE progress events at each boundary. This replaces the v1 monolithic analysis function and makes each stage independently testable. Matching is parallelizable at the requirement level (each requirement matched independently via batched calls); extraction must be sequential to enable cross-document enrichment. The key insight driving component design is that Pydantic models serve dual duty as data contracts between pipeline stages AND as Claude output schemas via `messages.parse()`, so investing in good schema design early pays dividends throughout.

**Major components:**
1. `services/extraction_engine.py` (NEW) — Multi-pass extraction: structural column parsing + AI semantic pass + deduplication/normalization; produces `list[ExtractedRequirement]`
2. `services/matching_pipeline.py` (NEW) — Orchestrates TF-IDF pre-filter + AI matching + adversarial validation + triple-check; produces `list[MatchResult]`
3. `services/gap_analyzer.py` (NEW) — Categorizes gaps by dimension and severity; generates alternative product suggestions; produces `list[GapReport]`
4. `services/plausibility_checker.py` (NEW) — Post-analysis validation: duplicate detection, coverage check, statistical anomaly detection
5. `services/ai_service.py` (ENHANCED) — All Claude API calls via `messages.parse()` with Pydantic models; token tracking; exponential backoff
6. `services/result_generator.py` (ENHANCED) — 4-sheet Excel generation with color-coding, reasoning column, style object reuse

### Critical Pitfalls

1. **Context window overflow on large tenders** — stuffing all 891 products + all requirements into one prompt causes API errors and silent data loss. Prevention: TF-IDF pre-filter to ~25 candidates per requirement built into the pipeline from day 1; batch 5-10 requirements per call; monitor `input_tokens` per call and alert if >150K.

2. **Adversarial pass miscalibration** — too lenient and it rubber-stamps everything (useless); too strict and it blocks the entire pipeline. Prevention: calibrate against 20-30 known v1 matches before deploying; target 15-30% rejection rate; track `adversarial_rejection_rate` as a monitored metric and alert if <5% or >50%.

3. **Structured output schema forcing hallucination** — grammar-enforced output means Claude MUST fill every required field; if the document doesn't contain the information, Claude invents plausible-looking values (e.g., fabricating fire ratings). Prevention: all extraction fields except `position` and `beschreibung` must be `Optional`; add `confidence_per_field: dict[str, float]` to track per-field uncertainty; cross-check extracted values against source text.

4. **Deduplication failures in multi-pass extraction** — "T1.01", "Tuer 1.01", "Position 1.01" all refer to the same door; treated as duplicates they inflate match counts and confuse the sales team. Prevention: robust position number normalization (strip prefixes, normalize separators, compare numeric components); flag requirement pairs with >80% text similarity for review.

5. **Excel memory blow-up for large tenders** — openpyxl stores each cell style as a separate object; 500 rows x 54 cols x 4 sheets = 108K styled cells, potentially 500MB+ RAM. Prevention: create style objects once and reuse across cells; use `write_only` mode for data-heavy sheets; log a warning at 1000 positions.

## Implications for Roadmap

The feature dependency graph from FEATURES.md mandates a strict ordering: extraction must precede matching, matching must precede gap analysis, and gap analysis must precede Excel generation. The adversarial validation integrates into the matching stage rather than being a separate downstream step. This maps cleanly to 4 phases.

### Phase 1: Pydantic Foundation + Multi-Pass Extraction

**Rationale:** Pydantic models are the contracts between ALL pipeline stages. Defining them first prevents rework when later stages reveal schema inadequacies. Multi-pass extraction is v1's most critical weakness and the prerequisite for all downstream features — you cannot match what you did not extract.
**Delivers:** Complete, deduplicated requirement lists from multi-format documents (PDF, XLSX, DOCX); all Pydantic schemas for the entire pipeline; `extraction_engine.py` with structural + AI semantic passes; position normalization and deduplication logic
**Addresses:** Complete requirement extraction (table stakes), structured requirement model (prerequisite for all other phases)
**Avoids:** Schema rigidity pitfall (design with Optional fields from the start); deduplication failures (normalization built in during extraction, not patched later)
**Needs research:** No — patterns are well-documented and partially implemented in v1. No additional research phase needed.

### Phase 2: Product Matching Pipeline + Adversarial Validation

**Rationale:** Matching is the core value proposition. The adversarial double-check must be integrated into the matching pipeline (not added afterward) because its revised confidence scores feed into gap severity categorization in Phase 3. Building matching and adversarial validation together avoids a rework cycle.
**Delivers:** TF-IDF pre-filter reducing 891 products to ~25 candidates; AI matching with multi-dimensional confidence scores; adversarial Claude Opus pass challenging all matches; triple-check for <95% confidence results; `matching_pipeline.py` with full validation chain
**Uses:** `anthropic>=0.84.0` `messages.parse()` for both matching and adversarial calls; `scikit-learn` TF-IDF; `MatchResult` and `AdversarialResult` Pydantic models from Phase 1
**Implements:** `matching_pipeline.py` (new); enhanced `ai_service.py`; adversarial validation with `AdversarialResult` Pydantic model
**Avoids:** Context overflow (TF-IDF pre-filter is a gate, not an optimization); adversarial miscalibration (calibration sprint against v1 data is the first task of this phase, before implementation)
**Needs research:** Adversarial prompt calibration strategy — requires empirical testing against real v1 match data before the main implementation begins. Recommend a dedicated calibration sub-task at phase start.

### Phase 3: Gap Analysis + 4-Sheet Excel Output

**Rationale:** Gap analysis consumes validated match results with finalized confidence scores from Phase 2. The 4-sheet Excel is the final deliverable and depends on requirements (Phase 1), matches (Phase 2), and gaps (Phase 3). Building the output format before all inputs are stable causes rework.
**Delivers:** Categorized gap analysis (Masse/Material/Norm/Zertifizierung/Leistung dimensions); gap severity ratings (Critical/Major/Minor); alternative product suggestions for each gap; 4-sheet Excel with color-coding (green/yellow/red), reasoning column, and executive summary sheet; `gap_analyzer.py` (new); enhanced `result_generator.py`
**Addresses:** Gap analysis (table stakes), 4-sheet output (table stakes), gap severity categorization (differentiator), alternative product suggestions (differentiator)
**Avoids:** Excel memory blow-up (style object reuse and write_only mode implemented from the start, not added as an optimization after OOM)
**Needs research:** No — openpyxl patterns are thoroughly documented; gap taxonomy is domain knowledge already present in the team.

### Phase 4: Cross-Document Enrichment + Plausibility + Polish

**Rationale:** Cross-document enrichment is the highest-complexity item in the project (position-to-spec mapping across document types is genuinely ambiguous) and improves quality rather than enabling core functionality. Plausibility check and chain-of-thought export are low-effort polish. All Phase 4 work is additive — it enhances Phase 1-3 outputs without changing pipeline contracts.
**Delivers:** Position-to-spec mapping that merges requirements across Excel door lists, PDF specifications, and Word documents; `plausibility_checker.py` with duplicate detection, coverage validation, and anomaly detection; chain-of-thought reasoning exported to Excel "Hinweise" column; per-position SSE progress updates (not just per-stage)
**Addresses:** Cross-document enrichment (differentiator), plausibility check (differentiator), chain-of-thought export (differentiator)
**Avoids:** SSE connection drops on long analyses (keepalive heartbeats every 15-20 seconds verified); unit normalization errors (AI explicitly extracts unit alongside value, normalizes to mm)
**Needs research:** Cross-document position-to-spec mapping strategy is the highest-ambiguity design decision in the project. Sparse prior art for this specific domain combination. Recommend a focused design research task before Phase 4 implementation.

### Phase Ordering Rationale

- Pydantic schemas before everything else: they define the contracts between all pipeline stages; schema changes after stages are built cause cascading rework
- Extraction before matching: fundamental data dependency; incomplete extraction means permanently missed revenue
- Adversarial validation with matching (Phase 2, not Phase 3): adversarial confidence scores feed into gap severity; splitting them creates a two-pass rework cycle
- Gap analysis and Excel together (Phase 3): gap data is the missing input to the complete Excel format; building Excel structure before gap data is stable means rewriting the gap sheets
- Phase 4 explicitly last and additive: each feature enhances existing outputs without changing pipeline contracts; Phase 3 can ship as a complete product while Phase 4 proceeds

### Research Flags

Phases needing deeper research during planning:
- **Phase 2 (Adversarial Validation):** Adversarial prompt calibration requires empirical testing against v1 match data. The target rejection rate (15-30%) is a research-derived estimate; the actual baseline from v1 is unknown. Recommend a calibration sub-task as the first item in Phase 2 planning.
- **Phase 4 (Cross-document Enrichment):** Position-to-spec mapping across document types is the highest-complexity item in the project. The core challenge — linking a requirement in a PDF to a door position in an Excel file by position number, room, or floor — has no well-documented solution for this domain. Needs a focused design research task.

Phases with standard patterns (can skip research-phase):
- **Phase 1 (Multi-Pass Extraction):** `messages.parse()` has official Anthropic SDK documentation; TF-IDF pre-filter already implemented in v1; Pydantic schema design is well-understood. No new technology bets.
- **Phase 3 (Gap Analysis + Excel):** openpyxl is thoroughly documented including write_only mode and style reuse; gap taxonomy is domain knowledge; no external API dependencies introduced.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All technologies already in use in v1 or have official documentation. Version upgrades are minor SDK bumps. No new technology bets. |
| Features | HIGH | Feature set derived from direct v1 codebase analysis + domain research + PROJECT.md requirements. The gaps are known and measurable from v1 error rates. |
| Architecture | HIGH | Pipeline pattern is well-established for multi-stage AI processing. Pydantic-first is the official Claude SDK recommendation. Component boundaries derived from v1 service structure. |
| Pitfalls | HIGH | Five critical pitfalls all derived from v1 failure modes or official documentation constraints (context limits, openpyxl memory, structured output grammar). Not theoretical — observed or documented risks with known mitigations. |

**Overall confidence:** HIGH

### Gaps to Address

- **Adversarial rejection rate baseline:** Need to run v1 matches through a prototype adversarial prompt to establish the actual baseline rejection rate before tuning for the 15-30% target. Cannot be determined from research alone — requires empirical testing with real v1 data.
- **Token cost per tender:** Research estimates $15-50 per tender (Sonnet + Opus combined) but this depends on actual tender sizes from FTAG customers. Validate with 3-5 real tenders from v1 before committing to the full validation pipeline cost model.
- **Seed feedback data quality:** v1 has accumulated matching feedback in `data/matching_feedback.json` but its quality and coverage of edge cases is unknown. Audit at Phase 1 start to determine whether a curated seed set of 20-30 examples needs to be created manually.
- **pymupdf4llm 0.3.4 table quality on FTAG documents:** Version 0.3.4 claims major table detection improvements over 0.0.17 but this needs verification on actual FTAG construction tender PDFs (Swiss/German market formatting conventions may differ from test datasets).
- **GAEB/IFC parser scope confirmation:** Research flagged GAEB as low priority for v2 (most Swiss tenders are PDF/Excel). Confirm with FTAG before Phase 1 whether any specific customers require GAEB X83 support before scoping it out entirely.

## Sources

### Primary (HIGH confidence)
- Existing v1 codebase (direct analysis) — all service implementations, existing pitfall mitigations, current version numbers, known failure modes
- [Anthropic Python SDK - PyPI](https://pypi.org/project/anthropic/) — version 0.84.0, `messages.parse()` availability confirmed
- [Structured Outputs - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) — schema constraints, grammar enforcement behavior, schema design requirements (no $ref, additionalProperties: false, all fields required or Optional pattern)
- [pymupdf4llm - PyPI](https://pypi.org/project/pymupdf4llm/) — table detection improvements in 0.3.4 vs 0.0.17
- [pdfplumber - PyPI](https://pypi.org/project/pdfplumber/) — version 0.11.9 bug fixes
- [openpyxl documentation](https://openpyxl.readthedocs.io/) — write_only mode, style object reuse, memory optimization
- [FastAPI SSE documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/) — native SSE since 0.135.0

### Secondary (MEDIUM confidence)
- [Tenderbolt - Best AI solutions for tenders 2025](https://www.tenderbolt.ai/en/post/les-meilleures-solutions-ia-de-reponse-aux-appels-doffres-en-2025) — industry feature benchmarking for AI tender tools
- [Altura - AI in tender and RFP management 2025](https://altura.io/en/blog/ai-tendermanagement) — feature expectations and trust requirements in AI tender tools
- [iFieldSmart - AI Scope Gap Analysis for Construction](https://www.ifieldsmart.com/blogs/ai-scope-gap-analysis-for-construction-teams/) — gap severity taxonomy applicable to door/construction domain
- [Multi-Agent Validation Architectures](https://collabnix.com/multi-agent-and-multi-llm-architecture-complete-guide-for-2025/) — adversarial validation pattern in multi-agent AI systems
- [Anthropic SDK retry handling](https://github.com/anthropics/anthropic-sdk-python) — built-in 429 retry since v0.50+

### Tertiary (LOW confidence — validate during implementation)
- [arXiv - Confidence alignment with correctness for LLM error detection](https://arxiv.org/html/2603.06604) — theoretical basis for confidence score calibration; must be applied empirically against real FTAG tenders
- [arXiv - Fact-checking with LLMs via probabilistic certainty](https://arxiv.org/html/2601.02574) — adversarial prompting theory; needs domain-specific adaptation for construction product matching

---
*Research completed: 2026-03-10*
*Ready for roadmap: yes*
