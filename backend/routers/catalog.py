"""
Catalog Router -- View, search, validate, activate, and diff the FTAG product catalog.

GET  /api/catalog/info              -- Current catalog metadata
POST /api/catalog/upload            -- Upload a new product catalog (direct file)
GET  /api/catalog/products          -- Search/filter products with pagination
POST /api/catalog/validate          -- Validate a catalog file from blob URL
POST /api/catalog/activate          -- Activate a catalog version from blob URL
POST /api/catalog/diff              -- Compare two catalog versions
GET  /api/catalog/products/{index}  -- Get full product details by row index
POST /api/catalog/products/override -- Apply a product override (placeholder)
"""

import io
import os
import glob
import logging
import math
from datetime import datetime
from typing import Optional

import httpx
import pandas as pd
from fastapi import APIRouter, HTTPException, UploadFile, File, Query
from pydantic import BaseModel
from config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PRODUCT_FILE = os.path.join(DATA_DIR, "produktuebersicht.xlsx")
MAX_BACKUPS = 3

# -- Pydantic request models --------------------------------------------------


class ValidateRequest(BaseModel):
    blob_url: str


class ActivateRequest(BaseModel):
    blob_url: str


class DiffRequest(BaseModel):
    old_blob_url: str
    new_blob_url: str


class OverrideRequest(BaseModel):
    product_key: str
    action: str  # "edit" | "add" | "delete"
    data: Optional[dict] = None


# -- Helpers -------------------------------------------------------------------


