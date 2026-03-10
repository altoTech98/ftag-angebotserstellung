# Domain Pitfalls

**Domain:** AI multi-pass document analysis with product catalog matching (construction/doors)
**Researched:** 2026-03-10

## Critical Pitfalls

Mistakes that cause rewrites or major issues.

### Pitfall 1: Context Window Overflow on Large Tenders

**What goes wrong:** A tender with 500+ positions generates prompts that exceed Claude's 200K context window when you include the full catalog for matching.
**Why it happens:** Naive approach stuffs all 891 products + all requirements into one prompt.
**Consequences:** API errors, truncated responses, silent data loss.
**Prevention:** TF-IDF pre-filter is essential (891 -> ~25 candidates per requirement). Batch matching calls with 5-10 requirements at a time, each with their own pre-filtered candidate set. Monitor token usage via `ai_service.get_context_usage()`.
**Detection:** Track `input_tokens` per call. Alert if any call exceeds 150K tokens.

### Pitfall 2: Adversarial Pass That Always Agrees or Always Disagrees

**What goes wrong:** The adversarial validation pass either rubber-stamps everything (useless) or rejects everything (blocks pipeline).
**Why it happens:** System prompt calibration. Too weak = "looks fine". Too aggressive = "every match has a flaw".
**Consequences:** False confidence in results (if always agrees) or zero throughput (if always rejects).
**Prevention:** Calibrate adversarial prompt on 20-30 known-good and known-bad matches from v1 data. Measure: target adversarial rejection rate of 15-30% (based on v1 error rates). If outside this range, adjust prompt temperature and specificity.
**Detection:** Track adversarial rejection rate per analysis run. Dashboard metric: `adversarial_rejection_rate`. Alert if <5% (too lenient) or >50% (too strict).

### Pitfall 3: Deduplication Failures in Multi-Pass Extraction

**What goes wrong:** Two extraction passes find the same door position but describe it slightly differently (e.g., "T1.01" vs "Tuer 1.01" vs "Position 1.01"). System treats them as separate requirements.
**Why it happens:** Position number normalization is harder than it looks. Swiss/German tenders use inconsistent numbering.
**Consequences:** Duplicate entries in output Excel. Sales team loses trust. Match count inflated.
**Prevention:** Implement robust position number normalization: strip prefixes (T, Tuer, Pos, Position), normalize separators (. / - _), compare numeric components. Also check for duplicate descriptions within same floor/room.
**Detection:** Post-extraction check: flag any two requirements with >80% text similarity as potential duplicates.

### Pitfall 4: Structured Output Schema Too Rigid

**What goes wrong:** Pydantic model requires fields that Claude cannot always determine from the document. Model is forced to hallucinate values to satisfy the schema.
**Why it happens:** Grammar-enforced output means the model MUST fill every required field. If the document does not contain the information, the model invents it.
**Consequences:** Plausible-looking but fabricated data (e.g., inventing fire ratings that are not in the document).
**Prevention:** Make all extraction fields Optional (nullable). Use `str | None` and `int | None` liberally. Only `position` and `beschreibung` should be required. Add a `confidence_per_field: dict[str, float]` to track which fields the model was sure about.
**Detection:** Cross-check extracted values against document text. If a field value does not appear anywhere in the source text, flag it.

### Pitfall 5: Excel Generation Memory Blow-Up

**What goes wrong:** openpyxl holds the entire workbook in memory. For 500+ rows with 54 columns across 4 sheets, with formatting per cell, memory usage can spike to 500MB+.
**Why it happens:** openpyxl stores each cell's style as a separate object. 500 rows x 54 cols x 4 sheets = 108,000 styled cells.
**Consequences:** Server OOM on small VPS instances. Slow generation.
**Prevention:** Use `write_only` mode for large sheets where possible. Reuse style objects (create once, apply to many cells -- already partially done in `result_generator.py`). Set a position limit warning at 1000 positions.
**Detection:** Monitor memory before and after Excel generation. Log if >200MB.

## Moderate Pitfalls

### Pitfall 1: Multi-Pass Extraction Ordering Dependency

**What goes wrong:** Pass B (AI semantic) overwrites better data from Pass A (structural) during merge, or vice versa.
**Prevention:** Define clear merge priority: structural data takes precedence for exact values (dimensions, position numbers), AI data takes precedence for semantic fields (descriptions, classifications). Never silently overwrite -- log all merge conflicts.

### Pitfall 2: Claude API Rate Limits During Batch Processing

