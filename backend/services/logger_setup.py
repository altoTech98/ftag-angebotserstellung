"""
═══════════════════════════════════════════════════════════════════════════════
Logging Setup & Configuration
Strukturiertes Logging für Production
═══════════════════════════════════════════════════════════════════════════════
"""

import logging
import logging.config
import json
from pathlib import Path
from config import settings, BASE_DIR

# Logs-Verzeichnis
LOGS_DIR = BASE_DIR / "logs"
LOGS_DIR.mkdir(parents=True, exist_ok=True)


class JSONFormatter(logging.Formatter):
    """JSON-formatierter Logger für strukturierte Logs"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data, ensure_ascii=False)


class SafeStreamHandler(logging.StreamHandler):
    """StreamHandler that replaces unencodable characters instead of crashing."""
    def emit(self, record):
        try:
            msg = self.format(record)
            stream = self.stream
            # Replace characters that can't be encoded (e.g. emojis on cp1252)
            if hasattr(stream, 'encoding') and stream.encoding:
                msg = msg.encode(stream.encoding, errors='replace').decode(stream.encoding, errors='replace')
            stream.write(msg + self.terminator)
            self.flush()
        except Exception:
            self.handleError(record)


LOGGING_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "standard": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        },
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(funcName)s: %(message)s"
        },
        "json": {
            "()": JSONFormatter,
        }
    },
    "handlers": {
        "console": {
            "()": SafeStreamHandler,
            "level": settings.LOG_LEVEL,
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        },
        "file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "detailed",
            "filename": LOGS_DIR / "app.log",
            "maxBytes": 10485760,  # 10MB
            "backupCount": 5,
        },
        "error_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "ERROR",
            "formatter": "detailed",
            "filename": LOGS_DIR / "errors.log",
            "maxBytes": 10485760,
            "backupCount": 5,
        },
        "json_file": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "DEBUG",
            "formatter": "json",
            "filename": LOGS_DIR / "structured.log",
            "maxBytes": 10485760,
            "backupCount": 5,
        }
    },
    "loggers": {
        "": {  # root logger
            "handlers": ["console", "file", "json_file"],
            "level": settings.LOG_LEVEL,
            "propagate": True
        },
        "uvicorn": {
            "handlers": ["console", "file"],
            "level": "INFO",
            "propagate": False
        },
        "uvicorn.access": {
            "handlers": ["file"],
            "level": "INFO",
            "propagate": False
        },
        "sqlalchemy": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False
        }
    }
}


def setup_logging():
    """Initialisiert Logging-Konfiguration"""
    logging.config.dictConfig(LOGGING_CONFIG)
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialisiert | Environment: {settings.ENVIRONMENT}")
    return logger


def get_logger(name: str) -> logging.Logger:
    """Gibt einen Logger mit Name zurück"""
    return logging.getLogger(name)


if __name__ == "__main__":
    logger = setup_logging()
    logger.info("Test: Info-Level")
    logger.warning("Test: Warning-Level")
    logger.error("Test: Error-Level")
