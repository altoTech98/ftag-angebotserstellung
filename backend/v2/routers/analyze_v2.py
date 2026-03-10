"""
V2 Analyze Router - Async background job execution with SSE progress streaming.

POST /api/v2/analyze returns job_id immediately and runs the full pipeline
(extraction, matching, adversarial, gap analysis, plausibility) in a background
thread. Progress events are streamed via SSE or polled via status endpoint.
"""

import asyncio
import json
import logging
import time
import traceback
import uuid
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from services.job_store import (
    create_job,
    get_job,
    update_job,
    run_in_background,
    subscribe_job,
    unsubscribe_job,
)
from v2.exceptions import AIServiceError, raise_ai_error
from v2.extraction.pipeline import run_extraction_pipeline
from v2.parsers.base import ParseResult
from v2.pipeline_logging import log_step
from v2.routers.upload_v2 import _tenders
from v2.validation.plausibility import check_plausibility

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

# Lazy imports for gap analysis (may not be available)
try:
    from v2.gaps import analyze_gaps
    _GAPS_AVAILABLE = True
except ImportError as _gap_import_err:
    _GAPS_AVAILABLE = False
    logger.warning(f"[V2 Analyze] Gap modules not available: {_gap_import_err}")

router = APIRouter(prefix="/api/v2", tags=["V2 Analysis"])

# Lazy singleton for TF-IDF index
_tfidf_index: Optional["CatalogTfidfIndex"] = None  # type: ignore

# Analysis results storage for Excel generation (keyed by analysis_id)
_analysis_results: dict[str, dict] = {}


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
    """Start async analysis as background job. Returns job_id immediately."""
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

    job = create_job()
    run_in_background(job, _run_v2_pipeline_sync, job.id, tender_id)
    return {"job_id": job.id, "status": "started"}


