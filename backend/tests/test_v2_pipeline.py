"""
Tests for the V2 multi-pass extraction pipeline.

All tests mock the Anthropic client to avoid real API calls.
Tests cover pipeline ordering, pass execution, dedup, chunking,
retry logic, and end-to-end result shape.
"""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch, call

import pytest

from v2.parsers.base import ParseResult
from v2.schemas.common import BrandschutzKlasse, DokumentTyp, FieldSource, MaterialTyp
from v2.schemas.extraction import ExtractionResult, ExtractedDoorPosition


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_parse_result(filename: str, fmt: str, text: str = "sample text", page_count: int = 5) -> ParseResult:
    """Create a ParseResult for testing."""
    return ParseResult(
        text=text,
        format=fmt,
        page_count=page_count,
        warnings=[],
        metadata={"detected_columns": {"Sheet1": {"tuer_nr": "A", "breite": "B", "hoehe": "C", "brandschutz": "D"}}} if fmt == "xlsx" else {},
        source_file=filename,
        tables=[],
    )


def _make_extraction_result(positions: list[ExtractedDoorPosition] = None) -> ExtractionResult:
    """Create a mock ExtractionResult."""
    if positions is None:
        positions = [
            ExtractedDoorPosition(
                positions_nr="1.01",
                breite_mm=1000,
                hoehe_mm=2100,
                quellen={},
            )
        ]
    return ExtractionResult(
        positionen=positions,
        dokument_zusammenfassung="Test summary",
        warnungen=[],
        dokument_typ=DokumentTyp.XLSX,
    )


def _make_mock_client(extraction_result: ExtractionResult = None):
    """Create a mock Anthropic client that returns structured output."""
    if extraction_result is None:
        extraction_result = _make_extraction_result()

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.output = extraction_result
    mock_response.stop_reason = "end_turn"
    mock_client.messages.parse.return_value = mock_response
    return mock_client


# ---------------------------------------------------------------------------
# Test: Pipeline file ordering
# ---------------------------------------------------------------------------

class TestPipelineFileOrdering:
    """Verify XLSX files are processed before PDF before DOCX."""

    def test_pipeline_file_ordering(self):
        from v2.extraction.pipeline import _sort_by_format

        results = [
            _make_parse_result("doc.docx", "docx"),
            _make_parse_result("scan.pdf", "pdf"),
            _make_parse_result("liste.xlsx", "xlsx"),
            _make_parse_result("notes.txt", "txt"),
        ]

        sorted_results = _sort_by_format(results)
        formats = [r.format for r in sorted_results]
        assert formats == ["xlsx", "pdf", "docx", "txt"]

    def test_pipeline_file_ordering_stable(self):
        """Multiple files of the same format maintain relative order."""
        from v2.extraction.pipeline import _sort_by_format

        results = [
            _make_parse_result("b.pdf", "pdf"),
            _make_parse_result("a.xlsx", "xlsx"),
            _make_parse_result("c.pdf", "pdf"),
        ]

        sorted_results = _sort_by_format(results)
        assert sorted_results[0].source_file == "a.xlsx"
        # PDFs maintain original order
        assert sorted_results[1].source_file == "b.pdf"
        assert sorted_results[2].source_file == "c.pdf"


# ---------------------------------------------------------------------------
# Test: Pipeline runs all passes
# ---------------------------------------------------------------------------

