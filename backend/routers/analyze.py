"""
Analyze Router – Document analysis with Claude AI and product listing.
POST /api/analyze          – Single-file analysis (background job)
POST /api/analyze/project  – Multi-file project analysis (background job)
GET  /api/analyze/status/{job_id} – Poll job status
GET  /api/products
"""

import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.document_parser import parse_document_bytes, parse_pdf_specs_bytes
from services.claude_client import extract_requirements_from_text, normalize_door_positions
from services.excel_parser import parse_tuerliste_bytes, merge_tuerlisten
from services.project_store import get_project, update_project, update_file_classification
from services.product_matcher import (
    get_products_summary,
    load_product_catalog,
    match_requirements,
    match_requirements_ai,
)
from services.history_store import save_analysis
from services.memory_cache import text_cache, project_cache
from services.job_store import create_job, get_job, update_job, run_in_background

logger = logging.getLogger(__name__)

router = APIRouter()


# ─────────────────────────────────────────────
# JOB STATUS ENDPOINT
# ─────────────────────────────────────────────

@router.get("/analyze/status/{job_id}")
async def get_analyze_status(job_id: str):
    """Poll the status of a background analysis job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")
    return job.to_dict()


# ─────────────────────────────────────────────
# SINGLE FILE ANALYSIS
# ─────────────────────────────────────────────

class AnalyzeRequest(BaseModel):
    file_id: str


@router.post("/analyze")
async def analyze_document(request: AnalyzeRequest):
    """Start single-file analysis as background job. Returns job_id immediately."""
    text = text_cache.get(request.file_id)
    if text is None:
        raise HTTPException(
            status_code=410,
            detail="Datei abgelaufen oder nicht gefunden. Bitte erneut hochladen.",
        )
    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Dokument ist leer oder konnte nicht geparst werden",
        )

    job = create_job()
    run_in_background(job, _run_single_analysis, request.file_id, text)

    return {"job_id": job.id, "status": "started"}


def _run_single_analysis(file_id: str, text: str) -> dict:
    """Run single-file analysis (called in background thread)."""
    update_job_by_file = lambda prog: None  # placeholder

    # Find the job for progress updates
    # We get job_id from the thread context via the job store
    import threading
    # Progress is updated via update_job in the calling wrapper

    # Extract requirements with Claude
    requirements = extract_requirements_from_text(text)

    # Match against product catalog
    try:
        match_result = match_requirements_ai(requirements)
    except Exception as e:
        logger.warning(f"AI matching failed, falling back to keyword: {e}")
        match_result = match_requirements(requirements)

    # Save to history
    try:
        save_analysis(file_id=file_id, filename=file_id, requirements=requirements, matching=match_result)
    except Exception as e:
        logger.warning(f"Failed to save analysis to history: {e}")

    return {
        "file_id": file_id,
        "requirements": requirements,
        "matching": match_result,
        "status": "analyzed",
        "message": (
            f"Analyse abgeschlossen: {match_result['summary']['total_positions']} Positionen, "
            f"{match_result['summary']['matched_count']} erfüllbar, "
            f"{match_result['summary']['unmatched_count']} nicht erfüllbar"
        ),
    }


# ─────────────────────────────────────────────
# PROJECT ANALYSIS
# ─────────────────────────────────────────────

class AnalyzeProjectRequest(BaseModel):
    project_id: str
    file_overrides: dict = {}


@router.post("/analyze/project")
async def analyze_project(request: AnalyzeProjectRequest):
    """Start project analysis as background job. Returns job_id immediately."""
    logger.info(f"Starting project analysis for {request.project_id}")

    project = get_project(request.project_id)
    if not project:
        raise HTTPException(status_code=404, detail=f"Projekt '{request.project_id}' nicht gefunden")

    cached_files = project_cache.get(f"project_{request.project_id}")
    if cached_files is None:
        raise HTTPException(status_code=410, detail="Projektdateien abgelaufen. Bitte erneut hochladen.")

    # Apply overrides before starting background job
    for file_id, new_category in request.file_overrides.items():
        try:
            update_file_classification(request.project_id, file_id, new_category)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    job = create_job()
    run_in_background(job, _run_project_analysis, job.id, request.project_id, cached_files)

    return {"job_id": job.id, "status": "started"}


def _run_project_analysis(job_id: str, project_id: str, cached_files: dict) -> dict:
    """Run full project analysis pipeline (called in background thread)."""

    project = get_project(project_id)
    files = project["files"]
    update_project(project_id, {"status": "analyzing"})

    parsed_files_info = []

    # Step 1: Parse Excel Türlisten
    update_job(job_id, progress="Excel-Türlisten werden geparst...")
    tuerlisten_files = [f for f in files if f["category"] == "tuerliste"]
    logger.info(f"Found {len(tuerlisten_files)} Türlisten, {len(files)} total files")

    if not tuerlisten_files:
        update_project(project_id, {"status": "error"})
        raise ValueError("Keine Türliste gefunden. Bitte mindestens eine Excel-Datei als 'Türliste' klassifizieren.")

    parsed_tuerlisten = []
    for tf in tuerlisten_files:
        file_bytes = cached_files.get(tf["file_id"])
        if not file_bytes:
            parsed_files_info.append({
                "filename": tf["filename"], "category": "tuerliste",
                "status": "error", "error": "Datei nicht im Cache", "doors_found": 0,
            })
            continue
        try:
            parsed = parse_tuerliste_bytes(file_bytes)
            parsed_tuerlisten.append(parsed)
            parsed_files_info.append({
                "filename": tf["filename"], "category": "tuerliste", "status": "ok",
                "doors_found": parsed["total_rows"],
                "columns_mapped": len(parsed["column_mapping"]),
                "sheet_name": parsed["sheet_name"],
            })
        except Exception as e:
            logger.warning(f"Failed to parse Tuerliste {tf['filename']}: {e}")
            parsed_files_info.append({
                "filename": tf["filename"], "category": "tuerliste",
                "status": "error", "error": str(e), "doors_found": 0,
            })

    if not parsed_tuerlisten:
        update_project(project_id, {"status": "error"})
        raise ValueError("Keine Türliste konnte gelesen werden. Bitte Dateien prüfen.")

    # Step 2: Merge
    merged = merge_tuerlisten(parsed_tuerlisten) if len(parsed_tuerlisten) > 1 else parsed_tuerlisten[0]
    doors = merged["doors"]
    column_mapping = merged["column_mapping"]
    logger.info(f"Parsed {len(doors)} doors, mapping: {column_mapping}")

    if not doors:
        update_project(project_id, {"status": "error"})
        raise ValueError("Keine Türpositionen in der Türliste gefunden.")

    # Step 3: Parse PDF specs
    update_job(job_id, progress="PDF-Spezifikationen werden gelesen...")
    spec_files = [f for f in files if f["category"] == "spezifikation" and f["parseable"]]
    supplementary_context = ""
    for sf in spec_files[:3]:
        file_bytes = cached_files.get(sf["file_id"])
        if not file_bytes:
            continue
        try:
            ext = os.path.splitext(sf["filename"])[1].lower()
            if ext == ".pdf":
                text = parse_pdf_specs_bytes(file_bytes, max_chars=4000)
            else:
                text = parse_document_bytes(file_bytes, ext)
                if len(text) > 4000:
                    text = text[:4000] + "\n... [gekürzt]"
            if text.strip():
                supplementary_context += f"\n--- {sf['filename']} ---\n{text}\n"
                parsed_files_info.append({
                    "filename": sf["filename"], "category": "spezifikation",
                    "status": "ok", "text_length": len(text),
                })
        except Exception as e:
            logger.warning(f"Failed to parse spec {sf['filename']}: {e}")
            parsed_files_info.append({
                "filename": sf["filename"], "category": "spezifikation",
                "status": "error", "error": str(e),
            })

    for f in files:
        if f["category"] in ("plan", "foto", "sonstig"):
            parsed_files_info.append({"filename": f["filename"], "category": f["category"], "status": "skipped"})

    # Step 4: Claude normalization
    update_job(job_id, progress=f"KI normalisiert {len(doors)} Türpositionen...")
    try:
        unmapped_sample = None
        if merged.get("unmapped_columns") and doors:
            unmapped_sample = {}
            for col in merged["unmapped_columns"][:10]:
                values = [d.get("_raw_row", {}).get(col) for d in doors[:5] if d.get("_raw_row", {}).get(col)]
                if values:
                    unmapped_sample[col] = values

        def on_norm_progress(msg):
            update_job(job_id, progress=msg)

        requirements = normalize_door_positions(
            doors=doors,
            supplementary_context=supplementary_context[:8000],
            unmapped_columns_sample=unmapped_sample,
            on_progress=on_norm_progress,
        )
    except ValueError as e:
        raise
    except Exception as e:
        logger.error(f"Claude normalization failed, using fallback: {e}", exc_info=True)
        from services.claude_client import _fallback_normalize
        positions = _fallback_normalize(doors)
        requirements = {
            "projekt": "", "auftraggeber": "", "positionen": positions,
            "gesamtanzahl_tueren": sum(p.get("menge", 1) for p in positions),
            "hinweise": "Fallback-Normalisierung (ohne KI)",
        }

    # Step 5: Product matching
    pos_count = len(requirements.get("positionen", []))
    update_job(job_id, progress=f"Produkt-Matching für {pos_count} Positionen...")

    # For large files, use fast keyword matching instead of slow AI matching
    def _pos_sig(p):
        return "|".join(str(p.get(k) or "") for k in
                        ("tuertyp","brandschutz","schallschutz","einbruchschutz","breite","hoehe")).lower()
    unique_pos_count = len(set(_pos_sig(p) for p in requirements.get("positionen", [])))
    use_ai = unique_pos_count <= 30  # AI only for small files

    try:
        if use_ai:
            logger.info(f"Using AI matching ({unique_pos_count} unique positions)")
            match_result = match_requirements_ai(requirements)
        else:
            logger.info(f"Using keyword matching ({unique_pos_count} unique positions, too many for AI)")
            match_result = match_requirements(requirements)
    except FileNotFoundError:
        raise
    except Exception as e:
        logger.warning(f"Matching failed, falling back to keyword: {e}")
        match_result = match_requirements(requirements)

    # Step 6: Save to history
    update_job(job_id, progress="Ergebnisse werden gespeichert...")
    try:
        filenames = ", ".join(tf["filename"] for tf in tuerlisten_files)
        save_analysis(file_id=project_id, filename=filenames, requirements=requirements, matching=match_result)
    except Exception as e:
        logger.warning(f"Failed to save project analysis to history: {e}")

    update_project(project_id, {"status": "analyzed"})

    return {
        "project_id": project_id,
        "requirements": requirements,
        "matching": match_result,
        "parsed_files": parsed_files_info,
        "column_mapping": column_mapping,
        "status": "analyzed",
        "message": (
            f"Projektanalyse abgeschlossen: {match_result['summary']['total_positions']} Positionen aus "
            f"{len(tuerlisten_files)} Türliste(n), "
            f"{match_result['summary']['matched_count']} erfüllbar, "
            f"{match_result['summary']['unmatched_count']} nicht erfüllbar"
        ),
    }


# ─────────────────────────────────────────────
# PRODUCTS
# ─────────────────────────────────────────────

@router.get("/products")
async def get_products(limit: int = 100, search: str = ""):
    """Return the FTAG product catalog (summary)."""
    try:
        products = get_products_summary()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Produktliste konnte nicht geladen werden: {str(e)}")

    if search:
        search_lower = search.lower()
        products = [p for p in products if any(search_lower in str(v).lower() for v in p.values())]

    try:
        df = load_product_catalog()
        total_count = len(df)
    except Exception:
        total_count = len(products)

    return {"total": total_count, "returned": len(products[:limit]), "products": products[:limit]}
