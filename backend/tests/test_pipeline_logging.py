"""
Tests for pipeline step logging helper.
"""

import logging
import pytest

from v2.pipeline_logging import log_step


class TestLogStep:
    def test_log_step_writes_structured_entry(self, caplog):
        """log_step produces a log record with tender_id, stage, position_nr, pass_num, result in extra."""
        with caplog.at_level(logging.INFO, logger="v2.pipeline"):
            log_step(
                tender_id="T-001",
                stage="matching",
                position_nr="1.01",
                pass_num=2,
                result="matched",
                details={"konfidenz": 0.85},
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]

        # Check the extra fields
        assert record.tender_id == "T-001"
        assert record.stage == "matching"
        assert record.position_nr == "1.01"
        assert record.pass_num == 2
        assert record.result == "matched"
        assert record.details == {"konfidenz": 0.85}

        # Check the formatted message contains the key info
        assert "T-001" in record.message
        assert "matching" in record.message
        assert "1.01" in record.message
        assert "Pass 2" in record.message
        assert "matched" in record.message

    def test_log_step_defaults_details_to_none(self, caplog):
        """log_step works without details parameter."""
        with caplog.at_level(logging.INFO, logger="v2.pipeline"):
            log_step(
                tender_id="T-002",
                stage="extraction",
                position_nr="2.01",
                pass_num=1,
                result="extracted",
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        assert record.details is None

    def test_log_step_level_is_info(self, caplog):
        """log_step logs at INFO level."""
        with caplog.at_level(logging.DEBUG, logger="v2.pipeline"):
            log_step(
                tender_id="T-003",
                stage="validation",
                position_nr="3.01",
                pass_num=1,
                result="validated",
            )

        assert caplog.records[0].levelno == logging.INFO
