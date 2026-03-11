"""
Result Router – Machbarkeitsanalyse generation and download (in-memory, no disk writes).

V1 endpoints:
  POST /api/result/generate       – Start result generation (background job)
  GET  /api/result/status/{job_id} – Poll job status
  GET  /api/result/{id}/download   – Download result Excel

V2 endpoints:
  POST /api/offer/generate        – Start v2 Excel generation from analysis_id
  GET  /api/offer/status/{job_id} – Poll v2 job status
  GET  /api/offer/{id}/download   – Download v2 Machbarkeitsanalyse Excel
"""

import uuid
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

from services.memory_cache import offer_cache
from services.job_store import create_job, get_job, run_in_background

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy import for anthropic (only needed when generating Executive Summary)
try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore


# ─────────────────────────────────────────────
# RESULT GENERATION (Machbarkeitsanalyse + GAP)
# ─────────────────────────────────────────────

class GenerateResultRequest(BaseModel):
    requirements: dict
    matching: dict


@router.post("/result/generate")
async def generate_result(request: GenerateResultRequest):
    """Generate Machbarkeitsanalyse + GAP report Excel. Returns job_id."""
    job = create_job()
    run_in_background(
        job, _run_result_generation,
        request.requirements, request.matching,
    )
    return {"job_id": job.id, "status": "started"}


