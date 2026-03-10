"""
Tests for V2 analyze endpoint and router registration.

Tests analysis trigger, tender validation, file sorting,
and v2 route registration in main.py.
"""

import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from v2.routers.upload_v2 import router as upload_router, _tenders
from v2.routers.analyze_v2 import router as analyze_router

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


class TestAnalyzeReturnsStub:
    """POST /api/v2/analyze with valid tender returns stub extraction."""

    def test_analyze_returns_extraction_stub(self, sample_xlsx_bytes):
        # Upload a file first
        resp = client.post(
            "/api/v2/upload",
            files=[("files", ("tuerliste.xlsx", sample_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        )
        tender_id = resp.json()["tender_id"]

        # Trigger analysis
        resp2 = client.post(
            "/api/v2/analyze",
            json={"tender_id": tender_id},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["tender_id"] == tender_id
        assert data["status"] == "completed"
        assert "positionen" in data
        assert isinstance(data["positionen"], list)
        assert "warnungen" in data
        assert isinstance(data["warnungen"], list)


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
        from datetime import datetime, timezone
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


class TestFileSorting:
    """Files are sorted by format priority: xlsx > pdf > docx."""

    def test_file_sort_order(self, sample_pdf_bytes, sample_docx_bytes, sample_xlsx_bytes):
        # Upload files in non-priority order
        resp = client.post(
            "/api/v2/upload",
            files=[
                ("files", ("doc.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                ("files", ("scan.pdf", sample_pdf_bytes, "application/pdf")),
                ("files", ("liste.xlsx", sample_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ],
        )
        tender_id = resp.json()["tender_id"]

        # Trigger analysis
        resp2 = client.post(
            "/api/v2/analyze",
            json={"tender_id": tender_id},
        )
        assert resp2.status_code == 200
        data = resp2.json()
        # Check that sorted_files shows xlsx first, then pdf, then docx
        sorted_files = data["sorted_files"]
        assert sorted_files[0]["format"] == "xlsx"
        assert sorted_files[1]["format"] == "pdf"
        assert sorted_files[2]["format"] == "docx"
