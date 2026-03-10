# Testing Patterns

**Analysis Date:** 2026-03-10

## Test Framework

### Runner

**Backend (Python):**
- Framework: `pytest`
- Config: `backend/pytest.ini`
- Async support: `asyncio_mode = auto` (pytest-asyncio)

```ini
[pytest]
testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*
asyncio_mode = auto
addopts = -v --tb=short
```

**Run Commands:**
```bash
pytest                          # Run all tests
pytest -v                       # Verbose output
pytest tests/test_document_parser.py  # Single file
pytest tests/test_document_parser.py::TestParseDocumentBytes  # Single class
pytest tests/test_document_parser.py::TestParseDocumentBytes::test_parse_empty_pdf  # Single test
pytest -k keyword              # Filter by name
pytest --tb=short              # Short traceback format
```

**Frontend:**
- No test framework configured
- No test files in `frontend-react/src/`
- ESLint only for linting (no Jest/Vitest setup)

### Assertion Library

**Python:**
- Built-in `assert` statements
- `pytest` fixtures for setup/teardown

**Examples:**
```python
assert DocumentParser.get_format("document.pdf") == "PDF"
assert DocumentParser.is_supported("file.exe") is False
```

## Test File Organization

### Location

**Backend:**
- Tests in `backend/tests/` directory
- Mirrors source structure conceptually (e.g., `test_document_parser.py` tests `services/document_parser.py`)

### Naming

**Pattern:** `test_*.py` or `*_test.py`
**Observed:** `test_*.py` (e.g., `test_document_parser.py`, `test_product_matcher.py`)

**Test classes:** `Test*` (e.g., `TestDocumentParser`, `TestParseDocumentBytes`)

**Test functions:** `test_*` (e.g., `test_get_format_pdf`, `test_parse_empty_pdf`)

### Structure

```
backend/
├── tests/
│   ├── __init__.py
│   ├── conftest.py              # Shared fixtures
│   ├── test_analyze.py          # Router/endpoint tests
│   ├── test_document_parser.py  # Document parsing service
│   ├── test_excel_parser.py     # Excel parsing service
│   ├── test_product_matcher.py  # Product matching logic
│   ├── test_offer.py            # Offer generation
│   ├── test_upload.py           # Upload endpoints
│   ├── test_validators.py       # Validation functions
│   ├── test_vision_parser.py    # Image/OCR parsing
│   └── test_ko_integration.py   # Integration tests
└── pytest.ini
```

## Test Structure

### Suite Organization

**Pattern observed in `test_product_matcher.py`:**

```python
"""
Tests for product_matcher service.
Focus on keyword scoring, synonym expansion, and TF-IDF logic.
AI matching is tested with mocked Claude responses.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from services.product_matcher import (
    expand_synonyms,
    _get_type_keywords,
    _build_requirement_text,
)


class TestExpandSynonyms:
    """Test domain synonym expansion."""

    def test_fire_protection_synonyms(self):
        terms = expand_synonyms("feuerschutztür T30")
        assert any("Brand" in t or "T30" in t for t in terms)

    def test_burglar_resistance_synonyms(self):
        terms = expand_synonyms("sicherheitstür RC3")
        assert any("RC" in t or "WK" in t for t in terms)

    def test_empty_input(self):
        assert expand_synonyms("") == []
```

### Patterns

**Setup/Teardown:**
```python
# Via fixtures (see conftest.py section below)
@pytest.fixture
def sample_position():
    """A typical door position from a tender document."""
    return {
        "position": "1.01",
        "beschreibung": "Stahltür einflügelig mit Brandschutz",
        ...
    }

# Class-based with setup_method
class TestSomething:
    def setup_method(self):
        """Called before each test in this class."""
        self.data = setup_data()

    def teardown_method(self):
        """Called after each test in this class."""
        cleanup()

    def test_something(self):
        assert self.data is not None
```

**Assertion pattern:**
```python
# Direct assertions
assert len(results) == 3
assert results[0]["status"] == "matched"
assert any("product" in r for r in results)

# Pytest assertion introspection (detailed failures)
assert document_text.startswith("Ausschreibung")
```

## Mocking

### Framework

**No explicit mocking framework dependency detected** - Using `unittest.mock` from Python stdlib

**In conftest.py (observed):**
```python
from unittest.mock import MagicMock, patch
```

### Patterns

