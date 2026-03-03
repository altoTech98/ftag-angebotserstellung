"""
Frank Türen AG – KI-gestützte Angebotserstellung
FastAPI Backend Entry Point
"""

import os
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import upload, analyze, offer, feedback, history

# Base directory for data files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

app = FastAPI(
    title="Frank Türen AG – Angebotserstellung",
    description="KI-gestützte Ausschreibungsanalyse und Angebotserstellung",
    version="1.0.0",
)

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(upload.router, prefix="/api")
app.include_router(analyze.router, prefix="/api")
app.include_router(offer.router, prefix="/api")
app.include_router(feedback.router, prefix="/api")
app.include_router(history.router, prefix="/api")

# Serve frontend static files
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(os.path.join(frontend_path, "index.html"))


@app.on_event("startup")
async def startup_event():
    """Pre-load product catalog and TF-IDF matrix at startup."""
    try:
        from services.product_matcher import load_product_catalog
        load_product_catalog()
        logging.getLogger(__name__).info("Product catalog pre-loaded at startup")
    except Exception as e:
        logging.getLogger(__name__).warning(f"Could not pre-load product catalog: {e}")


@app.get("/health")
async def health_check():
    api_key_set = bool(os.environ.get("ANTHROPIC_API_KEY"))
    from services.memory_cache import text_cache, offer_cache, project_cache
    return {
        "status": "ok",
        "service": "Frank Türen AG Angebotserstellung",
        "api_key_set": api_key_set,
        "cache": {
            "text": text_cache.stats(),
            "offer": offer_cache.stats(),
            "project": project_cache.stats(),
        },
    }