@router.get("/result/status/{job_id}")
async def get_result_status(job_id: str):
    """Poll the status of a result generation job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job.to_dict()


def _run_result_generation(requirements: dict, matching: dict) -> dict:
    """Generate Machbarkeitsanalyse Excel (2-sheet: matching + GAP)."""
    from services.result_generator import generate_result_excel

    result_id = str(uuid.uuid4())[:8]

    xlsx_bytes = generate_result_excel(matching, requirements, result_id)
    offer_cache.set(f"result_{result_id}_xlsx", xlsx_bytes, ttl_seconds=1800)

    summary = matching.get("summary", {})
    return {
        "result_id": result_id,
        "has_result": True,
        "summary": summary,
        "message": (
            f"Machbarkeitsanalyse erstellt: {summary.get('matched_count', 0)} machbar, "
            f"{summary.get('partial_count', 0)} teilweise, "
            f"{summary.get('unmatched_count', 0)} nicht machbar"
        ),
    }


@router.get("/result/{result_id}/download")
async def download_result(result_id: str):
    """Download Machbarkeitsanalyse + GAP report Excel from memory cache."""
    key = f"result_{result_id}_xlsx"
    data = offer_cache.get(key)
    if data is None:
        raise HTTPException(
            status_code=410,
            detail="Ergebnis nicht gefunden oder abgelaufen. Bitte erneut generieren.",
        )

    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="FTAG_Machbarkeit_{result_id}.xlsx"'},
    )


# ─────────────────────────────────────────────
# V2 OFFER GENERATION (from analysis_id)
# ─────────────────────────────────────────────


class GenerateV2ResultRequest(BaseModel):
    analysis_id: str


class ExecutiveSummaryResponse(BaseModel):
    """Structured response for Claude Executive Summary generation."""
    gesamtbewertung: str
    empfehlungen: list[str]


@router.post("/offer/generate")
async def v2_generate_result(request: GenerateV2ResultRequest):
    """Generate v2 Machbarkeitsanalyse Excel from analysis results.

    Looks up stored analysis results by analysis_id, generates Executive
    Summary via Claude Sonnet, produces 4-sheet Excel, and caches bytes.
    """
    # Lazy import _analysis_results
    try:
        from v2.routers.analyze_v2 import _analysis_results
    except ImportError:
        raise HTTPException(
            status_code=501,
            detail="V2 Analyse-Module nicht verfuegbar",
        )

    if request.analysis_id not in _analysis_results:
        raise HTTPException(
            status_code=404,
            detail=f"Analyse-Ergebnis '{request.analysis_id}' nicht gefunden",
        )

    job = create_job()
    run_in_background(job, _run_v2_excel_generation, request.analysis_id)
    return {"job_id": job.id, "status": "started"}


def _run_v2_excel_generation(analysis_id: str) -> dict:
    """Background task: generate v2 Excel with Executive Summary AI call.

    Steps:
    1. Look up stored analysis results
    2. Generate Executive Summary via Claude Sonnet API (with fallback)
    3. Call generate_v2_excel() to produce 4-sheet xlsx
    4. Cache bytes with 1-hour TTL
    """
    from v2.routers.analyze_v2 import _analysis_results
    from v2.output.excel_generator import generate_v2_excel

    stored = _analysis_results[analysis_id]
    positions = stored["positions"]
    match_results = stored["match_results"]
    adversarial_results = stored["adversarial_results"]
    gap_reports = stored["gap_reports"]

    # --- Generate Executive Summary via Claude Sonnet ---
    ai_summary = ""
    ai_recommendations = []

    # Build statistics for prompt
    total_pos = len(positions)
    confirmed = sum(
        1 for ar in adversarial_results
        if ar.adjusted_confidence >= 0.95
    )
    uncertain = sum(
        1 for ar in adversarial_results
        if 0.60 <= ar.adjusted_confidence < 0.95
    )
    rejected = total_pos - confirmed - uncertain

    total_gaps = sum(len(gr.gaps) for gr in gap_reports)
    kritisch_gaps = sum(
        1 for gr in gap_reports for g in gr.gaps
        if g.schweregrad.value == "kritisch"
    )

    if anthropic is not None:
        try:
            client = anthropic.Anthropic()
            prompt = (
                f"Analyseergebnisse:\n"
                f"- {total_pos} Positionen analysiert\n"
                f"- {confirmed} bestaetigt (95%+), {uncertain} unsicher (60-95%), "
                f"{rejected} abgelehnt (<60%)\n"
                f"- {total_gaps} Gaps identifiziert, davon {kritisch_gaps} kritisch\n\n"
                f"Erstelle eine Gesamtbewertung (2-4 Saetze) und 2-4 konkrete Empfehlungen."
            )
            response = client.messages.parse(
                model="claude-sonnet-4-20250514",
                max_tokens=1024,
                system="Du bist ein technischer Berater fuer Tueren und Brandschutz bei der Frank Tueren AG. "
                       "Erstelle eine professionelle Zusammenfassung der Machbarkeitsanalyse auf Deutsch. "
                       "Die Zusammenfassung ist fuer das Vertriebsteam und wird an Kunden weitergeleitet.",
                messages=[{"role": "user", "content": prompt}],
                response_model=ExecutiveSummaryResponse,
            )
            ai_summary = response.parsed.gesamtbewertung
            ai_recommendations = response.parsed.empfehlungen
            logger.info(f"[V2 Offer] Executive Summary generated via Claude for {analysis_id}")
        except Exception as e:
            logger.error(f"[V2 Offer] Claude Executive Summary failed: {e}")
            # Fallback: statistics-only summary
            ai_summary = (
                f"Machbarkeitsanalyse: {total_pos} Positionen analysiert. "
                f"{confirmed} bestaetigt, {uncertain} unsicher, {rejected} abgelehnt. "
                f"{total_gaps} Gaps identifiziert ({kritisch_gaps} kritisch)."
            )
            ai_recommendations = []
    else:
        # No anthropic SDK available - fallback
        ai_summary = (
            f"Machbarkeitsanalyse: {total_pos} Positionen analysiert. "
            f"{confirmed} bestaetigt, {uncertain} unsicher, {rejected} abgelehnt. "
            f"{total_gaps} Gaps identifiziert ({kritisch_gaps} kritisch)."
        )

    # --- Generate Excel ---
    xlsx_bytes = generate_v2_excel(
        positions=positions,
        match_results=match_results,
        adversarial_results=adversarial_results,
        gap_reports=gap_reports,
        ai_summary=ai_summary,
        ai_recommendations=ai_recommendations,
    )

    # Cache with 1-hour TTL
    offer_cache.set(f"v2_result_{analysis_id}_xlsx", xlsx_bytes, ttl_seconds=3600)

    logger.info(
        f"[V2 Offer] Excel generated for {analysis_id}: "
        f"{len(xlsx_bytes)} bytes cached"
    )

    return {"result_id": analysis_id, "has_result": True}


@router.get("/offer/status/{job_id}")
async def v2_get_result_status(job_id: str):
    """Poll the status of a v2 result generation job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job.to_dict()


@router.get("/offer/{result_id}/download")
async def v2_download_result(result_id: str):
    """Download v2 Machbarkeitsanalyse Excel from memory cache."""
    cache_key = f"v2_result_{result_id}_xlsx"
    data = offer_cache.get(cache_key)
    if data is None:
        raise HTTPException(
            status_code=410,
            detail="Ergebnis nicht gefunden oder abgelaufen. Bitte erneut generieren.",
        )

    filename = f"Machbarkeitsanalyse_{datetime.now().strftime('%Y%m%d')}_{result_id}.xlsx"

    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
