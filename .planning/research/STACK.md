# Technology Stack

**Project:** FTAG KI-Angebotserstellung v2 (Multi-Pass Validation)
**Researched:** 2026-03-10

## Recommended Stack

### Core Framework

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Python | 3.12+ | Runtime | Already in use, FastAPI-optimized, stable LTS | HIGH |
| FastAPI | >=0.115.0 | REST API + SSE | Already in use, native SSE support since 0.135.0, async-first | HIGH |
| uvicorn[standard] | >=0.32.0 | ASGI server | Already in use, production-proven with FastAPI | HIGH |
| Pydantic | >=2.5.3 | Validation + AI schema | Core for structured outputs with Claude API `messages.parse()` | HIGH |

### AI / LLM

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| anthropic | >=0.84.0 | Claude API SDK | Latest version supports `messages.parse()` with Pydantic models for schema-guaranteed structured outputs. The `output_format` parameter (deprecated but functional) is already used in codebase; migrate to `output_config.format` for forward compatibility. | HIGH |
| Claude Sonnet 4.6 | current | Primary model | Best price/performance for structured extraction. Use for Pass 1 (extraction) and Pass 2 (matching). | HIGH |
| Claude Opus 4.6 | current | Adversarial validator | Higher reasoning capability justifies cost for the adversarial double-check pass. Use for Pass 3 (validation) only. Costs irrelevant per project constraints. | MEDIUM |

**Structured Outputs Strategy:** Use `client.messages.parse(output_format=PydanticModel)` for ALL AI calls. This compiles JSON schema into a grammar that restricts token generation at inference time -- the model literally cannot produce invalid output. Eliminates retry logic and JSON parsing failures.

**Supported schema constraints:** No recursive schemas, no `$ref`, `additionalProperties: false` required on all objects, all properties must be `required`. Design Pydantic models flat, not deeply nested.

### Document Parsing

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| PyMuPDF (fitz) | >=1.24.0 | Fast PDF text extraction | 10-100x faster than pdfplumber for text. Already in use, handles large PDFs well. | HIGH |
| pymupdf4llm | >=0.3.4 | PDF-to-Markdown with tables | Converts PDF to LLM-optimized Markdown preserving table structure. Critical for construction tenders with tabular specs. Update from 0.0.17 to 0.3.4 for improved table detection. | HIGH |
| pdfplumber | >=0.11.9 | Table extraction fallback | Best-in-class table boundary detection via character/line geometry. Use as fallback when pymupdf4llm tables are incomplete. Update from 0.11.4 to 0.11.9. | HIGH |
| python-docx | 1.1.2 | Word document parsing | Already in use, stable, handles paragraphs + tables. No changes needed. | HIGH |
| openpyxl | 3.1.5 | Excel reading + writing | Dual-purpose: reads tender Excel files AND generates output Excel. Already in use. | HIGH |
| pandas | 2.2.3 | Excel sheet reading | DataFrame-based sheet reading for multi-sheet Excel tenders. Already in use. | HIGH |
| pytesseract | 0.3.10 | OCR for scanned PDFs | Already in use, handles scanned construction documents with deu+eng. | HIGH |

### Excel Output Generation

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| openpyxl | 3.1.5 | 4-sheet Excel generation | Use for the new 4-sheet output (Overview, Details, Gap Analysis, Executive Summary). Already proven in codebase for complex formatting: merged cells, color fills, conditional formatting, auto-filters, freeze panes. | HIGH |

**Why NOT XlsxWriter:** The codebase already uses openpyxl extensively. XlsxWriter cannot read existing files (write-only). openpyxl handles both read and write, which is needed since the system reads the product catalog Excel AND writes output Excel. Switching would fragment the Excel stack for marginal benefit.

**Why NOT xlwings:** Requires Excel installed on the server. Not suitable for headless Linux deployment.

### Validation & Data Models

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| Pydantic | >=2.5.3 | Data validation schemas | Define extraction schemas, matching results, gap analysis structures as Pydantic models. These models double as Claude structured output schemas via `messages.parse()`. | HIGH |
| pydantic-settings | 2.1.0 | Config management | Already in use for settings. | HIGH |

### Caching & Performance

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| In-memory dict cache | built-in | PDF text cache | Already implemented in `memory_cache.py`. Multi-pass analysis will re-read the same documents -- caching prevents re-parsing. | HIGH |
| hashlib (MD5) | stdlib | Cache key generation | Already used for content-based cache keys. | HIGH |

### Logging & Progress

| Technology | Version | Purpose | Why | Confidence |
|------------|---------|---------|-----|------------|
| python-json-logger | 2.0.7 | Structured logging | Already in requirements. Essential for tracing multi-pass analysis steps. | HIGH |
| sse-starlette | >=2.0.0 | SSE streaming | FastAPI has native SSE since 0.135.0, but sse-starlette provides more control (event IDs, retry). Use for live progress streaming during multi-pass analysis. | MEDIUM |

### Supporting Libraries

| Library | Version | Purpose | When to Use | Confidence |
|---------|---------|---------|-------------|------------|
| httpx | 0.28.1 | HTTP client | Ollama fallback calls (out of scope for v2 but keep for compatibility) | HIGH |
| python-dotenv | 1.0.1 | Env config | Loading ANTHROPIC_API_KEY | HIGH |
| scikit-learn | >=1.6.0 | TF-IDF pre-filter | Stage 1 keyword scoring to narrow 891 products to ~25 candidates before AI matching | HIGH |
| aiofiles | >=24.1.0 | Async file I/O | Async file uploads | HIGH |