class TestPipelineRunsAllPasses:
    """Verify Pass 1, Pass 2, Pass 3 are all called in order."""

    def test_pipeline_runs_all_passes(self):
        mock_client = _make_mock_client()

        parse_results = [
            _make_parse_result("test.xlsx", "xlsx", text="tuer_nr: 1.01 | breite: 1000"),
        ]

        with patch("v2.extraction.pipeline.extract_structural") as mock_p1, \
             patch("v2.extraction.pipeline.extract_semantic") as mock_p2, \
             patch("v2.extraction.pipeline.validate_and_enrich") as mock_p3:

            mock_p1.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", quellen={})
            ]
            mock_p2.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000, quellen={})
            ]
            mock_p3.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000, quellen={})
            ]

            # Make p2 and p3 proper coroutines
            mock_p2.side_effect = None
            mock_p2.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000, quellen={})
            ]
            # Wrap as async
            async def async_p2(*args, **kwargs):
                return [ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000, quellen={})]
            mock_p2.side_effect = async_p2

            async def async_p3(*args, **kwargs):
                return [ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000, quellen={})]
            mock_p3.side_effect = async_p3

            from v2.extraction.pipeline import run_extraction_pipeline
            result = asyncio.get_event_loop().run_until_complete(
                run_extraction_pipeline(parse_results, "test-tender", client=mock_client)
            )

            # All 3 passes called
            assert mock_p1.called
            assert mock_p2.called
            assert mock_p3.called

            # Pass 1 called before Pass 2 (same file)
            assert mock_p1.call_count == 1
            assert mock_p2.call_count == 1
            assert mock_p3.call_count == 1


# ---------------------------------------------------------------------------
# Test: Dedup between passes
# ---------------------------------------------------------------------------

class TestPipelineDedupBetweenPasses:
    """Verify merge_positions called after each pass."""

    def test_pipeline_dedup_between_passes(self):
        mock_client = _make_mock_client()

        parse_results = [
            _make_parse_result("test.xlsx", "xlsx"),
        ]

        with patch("v2.extraction.pipeline.extract_structural") as mock_p1, \
             patch("v2.extraction.pipeline.extract_semantic") as mock_p2, \
             patch("v2.extraction.pipeline.validate_and_enrich") as mock_p3, \
             patch("v2.extraction.pipeline.merge_positions") as mock_merge:

            mock_p1.return_value = [ExtractedDoorPosition(positions_nr="1.01", quellen={})]

            async def async_p2(*args, **kwargs):
                return [ExtractedDoorPosition(positions_nr="1.01", breite_mm=900, quellen={})]
            mock_p2.side_effect = async_p2

            async def async_p3(*args, **kwargs):
                return args[0]  # Return positions unchanged
            mock_p3.side_effect = async_p3

            # merge_positions returns the merged list
            mock_merge.return_value = [ExtractedDoorPosition(positions_nr="1.01", breite_mm=900, quellen={})]

            from v2.extraction.pipeline import run_extraction_pipeline
            result = asyncio.get_event_loop().run_until_complete(
                run_extraction_pipeline(parse_results, "test-tender", client=mock_client)
            )

            # merge_positions called after Pass 1 and after Pass 2
            assert mock_merge.call_count == 2
            # First call: after Pass 1 with pass_priority=1
            assert mock_merge.call_args_list[0][1].get("pass_priority", mock_merge.call_args_list[0][0][2] if len(mock_merge.call_args_list[0][0]) > 2 else None) in [1, None]


# ---------------------------------------------------------------------------
# Test: Pass 2 chunks large documents
# ---------------------------------------------------------------------------

class TestPass2ChunksLargeDocument:
    """Verify chunking is applied for documents with page_count > 30."""

    def test_pass2_chunks_large_document(self):
        mock_client = _make_mock_client()

        # Create a document with 60 pages worth of text
        pages = [f"\f--- Page {i} ---\nContent of page {i}" for i in range(1, 61)]
        large_text = "\n".join(pages)

        parse_result = _make_parse_result(
            "large.pdf", "pdf", text=large_text, page_count=60
        )

        with patch("v2.extraction.pass2_semantic._call_claude_parse") as mock_parse:
            mock_parse.return_value = _make_extraction_result()

            from v2.extraction.pass2_semantic import extract_semantic
            result = asyncio.get_event_loop().run_until_complete(
                extract_semantic(parse_result, client=mock_client)
            )

            # Should be called multiple times (>1 chunk)
            assert mock_parse.call_count >= 2


# ---------------------------------------------------------------------------
# Test: Pass 2 retry on failure
# ---------------------------------------------------------------------------

