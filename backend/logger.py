"""
Logging Configuration – Production-grade logging with structured outputs.
"""

import logging
import logging.handlers
import os
from typing import Optional
from config import settings


def setup_logging(
    name: Optional[str] = None,
    level: Optional[str] = None,
    log_file: Optional[str] = None,
) -> logging.Logger:
    """
    Configure and return a logger with optional file output.
    
    Args:
        name: Logger name (usually __name__)
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for log output
        
    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name or "frank_tueren_ag")
    
    # Use configured level if not specified
    log_level = getattr(logging, level or settings.LOG_LEVEL)
    logger.setLevel(log_level)
    
    # Avoid duplicate handlers
    if logger.handlers:
        return logger
    
    # Console handler (always)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    formatter = logging.Formatter(settings.LOG_FORMAT)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (optional)
    if log_file:
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5,
        )
        file_handler.setLevel(log_level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


# Root logger setup
root_logger = setup_logging(
    name=None,
    log_file=os.path.join(settings.OUTPUTS_DIR, "app.log")
)

# Module-specific loggers
def get_logger(module_name: str) -> logging.Logger:
    """Get a logger for a specific module."""
    return logging.getLogger(module_name)
