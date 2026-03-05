"""
Configuration Management für Frank Türen AG Application.
Umgebungsvariablen und Settings mit Validierung.
"""

import os
from pathlib import Path
from enum import Enum
from typing import Optional


class Environment(str, Enum):
    """Umgebung der Anwendung"""
    DEVELOPMENT = "development"
    STAGING = "staging"
    PRODUCTION = "production"


# ─────────────────────────────────────────────────────────────────────────────
# BASE PATHS
# ─────────────────────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent.parent.absolute()
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = BASE_DIR / "uploads"
OUTPUTS_DIR = BASE_DIR / "outputs"
LOGS_DIR = BASE_DIR / "logs"

# Erstelle Verzeichnisse wenn nicht vorhanden
for directory in [DATA_DIR, UPLOADS_DIR, OUTPUTS_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────────────────────
# ENVIRONMENT SETTINGS
# ─────────────────────────────────────────────────────────────────────────────

class Settings:
    """Zentrale Settings für die Applikation"""
    
    # Basic
    ENVIRONMENT: Environment = Environment(
        os.environ.get("ENVIRONMENT", "development").lower()
    )
    DEBUG: bool = ENVIRONMENT == Environment.DEVELOPMENT
    TESTING: bool = os.environ.get("TESTING", "false").lower() == "true"
    
    # API
    API_TITLE: str = "Frank Türen AG – KI-gestützte Angebotserstellung"
    API_VERSION: str = "2.0.0"
    API_DESCRIPTION: str = "Production-Grade API für Machbarkeitsanalyse und Angebotserstellung"
    
    # Server
    HOST: str = os.environ.get("HOST", "0.0.0.0")
    PORT: int = int(os.environ.get("PORT", 8000))
    RELOAD: bool = ENVIRONMENT == Environment.DEVELOPMENT
    WORKERS: int = int(os.environ.get("WORKERS", 1))
    
    # Logging
    LOG_LEVEL: str = os.environ.get("LOG_LEVEL", "INFO" if not DEBUG else "DEBUG")
    # LOG_FORMAT removed: was defined but never read
    
    # File Upload
    ALLOWED_EXTENSIONS: set = {
        # Documents
        "pdf", "docx", "doc", "xlsx", "xls", "xlsm", "txt",
        # Images
        "jpg", "jpeg", "png", "bmp", "tif", "tiff",
        # CAD
        "dwg", "dxf",
    }
    MAX_FILE_SIZE_MB: int = int(os.environ.get("MAX_FILE_SIZE_MB", 100))
    MAX_FILES_PER_UPLOAD: int = int(os.environ.get("MAX_FILES_PER_UPLOAD", 20))
    UPLOAD_CLEANUP_HOURS: int = 24  # Alte Uploads nach X Stunden löschen
    
    # Caching
    CACHE_MAX_SIZE_MB: int = int(os.environ.get("CACHE_MAX_SIZE_MB", 500))
    TEXT_CACHE_TTL_SECONDS: int = 3600  # 1 Stunde
    PROJECT_CACHE_TTL_SECONDS: int = 1800  # 30 Minuten
    OFFER_CACHE_TTL_SECONDS: int = 1800  # 30 Minuten
    ERP_PRICE_CACHE_TTL_SECONDS: int = 3600  # 1 Stunde für ERP-Preise
    # Aliases (used by memory_cache.py)
    CACHE_TTL_TEXT: int = TEXT_CACHE_TTL_SECONDS
    CACHE_TTL_PROJECT: int = PROJECT_CACHE_TTL_SECONDS
    CACHE_TTL_OFFER: int = OFFER_CACHE_TTL_SECONDS
    ERP_CACHE_TTL: int = ERP_PRICE_CACHE_TTL_SECONDS
    
    # ERP Integration (Bohr System)
    ERP_ENABLED: bool = os.environ.get("ERP_ENABLED", "false").lower() == "true"
    ERP_BOHR_URL: Optional[str] = os.environ.get("ERP_BOHR_URL")
    ERP_BOHR_API_KEY: Optional[str] = os.environ.get("ERP_BOHR_API_KEY")
    ERP_BOHR_USERNAME: Optional[str] = os.environ.get("ERP_BOHR_USERNAME")
    ERP_BOHR_PASSWORD: Optional[str] = os.environ.get("ERP_BOHR_PASSWORD")
    ERP_REQUEST_TIMEOUT: float = float(os.environ.get("ERP_REQUEST_TIMEOUT", 10.0))
    ERP_USE_CACHE: bool = os.environ.get("ERP_USE_CACHE", "true").lower() == "true"
    ERP_FALLBACK_TO_ESTIMATE: bool = os.environ.get("ERP_FALLBACK_TO_ESTIMATE", "true").lower() == "true"
    
    # LLM (Ollama)
    OLLAMA_URL: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    OLLAMA_MODEL: str = os.environ.get("OLLAMA_MODEL", "llama3.2")
    OLLAMA_TIMEOUT_SHORT: float = 30.0
    OLLAMA_TIMEOUT_MEDIUM: float = 90.0
    OLLAMA_TIMEOUT_LONG: float = 120.0
    OLLAMA_FALLBACK_ENABLED: bool = True  # Regex-Fallback wenn Ollama nicht verfügbar
    
    # Claude API (optional, backward compatibility)
    ANTHROPIC_API_KEY: Optional[str] = os.environ.get("ANTHROPIC_API_KEY")
    
    # Telegram Bot
    TELEGRAM_TOKEN: Optional[str] = os.environ.get("TELEGRAM_BOT_TOKEN")
    TELEGRAM_ENABLED: bool = bool(TELEGRAM_TOKEN)
    
    # Catalog
    PRODUCT_CATALOG_FILE: str = str(DATA_DIR / "produktuebersicht.xlsx")
    CATALOG_RELOAD_INTERVAL_MINUTES: int = 60
    
    # Processing
    BACKGROUND_JOB_TIMEOUT_SECONDS: int = 3600  # 1 Stunde
    MAX_CONCURRENT_JOBS: int = int(os.environ.get("MAX_CONCURRENT_JOBS", 10))
    
    # Performance
    ENABLE_COMPRESSION: bool = True
    COMPRESSION_MIN_SIZE_BYTES: int = 1000
    
    # Security
    RATE_LIMIT_ENABLED: bool = ENVIRONMENT == Environment.PRODUCTION
    RATE_LIMIT_REQUESTS: int = 100  # Requests
    RATE_LIMIT_PERIOD_SECONDS: int = 60  # Pro Minute
    
    # CORS
    CORS_ORIGINS: list = [
        "http://localhost",
        "http://localhost:3000",
        "http://localhost:8000",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8000",
    ]
    if ENVIRONMENT == Environment.PRODUCTION:
        CORS_ORIGINS.extend([
            "https://franktueren.ch",
            "https://www.franktueren.ch",
        ])
    
    # Validation
    MIN_TEXT_LENGTH_FOR_ANALYSIS: int = 50  # Minimum Characters für Analysis
    MIN_PRODUCTS_FOR_MATCHING: int = 3  # Minimum gefundene Produkte
    
    # Pricing
    VAT_RATE: float = 0.081  # 8.1% MwSt Schweiz

    # Company Info
    COMPANY_NAME: str = "Frank Türen AG"
    COMPANY_ADDRESS: str = "Industriestrasse 12 · 6374 Buochs NW · Tel. 041 620 76 76 · www.franktueren.ch"
    COMPANY_LOCATION: str = "Buochs NW"

    # Matching
    MATCH_SCORE_THRESHOLD: int = 60  # Score >= 60 = machbar
    PARTIAL_MATCH_THRESHOLD: int = 35  # 35-59 = teilweise machbar
    
    @classmethod
    def validate(cls) -> bool:
        """Validiert kritische Settings"""
        issues = []
        
        # Katalog prüfen
        if not Path(cls.PRODUCT_CATALOG_FILE).exists():
            issues.append(f"Katalogdatei nicht gefunden: {cls.PRODUCT_CATALOG_FILE}")
        
        # Ollama/Claude Prüfung
        if not cls.ANTHROPIC_API_KEY and cls.ENVIRONMENT == Environment.PRODUCTION:
            # In Production sollte mindestens Claude oder Ollama verfügbar sein
            pass
        
        if issues:
            raise RuntimeError(f"Settings-Validierung fehlgeschlagen:\n" + "\n".join(issues))
        
        return True
    
    @classmethod
    def to_dict(cls) -> dict:
        """Gibt alle Settings als Dict zurück (ohne sensitive Daten)"""
        return {
            "environment": cls.ENVIRONMENT.value,
            "debug": cls.DEBUG,
            "api_version": cls.API_VERSION,
            "max_file_size_mb": cls.MAX_FILE_SIZE_MB,
            "cache_max_size_mb": cls.CACHE_MAX_SIZE_MB,
            "ollama_model": cls.OLLAMA_MODEL,
            "log_level": cls.LOG_LEVEL,
        }


# ─────────────────────────────────────────────────────────────────────────────
# GLOBAL INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

settings = Settings()

# Validierung beim Import
try:
    settings.validate()
except RuntimeError as e:
    import logging
    logger = logging.getLogger(__name__)
    logger.error(str(e))
    # In Development: nur warnen, in Production: Exception werfen
    if settings.ENVIRONMENT == Environment.PRODUCTION:
        raise
