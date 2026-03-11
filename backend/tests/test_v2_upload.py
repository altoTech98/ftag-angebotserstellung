"""
Tests for V2 upload endpoint with tender_id session management.

Tests multi-file upload, tender session creation, file appending,
immediate parsing, and tender status retrieval.
"""

import io
import uuid

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook

from v2.routers.upload_v2 import router, _tenders

# Create a minimal FastAPI app for testing
from fastapi import FastAPI

app = FastAPI()
app.include_router(router)

client = TestClient(app)


@pytest.fixture(autouse=True)
def clear_tenders():
    """Clear tender storage before each test."""
    _tenders.clear()
    yield
    _tenders.clear()


def _make_xlsx_bytes() -> bytes:
    """Create minimal XLSX bytes for testing."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Tuerliste"
    ws.append(["Tuer Nr.", "Breite", "Hoehe"])
    ws.append(["1.01", 1000, 2100])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def _make_txt_bytes() -> bytes:
    """Create simple text bytes (unsupported format)."""
    return b"Some text content"


class TestUploadSingleFile:
    """POST /api/v2/upload with one file creates a tender."""

    def test_upload_single_file_creates_tender(self, sample_pdf_bytes):
        response = client.post(
            "/api/v2/upload",
            files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
        )
        assert response.status_code == 200
        data = response.json()
        # Should return a valid UUID tender_id
        uuid.UUID(data["tender_id"])  # Raises if not valid UUID
        assert data["total_files"] == 1
        assert len(data["files"]) == 1
        assert data["files"][0]["filename"] == "test.pdf"

    def test_upload_returns_file_metadata(self, sample_pdf_bytes):
        response = client.post(
            "/api/v2/upload",
            files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
        )
        data = response.json()
        file_meta = data["files"][0]
        assert "filename" in file_meta
        assert "format" in file_meta
        assert "page_count" in file_meta
        assert "warnings" in file_meta


class TestUploadMultipleFiles:
    """POST /api/v2/upload with multiple files."""

    def test_upload_multiple_files(self, sample_pdf_bytes, sample_docx_bytes, sample_xlsx_bytes):
        response = client.post(
            "/api/v2/upload",
            files=[
                ("files", ("doc1.pdf", sample_pdf_bytes, "application/pdf")),
                ("files", ("doc2.docx", sample_docx_bytes, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")),
                ("files", ("doc3.xlsx", sample_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")),
            ],
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total_files"] == 3
        assert len(data["files"]) == 3


class TestUploadAppendToTender:
    """POST /api/v2/upload with existing tender_id appends files."""

    def test_upload_append_to_tender(self, sample_pdf_bytes, sample_xlsx_bytes):
        # First upload creates tender
        resp1 = client.post(
            "/api/v2/upload",
            files=[("files", ("doc1.pdf", sample_pdf_bytes, "application/pdf"))],
        )
        tender_id = resp1.json()["tender_id"]

        # Second upload appends to same tender
        resp2 = client.post(
            f"/api/v2/upload?tender_id={tender_id}",
            files=[("files", ("doc2.xlsx", sample_xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        )
        assert resp2.status_code == 200
        data = resp2.json()
        assert data["tender_id"] == tender_id
        assert data["total_files"] == 2  # Cumulative count


class TestUploadParsesImmediately:
    """Upload triggers immediate parsing via Phase 1 parsers."""

    def test_upload_parses_immediately(self):
        xlsx_bytes = _make_xlsx_bytes()
        response = client.post(
            "/api/v2/upload",
            files=[("files", ("tuerliste.xlsx", xlsx_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))],
        )
        assert response.status_code == 200
        data = response.json()
        # format should be xlsx, proving parsing happened
        assert data["files"][0]["format"] == "xlsx"


class TestUploadInvalidTenderId:
    """POST /api/v2/upload with non-existent tender_id returns 404."""

    def test_upload_invalid_tender_id(self, sample_pdf_bytes):
        fake_id = str(uuid.uuid4())
        response = client.post(
            f"/api/v2/upload?tender_id={fake_id}",
            files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
        )
        assert response.status_code == 404


class TestGetTenderStatus:
    """GET /api/v2/tender/{tender_id} returns file list and status."""

    def test_get_tender_status(self, sample_pdf_bytes):
        # Upload first
        resp = client.post(
            "/api/v2/upload",
            files=[("files", ("test.pdf", sample_pdf_bytes, "application/pdf"))],
        )
        tender_id = resp.json()["tender_id"]

        # Get status
        status_resp = client.get(f"/api/v2/tender/{tender_id}")
        assert status_resp.status_code == 200
        data = status_resp.json()
        assert data["tender_id"] == tender_id
        assert data["status"] == "uploading"
        assert len(data["files"]) == 1

    def test_get_tender_status_not_found(self):
        fake_id = str(uuid.uuid4())
        resp = client.get(f"/api/v2/tender/{fake_id}")
        assert resp.status_code == 404
