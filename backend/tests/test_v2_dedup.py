"""
Tests for deduplication module and prompt templates.

Tests cover position merging (exact match, field-level merge, provenance),
pre-filtering, and prompt template content validation.
"""

import pytest

from v2.schemas.common import FieldSource
from v2.schemas.extraction import ExtractedDoorPosition


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pass1_positions():
    """Positions from Pass 1 (structural extraction)."""
    return [
        ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=1000,
            hoehe_mm=2100,
            quellen={
                "breite_mm": FieldSource(dokument="tuerliste.xlsx", konfidenz=0.8),
                "hoehe_mm": FieldSource(dokument="tuerliste.xlsx", konfidenz=0.8),
            },
        ),
        ExtractedDoorPosition(
            positions_nr="1.02",
            breite_mm=900,
            hoehe_mm=2050,
            quellen={
                "breite_mm": FieldSource(dokument="tuerliste.xlsx", konfidenz=0.8),
            },
        ),
    ]


@pytest.fixture
def pass2_positions():
    """Positions from Pass 2 (AI extraction) with some overlapping pos_nr."""
    return [
        ExtractedDoorPosition(
            positions_nr="1.01",
            breite_mm=1010,  # slightly different value (AI correction)
            hoehe_mm=None,   # AI didn't extract this
            brandschutz_freitext="EI30 gemäss Plan",
            quellen={
                "breite_mm": FieldSource(dokument="ausschreibung.pdf", konfidenz=0.9),
                "brandschutz_freitext": FieldSource(dokument="ausschreibung.pdf", konfidenz=0.85),
            },
        ),
        ExtractedDoorPosition(
            positions_nr="2.01",  # New position not in Pass 1
            breite_mm=800,
            hoehe_mm=2000,
            quellen={
                "breite_mm": FieldSource(dokument="ausschreibung.pdf", konfidenz=0.9),
            },
        ),
    ]


# ---------------------------------------------------------------------------
# Dedup Tests
# ---------------------------------------------------------------------------

class TestDedup:

    def test_dedup_exact_match(self, pass1_positions, pass2_positions):
        """Two positions with identical positions_nr are merged, later pass wins."""
        from v2.extraction.dedup import merge_positions

        result = merge_positions(pass1_positions, pass2_positions, pass_priority=2)

        # Should have 3 positions: 1.01 (merged), 1.02, 2.01
        assert len(result) == 3
        pos_nrs = [p.positions_nr for p in result]
        assert "1.01" in pos_nrs
        assert "1.02" in pos_nrs
        assert "2.01" in pos_nrs

        # For 1.01: pass 2 value wins for breite_mm (later pass)
        merged = next(p for p in result if p.positions_nr == "1.01")
        assert merged.breite_mm == 1010  # pass2 value wins

    def test_dedup_keeps_provenance(self, pass1_positions, pass2_positions):
        """Merged position retains the FieldSource of the winning value."""
        from v2.extraction.dedup import merge_positions

        result = merge_positions(pass1_positions, pass2_positions, pass_priority=2)
        merged = next(p for p in result if p.positions_nr == "1.01")

        # breite_mm source should be from pass2 (winner)
        assert "breite_mm" in merged.quellen
        assert merged.quellen["breite_mm"].dokument == "ausschreibung.pdf"

    def test_dedup_adds_new_positions(self, pass1_positions, pass2_positions):
        """Positions with no matching existing entry are appended."""
        from v2.extraction.dedup import merge_positions

        result = merge_positions(pass1_positions, pass2_positions, pass_priority=2)
        new_pos = next(p for p in result if p.positions_nr == "2.01")
        assert new_pos.breite_mm == 800

    def test_dedup_field_merge(self, pass1_positions, pass2_positions):
        """Fields None in winner but set in loser are preserved (fill gaps)."""
        from v2.extraction.dedup import merge_positions

        result = merge_positions(pass1_positions, pass2_positions, pass_priority=2)
        merged = next(p for p in result if p.positions_nr == "1.01")

        # hoehe_mm was None in pass2 but 2100 in pass1 -> should be preserved
        assert merged.hoehe_mm == 2100

        # brandschutz_freitext was only in pass2 -> should be present
        assert merged.brandschutz_freitext == "EI30 gemäss Plan"

    def test_dedup_pre_filter(self, pass1_positions, pass2_positions):
        """Exact positions_nr matches are identified without AI."""
        from v2.extraction.dedup import merge_positions

        # Just verifying merge_positions works without AI client
        result = merge_positions(pass1_positions, pass2_positions, pass_priority=2)
        assert len(result) == 3


# ---------------------------------------------------------------------------
# Prompt Template Tests
# ---------------------------------------------------------------------------

class TestPrompts:

    def test_prompts_pass2_contains_required_sections(self):
        """PASS2_SYSTEM_PROMPT has extraction instructions and field list."""
        from v2.extraction.prompts import PASS2_SYSTEM_PROMPT

        assert isinstance(PASS2_SYSTEM_PROMPT, str)
        assert len(PASS2_SYSTEM_PROMPT) > 100

        # Must contain key instructions
        prompt_lower = PASS2_SYSTEM_PROMPT.lower()
        assert "position" in prompt_lower
        assert "experte" in prompt_lower or "expert" in prompt_lower
        # "lieber zu viel als zu wenig" guidance
        assert "zu viel" in prompt_lower or "over-extract" in prompt_lower

    def test_prompts_pass3_contains_required_sections(self):
        """PASS3_SYSTEM_PROMPT has gap checking and adversarial review instructions."""
        from v2.extraction.prompts import PASS3_SYSTEM_PROMPT

        assert isinstance(PASS3_SYSTEM_PROMPT, str)
        assert len(PASS3_SYSTEM_PROMPT) > 100

        prompt_lower = PASS3_SYSTEM_PROMPT.lower()
        # Must mention validation/checking
        assert any(kw in prompt_lower for kw in ("prüf", "kontroll", "validier", "check", "review"))
        # Must mention correction
        assert any(kw in prompt_lower for kw in ("korrektur", "korrigier", "correct", "fehlend"))

    def test_prompts_dedup_template(self):
        """DEDUP_PROMPT_TEMPLATE accepts positions_json parameter."""
        from v2.extraction.prompts import DEDUP_PROMPT_TEMPLATE

        assert isinstance(DEDUP_PROMPT_TEMPLATE, str)
        assert "{positions_json}" in DEDUP_PROMPT_TEMPLATE

        # Should be formattable
        formatted = DEDUP_PROMPT_TEMPLATE.format(positions_json='[{"pos": "1.01"}]')
        assert '[{"pos": "1.01"}]' in formatted

    def test_prompts_pass2_user_template(self):
        """PASS2_USER_TEMPLATE has chunk_text and existing_positions_json placeholders."""
        from v2.extraction.prompts import PASS2_USER_TEMPLATE

        assert "{chunk_text}" in PASS2_USER_TEMPLATE
        assert "{existing_positions_json}" in PASS2_USER_TEMPLATE

    def test_prompts_pass3_user_template(self):
        """PASS3_USER_TEMPLATE has all_positions_json and original_texts placeholders."""
        from v2.extraction.prompts import PASS3_USER_TEMPLATE

        assert "{all_positions_json}" in PASS3_USER_TEMPLATE
        assert "{original_texts}" in PASS3_USER_TEMPLATE