async def _download_blob(url: str) -> bytes:
    """Download file content from a Vercel Blob URL."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(url)
        resp.raise_for_status()
        return resp.content


def _parse_catalog_df(content: bytes) -> pd.DataFrame:
    """Parse an FTAG catalog Excel file into a DataFrame."""
    from services.catalog_index import CATALOG_HEADER_ROW

    df = pd.read_excel(io.BytesIO(content), sheet_name=0, header=CATALOG_HEADER_ROW)
    df.columns = [str(c).strip() for c in df.columns]
    df = df.dropna(how="all").reset_index(drop=True)

    # Remove leftover header row
    if len(df) > 0:
        first_col = df.columns[0]
        df = df[df[first_col].astype(str) != "Produktegruppen"].reset_index(drop=True)

    return df


def _catalog_stats(df: pd.DataFrame) -> dict:
    """Extract basic stats from a parsed catalog DataFrame."""
    first_col = df.columns[0] if len(df.columns) > 0 else None
    categories = set()
    main_count = 0

    if first_col:
        for val in df[first_col]:
            if pd.notna(val):
                cat = str(val).strip()
                if cat:
                    categories.add(cat)
                    if "ZZ" not in cat:
                        main_count += 1

    return {
        "total_rows": len(df),
        "main_products": main_count,
        "categories": len(categories),
    }


# -- Existing endpoints --------------------------------------------------------


@router.get("/catalog/info")
async def catalog_info():
    """Return metadata about the currently loaded product catalog."""
    from services.catalog_index import get_catalog_index, PRODUCT_FILE as pf

    if not os.path.exists(pf):
        raise HTTPException(status_code=404, detail="Kein Produktkatalog vorhanden.")

    try:
        idx = get_catalog_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) if settings.DEBUG else "Katalog konnte nicht geladen werden")

    mod_time = os.path.getmtime(pf)
    mod_str = datetime.fromtimestamp(mod_time).strftime("%d.%m.%Y %H:%M")

    categories = {}
    for cat, prods in idx.by_category.items():
        categories[cat] = len(prods)

    return {
        "filename": os.path.basename(pf),
        "last_modified": mod_str,
        "total_products": len(idx.all_profiles),
        "main_products": len(idx.main_products),
        "accessory_products": sum(len(v) for v in idx.accessories.values()),
        "categories": len(idx.category_names),
        "category_breakdown": categories,
    }


@router.post("/catalog/upload")
async def upload_catalog(file: UploadFile = File(...)):
    """Upload a new product catalog Excel file. Validates, backs up old, reloads."""
    if not file.filename.lower().endswith(".xlsx"):
        raise HTTPException(status_code=422, detail="Nur .xlsx Dateien erlaubt.")

    content = await file.read()
    if len(content) < 1000:
        raise HTTPException(status_code=422, detail="Datei ist zu klein / leer.")

    # Validate it's a real Excel file
    try:
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, nrows=10)
        if len(df.columns) < 5:
            raise ValueError("Zu wenig Spalten")
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e) if settings.DEBUG else "Ungueltige Excel-Datei")

    # Backup existing catalog
    os.makedirs(DATA_DIR, exist_ok=True)
    if os.path.exists(PRODUCT_FILE):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DATA_DIR, f"produktuebersicht_backup_{ts}.xlsx")
        try:
            os.rename(PRODUCT_FILE, backup_path)
            logger.info(f"Catalog backed up to {backup_path}")
        except Exception as e:
            logger.warning(f"Backup failed: {e}")

        # Clean old backups (keep only MAX_BACKUPS)
        backups = sorted(glob.glob(os.path.join(DATA_DIR, "produktuebersicht_backup_*.xlsx")))
        while len(backups) > MAX_BACKUPS:
            try:
                os.remove(backups.pop(0))
            except Exception:
                pass

    # Write new catalog
    try:
        with open(PRODUCT_FILE, "wb") as f:
            f.write(content)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) if settings.DEBUG else "Datei konnte nicht gespeichert werden")

    # Invalidate cache and rebuild
    from services.catalog_index import invalidate_catalog_cache, get_catalog_index
    invalidate_catalog_cache()

    try:
        idx = get_catalog_index()
    except Exception as e:
        # Restore backup
        backups = sorted(glob.glob(os.path.join(DATA_DIR, "produktuebersicht_backup_*.xlsx")))
        if backups:
            try:
                os.replace(backups[-1], PRODUCT_FILE)
                invalidate_catalog_cache()
                get_catalog_index()
            except Exception:
                pass
        raise HTTPException(
            status_code=422,
            detail=str(e) if settings.DEBUG else "Katalog konnte nicht geladen werden (altes Backup wiederhergestellt)",
        )

    logger.info(f"New catalog loaded: {len(idx.all_profiles)} products")

    return {
        "status": "ok",
        "filename": file.filename,
        "total_products": len(idx.all_profiles),
        "main_products": len(idx.main_products),
        "categories": len(idx.category_names),
        "message": f"Katalog aktualisiert: {len(idx.all_profiles)} Produkte in {len(idx.category_names)} Kategorien",
    }


# -- New endpoints -------------------------------------------------------------


@router.get("/catalog/products")
async def search_products(
    search: str = Query("", description="Text search across product summaries"),
    category: str = Query("", description="Filter by category name"),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(50, ge=1, le=200, description="Products per page"),
):
    """Search and filter products with pagination."""
    from services.catalog_index import get_catalog_index

    try:
        idx = get_catalog_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) if settings.DEBUG else "Katalog konnte nicht geladen werden")

    # Filter profiles
    profiles = idx.all_profiles

    if category:
        cat_lower = category.lower()
        profiles = [p for p in profiles if p.category.lower() == cat_lower]

    if search:
        search_lower = search.lower()
        profiles = [p for p in profiles if search_lower in p.compact_text.lower()]

    total = len(profiles)
    pages = max(1, math.ceil(total / limit))
    start = (page - 1) * limit
    end = start + limit
    page_profiles = profiles[start:end]

    products = []
    for p in page_profiles:
        kostentraeger = p.key_fields.get("kostentraeger", "")
        if not kostentraeger:
            # Try extracting from key_fields or category
            kostentraeger = p.key_fields.get("cost_center", "")
        products.append({
            "row_index": p.row_index,
            "category": p.category,
            "summary": p.compact_text,
            "fields": p.key_fields,
            "kostentraeger": kostentraeger,
        })

    return {
        "products": products,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": pages,
    }


@router.post("/catalog/validate")
async def validate_catalog(req: ValidateRequest):
    """Validate a catalog file from a blob URL without activating it."""
    errors = []
    warnings = []

    try:
        content = await _download_blob(req.blob_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Datei konnte nicht heruntergeladen werden: {e}")

    try:
        df = _parse_catalog_df(content)
    except Exception as e:
        return {
            "valid": False,
            "total_rows": 0,
            "main_products": 0,
            "categories": 0,
            "errors": [f"Excel-Datei konnte nicht gelesen werden: {e}"],
            "warnings": [],
        }

    # Check minimum columns
    if len(df.columns) < 5:
        errors.append(f"Zu wenig Spalten: {len(df.columns)} (mindestens 5 erwartet)")

    # Check first column name looks like Produktegruppen
    first_col = str(df.columns[0]) if len(df.columns) > 0 else ""
    if "produkt" not in first_col.lower() and "gruppe" not in first_col.lower():
        warnings.append(f"Erste Spalte heisst '{first_col}' -- erwartet 'Produktegruppen'")

    # Check minimum rows
    if len(df) < 10:
        errors.append(f"Zu wenig Zeilen: {len(df)} (mindestens 10 erwartet)")

    stats = _catalog_stats(df)

    if stats["categories"] == 0:
        errors.append("Keine Kategorien gefunden")

    return {
        "valid": len(errors) == 0,
        "total_rows": stats["total_rows"],
        "main_products": stats["main_products"],
        "categories": stats["categories"],
        "errors": errors,
        "warnings": warnings,
    }


@router.post("/catalog/activate")
async def activate_catalog(req: ActivateRequest):
    """Activate a catalog version by downloading from blob URL and replacing local file."""
    from services.catalog_index import invalidate_catalog_cache, get_catalog_index

    try:
        content = await _download_blob(req.blob_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Datei konnte nicht heruntergeladen werden: {e}")

    # Validate the downloaded content
    try:
        df = _parse_catalog_df(content)
        if len(df) < 10:
            raise ValueError(f"Zu wenig Zeilen: {len(df)}")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Ungueltige Katalog-Datei: {e}")

    # Backup existing catalog
    os.makedirs(DATA_DIR, exist_ok=True)
    backup_path = None
    if os.path.exists(PRODUCT_FILE):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = os.path.join(DATA_DIR, f"produktuebersicht_backup_{ts}.xlsx")
        try:
            os.rename(PRODUCT_FILE, backup_path)
            logger.info(f"Catalog backed up to {backup_path}")
        except Exception as e:
            logger.warning(f"Backup failed: {e}")
            backup_path = None

        # Clean old backups
        backups = sorted(glob.glob(os.path.join(DATA_DIR, "produktuebersicht_backup_*.xlsx")))
        while len(backups) > MAX_BACKUPS:
            try:
                os.remove(backups.pop(0))
            except Exception:
                pass

    # Write new catalog
    try:
        with open(PRODUCT_FILE, "wb") as f:
            f.write(content)
    except Exception as e:
        # Restore backup
        if backup_path and os.path.exists(backup_path):
            try:
                os.replace(backup_path, PRODUCT_FILE)
            except Exception:
                pass
        raise HTTPException(status_code=500, detail=str(e) if settings.DEBUG else "Datei konnte nicht gespeichert werden")

    # Invalidate cache and rebuild
    invalidate_catalog_cache()

    try:
        idx = get_catalog_index()
    except Exception as e:
        # Restore backup
        if backup_path and os.path.exists(backup_path):
            try:
                os.replace(backup_path, PRODUCT_FILE)
                invalidate_catalog_cache()
                get_catalog_index()
            except Exception:
                pass
        raise HTTPException(
            status_code=422,
            detail=str(e) if settings.DEBUG else "Katalog konnte nicht geladen werden (Backup wiederhergestellt)",
        )

    logger.info(f"Catalog activated from blob: {len(idx.all_profiles)} products")

    # Return same format as catalog_info
    mod_time = os.path.getmtime(PRODUCT_FILE)
    mod_str = datetime.fromtimestamp(mod_time).strftime("%d.%m.%Y %H:%M")
    categories = {cat: len(prods) for cat, prods in idx.by_category.items()}

    return {
        "filename": os.path.basename(PRODUCT_FILE),
        "last_modified": mod_str,
        "total_products": len(idx.all_profiles),
        "main_products": len(idx.main_products),
        "accessory_products": sum(len(v) for v in idx.accessories.values()),
        "categories": len(idx.category_names),
        "category_breakdown": categories,
    }


@router.post("/catalog/diff")
async def diff_versions(req: DiffRequest):
    """Compare two catalog versions by downloading from blob URLs."""
    try:
        old_content = await _download_blob(req.old_blob_url)
        new_content = await _download_blob(req.new_blob_url)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Datei konnte nicht heruntergeladen werden: {e}")

    try:
        old_df = _parse_catalog_df(old_content)
        new_df = _parse_catalog_df(new_content)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Katalog konnte nicht gelesen werden: {e}")

    old_stats = _catalog_stats(old_df)
    new_stats = _catalog_stats(new_df)

    # Category comparison
    old_categories = set()
    new_categories = set()

    old_first_col = old_df.columns[0] if len(old_df.columns) > 0 else None
    new_first_col = new_df.columns[0] if len(new_df.columns) > 0 else None

    if old_first_col:
        for val in old_df[old_first_col]:
            if pd.notna(val) and str(val).strip():
                old_categories.add(str(val).strip())

    if new_first_col:
        for val in new_df[new_first_col]:
            if pd.notna(val) and str(val).strip():
                new_categories.add(str(val).strip())

    added_cats = sorted(new_categories - old_categories)
    removed_cats = sorted(old_categories - new_categories)

    return {
        "old_count": old_stats["total_rows"],
        "new_count": new_stats["total_rows"],
        "added": max(0, new_stats["total_rows"] - old_stats["total_rows"]),
        "removed": max(0, old_stats["total_rows"] - new_stats["total_rows"]),
        "category_changes": {
            "added": added_cats,
            "removed": removed_cats,
        },
    }


@router.get("/catalog/products/{row_index}")
async def get_product_detail(row_index: int):
    """Get full extended product details by row index."""
    from services.catalog_index import get_catalog_index

    try:
        idx = get_catalog_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e) if settings.DEBUG else "Katalog konnte nicht geladen werden")

    detail = idx.get_product_extended(row_index)
    if not detail:
        raise HTTPException(status_code=404, detail=f"Produkt mit Index {row_index} nicht gefunden")

    return detail


@router.post("/catalog/products/override")
async def apply_product_override(req: OverrideRequest):
    """Apply a product override (placeholder -- overrides managed in Next.js via Prisma)."""
    if req.action not in ("edit", "add", "delete"):
        raise HTTPException(status_code=422, detail=f"Ungueltige Aktion: {req.action}")

    logger.info(f"Product override received: key={req.product_key}, action={req.action}")

    return {
        "status": "ok",
        "product_key": req.product_key,
        "action": req.action,
        "message": "Override registriert (Persistenz via Next.js/Prisma)",
    }
