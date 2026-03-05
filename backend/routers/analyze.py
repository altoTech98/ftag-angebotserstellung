"""
Analyze Router – Document analysis with Ollama AI and product listing.
POST /api/analyze          – Single-file analysis (background job)
POST /api/analyze/project  – Multi-file project analysis (background job)
GET  /api/analyze/status/{job_id} – Poll job status
GET  /api/products
"""

import os
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from config import settings
from services.document_parser import parse_document_bytes, parse_pdf_specs_bytes
from services.local_llm import extract_requirements_from_text, extract_project_metadata
from services.document_scanner import scan_and_enrich
from services.excel_parser import parse_tuerliste_bytes, merge_tuerlisten
from services.project_store import get_project, update_project, update_file_classification
from services.product_matcher import get_products_summary
from services.catalog_index import get_catalog_index
from services.fast_matcher import match_all as fast_match_all
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
    # Check for cached Excel bytes first (structured parsing path)
    excel_bytes = project_cache.get(f"excel_{request.file_id}")

    if excel_bytes is not None:
        job = create_job()
        run_in_background(job, _run_excel_analysis, request.file_id, excel_bytes)
        return {"job_id": job.id, "status": "started"}

    # Fallback: text-based analysis (PDF/Word)
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
    run_in_background(job, _run_text_analysis, request.file_id, text)
    return {"job_id": job.id, "status": "started"}


def _run_excel_analysis(file_id: str, excel_bytes: bytes) -> dict:
    """Run structured Excel analysis (parse columns + fast matching)."""
    parsed = parse_tuerliste_bytes(excel_bytes)
    doors = parsed["doors"]

    if not doors:
        raise ValueError("Keine Tuerpositionen in der Datei gefunden.")

    # Strip internal _raw_row to reduce payload
    positions = []
    for d in doors:
        pos = {k: v for k, v in d.items() if k != "_raw_row" and v is not None}
        positions.append(pos)

    requirements = {
        "projekt": "",
        "auftraggeber": "",
        "positionen": positions,
        "gesamtanzahl_tueren": sum(d.get("menge", 1) for d in positions),
        "hinweise": "",
    }

    match_result = fast_match_all(positions)

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
            f"{match_result['summary']['matched_count']} erfuellbar, "
            f"{match_result['summary']['unmatched_count']} nicht erfuellbar"
        ),
    }


def _run_text_analysis(file_id: str, text: str) -> dict:
    """Run text-based analysis for PDF/Word files (Claude extraction + matching)."""
    requirements = extract_requirements_from_text(text)

    # Extract project metadata from the document text
    try:
        metadata = extract_project_metadata(text)
        requirements["metadata"] = metadata
        logger.info(f"Metadata extracted (source={metadata.get('source', 'none')}): "
                     f"bauherr={metadata.get('bauherr')}, bauort={metadata.get('bauort')}")
    except Exception as e:
        logger.warning(f"Metadata extraction failed: {e}")
        requirements["metadata"] = {"source": "none"}

    match_result = fast_match_all(requirements.get("positionen", []))

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
            f"{match_result['summary']['matched_count']} erfuellbar, "
            f"{match_result['summary']['unmatched_count']} nicht erfuellbar"
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

    # Step 3.5: Extract project metadata from spec documents
    update_job(job_id, progress="Projektmetadaten werden extrahiert...")
    metadata = {"source": "none"}
    if supplementary_context.strip():
        try:
            metadata = extract_project_metadata(supplementary_context)
            logger.info(f"Metadata extracted (source={metadata.get('source', 'none')}): "
                         f"bauherr={metadata.get('bauherr')}, bauort={metadata.get('bauort')}")
        except Exception as e:
            logger.warning(f"Metadata extraction failed: {e}")

    # Step 3.6: Scan documents for additional door data and enrich Tuerliste
    update_job(job_id, progress="Dokumente werden auf Tuerdaten gescannt...")
    try:
        def on_scan_progress(msg):
            update_job(job_id, progress=msg)
        scan_and_enrich(doors, spec_files, cached_files, on_progress=on_scan_progress)
        logger.info("Document scanning and enrichment complete")
    except Exception as e:
        logger.warning(f"Document scanning failed (continuing without enrichment): {e}")

    # Step 4: Prepare positions for matching
    # Use raw structured doors directly for AI matching (richer data than
    # Claude normalization which can lose fields like schloss_typ, zargentyp).
    # Strip internal _raw_row to reduce payload size.
    positions = []
    for d in doors:
        pos = {k: v for k, v in d.items() if k != "_raw_row" and v is not None}
        positions.append(pos)

    requirements = {
        "projekt": "",
        "auftraggeber": "",
        "positionen": positions,
        "gesamtanzahl_tueren": sum(d.get("menge", 1) for d in positions),
        "hinweise": supplementary_context[:2000] if supplementary_context else "",
        "metadata": {},
    }

    # Step 5: AI product matching (category-aware, batched)
    pos_count = len(positions)
    update_job(job_id, progress=f"KI-Produkt-Matching fuer {pos_count} Positionen...")

    def on_match_progress(msg):
        update_job(job_id, progress=msg)

    try:
        match_result = fast_match_all(
            positions,
            on_progress=on_match_progress,
        )
    except Exception as e:
        logger.error(f"AI matching failed: {e}", exc_info=True)
        raise

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
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Produktkatalog nicht gefunden")
    except Exception as e:
        logger.error(f"Products load error: {e}")
        raise HTTPException(status_code=500, detail=str(e) if settings.DEBUG else "Produktliste konnte nicht geladen werden")

    if search:
        search_lower = search.lower()
        products = [p for p in products if any(search_lower in str(v).lower() for v in p.values())]

    try:
        catalog = get_catalog_index()
        total_count = len(catalog.all_profiles)
    except Exception:
        total_count = len(products)

    return {"total": total_count, "returned": len(products[:limit]), "products": products[:limit]}