**What goes wrong:** Multi-pass analysis of a 500-position tender makes 100-200 API calls. Rate limits kick in mid-analysis.
**Prevention:** Implement exponential backoff with jitter. Use `anthropic` SDK's built-in retry logic. Monitor rate limit headers. Add 100ms delay between batch calls. The SDK handles 429 responses automatically since v0.50+.

### Pitfall 3: Product Catalog Column Drift

**What goes wrong:** The catalog Excel changes column order or adds new columns. Parser breaks silently, matching degraded.
**Prevention:** Catalog parser should auto-detect header row (already implemented). Add column name validation at startup: if expected columns are missing, log a clear error and refuse to start. Version-track the catalog schema.

### Pitfall 4: SSE Connection Drops During Long Analysis

**What goes wrong:** Browser or proxy drops the SSE connection after 60-120 seconds. User sees frozen progress.
**Prevention:** Already have keepalive events (existing code sends heartbeats). Ensure keepalive interval is 15-20 seconds. Add reconnection support in frontend (EventSource auto-reconnects, but must handle `lastEventId`).

### Pitfall 5: Inconsistent Units in Tender Documents

**What goes wrong:** One document specifies door dimensions in mm, another in cm, another in m. Parsed values are wrong by 10x or 1000x.
**Prevention:** Already partially handled in `_dim_to_mm()` with heuristic ranges (<20 = meters, 20-400 = cm, >400 = mm). Add explicit unit detection in AI extraction: instruct Claude to extract the unit alongside the value. Normalize all to mm in the Pydantic model.

### Pitfall 6: German/Swiss Text Encoding Issues

**What goes wrong:** Special characters (umlauts, sharp s) corrupted in PDF extraction or Excel output.
**Prevention:** Always use UTF-8. PyMuPDF and pdfplumber handle this well. openpyxl writes UTF-8 by default. The risk is in OCR output (pytesseract) -- set `lang="deu+eng"` explicitly. Test with documents containing Oeffnung, Tuerblatt, Schliessband, etc.

## Minor Pitfalls

### Pitfall 1: Feedback Loop Cold Start

**What goes wrong:** First analysis on a new system has no feedback data, so AI matching has no few-shot examples.
**Prevention:** Ship with a seed set of 20-30 curated matching examples covering common door types (fire doors, sound doors, security doors). Store in `data/seed_feedback.json`.

### Pitfall 2: Inconsistent Confidence Score Ranges

**What goes wrong:** Sonnet rates a match at 85%, Opus adversarial rates it at 70%, triple-check rates it at 92%. Which score to show?
**Prevention:** Define clear aggregation rule: final_confidence = min(pass2_confidence, adversarial_revised_confidence). If triple-check triggered, use triple-check score. Always show the most conservative estimate.

### Pitfall 3: GAEB/IFC Parser Edge Cases

**What goes wrong:** GAEB X83 files from different software export slightly different XML structures.
**Prevention:** The GAEB and IFC parsers are optional and already handle errors gracefully (return error strings). Low priority for v2 since most Swiss tenders are PDF/Excel. Do not invest in GAEB robustness unless specific customer requests it.

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Multi-pass extraction | Dedup failures on position numbers | Robust normalization + fuzzy matching on position IDs |
| Pydantic schema design | Too-rigid schemas force hallucination | Make all fields Optional except position/description |
| Adversarial validation | Prompt calibration (too lenient/strict) | Calibrate on 20-30 known matches from v1 data |
| Batch AI calls | Context overflow with large candidate sets | TF-IDF pre-filter essential, monitor token counts |
| 4-sheet Excel | Memory usage with 500+ styled rows | Reuse style objects, consider write_only mode |
| SSE progress | Connection drops on long analyses | Keepalive heartbeats every 15-20 seconds |
| Unit normalization | mm/cm/m confusion in tenders | AI extracts unit alongside value, normalize to mm |
| Confidence scoring | Inconsistent scores across passes | Use min() aggregation, show most conservative |

## Sources

- v1 codebase analysis -- identified existing mitigations and gaps
- [Structured Outputs limitations](https://platform.claude.com/docs/en/build-with-claude/structured-outputs) -- schema constraints
- [openpyxl performance considerations](https://openpyxl.readthedocs.io/en/stable/optimized.html) -- write_only mode
- [Anthropic SDK retry handling](https://github.com/anthropics/anthropic-sdk-python) -- built-in 429 retry
