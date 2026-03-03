"""
Catalog Router – View and update the FTAG product catalog.
GET  /api/catalog/info   – Current catalog metadata
POST /api/catalog/upload – Upload a new product catalog
"""

import os
import glob
import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException, UploadFile, File

logger = logging.getLogger(__name__)
router = APIRouter()

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")
PRODUCT_FILE = os.path.join(DATA_DIR, "produktuebersicht.xlsx")
MAX_BACKUPS = 3


@router.get("/catalog/info")
async def catalog_info():
    """Return metadata about the currently loaded product catalog."""
    from services.catalog_index import get_catalog_index, PRODUCT_FILE as pf

    if not os.path.exists(pf):
        raise HTTPException(status_code=404, detail="Kein Produktkatalog vorhanden.")

    try:
        idx = get_catalog_index()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Katalog konnte nicht geladen werden: {e}")

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
        import pandas as pd
        import io
        df = pd.read_excel(io.BytesIO(content), sheet_name=0, nrows=10)
        if len(df.columns) < 5:
            raise ValueError("Zu wenig Spalten")
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Ungueltige Excel-Datei: {e}")

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
        raise HTTPException(status_code=500, detail=f"Datei konnte nicht gespeichert werden: {e}")

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
            detail=f"Katalog konnte nicht geladen werden (altes Backup wiederhergestellt): {e}",
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