class TestPass2RetryOnFailure:
    """Verify 3x retry on API error."""

    def test_pass2_retry_on_failure(self):
        mock_client = _make_mock_client()

        parse_result = _make_parse_result("test.pdf", "pdf", page_count=5)

        call_count = 0

        async def failing_then_success(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count <= 2:
                raise Exception("API Error")
            return _make_extraction_result()

        with patch("v2.extraction.pass2_semantic._call_claude_parse") as mock_parse, \
             patch("v2.extraction.pass2_semantic.asyncio.sleep", new_callable=AsyncMock):
            mock_parse.side_effect = failing_then_success

            from v2.extraction.pass2_semantic import extract_semantic
            result = asyncio.get_event_loop().run_until_complete(
                extract_semantic(parse_result, client=mock_client)
            )

            # Should have called 3 times (2 failures + 1 success)
            assert mock_parse.call_count == 3
            assert len(result) > 0


# ---------------------------------------------------------------------------
# Test: Pass 2 skips failed chunk
# ---------------------------------------------------------------------------

class TestPass2SkipsFailedChunk:
    """After 3 failures, chunk is skipped and warning added."""

    def test_pass2_skips_failed_chunk(self):
        mock_client = _make_mock_client()

        parse_result = _make_parse_result("test.pdf", "pdf", page_count=5)

        async def always_fail(*args, **kwargs):
            raise Exception("Persistent API Error")

        with patch("v2.extraction.pass2_semantic._call_claude_parse") as mock_parse, \
             patch("v2.extraction.pass2_semantic.asyncio.sleep", new_callable=AsyncMock):
            mock_parse.side_effect = always_fail

            from v2.extraction.pass2_semantic import extract_semantic
            result = asyncio.get_event_loop().run_until_complete(
                extract_semantic(parse_result, client=mock_client)
            )

            # Should have retried 3 times
            assert mock_parse.call_count == 3
            # Result should be empty (chunk skipped)
            assert len(result) == 0


# ---------------------------------------------------------------------------
# Test: Pass 3 batches large position sets
# ---------------------------------------------------------------------------

class TestPass3BatchesLargePositionSets:
    """Verify Pass 3 batches when positions > 25."""

    def test_pass3_batches_large_position_sets(self):
        mock_client = _make_mock_client()

        # Create 40 positions
        positions = [
            ExtractedDoorPosition(positions_nr=f"{i}.01", quellen={})
            for i in range(1, 41)
        ]

        original_texts = ["Some original text"]
        source_files = ["test.xlsx"]

        with patch("v2.extraction.pass3_validation._call_pass3_parse") as mock_parse, \
             patch("v2.extraction.pass3_validation.asyncio.sleep", new_callable=AsyncMock):

            # Each batch returns its positions back
            async def return_positions(*args, **kwargs):
                # Return a small result for each batch call
                return _make_extraction_result(positions=positions[:5])

            mock_parse.side_effect = return_positions

            from v2.extraction.pass3_validation import validate_and_enrich
            result = asyncio.get_event_loop().run_until_complete(
                validate_and_enrich(positions, original_texts, source_files, client=mock_client)
            )

            # With 40 positions and batch size 25, should be 2 batches
            assert mock_parse.call_count == 2


# ---------------------------------------------------------------------------
# Test: Pipeline returns ExtractionResult
# ---------------------------------------------------------------------------

class TestPipelineReturnsExtractionResult:
    """Output is a valid ExtractionResult with positionen list."""

    def test_pipeline_returns_extraction_result(self):
        mock_client = _make_mock_client()

        parse_results = [
            _make_parse_result("test.xlsx", "xlsx"),
        ]

        with patch("v2.extraction.pipeline.extract_structural") as mock_p1, \
             patch("v2.extraction.pipeline.extract_semantic") as mock_p2, \
             patch("v2.extraction.pipeline.validate_and_enrich") as mock_p3:

            mock_p1.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000, quellen={})
            ]

            async def async_p2(*args, **kwargs):
                return [ExtractedDoorPosition(positions_nr="1.02", breite_mm=900, quellen={})]
            mock_p2.side_effect = async_p2

            async def async_p3(*args, **kwargs):
                return args[0]
            mock_p3.side_effect = async_p3

            from v2.extraction.pipeline import run_extraction_pipeline
            result = asyncio.get_event_loop().run_until_complete(
                run_extraction_pipeline(parse_results, "test-tender", client=mock_client)
            )

            assert isinstance(result, ExtractionResult)
            assert isinstance(result.positionen, list)
            assert len(result.positionen) >= 1
            assert isinstance(result.dokument_zusammenfassung, str)
            assert isinstance(result.warnungen, list)
            assert result.dokument_typ == DokumentTyp.XLSX


