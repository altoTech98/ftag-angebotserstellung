"""
Analyze Router – Document analysis with Claude AI and product listing.
POST /api/analyze
GET  /api/products
"""

import os
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from services.document_parser import parse_document
from services.claude_client import extract_requirements_from_text
from services.product_matcher import get_products_summary, load_product_catalog, match_requirements

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

    # Match against product catalog
    try:
        match_result = match_requirements(requirements)
    except FileNotFoundError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Produkt-Matching fehlgeschlagen: {str(e)}",
        )

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
