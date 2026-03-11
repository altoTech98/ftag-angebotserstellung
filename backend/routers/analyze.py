"""
Analyze Router – Document analysis with Ollama AI and product listing.
POST /api/analyze          – Single-file analysis (background job)
POST /api/analyze/project  – Multi-file project analysis (background job)
GET  /api/analyze/status/{job_id} – Poll job status
GET  /api/analyze/stream/{job_id} – SSE real-time streaming
GET  /api/products
"""

import asyncio
import json
import os
import logging
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
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
from services.job_store import create_job, get_job, update_job, run_in_background, subscribe_job, unsubscribe_job
from services.sse_token_validator import validate_sse_token

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


@router.get("/analyze/stream/{job_id}")
async def stream_analyze_status(job_id: str, token: str = ""):
    """SSE endpoint with token-based auth for direct browser connections."""
    if not token:
        raise HTTPException(status_code=401, detail="SSE token required")
    payload = validate_sse_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid or expired SSE token")

    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job nicht gefunden")

    queue = subscribe_job(job_id)

    async def event_generator():
        try:
            # Send initial status
            yield f"data: {json.dumps(job.to_dict())}\n\n"

            # If already terminal, stop
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

    # Try Vision-based structured extraction for PDFs
    pdf_bytes = project_cache.get(f"pdf_{file_id}")
    positions = []
    vision_used = False

    if pdf_bytes:
        try:
            from services.document_parser import parse_pdf_with_vision
            vision_result = parse_pdf_with_vision(pdf_bytes)
            if vision_result.get("positions"):
                positions = vision_result["positions"]
                vision_used = True
                logger.info(f"[ANALYZE] Vision extracted {len(positions)} positions")
                # Use vision text if original was poor
                if vision_result.get("text") and len(vision_result["text"]) > len(text):
                    text = vision_result["text"]
        except Exception as e:
            logger.debug(f"[ANALYZE] Vision analysis failed: {e}")

    # Standard AI extraction (if no Vision positions)
    if not positions:
        requirements = extract_requirements_from_text(text)
    else:
        requirements = {
            "projekt": "",
            "auftraggeber": "",
            "positionen": positions,
            "gesamtanzahl_tueren": sum(p.get("menge", 1) for p in positions),
            "hinweise": "Extrahiert via Claude Vision",
        }

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
    doors = []
    column_mapping = {}

    # Step 1: Parse Excel Türlisten (primary source)
    update_job(job_id, progress="Excel-Türlisten werden geparst...")
    tuerlisten_files = [f for f in files if f["category"] == "tuerliste"]
    logger.info(f"Found {len(tuerlisten_files)} Türlisten, {len(files)} total files")

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

    # Step 1b: If no Türliste found/parsed, try ALL Excel files as potential door lists
    if not parsed_tuerlisten:
        other_excel_files = [
            f for f in files
            if f["category"] != "tuerliste"
            and os.path.splitext(f["filename"])[1].lower() in (".xlsx", ".xls", ".xlsm")
        ]
        if other_excel_files:
            logger.info(f"No Türliste found, trying {len(other_excel_files)} other Excel files as potential door lists")
            update_job(job_id, progress="Keine Türliste erkannt – andere Excel-Dateien werden geprüft...")
            for ef in other_excel_files:
                file_bytes = cached_files.get(ef["file_id"])
                if not file_bytes:
                    continue
                try:
                    parsed = parse_tuerliste_bytes(file_bytes)
                    if parsed["doors"]:
                        parsed_tuerlisten.append(parsed)
                        # Reclassify this file as tuerliste
                        ef["category"] = "tuerliste"
                        try:
                            update_file_classification(project_id, ef["file_id"], "tuerliste")
                        except Exception:
                            pass
                        parsed_files_info.append({
                            "filename": ef["filename"], "category": "tuerliste",
                            "status": "ok", "doors_found": parsed["total_rows"],
                            "columns_mapped": len(parsed["column_mapping"]),
                            "sheet_name": parsed["sheet_name"],
                            "auto_detected": True,
                        })
                        logger.info(f"Auto-detected Türliste in {ef['filename']}: {parsed['total_rows']} doors")
                except Exception as e:
                    logger.debug(f"Excel {ef['filename']} is not a Türliste: {e}")

    # Step 2: Merge Türlisten (if any found)
    if parsed_tuerlisten:
        merged = merge_tuerlisten(parsed_tuerlisten) if len(parsed_tuerlisten) > 1 else parsed_tuerlisten[0]
        doors = merged["doors"]
        column_mapping = merged["column_mapping"]
        logger.info(f"Parsed {len(doors)} doors from Excel, mapping: {column_mapping}")
    else:
        logger.info("No Türliste found in any Excel file – will try extracting doors from other documents")

    # Step 2.5: Parse GAEB/IFC files as additional door sources
    gaeb_ifc_positions = []
    for f in files:
        ext = os.path.splitext(f["filename"])[1].lower()
        if ext in (".x83", ".x84", ".d83", ".d84", ".p83", ".p84", ".gaeb"):
            file_bytes = cached_files.get(f["file_id"])
            if file_bytes:
                try:
                    from services.gaeb_parser import parse_gaeb_bytes
                    gaeb_result = parse_gaeb_bytes(file_bytes)
                    gaeb_pos = gaeb_result.get("positionen", [])
                    if gaeb_pos:
                        gaeb_ifc_positions.extend(gaeb_pos)
                        logger.info(f"GAEB import: {len(gaeb_pos)} positions from {f['filename']}")
                        parsed_files_info.append({
                            "filename": f["filename"], "category": "gaeb",
                            "status": "ok", "doors_found": len(gaeb_pos),
                        })
                except Exception as e:
                    logger.warning(f"GAEB parse failed for {f['filename']}: {e}")
        elif ext == ".ifc":
            file_bytes = cached_files.get(f["file_id"])
            if file_bytes:
                try:
                    from services.ifc_parser import parse_ifc_bytes
                    ifc_result = parse_ifc_bytes(file_bytes)
                    ifc_pos = ifc_result.get("positionen", [])
                    if ifc_pos:
                        gaeb_ifc_positions.extend(ifc_pos)
                        logger.info(f"IFC import: {len(ifc_pos)} doors from {f['filename']}")
                        parsed_files_info.append({
                            "filename": f["filename"], "category": "ifc",
                            "status": "ok", "doors_found": len(ifc_pos),
                        })
                except Exception as e:
                    logger.warning(f"IFC parse failed for {f['filename']}: {e}")

    # Step 3: Parse PDF specs (parallel für mehrere Dateien)
    spec_files = [f for f in files if f["category"] == "spezifikation" and f["parseable"]]
    supplementary_context = ""

    def _parse_single_spec(sf):
        """Parse a single spec file. Returns (filename, text, error)."""
        file_bytes = cached_files.get(sf["file_id"])
        if not file_bytes:
            return (sf["filename"], None, "not in cache")
        try:
            ext = os.path.splitext(sf["filename"])[1].lower()
            if ext == ".pdf":
                text = parse_pdf_specs_bytes(file_bytes, max_chars=0)
            else:
                text = parse_document_bytes(file_bytes, ext)
            return (sf["filename"], text if text.strip() else None, None)
        except Exception as e:
            return (sf["filename"], None, str(e))

    update_job(job_id, progress=f"PDF-Spezifikationen werden gelesen ({len(spec_files)} Dateien parallel)...")
    logger.info(f"Parsing {len(spec_files)} spec files in parallel")

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=min(3, len(spec_files) or 1)) as pool:
        futures = {pool.submit(_parse_single_spec, sf): sf for sf in spec_files}
        for future in as_completed(futures):
            filename, text, error = future.result()
            if error:
                logger.warning(f"Failed to parse spec {filename}: {error}")
                parsed_files_info.append({
                    "filename": filename, "category": "spezifikation",
                    "status": "error", "error": error,
                })
            elif text:
                supplementary_context += f"\n--- {filename} ---\n{text}\n"
                parsed_files_info.append({
                    "filename": filename, "category": "spezifikation",
                    "status": "ok", "text_length": len(text),
                })
                logger.info(f"Spec parsed OK: {filename} ({len(text)} chars)")

    # Also parse "sonstig" files that might be parseable (PDFs, Word docs not yet classified)
    for f in files:
        if f["category"] == "sonstig" and f.get("parseable"):
            # Try parsing as spec too
            file_bytes = cached_files.get(f["file_id"])
            if file_bytes:
                try:
                    ext = os.path.splitext(f["filename"])[1].lower()
                    if ext == ".pdf":
                        text = parse_pdf_specs_bytes(file_bytes, max_chars=0)
                    else:
                        text = parse_document_bytes(file_bytes, ext)
                    if text and text.strip():
                        supplementary_context += f"\n--- {f['filename']} ---\n{text}\n"
                        parsed_files_info.append({
                            "filename": f["filename"], "category": "sonstig",
                            "status": "ok", "text_length": len(text),
                            "note": "als Spezifikation mitanalysiert",
                        })
                        logger.info(f"Sonstig file parsed as spec: {f['filename']} ({len(text)} chars)")
                        continue
                except Exception as e:
                    logger.debug(f"Could not parse sonstig file {f['filename']}: {e}")

        if f["category"] in ("plan", "foto", "sonstig"):
            # Only add to parsed_files_info if not already added above
            if not any(p["filename"] == f["filename"] for p in parsed_files_info):
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
    if doors:
        update_job(job_id, progress="Dokumente werden auf Tuerdaten gescannt...")
        try:
            def on_scan_progress(msg):
                update_job(job_id, progress=msg)
            scan_and_enrich(doors, spec_files, cached_files, on_progress=on_scan_progress)
            logger.info("Document scanning and enrichment complete")
        except Exception as e:
            logger.warning(f"Document scanning failed (continuing without enrichment): {e}")

    # Step 3.7: Merge GAEB/IFC positions into door list
    if gaeb_ifc_positions:
        logger.info(f"Merging {len(gaeb_ifc_positions)} GAEB/IFC positions with {len(doors)} Türliste doors")
        for gpos in gaeb_ifc_positions:
            # Only add if not already in Türliste (avoid duplicates)
            pos_nr = gpos.get("position", "")
            already_exists = any(
                d.get("tuer_nr", d.get("position", "")) == pos_nr
                for d in doors
            ) if pos_nr else False
            if not already_exists:
                doors.append(gpos)

    # Step 3.8: AI extraction fallback – if still no doors, use Claude to extract from all text
    if not doors and supplementary_context.strip():
        update_job(job_id, progress="Keine Türliste gefunden – KI analysiert alle Dokumente auf Türdaten...")
        logger.info(f"No doors from Excel/GAEB/IFC – trying AI extraction from {len(supplementary_context)} chars of text")
        try:
            ai_requirements = extract_requirements_from_text(supplementary_context)
            ai_positions = ai_requirements.get("positionen", [])
            if ai_positions:
                doors = ai_positions
                logger.info(f"AI extracted {len(doors)} door positions from documents")
                parsed_files_info.append({
                    "filename": "(KI-Extraktion aus Dokumenten)",
                    "category": "ai_extraction",
                    "status": "ok",
                    "doors_found": len(doors),
                    "note": "Türpositionen durch KI aus PDFs/Spezifikationen extrahiert",
                })
        except Exception as e:
            logger.warning(f"AI extraction from documents failed: {e}")

    # Step 3.9: Also try Vision extraction on PDFs if still no doors
    if not doors:
        pdf_files = [f for f in files if os.path.splitext(f["filename"])[1].lower() == ".pdf"]
        for pf in pdf_files[:3]:  # Limit to 3 PDFs for Vision
            file_bytes = cached_files.get(pf["file_id"])
            if not file_bytes:
                continue
            try:
                update_job(job_id, progress=f"Vision-Analyse: {pf['filename']}...")
                from services.document_parser import parse_pdf_with_vision
                vision_result = parse_pdf_with_vision(file_bytes)
                vision_positions = vision_result.get("positions", [])
                if vision_positions:
                    doors.extend(vision_positions)
                    logger.info(f"Vision extracted {len(vision_positions)} positions from {pf['filename']}")
                    parsed_files_info.append({
                        "filename": pf["filename"],
                        "category": "vision_extraction",
                        "status": "ok",
                        "doors_found": len(vision_positions),
                    })
            except Exception as e:
                logger.debug(f"Vision extraction failed for {pf['filename']}: {e}")

    # Final check: fail only if absolutely no doors found anywhere
    if not doors:
        update_project(project_id, {"status": "error"})
        raise ValueError(
            "Keine Türpositionen gefunden. Weder in Excel-Dateien noch in PDFs/Spezifikationen "
            "konnten Türdaten erkannt werden. Bitte prüfen Sie die hochgeladenen Dateien."
        )

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
        all_source_files = [f for f in files if f["category"] in ("tuerliste",)]
        if not all_source_files:
            all_source_files = [f for f in files if os.path.splitext(f["filename"])[1].lower() in (".pdf", ".xlsx", ".xls", ".docx")]
        filenames = ", ".join(f["filename"] for f in all_source_files) if all_source_files else project_id
        save_analysis(file_id=project_id, filename=filenames, requirements=requirements, matching=match_result)
    except Exception as e:
        logger.warning(f"Failed to save project analysis to history: {e}")

    update_project(project_id, {"status": "analyzed"})

    # Build source description for message
    source_desc = ""
    if tuerlisten_files:
        source_desc = f"aus {len(tuerlisten_files)} Türliste(n)"
    else:
        source_desc = "aus Dokumentenanalyse (keine Türliste erkannt)"

    return {
        "project_id": project_id,
        "requirements": requirements,
        "matching": match_result,
        "parsed_files": parsed_files_info,
        "column_mapping": column_mapping,
        "status": "analyzed",
        "message": (
            f"Projektanalyse abgeschlossen: {match_result['summary']['total_positions']} Positionen "
            f"{source_desc}, "
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
