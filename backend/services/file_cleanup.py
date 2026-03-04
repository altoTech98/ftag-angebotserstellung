"""
File Cleanup Service
Löscht alte/abgelaufene Dateien aus dem Upload-Verzeichnis
"""

import os
import logging
from datetime import datetime, timedelta
from pathlib import Path

from config import settings

logger = logging.getLogger(__name__)


def cleanup_old_files(hours: int = None) -> int:
    """
    Löscht Dateien älter als X Stunden aus dem Upload-Verzeichnis.
    
    Args:
        hours: Alter in Stunden (default: settings.UPLOAD_CLEANUP_HOURS)
    
    Returns:
        Anzahl der gelöschten Dateien
    """
    if hours is None:
        hours = settings.UPLOAD_CLEANUP_HOURS
    
    uploads_dir = Path(settings.UPLOADS_DIR)
    if not uploads_dir.exists():
        return 0
    
    deleted_count = 0
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    try:
        for file_path in uploads_dir.glob("*"):
            if not file_path.is_file():
                continue
            
            # Check file modification time
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if file_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                    logger.debug(f"Deleted old file: {file_path.name}")
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path.name}: {e}")
    
    except Exception as e:
        logger.error(f"Cleanup error: {e}")
    
    return deleted_count


def cleanup_cache_dir(hours: int = 1) -> int:
    """
    Löscht alte Dateien aus dem Output/Cache Verzeichnis.
    
    Returns:
        Anzahl der gelöschten Dateien
    """
    outputs_dir = Path(settings.OUTPUTS_DIR)
    if not outputs_dir.exists():
        return 0
    
    deleted_count = 0
    cutoff_time = datetime.now() - timedelta(hours=hours)
    
    try:
        for file_path in outputs_dir.glob("*"):
            if not file_path.is_file():
                continue
            
            file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
            
            if file_mtime < cutoff_time:
                try:
                    file_path.unlink()
                    deleted_count += 1
                except Exception as e:
                    logger.warning(f"Failed to delete {file_path.name}: {e}")
    
    except Exception as e:
        logger.error(f"Output cleanup error: {e}")
    
    return deleted_count