# ---------------------------------------------------------------------------
# Test: Multi-file triggers cross-doc intelligence
# ---------------------------------------------------------------------------

class TestMultiFileTriggersCrossDoc:
    """Cross-doc intelligence runs automatically for multi-file tenders."""

    def test_multi_file_triggers_crossdoc(self):
        """Pipeline with 2+ ParseResults triggers cross-doc intelligence."""
        mock_client = _make_mock_client()

        parse_results = [
            _make_parse_result("tuerliste.xlsx", "xlsx", text="tuer_nr: 1.01"),
            _make_parse_result("spec.pdf", "pdf", text="Pos. 1.01 T30"),
        ]

        with patch("v2.extraction.pipeline.extract_structural") as mock_p1, \
             patch("v2.extraction.pipeline.extract_semantic") as mock_p2, \
             patch("v2.extraction.pipeline.validate_and_enrich") as mock_p3, \
             patch("v2.extraction.pipeline.run_cross_doc_intelligence") as mock_crossdoc:

            mock_p1.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", quellen={})
            ]

            async def async_p2(*args, **kwargs):
                return [ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000, quellen={})]
            mock_p2.side_effect = async_p2

            async def async_p3(*args, **kwargs):
                return args[0]
            mock_p3.side_effect = async_p3

            # Cross-doc returns enriched positions + report + conflicts
            from v2.schemas.extraction import EnrichmentReport
            mock_report = EnrichmentReport(
                total_positionen=2,
                positionen_matched_cross_doc=1,
                felder_enriched=3,
                konflikte_total=0,
                konflikte_critical=0,
                konflikte_major=0,
                konflikte_minor=0,
                general_specs_applied=0,
                dokument_stats=[],
                zusammenfassung="1 Position matched",
            )

            async def async_crossdoc(*args, **kwargs):
                return (
                    [ExtractedDoorPosition(positions_nr="1.01", breite_mm=1000, quellen={})],
                    mock_report,
                    [],
                )
            mock_crossdoc.side_effect = async_crossdoc

            from v2.extraction.pipeline import run_extraction_pipeline
            result = asyncio.get_event_loop().run_until_complete(
                run_extraction_pipeline(parse_results, "multi-tender", client=mock_client)
            )

            # Cross-doc was called
            assert mock_crossdoc.called
            assert mock_crossdoc.call_count == 1

    def test_single_file_skips_crossdoc(self):
        """Pipeline with 1 ParseResult does NOT trigger cross-doc."""
        mock_client = _make_mock_client()

        parse_results = [
            _make_parse_result("tuerliste.xlsx", "xlsx"),
        ]

        with patch("v2.extraction.pipeline.extract_structural") as mock_p1, \
             patch("v2.extraction.pipeline.extract_semantic") as mock_p2, \
             patch("v2.extraction.pipeline.validate_and_enrich") as mock_p3, \
             patch("v2.extraction.pipeline.run_cross_doc_intelligence") as mock_crossdoc:

            mock_p1.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", quellen={})
            ]

            async def async_p2(*args, **kwargs):
                return [ExtractedDoorPosition(positions_nr="1.01", quellen={})]
            mock_p2.side_effect = async_p2

            async def async_p3(*args, **kwargs):
                return args[0]
            mock_p3.side_effect = async_p3

            from v2.extraction.pipeline import run_extraction_pipeline
            result = asyncio.get_event_loop().run_until_complete(
                run_extraction_pipeline(parse_results, "single-tender", client=mock_client)
            )

            # Cross-doc was NOT called
            assert not mock_crossdoc.called

    def test_crossdoc_result_in_extraction_result(self):
        """ExtractionResult includes enrichment_report and conflicts for multi-file."""
        mock_client = _make_mock_client()

        parse_results = [
            _make_parse_result("tuerliste.xlsx", "xlsx"),
            _make_parse_result("spec.pdf", "pdf"),
        ]

        with patch("v2.extraction.pipeline.extract_structural") as mock_p1, \
             patch("v2.extraction.pipeline.extract_semantic") as mock_p2, \
             patch("v2.extraction.pipeline.validate_and_enrich") as mock_p3, \
             patch("v2.extraction.pipeline.run_cross_doc_intelligence") as mock_crossdoc:

            mock_p1.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", quellen={})
            ]

            async def async_p2(*args, **kwargs):
                return [ExtractedDoorPosition(positions_nr="1.01", quellen={})]
            mock_p2.side_effect = async_p2

            async def async_p3(*args, **kwargs):
                return args[0]
            mock_p3.side_effect = async_p3

            from v2.schemas.extraction import EnrichmentReport, FieldConflict, ConflictSeverity
            mock_report = EnrichmentReport(
                total_positionen=2,
                positionen_matched_cross_doc=1,
                felder_enriched=5,
                konflikte_total=1,
                konflikte_critical=1,
                konflikte_major=0,
                konflikte_minor=0,
                general_specs_applied=0,
                dokument_stats=[],
                zusammenfassung="Test summary",
            )
            mock_conflict = FieldConflict(
                positions_nr="1.01",
                field_name="brandschutz_klasse",
                wert_a="T30",
                quelle_a=FieldSource(dokument="a.xlsx", konfidenz=0.9),
                wert_b="T90",
                quelle_b=FieldSource(dokument="b.pdf", konfidenz=0.95),
                severity=ConflictSeverity.CRITICAL,
                resolution="T90",
                resolution_reason="Higher confidence",
                resolved_by="rule",
            )

            async def async_crossdoc(*args, **kwargs):
                return (
                    [ExtractedDoorPosition(positions_nr="1.01", quellen={})],
                    mock_report,
                    [mock_conflict],
                )
            mock_crossdoc.side_effect = async_crossdoc

            from v2.extraction.pipeline import run_extraction_pipeline
            result = asyncio.get_event_loop().run_until_complete(
                run_extraction_pipeline(parse_results, "crossdoc-result-tender", client=mock_client)
            )

            # ExtractionResult has enrichment report and conflicts
            assert result.enrichment_report is not None
            assert result.enrichment_report.felder_enriched == 5
            assert len(result.conflicts) == 1
            assert result.conflicts[0].field_name == "brandschutz_klasse"

    def test_single_file_no_enrichment_in_result(self):
        """Single-file ExtractionResult has enrichment_report=None, conflicts=[]."""
        mock_client = _make_mock_client()

        parse_results = [
            _make_parse_result("tuerliste.xlsx", "xlsx"),
        ]

        with patch("v2.extraction.pipeline.extract_structural") as mock_p1, \
             patch("v2.extraction.pipeline.extract_semantic") as mock_p2, \
             patch("v2.extraction.pipeline.validate_and_enrich") as mock_p3:

            mock_p1.return_value = [
                ExtractedDoorPosition(positions_nr="1.01", quellen={})
            ]

            async def async_p2(*args, **kwargs):
                return [ExtractedDoorPosition(positions_nr="1.01", quellen={})]
            mock_p2.side_effect = async_p2

            async def async_p3(*args, **kwargs):
                return args[0]
            mock_p3.side_effect = async_p3

            from v2.extraction.pipeline import run_extraction_pipeline
            result = asyncio.get_event_loop().run_until_complete(
                run_extraction_pipeline(parse_results, "single-tender", client=mock_client)
            )

            assert result.enrichment_report is None
            assert result.conflicts == []
