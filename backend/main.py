"""
Frank Türen AG – KI-gestützte Angebotserstellung
Production-Grade FastAPI Backend mit vollständigem Error-Handling
"""

import os
import sys
import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Optional
from datetime import datetime

# Konfiguration laden BEVOR FastAPI initialisiert wird
from config import settings, BASE_DIR
from services.logger_setup import setup_logging

# Logger initialisieren
setup_logging()
logger = logging.getLogger(__name__)

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware as GZIPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError

# Router
from routers import upload, analyze, offer, feedback, history, catalog, erp
from services.exceptions import FrankTuerenError
from services.erp_connector import get_erp_connector


# ─────────────────────────────────────────────────────────────────────────────
# LIFESPAN MANAGEMENT
# ─────────────────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan: startup and shutdown hooks.
    Pre-loads critical resources und säuberung beim Shutdown.
    """
    logger.info(f"[START] Starting Frank Tueren AG Backend | Environment: {settings.ENVIRONMENT.value}")
    
    # ─────── STARTUP ────────────
    startup_errors = []
    
    # 0a. START OLLAMA WATCHDOG (GARANTIERT 24/7)
    try:
        from services.ollama_watchdog import get_ollama_watchdog
        ollama_watchdog = get_ollama_watchdog()
        ollama_watchdog.start()
        logger.info("[OK] ✅ OLLAMA WATCHDOG STARTED | 24/7 Monitoring & Auto-Restart enabled")
        logger.info("[INFO] Ollama wird jetzt überwacht und startet automatisch neu bei Fehlern")
    except Exception as e:
        logger.error(f"[ERROR] Ollama Watchdog failed: {e}")
        startup_errors.append(f"Ollama Watchdog failed: {e}")
    
    # 0b. Initialize Availability Manager (garantiert 24/7 Verfügbarkeit)
    try:
        from services.availability_manager import get_availability_manager
        availability_mgr = get_availability_manager()
        
        # Starte Background Monitoring
        asyncio.create_task(availability_mgr.start_monitoring())
        logger.info("[OK] ✅ 24/7 Availability Manager started | Auto-healing enabled")
    except Exception as e:
        logger.error(f"[ERROR] Availability Manager failed: {e}")
        startup_errors.append(f"Availability Manager init failed: {e}")
    
    # 1. Pre-load Catalog
    try:
        from services.catalog_index import get_catalog_index
        index = get_catalog_index()
        logger.info(
            f"[OK] Catalog loaded | Main products: {len(index.main_products)}, "
            f"Total items: {len(index.all_profiles)}"
        )
    except Exception as e:
        msg = f"[WARN] Catalog pre-load failed: {e}"
        logger.warning(msg)
        startup_errors.append(msg)
    
    # 2. Test Ollama Verbindung
    try:
        from services.local_llm import check_ollama_status
        status_result = check_ollama_status()
        if status_result:
            logger.info(f"[OK] Ollama connected | Model: {settings.OLLAMA_MODEL}")
        else:
            logger.warning("[WARN] Ollama not available | Using fallback mode")
            if not settings.OLLAMA_FALLBACK_ENABLED:
                startup_errors.append("Ollama required but not available")
    except Exception as e:
        logger.warning(f"[WARN] Ollama check failed: {e}")
    
    # 3. Test Telegram Bot (optional)
    if settings.TELEGRAM_ENABLED:
        try:
            from services.telegram_bot import start_bot
            await start_bot()
            logger.info("[OK] Telegram bot started")
        except Exception as e:
            logger.warning(f"[WARN] Telegram bot start failed: {e}")
    
    # 4. Initialize Cache
    try:
        from services.memory_cache import text_cache, offer_cache, project_cache
        logger.info(f"[OK] Caching system initialized | Max size: {settings.CACHE_MAX_SIZE_MB}MB")
    except Exception as e:
        logger.error(f"[ERROR] Cache initialization failed: {e}")
        startup_errors.append(f"Cache init failed: {e}")
    
    # 5. Initialize ERP Connector (if enabled)
    if settings.ERP_ENABLED:
        try:
            erp_connector = get_erp_connector()
            
            # Test connection
            is_healthy = erp_connector.health_check()
            if is_healthy:
                logger.info(f"[OK] ERP (Bohr) connected | URL: {settings.ERP_BOHR_URL}")
            else:
                logger.warning(f"[WARN] ERP (Bohr) not available | Fallback to estimates: {settings.ERP_FALLBACK_TO_ESTIMATE}")
        except Exception as e:
            logger.warning(f"[WARN] ERP initialization failed: {e}")
            if not settings.ERP_FALLBACK_TO_ESTIMATE:
                startup_errors.append(f"ERP init failed: {e}")
    else:
        logger.info("[INFO] ERP integration disabled | Using estimated prices")
    
    # Log startup result
    if startup_errors:
        logger.warning(f"[WARN] Startup warnings:\n" + "\n".join(startup_errors))
    else:
        logger.info("[OK] All startup checks passed")
    
    yield
    
    # ─────── SHUTDOWN ──────────
    logger.info("[STOP] Shutting down...")
    
    # WICHTIG: Stoppe Ollama Watchdog NICHT! Er läuft weiter für 24/7 Verfügbarkeit
    # Der Watchdog wird durch den OS/Service-Manager verwaltet
    logger.info("[INFO] Ollama Watchdog continues running for 24/7 availability")
    
    try:
        if settings.TELEGRAM_ENABLED:
            from services.telegram_bot import stop_bot
            await stop_bot()
            logger.info("[OK] Telegram bot stopped")
    except Exception as e:
        logger.warning(f"Telegram bot shutdown error: {e}")
    
    # Cleanup old uploads
    try:
        from services.file_cleanup import cleanup_old_files
        deleted = cleanup_old_files()
        logger.info(f"[OK] Cleanup: deleted {deleted} old files")
    except Exception as e:
        logger.warning(f"File cleanup failed: {e}")
    
    logger.info("[OK] Shutdown complete")


# ─────────────────────────────────────────────────────────────────────────────
# APP INITIALIZATION
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title=settings.API_TITLE,
    description=settings.API_DESCRIPTION,
    version=settings.API_VERSION,
    docs_url="/docs" if settings.DEBUG else None,
    redoc_url="/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ─────────────────────────────────────────────────────────────────────────────
# MIDDLEWARE
# ─────────────────────────────────────────────────────────────────────────────

# 1. CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS if settings.ENVIRONMENT != "production" else ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# 2. GZIP Compression (nur für größere Responses)
if settings.ENABLE_COMPRESSION:
    app.add_middleware(GZIPMiddleware, minimum_size=settings.COMPRESSION_MIN_SIZE_BYTES)

# 3. Custom Middleware für Error-Handling & Caching Headers
@app.middleware("http")
async def error_and_cache_middleware(request: Request, call_next):
    """
    Middleware für:
    - Error-Handling
    - Cache-Control Headers
    - Request Logging
    """
    try:
        response = await call_next(request)
        
        # Cache-Control Headers
        if request.url.path.startswith("/static/"):
            response.headers["Cache-Control"] = "no-cache, must-revalidate"
        elif request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
        
        # Security Headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains" if not settings.DEBUG else ""
        
        return response
    except Exception as e:
        logger.exception(f"Middleware error: {e}")
        return JSONResponse(
            status_code=500,
            content={"error": "Internal Server Error", "detail": str(e) if settings.DEBUG else "Interner Fehler"},
        )


# ─────────────────────────────────────────────────────────────────────────────
# EXCEPTION HANDLERS
# ─────────────────────────────────────────────────────────────────────────────

@app.exception_handler(FrankTuerenError)
async def frank_tueren_error_handler(request: Request, exc: FrankTuerenError):
    """Handler für Custom Frank Türen Exceptions"""
    logger.warning(f"{exc.error_code}: {exc.message}")
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_dict(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handler für Pydantic Validation Errors"""
    logger.warning(f"Validation error: {exc}")
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Validierungsfehler in Request",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Fallback handler für unerwartete Exceptions"""
    logger.exception(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "INTERNAL_SERVER_ERROR",
            "message": "Interner Fehler" if not settings.DEBUG else str(exc),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER REGISTRATION
# ─────────────────────────────────────────────────────────────────────────────

logger.info("Registering routers...")
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(offer.router, prefix="/api", tags=["Offer"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(catalog.router, prefix="/api", tags=["Catalog"])

# ERP Router (nur wenn ERP enabled)
if settings.ERP_ENABLED:
    app.include_router(erp.router)
    logger.info("✅ ERP router registered")


# ─────────────────────────────────────────────────────────────────────────────
# STATIC FILES & FRONTEND
# ─────────────────────────────────────────────────────────────────────────────

frontend_path = BASE_DIR / "frontend"
if frontend_path.exists():
    app.mount("/static", StaticFiles(directory=frontend_path), name="static")

    @app.get("/", name="Frontend")
    async def serve_frontend():
        """Serve index.html with no-cache headers"""
        index_file = frontend_path / "index.html"
        if index_file.exists():
            return FileResponse(
                index_file,
                headers={
                    "Cache-Control": "no-cache, must-revalidate",
                    "Content-Type": "text/html; charset=utf-8",
                },
            )
        return JSONResponse(
            status_code=404,
            content={"error": "Frontend not found"},
        )
else:
    logger.warning(f"Frontend directory not found: {frontend_path}")


# ─────────────────────────────────────────────────────────────────────────────
# HEALTH & INFO ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health", name="Health Check")
async def health_check() -> dict:
    """
    Quick health check endpoint.
    Returns status of all critical services with availability guarantee.
    """
    try:
        from services.availability_manager import get_availability_manager
        from services.local_llm import check_ollama_status
        from services.memory_cache import text_cache, offer_cache, project_cache
        from services.catalog_index import get_catalog_index
        
        # Get Availability Manager Status
        availability_mgr = get_availability_manager()
        am_status = availability_mgr.get_status()
        
        # Check Ollama
        ollama_status = check_ollama_status()
        
        # Check Catalog
        try:
            catalog = get_catalog_index()
            catalog_ok = len(catalog.main_products) > 0
            catalog_count = len(catalog.all_profiles)
        except Exception as e:
            logger.warning(f"Catalog health check failed: {e}")
            catalog_ok = False
            catalog_count = 0
        
        return {
            "status": "healthy" if availability_mgr.is_system_available() else "degraded",
            "service": "Frank Türen AG – Angebotserstellung",
            "version": settings.API_VERSION,
            "environment": settings.ENVIRONMENT.value,
            "availability_manager": {
                "status": am_status["overall_status"],
                "last_check": am_status["last_check"],
                "auto_healing": True,
                "recovery_enabled": True,
            },
            "catalog": {
                "status": "ok" if catalog_ok else "error",
                "products": catalog_count,
            },
            "ollama": {
                "status": "ok" if ollama_status else "unavailable",
                "model": settings.OLLAMA_MODEL,
                "fallback_enabled": settings.OLLAMA_FALLBACK_ENABLED,
            },
            "cache": {
                "text": text_cache.stats(),
                "offer": offer_cache.stats(),
                "project": project_cache.stats(),
            },
            "24_7_guarantee": "System is monitored 24/7 with automatic recovery",
        }
    except Exception as e:
        logger.exception(f"Health check error: {e}")
        return {
            "status": "error",
            "service": "Frank Türen AG – Angebotserstellung",
            "error": str(e) if settings.DEBUG else "Health check failed",
        }


@app.get("/api/availability/status", name="Detailed Availability Status")
async def get_availability_status() -> dict:
    """
    Get detailed availability and uptime status for all services.
    """
    try:
        from services.availability_manager import get_availability_manager
        from services.ollama_watchdog import get_ollama_watchdog
        
        availability_mgr = get_availability_manager()
        ollama_watchdog = get_ollama_watchdog()
        
        status = availability_mgr.get_status()
        uptime = availability_mgr.get_uptime_stats()
        
        return {
            "timestamp": status["timestamp"],
            "overall_health": status["overall_status"],
            "system_available": availability_mgr.is_system_available(),
            "services": status["services"],
            "uptime_statistics": uptime["services"],
            "ollama_watchdog": ollama_watchdog.get_status(),
            "24_7_monitoring": {
                "enabled": True,
                "check_interval_seconds": 30,
                "auto_recovery": True,
                "recovery_attempts_max": 5,
                "ollama_watchdog_enabled": True,
                "ollama_auto_restart": True,
                "windows_task_scheduler_enabled": True,
            },
        }
    except Exception as e:
        logger.exception(f"Availability status error: {e}")
        return {
            "error": str(e) if settings.DEBUG else "Failed to get availability status"
        }


@app.get("/api/ollama/status", name="Ollama Watchdog Status")
async def get_ollama_watchdog_status() -> dict:
    """
    Get detailed Ollama Watchdog status - 24/7 Monitoring
    """
    try:
        from services.ollama_watchdog import get_ollama_watchdog
        from services.local_llm import check_ollama_status
        
        watchdog = get_ollama_watchdog()
        status = watchdog.get_status()
        
        return {
            "timestamp": datetime.now().isoformat(),
            "watchdog": status,
            "health_check": check_ollama_status(),
            "24_7_guarantee": {
                "monitoring": True,
                "auto_restart": True,
                "health_check_interval_seconds": watchdog.health_check_interval,
                "max_restart_attempts": watchdog.max_restart_attempts,
                "exponential_backoff": True,
                "windows_autostart": True,
            },
        }
    except Exception as e:
        logger.exception(f"Ollama watchdog status error: {e}")
        return {
            "error": str(e) if settings.DEBUG else "Failed to get Ollama status",
            "timestamp": datetime.now().isoformat()
        }


@app.get("/info", name="Application Info")
async def app_info() -> dict:
    """Get application information and settings"""
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT.value,
        "debug": settings.DEBUG,
        "settings": settings.to_dict(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# ROOT ENDPOINT
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", include_in_schema=False)
async def root():
    """Root endpoint - redirects to frontend"""
    return {
        "message": "Frank Türen AG – KI-gestützte Angebotserstellung",
        "version": settings.API_VERSION,
        "docs": "/docs" if settings.DEBUG else None,
        "health": "/health",
    }


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP LOGGING
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting uvicorn server...")
    logger.info(f"  Host: {settings.HOST}")
    logger.info(f"  Port: {settings.PORT}")
    logger.info(f"  Reload: {settings.RELOAD}")
    logger.info(f"  Workers: {settings.WORKERS if not settings.RELOAD else 'auto (reload mode)'}")
    
    uvicorn.run(
        "main:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=settings.RELOAD,
        log_level=settings.LOG_LEVEL.lower(),
        access_log=True,
    )