## What NOT to Use

| Technology | Why Not |
|------------|---------|
| LangChain | Massive dependency for simple Claude API calls. The project needs direct SDK control for multi-pass orchestration, not abstracted chains. Adds complexity without value for this use case. |
| LlamaIndex | Same reasoning as LangChain. The product catalog is small (~891 rows) -- no need for a full RAG framework. TF-IDF pre-filter + Claude matching is simpler and more controllable. |
| sentence-transformers | Currently commented out in requirements. For 891 products, TF-IDF cosine similarity is fast enough. Embedding models add GPU requirements and cold-start latency. Revisit only if catalog grows to 10K+. |
| unstructured[all-docs] | Already optionally integrated but adds ~2GB of dependencies. pymupdf4llm 0.3.4 handles the PDF-to-Markdown conversion well enough for construction tenders. Keep as optional fallback, do not make it a hard dependency. |
| XlsxWriter | Write-only library. Cannot read Excel files. Project needs both read (catalog) and write (output). Would fragment the Excel stack. |
| Celery + Redis | Overkill for single-user/small-team use. FastAPI BackgroundTasks + SSE is sufficient for the analysis pipeline. No need for distributed task queues. |
| SQLAlchemy + PostgreSQL | Already in requirements but not needed for v2 core. The system operates on file-based I/O (upload Excel/PDF, output Excel). JSON feedback store is sufficient. Remove from v2 core requirements to reduce complexity. |
| Ollama / local LLM | Explicitly out of scope per PROJECT.md: "v2 nutzt ausschliesslich Claude (bestes Modell, Kosten irrelevant)". Keep the AIService abstraction but do not invest in Ollama fallback for v2. |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| PDF extraction | PyMuPDF + pymupdf4llm | unstructured.io | 2GB dependency overhead, pymupdf4llm 0.3.4 handles tables well |
| AI SDK | anthropic (direct) | LangChain/Anthropic | Unnecessary abstraction layer for multi-pass orchestration |
| Excel output | openpyxl | XlsxWriter | XlsxWriter is write-only, openpyxl handles both read and write |
| Task queue | FastAPI BackgroundTasks | Celery + Redis | Single-user system, no distributed computing needed |
| Embeddings | scikit-learn TF-IDF | sentence-transformers | 891 products is small, TF-IDF is fast and sufficient |
| Structured output | Pydantic + messages.parse() | Tool use (force_tool) | messages.parse() is the official recommended approach, grammar-enforced |

## Key Version Upgrades from v1

| Library | v1 Version | v2 Version | Reason |
|---------|-----------|-----------|--------|
| anthropic | >=0.49.0 | >=0.84.0 | Structured outputs GA, `output_config.format` parameter |
| pymupdf4llm | >=0.0.17 | >=0.3.4 | Major table detection improvements, layout analysis |
| pdfplumber | 0.11.4 | >=0.11.9 | Bug fixes, better Unicode handling |

## Installation

```bash
# Core (what v2 actually needs)
pip install fastapi>=0.115.0 uvicorn[standard]>=0.32.0 python-multipart>=0.0.20
pip install anthropic>=0.84.0
pip install pydantic>=2.5.3 pydantic-settings==2.1.0
pip install PyMuPDF>=1.24.0 pymupdf4llm>=0.3.4
pip install pdfplumber>=0.11.9
pip install python-docx==1.1.2
pip install openpyxl==3.1.5 pandas==2.2.3
pip install scikit-learn>=1.6.0
pip install httpx==0.28.1 aiofiles>=24.1.0
pip install python-dotenv==1.0.1
pip install python-json-logger==2.0.7

# Dev dependencies
pip install pytest pytest-asyncio pytest-cov
pip install ruff mypy

# Optional (already integrated, large dependency)
# pip install unstructured[all-docs]>=0.16.0
# pip install pytesseract==0.3.10 Pillow==10.2.0
```

## Architecture Pattern: Multi-Pass with Pydantic

The core innovation for v2 is using Pydantic models as both data validation AND Claude output schemas:

```python
from pydantic import BaseModel, Field

class ExtractedRequirement(BaseModel):
    """Single technical requirement extracted from tender document."""
    position: str = Field(description="Door position number (e.g., T1.01)")
    beschreibung: str = Field(description="Full description of requirement")
    breite_mm: int | None = Field(description="Width in mm, null if not specified")
    hoehe_mm: int | None = Field(description="Height in mm, null if not specified")
    brandschutz: str | None = Field(description="Fire protection class (EI30/EI60/EI90)")
    schallschutz_db: int | None = Field(description="Sound protection in dB")
    # ... all fields

class ExtractionResult(BaseModel):
    """All requirements extracted from a single document."""
    requirements: list[ExtractedRequirement]
    document_metadata: dict

# Pass 1: Extract
result = client.messages.parse(
    model="claude-sonnet-4-6",
    output_format=ExtractionResult,
    messages=[{"role": "user", "content": f"Extract all door requirements:\n{document_text}"}]
)
# result.parsed_output is guaranteed to be a valid ExtractionResult
```

## Sources

- [Anthropic Python SDK - PyPI](https://pypi.org/project/anthropic/)
- [Structured Outputs - Claude API Docs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)
- [pymupdf4llm - PyPI](https://pypi.org/project/pymupdf4llm/)
- [pdfplumber - PyPI](https://pypi.org/project/pdfplumber/)
- [openpyxl documentation](https://openpyxl.readthedocs.io/)
- [FastAPI SSE documentation](https://fastapi.tiangolo.com/tutorial/server-sent-events/)
