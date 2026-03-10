"""
V2 Analyze Router - Analysis trigger endpoint with full extraction pipeline
and product matching integration.

Validates tender session, runs the 3-pass extraction pipeline,
then triggers TF-IDF + AI product matching on extracted positions.
Returns structured ExtractionResult with MatchResults.
"""

import logging
import traceback
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from v2.extraction.pipeline import run_extraction_pipeline
from v2.parsers.base import ParseResult
from v2.routers.upload_v2 import _tenders

logger = logging.getLogger(__name__)

# Lazy imports for matching modules (may not be available)
try:
    from v2.matching import CatalogTfidfIndex, match_positions
    from v2.matching.feedback_v2 import get_feedback_store

    _MATCHING_AVAILABLE = True
except ImportError as _import_err:
    CatalogTfidfIndex = None  # type: ignore
    _MATCHING_AVAILABLE = False
    logger.warning(f"[V2 Analyze] Matching modules not available: {_import_err}")

# Lazy imports for adversarial validation (may not be available)
try:
    from v2.matching.adversarial import validate_positions
    _ADVERSARIAL_AVAILABLE = True
except ImportError as _adv_import_err:
    _ADVERSARIAL_AVAILABLE = False
    logger.warning(f"[V2 Analyze] Adversarial modules not available: {_adv_import_err}")

router = APIRouter(prefix="/api/v2", tags=["V2 Analysis"])

# Lazy singleton for TF-IDF index
_tfidf_index: Optional["CatalogTfidfIndex"] = None  # type: ignore


def _get_tfidf_index():
    """Get or create the TF-IDF index singleton."""
    global _tfidf_index
    if _tfidf_index is None and CatalogTfidfIndex is not None:
        _tfidf_index = CatalogTfidfIndex()
    return _tfidf_index


class AnalyzeRequest(BaseModel):
    """Request body for analyze endpoint."""
    tender_id: str


@router.post("/analyze")
async def analyze_tender(request: AnalyzeRequest):
    """Trigger full 3-pass extraction pipeline and product matching.

    Validates tender exists and has files. Runs Pass 1 (structural),
    Pass 2 (semantic AI), and Pass 3 (validation) via the pipeline
    orchestrator. Then runs TF-IDF + AI matching on extracted positions.

    Args:
        request: JSON body with tender_id.

    Returns:
        JSON with tender_id, status, positionen, zusammenfassung,
        warnungen, total_positionen, and match_results.
    """
    tender_id = request.tender_id

    if tender_id not in _tenders:
        raise HTTPException(
            status_code=404,
            detail=f"Tender {tender_id} not found",
        )

    tender = _tenders[tender_id]
    files = tender["files"]

    if len(files) == 0:
        raise HTTPException(
            status_code=400,
            detail="Tender has no uploaded files",
        )

    # Extract ParseResult objects from tender files
    parse_results = [f for f in files if isinstance(f, ParseResult)]

    logger.info(
        f"[V2 Analyze] Tender {tender_id}: {len(parse_results)} files, "
        f"formats: {[f.format for f in parse_results]}"
    )

    # Update tender status to analyzing
    tender["status"] = "analyzing"

    try:
        result = await run_extraction_pipeline(parse_results, tender_id)

        # Update tender status to completed
        tender["status"] = "completed"

        response = {
            "tender_id": tender_id,
            "status": "completed",
            "positionen": [pos.model_dump() for pos in result.positionen],
            "zusammenfassung": result.dokument_zusammenfassung,
            "warnungen": result.warnungen,
            "total_positionen": len(result.positionen),
            "enrichment_report": (
                result.enrichment_report.model_dump()
                if result.enrichment_report
                else None
            ),
            "conflicts": [c.model_dump() for c in result.conflicts],
            "total_conflicts": len(result.conflicts),
        }

        # --- Product Matching Phase ---
        if _MATCHING_AVAILABLE and result.positionen:
            try:
                import anthropic

                client = anthropic.Anthropic()
                tfidf_idx = _get_tfidf_index()

                if tfidf_idx is not None:
                    # Build feedback function for few-shot learning
                    def _feedback_fn(pos):
                        """Get relevant feedback for a position."""
                        store = get_feedback_store()
                        query = tfidf_idx._build_query_from_position(pos)
                        return store.find_relevant_feedback(query)

                    match_results = await match_positions(
                        client=client,
                        positions=result.positionen,
                        tfidf_index=tfidf_idx,
                        feedback_examples_fn=_feedback_fn,
                    )

                    response["match_results"] = [
                        mr.model_dump() for mr in match_results
                    ]
                    response["total_matches"] = sum(
                        1 for mr in match_results if mr.hat_match
                    )
                    response["total_positions_matched"] = len(match_results)

                    # --- Adversarial Validation Phase ---
                    if _ADVERSARIAL_AVAILABLE and match_results:
                        try:
                            adversarial_results = await validate_positions(
                                client=client,
                                match_results=match_results,
                                tfidf_index=tfidf_idx,
                            )

                            response["adversarial_results"] = [
                                ar.model_dump() for ar in adversarial_results
                            ]
                            response["total_confirmed"] = sum(
                                1 for ar in adversarial_results
                                if ar.validation_status.value == "bestaetigt"
                            )
                            response["total_uncertain"] = sum(
                                1 for ar in adversarial_results
                                if ar.validation_status.value == "unsicher"
                            )
                            response["total_api_calls"] = sum(
                                ar.api_calls_count for ar in adversarial_results
                            )
                        except Exception as e:
                            logger.error(
                                f"[V2 Analyze] Adversarial validation failed for tender {tender_id}: {e}\n"
                                f"{traceback.format_exc()}"
                            )
                            response["adversarial_skipped"] = True
                            response["adversarial_warning"] = f"Adversarial validation failed: {str(e)}"
                    elif not _ADVERSARIAL_AVAILABLE:
                        response["adversarial_skipped"] = True
                        response["adversarial_warning"] = "Adversarial modules not installed"

                else:
                    response["matching_skipped"] = True
                    response["matching_warning"] = "TF-IDF index not available"

            except Exception as e:
                logger.error(
                    f"[V2 Analyze] Matching failed for tender {tender_id}: {e}\n"
                    f"{traceback.format_exc()}"
                )
                response["matching_skipped"] = True
                response["matching_warning"] = f"Matching failed: {str(e)}"
        elif not _MATCHING_AVAILABLE:
            response["matching_skipped"] = True
            response["matching_warning"] = "Matching modules not installed"

        return response

    except Exception as e:
        logger.error(
            f"[V2 Analyze] Pipeline failed for tender {tender_id}: {e}\n"
            f"{traceback.format_exc()}"
        )
        tender["status"] = "error"
        raise HTTPException(
            status_code=500,
            detail=f"Extraction pipeline failed: {str(e)}",
        )