**Mocking external services (Claude AI):**
```python
# Example pattern (would appear in test files that test AI integration)
from unittest.mock import patch, MagicMock

@patch('services.ai_service.AIService._call_claude')
def test_analyze_with_claude_mock(mock_claude):
    mock_claude.return_value = "Stahltür, Holztür"
    # Test calls AI service with mocked Claude
    result = analyze_document(requirements)
    assert result is not None
```

**Mocking file I/O:**
```python
# Document parser can mock file reading
from unittest.mock import mock_open

mock_file_content = b"Ausschreibung..."
with patch("builtins.open", mock_open(read_data=mock_file_content)):
    result = parse_document("test.txt")
```

**Mocking Ollama availability:**
```python
# Test AI service failover logic
@patch('services.ai_service.httpx.post')
def test_ollama_fallback(mock_ollama_post):
    mock_ollama_post.side_effect = ConnectionError()
    ai_service = AIService()
    # Should fallback to Claude or None
    result = ai_service.call("test prompt")
```

### What to Mock

**Mock these:**
- External API calls (Claude, Ollama, ERP)
- File system operations (in unit tests)
- Network requests (httpx calls)
- Time-dependent operations (use freezegun or mock time)

**Don't mock these:**
- Internal service calls (test the actual integration)
- Data validation logic
- Business logic (matching, scoring algorithms)
- Database operations in integration tests

## Fixtures and Factories

### Test Data (conftest.py)

**Location:** `backend/tests/conftest.py`

**Sample position fixture:**
```python
@pytest.fixture
def sample_position():
    """A typical door position from a tender document."""
    return {
        "position": "1.01",
        "beschreibung": "Stahltür einflügelig mit Brandschutz",
        "tuertyp": "Stahltür",
        "brandschutz": "EI30",
        "einbruchschutz": "",
        "schallschutz": "",
        "breite": 900,
        "hoehe": 2100,
        "menge": 2,
        "einheit": "Stk",
    }
```

**Multiple positions fixture:**
```python
@pytest.fixture
def sample_positions():
    """Multiple door positions for batch testing."""
    return [
        {
            "position": "1.01",
            "beschreibung": "Stahltür mit Brandschutz T30",
            "tuertyp": "Stahltür",
            "menge": 3,
            ...
        },
        # ... more positions
    ]
```

**File bytes fixtures:**
```python
@pytest.fixture
def sample_excel_bytes():
    """Minimal Excel file bytes for parser tests."""
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Türliste"
    ws.append(["Position", "Beschreibung", "Menge", "Einheit"])
    ws.append(["1.01", "Stahltür T30", 3, "Stk"])

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)
    return buf.getvalue()
```

**Requirements fixture (uses sample_positions):**
```python
@pytest.fixture
def sample_requirements(sample_positions):
    """A full requirements dict as returned by the analyze pipeline."""
    return {
        "projekt": "Testprojekt Schulhaus Buochs",
        "auftraggeber": "Gemeinde Buochs",
        "positionen": sample_positions,
    }
```

**Matched positions fixture (test results):**
```python
@pytest.fixture
def sample_matched_positions(sample_positions):
    """Matched positions as returned by the product matcher."""
    return [
        {
            "status": "matched",
            "confidence": 0.85,
            "position": "1.01",
            "matched_products": [{"bezeichnung": "FTAG Stahltür T30"}],
            "reason": "Produkt im FTAG-Sortiment verfügbar",
            ...
        },
        # ... more results
    ]
```

### Fixture Dependency

**Fixtures can depend on other fixtures:**
```python
@pytest.fixture
def sample_matched_positions(sample_positions):  # Depends on sample_positions
    # Use sample_positions to build matched results
    return [...]

def test_offer_generation(sample_matched_positions):  # Uses fixture
    result = generate_offer(sample_matched_positions)
    assert result is not None
```

**Fixture scope:**
- Default: `"function"` - new instance per test
- Options: `"class"`, `"module"`, `"session"` (observed: all use function scope for isolation)

## Coverage

### Requirements

**Not enforced** - No coverage configuration or GitHub Actions workflow detected

**View Coverage:**
```bash
pytest --cov=backend --cov-report=html  # Would work if pytest-cov installed
# Requires: pip install pytest-cov
```

**Recommended:**
```bash
pytest --cov=backend --cov-report=term-missing --cov-report=html
```

## Test Types

### Unit Tests

**Scope:** Individual functions/methods in isolation

**Approach (from test files):**
```python
# test_document_parser.py - Tests format detection
def test_get_format_pdf(self):
    assert DocumentParser.get_format("document.pdf") == "PDF"

def test_get_format_case_insensitive(self):
    assert DocumentParser.get_format("DOC.PDF") == "PDF"
```