def _run_v2_pipeline_sync(job_id: str, tender_id: str):
    """Sync wrapper that creates an event loop for the async pipeline."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run_v2_pipeline_async(job_id, tender_id))
    finally:
        loop.close()


async def _run_v2_pipeline_async(job_id: str, tender_id: str):
    """Run the full v2 pipeline with progress reporting.

    Stages: extraction -> matching -> adversarial -> gap_analyse -> plausibility.
    Progress events are throttled to max 1 per 500ms to prevent SSE flooding.
    AI failures raise PipelineError (fail-fast, no partial results).
    """
    # Progress throttle: max 1 update per 500ms
    _last_progress = [0.0]

    def on_progress(stage, detail, percent, *, current_position=None, positions_done=None, positions_total=None):
        now = time.time()
        if now - _last_progress[0] < 0.5:
            return
        _last_progress[0] = now
        update_job(job_id, progress=json.dumps({
            "message": detail,
            "stage": stage,
            "percent": percent,
            "current_position": current_position,
            "positions_done": positions_done,
            "positions_total": positions_total,
        }))

    tender = _tenders[tender_id]
    files = tender["files"]
    parse_results = [f for f in files if isinstance(f, ParseResult)]

    logger.info(
        f"[V2 Analyze] Tender {tender_id}: {len(parse_results)} files, "
        f"formats: {[f.format for f in parse_results]}"
    )
    tender["status"] = "analyzing"

    # --- Stage 1: Extraction ---
    on_progress("extraction", "Extraktion wird gestartet...", 0.0)

    def _extraction_progress(stage, detail, percent):
        # Scale extraction to 0-30% of total
        on_progress("extraction", detail, percent * 0.3)

    try:
        result = await run_extraction_pipeline(
            parse_results, tender_id, on_progress=_extraction_progress
        )
    except Exception as e:
        tender["status"] = "error"
        raise_ai_error(e, "extraction")

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

    match_results = []
    adversarial_results = []
    gap_results_raw = []

    # --- Stage 2: Product Matching ---
    if _MATCHING_AVAILABLE and result.positionen:
        try:
            import anthropic

            client = anthropic.Anthropic()
            tfidf_idx = _get_tfidf_index()

            if tfidf_idx is not None:
                def _feedback_fn(pos):
                    store = get_feedback_store()
                    query = tfidf_idx._build_query_from_position(pos)
                    return store.find_relevant_feedback(query)

                n = len(result.positionen)
                for i, pos in enumerate(result.positionen):
                    on_progress(
                        "matching",
                        f"Matching Position {i + 1} von {n}",
                        30.0 + (i / n) * 20.0,
                        current_position=pos.positions_nr,
                        positions_done=i,
                        positions_total=n,
                    )

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

                # --- Stage 3: Adversarial Validation ---
                if _ADVERSARIAL_AVAILABLE and match_results:
                    try:
                        n_adv = len(match_results)
                        for i in range(n_adv):
                            on_progress(
                                "adversarial",
                                f"Adversarial Check Position {i + 1} von {n_adv}",
                                50.0 + (i / n_adv) * 20.0,
                                current_position=match_results[i].positions_nr,
                                positions_done=i,
                                positions_total=n_adv,
                            )

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
                        raise_ai_error(e, "adversarial")
                elif not _ADVERSARIAL_AVAILABLE:
                    response["adversarial_skipped"] = True
                    response["adversarial_warning"] = "Adversarial modules not installed"

                # --- Stage 4: Gap Analysis ---
                adversarial_results_for_gaps = adversarial_results
                if _GAPS_AVAILABLE and adversarial_results_for_gaps:
                    try:
                        n_gap = len(match_results)
                        for i in range(n_gap):
                            on_progress(
                                "gap_analyse",
                                f"Gap-Analyse Position {i + 1} von {n_gap}",
                                70.0 + (i / n_gap) * 15.0,
                                current_position=match_results[i].positions_nr,
                                positions_done=i,
                                positions_total=n_gap,
                            )

                        gap_results_raw = await analyze_gaps(
                            client=client,
                            match_results=match_results,
                            adversarial_results=adversarial_results_for_gaps,
                            tfidf_index=tfidf_idx,
                        )
                        response["gap_results"] = [gr.model_dump() for gr in gap_results_raw]
                        response["total_gaps"] = sum(len(gr.gaps) for gr in gap_results_raw)
                        response["total_gap_reports"] = len(gap_results_raw)
                    except Exception as e:
                        raise_ai_error(e, "gap_analyse")
                elif _GAPS_AVAILABLE and match_results and not adversarial_results_for_gaps:
                    # Adversarial was skipped -- create synthetic results for gap analysis
                    from v2.schemas.adversarial import AdversarialResult, ValidationStatus
                    synthetic_adversarial = [
                        AdversarialResult(
                            positions_nr=mr.positions_nr,
                            validation_status=(
                                ValidationStatus.UNSICHER if mr.hat_match
                                else ValidationStatus.ABGELEHNT
                            ),
                            adjusted_confidence=(
                                mr.bester_match.gesamt_konfidenz if mr.bester_match else 0.0
                            ),
                            debate=[],
                            resolution_reasoning="Synthetic - adversarial skipped",
                            per_dimension_cot=[],
                        )
                        for mr in match_results
                    ]
                    try:
                        gap_results_raw = await analyze_gaps(
                            client=client,
                            match_results=match_results,
                            adversarial_results=synthetic_adversarial,
                            tfidf_index=tfidf_idx,
                        )
                        response["gap_results"] = [gr.model_dump() for gr in gap_results_raw]
                        response["total_gaps"] = sum(len(gr.gaps) for gr in gap_results_raw)
                        response["total_gap_reports"] = len(gap_results_raw)
                    except Exception as e:
                        raise_ai_error(e, "gap_analyse")
                elif not _GAPS_AVAILABLE:
                    response["gaps_skipped"] = True
                    response["gaps_warning"] = "Gap modules not installed"

            else:
                response["matching_skipped"] = True
                response["matching_warning"] = "TF-IDF index not available"

        except AIServiceError:
            raise  # Let fail-fast errors propagate
        except Exception as e:
            raise_ai_error(e, "matching")
    elif not _MATCHING_AVAILABLE:
        response["matching_skipped"] = True
        response["matching_warning"] = "Matching modules not installed"

    # --- Stage 5: Plausibility Check ---
    on_progress("plausibility", "Plausibilitaetspruefung...", 90.0)
    try:
        plausibility = check_plausibility(
            positions=result.positionen,
            match_results=match_results,
            adversarial_results=adversarial_results,
            gap_reports=gap_results_raw,
        )
        response["plausibility"] = plausibility.model_dump()
    except Exception as e:
        logger.warning(f"[V2 Analyze] Plausibility check failed: {e}")
        response["plausibility"] = None

    # Store analysis results for later Excel generation
    analysis_id = str(uuid.uuid4())[:8]
    _analysis_results[analysis_id] = {
        "positions": result.positionen,
        "match_results": match_results,
        "adversarial_results": adversarial_results,
        "gap_reports": gap_results_raw,
        "created_at": datetime.now(),
    }
    response["analysis_id"] = analysis_id

    tender["status"] = "completed"
    on_progress("completed", "Analyse abgeschlossen", 100.0)

    return response


# -----------------------------------------------
# SSE streaming endpoint (reuses v1 pattern)
# -----------------------------------------------

@router.get("/analyze/stream/{job_id}")
async def stream_v2_status(job_id: str):
    """SSE endpoint for real-time v2 job progress streaming."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    queue = subscribe_job(job_id)

    async def event_generator():
        try:
            yield f"data: {json.dumps(job.to_dict())}\n\n"
            if job.status in ("completed", "failed"):
                return
            while True:
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=30.0)
                    yield f"data: {json.dumps(event)}\n\n"
                    if event.get("status") in ("completed", "failed"):
                        break
                except asyncio.TimeoutError:
                    yield f"data: {json.dumps({'type': 'keepalive'})}\n\n"
        finally:
            unsubscribe_job(job_id, queue)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# -----------------------------------------------
# Status polling endpoint
# -----------------------------------------------

@router.get("/analyze/status/{job_id}")
async def get_v2_status(job_id: str):
    """Poll the status of a v2 analysis job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job.to_dict()
