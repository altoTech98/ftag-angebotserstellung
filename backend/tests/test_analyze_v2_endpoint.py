"""
Integration tests for V2 async analyze endpoint.

Tests POST /api/v2/analyze, GET /api/v2/analyze/status/{job_id},
and background job execution pattern.
"""

import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from v2.routers.analyze_v2 import router, _analysis_results
from v2.parsers.base import ParseResult


@pytest.fixture
def app():
    """Create a minimal FastAPI app with v2 router."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_tender():
    """Create a mock tender with ParseResult objects in _tenders."""
    from v2.routers.analyze_v2 import _tenders

    tender_id = "test-tender-001"
    pr = ParseResult(
        format="xlsx",
        source_file="test.xlsx",
        text="Position 1|Tuer|T30|1",
        page_count=1,
        tables=[],
        metadata={},
    )
    _tenders[tender_id] = {
        "files": [pr],
        "status": "uploaded",
    }
    yield tender_id
    _tenders.pop(tender_id, None)


class TestAnalyzeV2Endpoint:
    """Tests for POST /api/v2/analyze."""

    def test_analyze_returns_job_id(self, client, mock_tender):
        """POST /api/v2/analyze with valid tender returns job_id and status started."""
        with patch("v2.routers.analyze_v2.run_in_background") as mock_bg:
            mock_bg.return_value = None
            resp = client.post("/api/v2/analyze", json={"tender_id": mock_tender})

        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] == "started"
        assert len(data["job_id"]) > 0

    def test_analyze_invalid_tender_returns_404(self, client):
        """POST /api/v2/analyze with unknown tender returns 404."""
        resp = client.post("/api/v2/analyze", json={"tender_id": "nonexistent-999"})
        assert resp.status_code == 404

    def test_analyze_empty_tender_returns_400(self, client):
        """POST /api/v2/analyze with no files returns 400."""
        from v2.routers.analyze_v2 import _tenders
        tid = "empty-tender"
        _tenders[tid] = {"files": [], "status": "uploaded"}
        try:
            resp = client.post("/api/v2/analyze", json={"tender_id": tid})
            assert resp.status_code == 400
        finally:
            _tenders.pop(tid, None)


class TestStatusEndpoint:
    """Tests for GET /api/v2/analyze/status/{job_id}."""

    def test_status_returns_job_dict(self, client):
        """GET /api/v2/analyze/status returns job status."""
        from services.job_store import create_job, update_job

        job = create_job()
        update_job(job.id, status="running", progress="test progress")

        resp = client.get(f"/api/v2/analyze/status/{job.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["job_id"] == job.id
        assert data["status"] == "running"
        assert data["progress"] == "test progress"

    def test_status_unknown_job_returns_404(self, client):
        """GET /api/v2/analyze/status with unknown job returns 404."""
        resp = client.get("/api/v2/analyze/status/nonexistent-job")
        assert resp.status_code == 404


class TestBackgroundJobPattern:
    """Tests for the background job execution pattern."""

    def test_job_receives_structured_progress(self, client):
        """update_job with JSON progress is retrievable via status endpoint."""
        from services.job_store import create_job, update_job

        job = create_job()
        progress_data = json.dumps({
            "message": "Matching Position 3 von 10",
            "stage": "matching",
            "percent": 45.0,
            "current_position": "P003",
            "positions_done": 2,
            "positions_total": 10,
        })
        update_job(job.id, status="running", progress=progress_data)

        resp = client.get(f"/api/v2/analyze/status/{job.id}")
        data = resp.json()
        progress = json.loads(data["progress"])
        assert progress["stage"] == "matching"
        assert progress["current_position"] == "P003"
        assert progress["positions_done"] == 2
        assert progress["positions_total"] == 10
        assert progress["percent"] == 45.0
