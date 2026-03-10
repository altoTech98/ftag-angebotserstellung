"""
Tests for V2 analyze endpoint and router registration.

Tests analysis trigger, tender validation, file sorting,
pipeline integration, error handling, and v2 route registration.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from v2.parsers.base import ParseResult
from v2.routers.upload_v2 import router as upload_router, _tenders
from v2.routers.analyze_v2 import router as analyze_router
from v2.schemas.common import DokumentTyp
from v2.schemas.extraction import ExtractionResult, ExtractedDoorPosition

# Create a minimal FastAPI app for testing
app = FastAPI()
app.include_router(upload_router)
app.include_router(analyze_router)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_tenders():
    """Clear tender storage before each test."""
    _tenders.clear()
    yield
    _tenders.clear()


def _make_sample_tender_with_parse_results():
    """Create a tender with ParseResult objects for pipeline testing."""
    tender_id = str(uuid.uuid4())
    pr = ParseResult(
        text="tuer_nr: 1.01 | breite: 1000 | hoehe: 2100",
        format="xlsx",
        page_count=1,
        warnings=[],
        metadata={"detected_columns": {"Sheet1": {"tuer_nr": "A", "breite": "B", "hoehe": "C", "brandschutz": "D"}}},
        source_file="test_tuerliste.xlsx",
        tables=[],
    )
    _tenders[tender_id] = {
        "files": [pr],
        "status": "uploading",
        "created_at": datetime.now(timezone.utc),
    }
    return tender_id


def _make_mock_extraction_result():
    """Create a sample ExtractionResult for mocking."""
    return ExtractionResult(
        positionen=[
            ExtractedDoorPosition(
                positions_nr="1.01",
                breite_mm=1000,
                hoehe_mm=2100,
                quellen={},
            ),
            ExtractedDoorPosition(
                positions_nr="1.02",
                breite_mm=900,
                hoehe_mm=2050,
                quellen={},
            ),
        ],
        dokument_zusammenfassung="Test extraction from 1 document",
        warnungen=["Test warning"],
        dokument_typ=DokumentTyp.XLSX,
    )


class TestAnalyzeCallsPipeline:
    """POST /api/v2/analyze calls run_extraction_pipeline with correct args."""

    def test_analyze_calls_pipeline(self):
        tender_id = _make_sample_tender_with_parse_results()
        mock_result = _make_mock_extraction_result()

        async def mock_pipeline(parse_results, tid, **kwargs):
            # Verify correct args
            assert len(parse_results) == 1
            assert parse_results[0].format == "xlsx"
            assert tid == tender_id
            return mock_result

        with patch("v2.routers.analyze_v2.run_extraction_pipeline", side_effect=mock_pipeline):
            resp = client.post(
                "/api/v2/analyze",
                json={"tender_id": tender_id},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["tender_id"] == tender_id
            assert data["status"] == "completed"


class TestAnalyzeReturnsPositions:
    """POST /api/v2/analyze returns positionen list from pipeline result."""

    def test_analyze_returns_positions(self):
        tender_id = _make_sample_tender_with_parse_results()
        mock_result = _make_mock_extraction_result()

        async def mock_pipeline(*args, **kwargs):
            return mock_result

        with patch("v2.routers.analyze_v2.run_extraction_pipeline", side_effect=mock_pipeline):
            resp = client.post(
                "/api/v2/analyze",
                json={"tender_id": tender_id},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert len(data["positionen"]) == 2
            assert data["positionen"][0]["positions_nr"] == "1.01"
            assert data["positionen"][1]["positions_nr"] == "1.02"
            assert data["total_positionen"] == 2
            assert data["zusammenfassung"] == "Test extraction from 1 document"
            assert data["warnungen"] == ["Test warning"]


class TestAnalyzeHandlesPipelineError:
    """If pipeline raises, endpoint returns 500 with error message."""

    def test_analyze_handles_pipeline_error(self):
        tender_id = _make_sample_tender_with_parse_results()

        async def failing_pipeline(*args, **kwargs):
            raise RuntimeError("AI service unavailable")

        with patch("v2.routers.analyze_v2.run_extraction_pipeline", side_effect=failing_pipeline):
            resp = client.post(
                "/api/v2/analyze",
                json={"tender_id": tender_id},
            )
            assert resp.status_code == 500
            assert "AI service unavailable" in resp.json()["detail"]

        # Tender status should be set to error
        assert _tenders[tender_id]["status"] == "error"


class TestAnalyzeInvalidTender:
    """POST /api/v2/analyze with unknown tender_id returns 404."""

    def test_analyze_invalid_tender(self):
        fake_id = str(uuid.uuid4())
        resp = client.post(
            "/api/v2/analyze",
            json={"tender_id": fake_id},
        )
        assert resp.status_code == 404


class TestAnalyzeNoFiles:
    """POST /api/v2/analyze with tender that has 0 files returns 400."""

    def test_analyze_no_files(self):
        # Create empty tender directly
        tender_id = str(uuid.uuid4())
        _tenders[tender_id] = {
            "files": [],
            "status": "uploading",
            "created_at": datetime.now(timezone.utc),
        }

        resp = client.post(
            "/api/v2/analyze",
            json={"tender_id": tender_id},
        )
        assert resp.status_code == 400


class TestV2RoutesRegistered:
    """V2 routes are accessible (registered correctly)."""

    def test_v2_routes_registered(self):
        # GET on /api/v2/upload should return 405 (method not allowed)
        # proving the route exists but only accepts POST
        resp = client.get("/api/v2/upload")
        assert resp.status_code == 405
