# Architecture Patterns

**Domain:** AI multi-pass document analysis with product catalog matching
**Researched:** 2026-03-10

## Recommended Architecture

### High-Level Pipeline

```
Upload Files (PDF/DOCX/XLSX)
       |
       v
[1] Document Parsing Layer (existing, enhanced)
    - PyMuPDF + pymupdf4llm for PDF
    - python-docx for Word
    - pandas + openpyxl for Excel
    - Content cached by hash
       |
       v
[2] Multi-Pass Extraction Engine (NEW)
    - Pass A: Structural extraction (column/table parsing)
    - Pass B: AI semantic extraction (Claude Sonnet, Pydantic output)
    - Deduplication + merge of both passes
       |
       v
[3] Unified Requirements List
    - Pydantic model per requirement
    - All fields normalized (mm, dB, classification codes)
       |
       v
[4] Product Matching Pipeline (NEW)
    - Stage 1: TF-IDF pre-filter (891 -> ~25 candidates)
    - Stage 2: AI matching (Claude Sonnet, structured output per match)
    - Stage 3: Adversarial validation (Claude Opus, challenges each match)
    - Stage 4: Triple-check (Claude Opus, only for <95% confidence)
       |
       v
[5] Gap Analysis Engine (NEW)
    - Categorize gaps: Masse/Material/Norm/Zertifizierung/Leistung
    - Severity: Critical/Major/Minor
    - Alternative product suggestions
       |
       v
[6] Plausibility Check (NEW)
    - Duplicate detection
    - Coverage validation (all positions accounted for)
    - Statistical anomaly detection
       |
       v
[7] Excel Generator (enhanced)
    - Sheet 1: Tuermatrix-FTAG overview (existing format)
    - Sheet 2: Detailed match results with confidence + reasoning
    - Sheet 3: Gap analysis with categories + severity
    - Sheet 4: Executive summary with statistics
       |
       v
[8] SSE Progress Stream (existing, enhanced)
    - Real-time updates per step and per position
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| `routers/analyze.py` | HTTP endpoint, job orchestration, SSE streaming | All services via pipeline coordinator |
| `services/document_parser.py` | File bytes -> text/markdown, format detection, OCR fallback | Called by pipeline coordinator |
| `services/extraction_engine.py` (NEW) | Multi-pass requirement extraction, dedup, normalization | document_parser, ai_service |
| `services/ai_service.py` | Claude API calls (messages.parse), token tracking, error handling | extraction_engine, matching_pipeline |
| `services/matching_pipeline.py` (NEW) | Orchestrates TF-IDF pre-filter + AI matching + adversarial + triple-check | ai_service, catalog_index |
| `services/catalog_index.py` | Product catalog loading, TF-IDF index, product lookups | matching_pipeline |
| `services/gap_analyzer.py` (NEW) | Gap categorization, severity scoring, alternative suggestions | matching_pipeline results |
| `services/plausibility_checker.py` (NEW) | Post-analysis validation, anomaly detection | pipeline output |
| `services/result_generator.py` | 4-sheet Excel generation with formatting | All upstream results |
| `services/feedback_store.py` | Correction persistence, few-shot example retrieval | matching_pipeline |

### Data Flow

1. **Upload**: Files stored on disk, metadata tracked per analysis job
2. **Parsing**: Each file parsed independently, text cached by content hash
3. **Extraction**: Multi-pass extraction produces `list[ExtractedRequirement]` (Pydantic)
4. **Matching**: Each requirement matched independently (parallelizable), produces `list[MatchResult]` (Pydantic)
5. **Validation**: Adversarial pass receives `(requirement, match, product_details)` tuples, produces `list[ValidationResult]`
6. **Gap Analysis**: Non-matches and partial matches analyzed, produces `list[GapReport]`
7. **Excel**: All Pydantic results assembled into 4-sheet workbook
8. **Progress**: SSE events emitted at each stage boundary and per-position during matching

## Patterns to Follow

### Pattern 1: Pydantic-First AI Calls

**What:** Define Pydantic models for every AI call's expected output. Use `messages.parse()` to get grammar-enforced structured responses.

**When:** Every Claude API call in the multi-pass pipeline.

**Why:** Eliminates JSON parsing failures, retry logic, and ambiguous output formats. The model cannot produce invalid output.

```python
from pydantic import BaseModel, Field
from typing import Literal

