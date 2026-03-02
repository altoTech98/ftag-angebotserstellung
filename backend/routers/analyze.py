"""
Analyze Router – Document analysis with Claude AI and product listing.
POST /api/analyze          – Single-file analysis (legacy)
POST /api/analyze/project  – Multi-file project analysis
GET  /api/products
"""

import os
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.document_parser import parse_document, parse_pdf_specs
from services.claude_client import extract_requirements_from_text, normalize_door_positions
from services.excel_parser import parse_tuerliste, merge_tuerlisten
from services.project_store import get_project, update_project, update_file_classification
from services.product_matcher import (
    get_products_summary,
    load_product_catalog,
    match_requirements,
    match_requirements_ai,
)
from services.history_store import save_analysis

logger = logging.getLogger(__name__)

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "uploads")


class AnalyzeRequest(BaseModel):
    file_id: str


@router.post("/analyze")
async def analyze_document(request: AnalyzeRequest):
    """
    Analyze an uploaded document with Claude AI.
    Extracts structured door requirements and matches against product catalog.
    """
    # Find uploaded file
    file_path = _find_uploaded_file(request.file_id)
    if not file_path:
        raise HTTPException(
            status_code=404,
            detail=f"Datei mit ID '{request.file_id}' nicht gefunden",
        )

    # Parse document to text
    try:
        text = parse_document(file_path)
    except Exception as e:
        raise HTTPException(
            status_code=422,
            detail=f"Dokument konnte nicht gelesen werden: {str(e)}",
        )

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail="Dokument ist leer oder konnte nicht geparst werden",
        )

    # Extract requirements with Claude
    try:
        requirements = extract_requirements_from_text(text)
    except ValueError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"KI-Analyse fehlgeschlagen: {str(e)}",
        )

    # Match against product catalog (AI-powered with keyword fallback)
    try:
        match_result = match_requirements_ai(requirements)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.warning(f"AI matching failed, falling back to keyword matching: {e}")
        try:
            match_result = match_requirements(requirements)
        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Produkt-Matching fehlgeschlagen: {str(e2)}",
            )

    # Auto-save to history
    try:
        upload_filename = os.path.basename(file_path) if file_path else request.file_id
        save_analysis(
            file_id=request.file_id,
            filename=upload_filename,
            requirements=requirements,
            matching=match_result,
        )
    except Exception as e:
        logger.warning(f"Failed to save analysis to history: {e}")

    return {
        "file_id": request.file_id,
        "requirements": requirements,
        "matching": match_result,
        "status": "analyzed",
        "message": (
            f"Analyse abgeschlossen: {match_result['summary']['total_positions']} Positionen gefunden, "
            f"{match_result['summary']['matched_count']} erfüllbar, "
            f"{match_result['summary']['unmatched_count']} nicht erfüllbar"
        ),
    }


class AnalyzeProjectRequest(BaseModel):
    project_id: str
    file_overrides: dict = {}  # {file_id: "new_category"} for user corrections


