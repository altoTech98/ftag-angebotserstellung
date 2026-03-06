"""
Frank Türen AG – KI-gestützte Angebotserstellung
Production-Grade FastAPI Backend mit vollständigem Error-Handling
"""

import logging
import asyncio
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware as GZIPMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.exceptions import RequestValidationError

from config import settings, BASE_DIR
from services.logger_setup import setup_logging
from routers import upload, analyze, offer, feedback, history, catalog, erp, auth
from services.exceptions import FrankTuerenError
from services.erp_connector import get_erp_connector

# Logger initialisieren (nach allen Imports)
setup_logging()
logger = logging.getLogger(__name__)

# Rate Limiting (optional dependency)
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler  # noqa: E402
    from slowapi.util import get_remote_address  # noqa: E402
    from slowapi.errors import RateLimitExceeded  # noqa: E402
    SLOWAPI_AVAILABLE = True
except ImportError:
    SLOWAPI_AVAILABLE = False


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
    
    # 0. Initialize Auth (Admin-User erstellen falls nötig)
    try:
        from services.auth_service import init_admin_user
        init_admin_user()
    except Exception as e:
        logger.error(f"[ERROR] Auth initialization failed: {e}")
        startup_errors.append(f"Auth init failed: {e}")

    # 0a. START OLLAMA WATCHDOG (GARANTIERT 24/7)
    try:
        from services.ollama_watchdog import get_ollama_watchdog
        ollama_watchdog = get_ollama_watchdog()
        ollama_watchdog.start()
        logger.info("[OK] OLLAMA WATCHDOG STARTED | 24/7 Monitoring & Auto-Restart enabled")
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
        logger.info("[OK] 24/7 Availability Manager started | Auto-healing enabled")
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
    
    # 2. Initialize AI Service (Claude -> Ollama -> Regex failover)
    try:
        from services.ai_service import get_ai_service
        ai_service = get_ai_service()
        ai_status = ai_service.get_status()
        engine = ai_status["engine"]
        model = ai_status["model"]
        if engine == "claude":
            logger.info(f"[OK] AI Service: Claude API | Model: {model}")
        elif engine == "ollama":
            logger.info(f"[OK] AI Service: Ollama (lokal) | Model: {model}")
        else:
            logger.warning("[WARN] AI Service: Regex-Fallback (keine KI-Engine verfuegbar)")
    except Exception as e:
        logger.warning(f"[WARN] AI Service init failed: {e}")
    
    # 3. Test Telegram Bot (optional)
    if settings.TELEGRAM_ENABLED:
        try:
            from services.telegram_bot import start_bot
            await start_bot()
            logger.info("[OK] Telegram bot started")
        except Exception as e:
            logger.warning(f"[WARN] Telegram bot start failed: {e}")
    
    # 3b. Start periodic file cleanup (every 6 hours)
    async def _periodic_cleanup():
        while True:
            await asyncio.sleep(6 * 3600)  # 6 hours
            try:
                from services.file_cleanup import cleanup_old_files
                deleted = cleanup_old_files()
                if deleted:
                    logger.info(f"[Cleanup] Periodic cleanup: deleted {deleted} old files")
            except Exception as e:
                logger.warning(f"Periodic cleanup failed: {e}")

    asyncio.create_task(_periodic_cleanup())

    # 4. Initialize Cache
    try:
        import services.memory_cache  # noqa: F401 — triggers cache initialization
        logger.info("[OK] Caching system initialized | Max size: %sMB", settings.CACHE_MAX_SIZE_MB)
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
        logger.warning("[WARN] Startup warnings:\n" + "\n".join(startup_errors))
    else:
        logger.info("[OK] All startup checks passed")
    
    yield
    
    # ─────── SHUTDOWN ──────────
    logger.info("[STOP] Shutting down...")
    
    # Stop Ollama Watchdog gracefully
    try:
        from services.ollama_watchdog import get_ollama_watchdog
        ollama_watchdog = get_ollama_watchdog()
        ollama_watchdog.stop()
        logger.info("[OK] Ollama Watchdog stopped")
    except Exception as e:
        logger.warning(f"Ollama Watchdog shutdown error: {e}")
    
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

# 0. Rate Limiting (if enabled and slowapi available)
if settings.RATE_LIMIT_ENABLED and SLOWAPI_AVAILABLE:
    limiter = Limiter(key_func=get_remote_address, default_limits=[f"{settings.RATE_LIMIT_REQUESTS}/minute"])
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    logger.info(f"[OK] Rate limiting enabled: {settings.RATE_LIMIT_REQUESTS} req/min")
elif settings.RATE_LIMIT_ENABLED and not SLOWAPI_AVAILABLE:
    logger.warning("[WARN] Rate limiting enabled in config but slowapi not installed. Run: pip install slowapi")