**Characteristics:**
- No external services
- Test single function behavior
- Use fixtures for data setup
- Fast execution (< 100ms per test)

### Integration Tests

**Scope:** Multiple services working together

**Examples (from test files):**
- `test_ko_integration.py` - Tests full pipeline from document parsing to offer generation
- Document parsing + product matching + offer generation

**Pattern:**
```python
# Pseudo-code example
def test_full_analysis_pipeline(sample_requirements, sample_excel_bytes):
    # Parse document
    text = parse_document_bytes(sample_excel_bytes, ".xlsx")
    assert text is not None

    # Extract requirements
    positions = extract_positions(text)
    assert len(positions) > 0

    # Match products (may call AI)
    matches = match_products(positions)
    assert matches[0]["status"] in ["matched", "unmatched"]

    # Generate offer
    offer_bytes = generate_offer(matches)
    assert offer_bytes is not None
```

### E2E Tests

**Framework:** Not used in current codebase

**Would require:** Selenium/Playwright for browser automation
- Could test full flow: upload file → analyze → download offer
- Not currently configured

## Common Patterns

### Async Testing

**Pytest with asyncio:**
```python
# asyncio_mode = auto in pytest.ini enables this

@pytest.mark.asyncio
async def test_async_function():
    result = await some_async_function()
    assert result is not None
```

**Testing routers (async):**
```python
# Example for FastAPI routes (if using TestClient)
from fastapi.testclient import TestClient

def test_analyze_endpoint():
    # Synchronous test wrapper (TestClient handles async)
    response = client.post("/api/analyze", json={"file_id": "123"})
    assert response.status_code == 200
```

### Error Testing

**Testing exceptions:**
```python
# test_document_parser.py pattern
def test_parse_empty_bytes(self):
    with pytest.raises(FileError) as exc_info:
        parse_document_bytes(b"", ".pdf")
    assert exc_info.value.error_code == "FILE_PARSE_ERROR"
```

**Testing validation errors:**
```python
def test_validate_file_extension_invalid(self):
    with pytest.raises(ValidationError) as exc_info:
        validate_file_extension("file.exe", ["pdf", "docx"])
    assert "nicht erlaubt" in str(exc_info.value)
```

**Testing error handlers:**
```python
@patch('services.ai_service.AIService._call_claude')
def test_claude_api_error_handling(mock_claude):
    mock_claude.side_effect = Exception("API key invalid")
    ai = AIService()
    result = ai.call("test")  # Should fallback gracefully
    assert result is None  # Or returns via Ollama
```

## Environment Setup

### Testing Configuration

**Environment before imports (conftest.py):**
```python
# Set testing environment before importing anything
os.environ["TESTING"] = "true"
os.environ["ENVIRONMENT"] = "development"

# This ensures:
# - settings.TESTING = True
# - settings.DEBUG = True (development mode)
# - No production-only services start
```

**Database setup:**
```python
# Would configure test database (SQLite) instead of production DB
# Currently not seen in conftest, may use in-memory data structures
```

## Frontend Testing Notes

**Status:** No tests currently exist

**Missing coverage:**
- Components (FileUpload, StatusBadge, etc.)
- Context providers (AuthContext, AppContext)
- API client (api.js)
- Hooks (useSSE)

**Would require:**
```json
{
  "devDependencies": {
    "vitest": "^latest",
    "jsdom": "^latest",
    "@testing-library/react": "^latest"
  }
}
```

**Recommended patterns (if added):**
```javascript
// Example structure for future tests
describe('FileUpload component', () => {
  it('should accept valid file extensions', () => {
    // Test component
  })

  it('should reject invalid extensions', () => {
    // Test validation
  })
})
```

## Test Execution

### Run All Tests
```bash
cd backend
pytest
```

### Run Specific Test File
```bash
pytest tests/test_product_matcher.py -v
```

### Run Specific Test Class
```bash
pytest tests/test_document_parser.py::TestDocumentParser -v
```

### Run Specific Test
```bash
pytest tests/test_document_parser.py::TestDocumentParser::test_get_format_pdf -v
```

### Watch Mode
```bash
# Install: pip install pytest-watch
ptw
```

### Coverage Report
```bash
# Install: pip install pytest-cov
pytest --cov=backend --cov-report=html --cov-report=term-missing
```

### Verbose Output
```bash
pytest -vv --tb=long  # Very verbose with full tracebacks
pytest -v --tb=short  # Verbose with short tracebacks (default)
pytest --tb=no        # No tracebacks, just pass/fail
```

---

*Testing analysis: 2026-03-10*
