"""
Integration tests for SSE progress events and job store progress patterns.

Tests structured JSON progress (with position-level fields),
progress throttling, and job completion with plausibility data.
"""

import json
import time
from unittest.mock import patch

import pytest

from services.job_store import create_job, get_job, update_job


class TestStructuredProgress:
    """Tests for structured JSON progress in job store."""

    def test_structured_progress_roundtrip(self):
        """JSON progress with all position-level fields is stored and retrieved correctly."""
        job = create_job()
        progress = {
            "message": "Matching Position 5 von 20",
            "stage": "matching",
            "percent": 55.0,
            "current_position": "T-005",
            "positions_done": 4,
            "positions_total": 20,
        }
        update_job(job.id, status="running", progress=json.dumps(progress))

        retrieved = get_job(job.id)
        assert retrieved is not None
        parsed = json.loads(retrieved.progress)
        assert parsed["stage"] == "matching"
        assert parsed["current_position"] == "T-005"
        assert parsed["positions_done"] == 4
        assert parsed["positions_total"] == 20
        assert parsed["percent"] == 55.0
        assert parsed["message"] == "Matching Position 5 von 20"

    def test_progress_with_none_fields(self):
        """Progress without position-level fields (extraction stage) stores nulls."""
        job = create_job()
        progress = {
            "message": "Pass 1: test.xlsx",
            "stage": "extraction",
            "percent": 15.0,
            "current_position": None,
            "positions_done": None,
            "positions_total": None,
        }
        update_job(job.id, status="running", progress=json.dumps(progress))

        retrieved = get_job(job.id)
        parsed = json.loads(retrieved.progress)
        assert parsed["stage"] == "extraction"
        assert parsed["current_position"] is None
        assert parsed["positions_done"] is None

    def test_adversarial_progress(self):
        """Adversarial stage progress includes position-level fields."""
        job = create_job()
        progress = {
            "message": "Adversarial Check Position 3 von 8",
            "stage": "adversarial",
            "percent": 62.5,
            "current_position": "P-003",
            "positions_done": 2,
            "positions_total": 8,
        }
        update_job(job.id, status="running", progress=json.dumps(progress))

        parsed = json.loads(get_job(job.id).progress)
        assert parsed["stage"] == "adversarial"
        assert parsed["positions_total"] == 8

    def test_gap_analyse_progress(self):
        """Gap analysis stage progress includes position-level fields."""
        job = create_job()
        progress = {
            "message": "Gap-Analyse Position 1 von 5",
            "stage": "gap_analyse",
            "percent": 75.0,
            "current_position": "P-001",
            "positions_done": 0,
            "positions_total": 5,
        }
        update_job(job.id, status="running", progress=json.dumps(progress))

        parsed = json.loads(get_job(job.id).progress)
        assert parsed["stage"] == "gap_analyse"
        assert parsed["positions_total"] == 5


class TestProgressThrottling:
    """Tests for progress update throttling pattern."""

    def test_throttle_skips_rapid_updates(self):
        """Updates within 500ms window should be skipped by throttle logic."""
        _last_progress = [0.0]

        def throttled_update(detail):
            now = time.time()
            if now - _last_progress[0] < 0.5:
                return False  # Skipped
            _last_progress[0] = now
            return True  # Sent

        # First update should go through
        assert throttled_update("first") is True
        # Immediate second should be skipped
        assert throttled_update("second") is False

    def test_throttle_allows_after_delay(self):
        """Updates after 500ms delay should go through."""
        _last_progress = [0.0]

        def throttled_update():
            now = time.time()
            if now - _last_progress[0] < 0.5:
                return False
            _last_progress[0] = now
            return True

        assert throttled_update() is True

        # Mock time to advance past throttle
        with patch("time.time", return_value=_last_progress[0] + 0.6):
            # Need to re-test with mocked time
            now = time.time()
            if now - _last_progress[0] >= 0.5:
                result = True
                _last_progress[0] = now
            else:
                result = False
            assert result is True


class TestJobCompletionWithPlausibility:
    """Tests for job completion including plausibility data."""

    def test_completed_job_with_plausibility_result(self):
        """Completed job result includes plausibility data."""
        job = create_job()
        result = {
            "tender_id": "test-123",
            "status": "completed",
            "total_positionen": 10,
            "plausibility": {
                "passed": True,
                "issues": [],
                "positions_total": 10,
                "positions_matched": 8,
                "positions_unmatched": 2,
                "duplicate_positions": [],
            },
            "analysis_id": "abc12345",
        }
        update_job(job.id, status="completed", result=result)

        retrieved = get_job(job.id)
        assert retrieved.status == "completed"
        assert retrieved.result["plausibility"]["passed"] is True
        assert retrieved.result["plausibility"]["positions_total"] == 10

    def test_failed_job_has_german_error(self):
        """Failed job has German error message."""
        job = create_job()
        update_job(
            job.id,
            status="failed",
            error="KI-Service nicht erreichbar. Bitte Internetverbindung pruefen.",
        )

        retrieved = get_job(job.id)
        assert retrieved.status == "failed"
        assert "KI-Service" in retrieved.error

    def test_job_to_dict_includes_all_fields(self):
        """Job.to_dict() returns all expected fields."""
        job = create_job()
        update_job(job.id, status="running", progress="test")
        d = get_job(job.id).to_dict()
        assert "job_id" in d
        assert "status" in d
        assert "progress" in d
        assert "error" in d
        assert "result" in d