# 1. CORS Middleware
_cors_origins = settings.CORS_ORIGINS if settings.ENVIRONMENT == "production" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=("*" not in _cors_origins),  # credentials requires explicit origins
    allow_methods=["*"],
    allow_headers=["*"],
    max_age=3600,
)

# 2. GZIP Compression (nur für größere Responses)
if settings.ENABLE_COMPRESSION:
    app.add_middleware(GZIPMiddleware, minimum_size=settings.COMPRESSION_MIN_SIZE_BYTES)

# 3. Auth Middleware – schützt alle /api/* Routen (außer Whitelist)
AUTH_WHITELIST = {
    "/api/auth/login",
    "/api/auth/logout",
    "/health",
    "/info",
    "/",
    "/docs",
    "/redoc",
    "/openapi.json",
}

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """Check Bearer token for protected /api/* routes."""
    path = request.url.path
    method = request.method

    # Skip auth for whitelisted paths, OPTIONS, static files, and downloads
    if (
        method == "OPTIONS"
        or path in AUTH_WHITELIST
        or path.startswith("/static/")
        or not path.startswith("/api/")
        or "/download" in path
    ):
        return await call_next(request)

    # Extract Bearer token
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        return JSONResponse(
            status_code=401,
            content={"detail": "Nicht authentifiziert"},
        )

    try:
        from services.auth_service import verify_token
        token = auth_header[7:]  # Remove "Bearer " prefix
        user = verify_token(token)
        if not user:
            return JSONResponse(
                status_code=401,
                content={"detail": "Token ungueltig oder abgelaufen"},
            )
    except Exception as e:
        logger.error(f"Auth verification error: {e}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Authentifizierung fehlgeschlagen"},
        )

    return await call_next(request)

# 4. Custom Middleware für Error-Handling & Caching Headers
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
app.include_router(auth.router, prefix="/api", tags=["Auth"])
app.include_router(upload.router, prefix="/api", tags=["Upload"])
app.include_router(analyze.router, prefix="/api", tags=["Analysis"])
app.include_router(offer.router, prefix="/api", tags=["Offer"])
app.include_router(feedback.router, prefix="/api", tags=["Feedback"])
app.include_router(history.router, prefix="/api", tags=["History"])
app.include_router(catalog.router, prefix="/api", tags=["Catalog"])

# ERP Router (nur wenn ERP enabled)
if settings.ERP_ENABLED:
    app.include_router(erp.router)
    logger.info("[OK] ERP router registered")


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
        from services.ai_service import get_ai_service
        from services.local_llm import check_ollama_status_live
        from services.memory_cache import text_cache, offer_cache, project_cache
        from services.catalog_index import get_catalog_index

        # Get Availability Manager Status
        availability_mgr = get_availability_manager()
        am_status = availability_mgr.get_status()

        # Get AI Service status (unified engine status)
        ai_service = get_ai_service()
        ai_status = ai_service.get_status()

        # Check Ollama (live check without cache, for backward compat)
        ollama_status = check_ollama_status_live()

        # Check Catalog
        try:
            catalog = get_catalog_index()
            catalog_ok = len(catalog.main_products) > 0
            catalog_count = len(catalog.all_profiles)
        except Exception as e:
            logger.warning(f"Catalog health check failed: {e}")
            catalog_ok = False
            catalog_count = 0

        # Add context usage to AI status
        ai_status["context"] = ai_service.get_context_usage()

        # Health info with AI engine status for frontend
        ollama_available = ollama_status.get("available", False)
        health_response = {
            "status": "healthy" if availability_mgr.is_system_available() else "degraded",
            "service": "Frank Türen AG – Angebotserstellung",
            "version": settings.API_VERSION,
            "ai": ai_status,
            "ollama": {
                "available": ollama_available,
                "fallback_enabled": settings.OLLAMA_FALLBACK_ENABLED,
            },
        }

        # Detailed info only in development/debug mode
        if settings.DEBUG:
            health_response["ollama"].update({
                "status": "ok" if ollama_available else "unavailable",
                "models": ollama_status.get("models", []),
                "model": settings.OLLAMA_MODEL,
            })
            health_response.update({
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
                "cache": {
                    "text": text_cache.stats(),
                    "offer": offer_cache.stats(),
                    "project": project_cache.stats(),
                },
            })

        return health_response
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
    """Get application information and settings (only in debug mode)"""
    if not settings.DEBUG:
        return {
            "name": settings.API_TITLE,
            "version": settings.API_VERSION,
        }
    return {
        "name": settings.API_TITLE,
        "version": settings.API_VERSION,
        "environment": settings.ENVIRONMENT.value,
        "debug": settings.DEBUG,
        "settings": settings.to_dict(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# STARTUP LOGGING
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting uvicorn server...")
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