@router.post("/analyze/project")
async def analyze_project(request: AnalyzeProjectRequest):
    """
    Analyze an entire project (folder upload) with structured Excel parsing.

    Pipeline:
    1. Load project, apply classification overrides
    2. Parse Excel Türliste(n) → structured door data
    3. Merge if multiple Türlisten
    4. Parse PDF specs for supplementary context
    5. Claude normalization (structured, not raw text)
    6. Product matching (existing pipeline, unchanged)
    7. Save to history
    """
    logger.info(f"Starting project analysis for {request.project_id} with overrides: {request.file_overrides}")

    # 1. Load project
    project = get_project(request.project_id)
    if not project:
        raise HTTPException(
            status_code=404,
            detail=f"Projekt '{request.project_id}' nicht gefunden",
        )

    # Apply user classification overrides
    for file_id, new_category in request.file_overrides.items():
        try:
            update_file_classification(request.project_id, file_id, new_category)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    # Reload project after overrides
    project = get_project(request.project_id)
    files = project["files"]

    # Update project status
    update_project(request.project_id, {"status": "analyzing"})

    parsed_files_info = []

    # 2. Parse Excel Türlisten
    tuerlisten_files = [f for f in files if f["category"] == "tuerliste"]
    logger.info(f"Found {len(tuerlisten_files)} Türlisten, {len(files)} total files")
    if not tuerlisten_files:
        update_project(request.project_id, {"status": "error"})
        raise HTTPException(
            status_code=422,
            detail="Keine Türliste gefunden. Bitte mindestens eine Excel-Datei als 'Türliste' klassifizieren.",
        )

    parsed_tuerlisten = []
    for tf in tuerlisten_files:
        try:
            parsed = parse_tuerliste(tf["file_path"])
            parsed_tuerlisten.append(parsed)
            parsed_files_info.append({
                "filename": tf["filename"],
                "category": "tuerliste",
                "status": "ok",
                "doors_found": parsed["total_rows"],
                "columns_mapped": len(parsed["column_mapping"]),
                "sheet_name": parsed["sheet_name"],
            })
        except Exception as e:
            logger.warning(f"Failed to parse Tuerliste {tf['filename']}: {e}")
            parsed_files_info.append({
                "filename": tf["filename"],
                "category": "tuerliste",
                "status": "error",
                "error": str(e),
                "doors_found": 0,
            })

    if not parsed_tuerlisten:
        update_project(request.project_id, {"status": "error"})
        raise HTTPException(
            status_code=422,
            detail="Keine Türliste konnte gelesen werden. Bitte Dateien prüfen.",
        )

    # 3. Merge if multiple Türlisten
    if len(parsed_tuerlisten) > 1:
        merged = merge_tuerlisten(parsed_tuerlisten)
    else:
        merged = parsed_tuerlisten[0]

    doors = merged["doors"]
    column_mapping = merged["column_mapping"]

    logger.info(f"Parsed {len(doors)} doors from {len(parsed_tuerlisten)} Türliste(n), mapping: {column_mapping}")

    if not doors:
        update_project(request.project_id, {"status": "error"})
        raise HTTPException(
            status_code=422,
            detail="Keine Türpositionen in der Türliste gefunden.",
        )

    # 4. Parse PDF specs for supplementary context
    spec_files = [f for f in files if f["category"] == "spezifikation" and f["parseable"]]
    supplementary_context = ""
    for sf in spec_files[:3]:  # Max 3 spec files
        try:
            ext = os.path.splitext(sf["filename"])[1].lower()
            if ext == ".pdf":
                text = parse_pdf_specs(sf["file_path"], max_chars=4000)
            else:
                text = parse_document(sf["file_path"])
                if len(text) > 4000:
                    text = text[:4000] + "\n... [gekürzt]"
            if text.strip():
                supplementary_context += f"\n--- {sf['filename']} ---\n{text}\n"
                parsed_files_info.append({
                    "filename": sf["filename"],
                    "category": "spezifikation",
                    "status": "ok",
                    "text_length": len(text),
                })
        except Exception as e:
            logger.warning(f"Failed to parse spec file {sf['filename']}: {e}")
            parsed_files_info.append({
                "filename": sf["filename"],
                "category": "spezifikation",
                "status": "error",
                "error": str(e),
            })

    # Track skipped files
    for f in files:
        if f["category"] in ("plan", "foto", "sonstig"):
            parsed_files_info.append({
                "filename": f["filename"],
                "category": f["category"],
                "status": "skipped",
            })

    logger.info(f"Supplementary context: {len(supplementary_context)} chars from {len(spec_files)} spec files")

    # 5. Claude normalization
    try:
        # Collect unmapped column samples for Claude
        unmapped_sample = None
        if merged.get("unmapped_columns") and doors:
            unmapped_sample = {}
            for col in merged["unmapped_columns"][:10]:
                values = []
                for d in doors[:5]:
                    raw = d.get("_raw_row", {})
                    if col in raw and raw[col]:
                        values.append(raw[col])
                if values:
                    unmapped_sample[col] = values

        requirements = normalize_door_positions(
            doors=doors,
            supplementary_context=supplementary_context[:8000],
            unmapped_columns_sample=unmapped_sample,
        )
    except ValueError as e:
        logger.error(f"Claude client error (likely missing API key): {e}")
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.error(f"Claude normalization failed, using fallback: {e}", exc_info=True)
        # Use fallback normalization (built into claude_client)
        from services.claude_client import _fallback_normalize
        positions = _fallback_normalize(doors)
        requirements = {
            "projekt": "",
            "auftraggeber": "",
            "positionen": positions,
            "gesamtanzahl_tueren": sum(p.get("menge", 1) for p in positions),
            "hinweise": "Fallback-Normalisierung (ohne KI)",
        }

    # 6. Product matching (existing pipeline, unchanged)
    try:
        match_result = match_requirements_ai(requirements)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.warning(f"AI matching failed, falling back to keyword matching: {e}")
        try:
            match_result = match_requirements(requirements)
        except Exception as e2:
            raise HTTPException(
                status_code=500,
                detail=f"Produkt-Matching fehlgeschlagen: {str(e2)}",
            )

    # 7. Save to history
    try:
        filenames = ", ".join(tf["filename"] for tf in tuerlisten_files)
        save_analysis(
            file_id=request.project_id,
            filename=filenames,
            requirements=requirements,
            matching=match_result,
        )
    except Exception as e:
        logger.warning(f"Failed to save project analysis to history: {e}")

    # Update project status
    update_project(request.project_id, {"status": "analyzed"})

    return {
        "project_id": request.project_id,
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


@router.get("/products")
async def get_products(limit: int = 100, search: str = ""):
    """
    Return the FTAG product catalog (summary).
    Optional: filter by search term.
    """
    try:
        products = get_products_summary()
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Produktliste konnte nicht geladen werden: {str(e)}",
        )

    # Filter by search term
    if search:
        search_lower = search.lower()
        products = [
            p for p in products
            if any(search_lower in str(v).lower() for v in p.values())
        ]

    # Get total count
    try:
        df = load_product_catalog()
        total_count = len(df)
    except Exception:
        total_count = len(products)

    return {
        "total": total_count,
        "returned": len(products[:limit]),
        "products": products[:limit],
    }


def _find_uploaded_file(file_id: str) -> str | None:
    """Find an uploaded file by its ID."""
    if not os.path.exists(UPLOAD_DIR):
        return None
    for filename in os.listdir(UPLOAD_DIR):
        if filename.startswith(file_id):
            return os.path.join(UPLOAD_DIR, filename)
    return None