class MatchResult(BaseModel):
    """Result of matching one requirement against the product catalog."""
    position: str
    status: Literal["matched", "partial", "unmatched"]
    confidence: float = Field(ge=0, le=100, description="Match confidence 0-100%")
    product_row_index: int | None = Field(description="Catalog row index of best match")
    reasoning: str = Field(description="Step-by-step reasoning for this match decision")
    matching_dimensions: dict[str, bool] = Field(
        description="Which dimensions match: masse, material, norm, zertifizierung, leistung"
    )

# Usage
result = ai_service.call_parsed(
    prompt=matching_prompt,
    output_model=MatchResult,
    system="You are a construction product matching expert..."
)
```

### Pattern 2: Adversarial Validation (Devil's Advocate)

**What:** After initial matching, a second AI call with a deliberately adversarial system prompt tries to disprove each match.

**When:** After Pass 2 (AI matching), for ALL matches (not just uncertain ones).

**Why:** Catches false positives that the initial matching pass accepted too eagerly. The adversarial model is incentivized to find flaws.

```python
class AdversarialResult(BaseModel):
    """Result of adversarial challenge to a match."""
    challenge_successful: bool = Field(
        description="True if a valid reason to reject the match was found"
    )
    challenge_reasoning: str = Field(
        description="Argument for why this match might be wrong"
    )
    revised_confidence: float = Field(
        ge=0, le=100,
        description="Revised confidence after adversarial review"
    )
    failed_dimensions: list[str] = Field(
        description="Which dimensions the adversarial check found issues with"
    )

# Adversarial system prompt
ADVERSARIAL_SYSTEM = """You are a quality control expert reviewing product matches.
Your job is to find reasons why a proposed match might be WRONG.
Be thorough and skeptical. Look for:
- Dimension mismatches (even small ones matter for doors)
- Fire rating insufficiency (EI30 proposed for EI60 requirement)
- Sound class mismatches
- Material incompatibilities
- Missing certifications
If you find a valid reason to reject, set challenge_successful=true."""
```

### Pattern 3: Pipeline Coordinator with SSE

**What:** A coordinator class orchestrates the multi-pass pipeline, emitting SSE events at each stage.

**When:** During the analysis endpoint execution.

**Why:** Decouples pipeline stages from HTTP handling. Makes testing individual stages possible. SSE events give users real-time feedback.

```python
class AnalysisPipeline:
    """Orchestrates the complete multi-pass analysis."""

    async def run(self, files: list, progress_callback):
        # Stage 1: Parse
        await progress_callback("parsing", 0, len(files))
        documents = []
        for i, f in enumerate(files):
            doc = parse_document_bytes(f.content, f.ext)
            documents.append(doc)
            await progress_callback("parsing", i + 1, len(files))

        # Stage 2: Extract requirements (multi-pass)
        await progress_callback("extracting", 0, len(documents))
        requirements = await self.extraction_engine.extract_all(
            documents, progress_callback
        )

        # Stage 3: Match
        await progress_callback("matching", 0, len(requirements))
        matches = await self.matching_pipeline.match_all(
            requirements, progress_callback
        )

        # Stage 4: Validate (adversarial)
        await progress_callback("validating", 0, len(matches))
        validated = await self.matching_pipeline.validate_all(
            matches, progress_callback
        )

        # Stage 5: Gap analysis
        await progress_callback("gap_analysis", 0, 1)
        gaps = self.gap_analyzer.analyze(validated)

        # Stage 6: Generate Excel
        await progress_callback("generating", 0, 1)
        excel_bytes = generate_result_excel(validated, gaps, requirements)

        return excel_bytes
