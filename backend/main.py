"""
Frank Türen AG – KI-gestützte Angebotserstellung
FastAPI Backend Entry Point
"""

import os
import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from routers import upload, analyze, offer, feedback, history, catalog

# Base directory for data files
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    _logger = logging.getLogger(__name__)

    # Startup: pre-load catalog
    try:
        from services.catalog_index import get_catalog_index
        index = get_catalog_index()
        _logger.info(
            f"Catalog index pre-loaded: {len(index.main_products)} main products, "
            f"{len(index.all_profiles)} total"
        )
    except Exception as e:
        _logger.warning(f"Could not pre-load catalog index: {e}")

    # Startup: start Telegram bot
    try:
        from services.telegram_bot import start_bot
        await start_bot()
    except Exception as e:
        _logger.warning(f"Telegram bot start failed: {e}")

    yield

    # Shutdown: stop Telegram bot
    try:
        from services.telegram_bot import stop_bot
        await stop_bot()
    except Exception as e:
        _logger.warning(f"Telegram bot shutdown error: {e}")


app = FastAPI(
    title="Frank Türen AG – Angebotserstellung",
    description="KI-gestützte Ausschreibungsanalyse und Angebotserstellung",
    version="1.0.0",
    lifespan=lifespan,
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
app.include_router(catalog.router, prefix="/api")

# Serve frontend static files (with no-cache headers to prevent stale JS/CSS)
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(frontend_path):
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(
            os.path.join(frontend_path, "index.html"),
            headers={"Cache-Control": "no-cache, must-revalidate"},
        )


@app.middleware("http")
async def add_cache_headers(request: Request, call_next):
    response = await call_next(request)
    if request.url.path.startswith("/static/"):
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
    return response


@app.get("/health")
async def health_check():
    from services.local_llm import check_ollama_status
    from services.memory_cache import text_cache, offer_cache, project_cache
    ollama = check_ollama_status()
    return {
        "status": "ok",
        "service": "Frank Türen AG Angebotserstellung",
        "ollama": ollama,
        "cache": {
            "text": text_cache.stats(),
            "offer": offer_cache.stats(),
            "project": project_cache.stats(),
        },
    }