```

### Pattern 4: Batch AI Calls for Cost/Speed

**What:** Group multiple requirements into single AI calls where possible, rather than one call per requirement.

**When:** During extraction (batch all requirements from one document) and during matching (batch 5-10 requirements per call).

**Why:** Reduces API overhead. Claude handles batched structured output well with `list[Model]` return types.

```python
class BatchMatchResult(BaseModel):
    """Batch of match results for multiple requirements."""
    matches: list[MatchResult]

# Send 5-10 requirements per call instead of 1
batch_prompt = format_batch_prompt(requirements_batch, candidates_per_req)
result = ai_service.call_parsed(
    prompt=batch_prompt, output_model=BatchMatchResult
)
```

## Anti-Patterns to Avoid

### Anti-Pattern 1: Single-Pass Extraction

**What:** Parsing each document once and assuming all requirements were found.
**Why bad:** v1's biggest failure. Construction tenders encode requirements in multiple ways (tables, prose, cross-references). Single pass misses 10-30% of positions.
**Instead:** Minimum 2 passes: structural (column parsing) + semantic (AI extraction). Deduplicate by position number.

### Anti-Pattern 2: Unstructured AI Output

**What:** Using `ai_service.call()` (plain text response) and then regex-parsing the result.
**Why bad:** Fragile, fails on edge cases, requires retry logic. The codebase already has `call_parsed()` and `call_structured()` -- use them.
**Instead:** Always use `call_parsed()` with Pydantic models. Grammar-enforced output eliminates parsing failures entirely.

### Anti-Pattern 3: Sequential Per-Position Processing

**What:** Making one API call per door position (200-500 calls per tender).
**Why bad:** Each call has ~1-2s latency overhead. 500 positions = 8-16 minutes of pure API latency.
**Instead:** Batch 5-10 positions per call. Total calls: 50-100 instead of 500. Time: 2-4 minutes.

### Anti-Pattern 4: Monolithic Analysis Function

**What:** One giant async function that does parsing + extraction + matching + gap analysis + Excel generation.
**Why bad:** Untestable, impossible to debug, cannot resume on failure.
**Instead:** Pipeline pattern with discrete stages. Each stage has input/output Pydantic models. Stages can be tested independently.

### Anti-Pattern 5: Caching at the Wrong Level

**What:** Caching AI responses by prompt text.
**Why bad:** Prompts include dynamic context (feedback examples, catalog versions). Cache hit rate near zero.
**Instead:** Cache at the document parsing level (by content hash). Already implemented in `memory_cache.py`. This prevents re-parsing the same PDF across multi-pass extraction.

## Scalability Considerations

| Concern | At 1 tender/day | At 10 tenders/day | At 100 tenders/day |
|---------|-----------------|--------------------|--------------------|
| Claude API rate limits | No issue | No issue | May need rate limit awareness, request queuing |
| Analysis time (2-10 min) | Acceptable | Background jobs essential | Need job queue (consider Celery) |
| Memory (PDF parsing) | No issue | Monitor for large PDFs | Process limits per worker |
| Excel generation | No issue | No issue | No issue (in-memory, fast) |
| Token costs | ~$5-20/tender (Sonnet) + ~$10-30/tender (Opus) | ~$150-500/day | Consider prompt caching |

**Current scale:** 1-5 tenders/day. FastAPI BackgroundTasks + SSE is sufficient.

## Sources

- Existing codebase analysis (ai_service.py, document_parser.py, result_generator.py, catalog_index.py)
- [Structured Outputs - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [Multi-Agent Validation Architectures](https://collabnix.com/multi-agent-and-multi-llm-architecture-complete-guide-for-2025/)
- [FastAPI SSE documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
