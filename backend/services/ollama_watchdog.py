"""
Ollama Watchdog Service - Garantiert 24/7 Verfügbarkeit
Überwacht Ollama-Prozess und startet ihn automatisch neu bei Fehlern
"""

import os
import sys
import subprocess
import time
import logging
import threading
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class OllamaWatchdog:
    """
    Watchdog Service für Ollama
    - Überwacht Prozess kontinuierlich
    - Auto-Restart bei Crashes
    - Health Checks alle 30 Sekunden
    - Exponential Backoff bei Fehlern
    """
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.running = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.health_check_interval = 30  # Sekunden
        self.max_restart_attempts = 10
        self.restart_attempts = 0
        self.last_restart = None
        self.failure_backoff = 5  # Sekunden, erhöht sich exponentiell
        
        # Ollama Path Detection
        self.ollama_paths = self._detect_ollama_path()
        self.ollama_binary = self._find_ollama_binary()
        
        logger.info(f"OllamaWatchdog initialized | Binary: {self.ollama_binary}")
    
    def _detect_ollama_path(self) -> list:
        """Detect possible Ollama installation paths on Windows"""
        possible_paths = [
            Path(os.getenv("APPDATA", "")) / "Ollama",  # Standard Windows
            Path("C:/Program Files/Ollama"),
            Path("C:/Program Files (x86)/Ollama"),
            Path(os.path.expanduser("~/.ollama")),
        ]
        return [p for p in possible_paths if p.exists()]
    
    def _find_ollama_binary(self) -> Optional[str]:
        """Finde Ollama executable"""
        # Try direct ollama command (wenn in PATH)
        try:
            result = subprocess.run(
                ["where", "ollama"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                path = result.stdout.strip().split('\n')[0]
                if path:
                    return path
        except Exception as e:
            logger.debug(f"Ollama not in PATH via where: {e}")
        
        # Suche in bekannten Pfaden
        for base_path in self.ollama_paths:
            binary = base_path / "ollama.exe"
            if binary.exists():
                return str(binary)
        
        # Fallback: Einfach "ollama" versuchen (muss in PATH sein)
        logger.info("Using 'ollama' command directly (assuming it's in PATH)")
        return "ollama"
    
    def check_ollama_health(self) -> bool:
        """
        Prüfe Ollama Health via API
        """
        try:
            response = requests.get(
                "http://localhost:11434/api/tags",
                timeout=5
            )
            return response.status_code == 200
        except requests.exceptions.ConnectionError:
            return False
        except Exception as e:
            logger.debug(f"Health check error: {e}")
            return False
    
    def start_ollama(self) -> bool:
        """
        Starte Ollama Prozess
        """
        if not self.ollama_binary:
            logger.error("Cannot start Ollama: binary not found")
            return False
        
        if self.is_running():
            logger.info("Ollama already running")
            return True
        
        try:
            # Starte als detached process
            if sys.platform == "win32":
                # Windows: CREATE_NEW_PROCESS_GROUP für echten Detach
                creation_flags = (
                    subprocess.CREATE_NEW_PROCESS_GROUP | 
                    subprocess.CREATE_NO_WINDOW
                )
                self.process = subprocess.Popen(
                    [self.ollama_binary, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    creationflags=creation_flags,
                    close_fds=True
                )
            else:
                # Unix-like
                self.process = subprocess.Popen(
                    [self.ollama_binary, "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    stdin=subprocess.DEVNULL,
                    start_new_session=True,
                    close_fds=True
                )
            
            logger.info(f"✅ Ollama started | PID: {self.process.pid}")
            self.last_restart = datetime.now()
            
            # Warte bis Ollama bereit ist
            max_wait = 30
            waited = 0
            while waited < max_wait:
                if self.check_ollama_health():
                    logger.info("✅ Ollama Health Check passed")
                    self.restart_attempts = 0  # Reset counter
                    return True
                
                time.sleep(2)
                waited += 2
            
            logger.warning(f"Ollama started but health check failed after {max_wait}s")
            return False
        
        except Exception as e:
            logger.error(f"❌ Failed to start Ollama: {e}")
            return False
    
    def is_running(self) -> bool:
        """Prüfe ob Ollama läuft"""
        if self.process is None:
            return False
        
        poll = self.process.poll()
        if poll is not None:
            # Prozess ist beendet
            return False
        
        # Zusätzlich: Health Check
        return self.check_ollama_health()
    
    def restart_ollama(self) -> bool:
        """
        Restart Ollama mit Exponential Backoff
        """
        logger.warning(f"⚠️ Restarting Ollama (attempt {self.restart_attempts + 1}/{self.max_restart_attempts})")
        
        # Kill existing process
        if self.process:
            try:
                if sys.platform == "win32":
                    subprocess.run(
                        ["taskkill", "/PID", str(self.process.pid), "/F"],
                        capture_output=True,
                        timeout=5
                    )
                else:
                    os.kill(self.process.pid, 9)
                time.sleep(2)
            except Exception as e:
                logger.warning(f"Could not kill Ollama process: {e}")
        
        # Exponential backoff
        wait_time = min(self.failure_backoff * (2 ** self.restart_attempts), 120)
        logger.info(f"Waiting {wait_time}s before restart...")
        time.sleep(wait_time)
        
        self.restart_attempts += 1
        
        if self.restart_attempts > self.max_restart_attempts:
            logger.error(f"❌ Max restart attempts ({self.max_restart_attempts}) exceeded!")
            return False
        
        return self.start_ollama()
    
    def monitor_loop(self):
        """
        Hauptüberwachungs-Loop - läuft in separatem Thread
        """
        logger.info("🔍 OllamaWatchdog monitor loop started")
        
        # Initial: Starte Ollama falls nicht laufen
        if not self.is_running():
            logger.info("Ollama not running, starting...")
            self.start_ollama()
        
        while self.running:
            try:
                # Health Check
                if not self.is_running():
                    logger.error("❌ Ollama is DOWN!")
                    
                    if not self.restart_ollama():
                        logger.critical("Failed to restart Ollama - entering recovery mode")
                        # Versuche später nochmal
                        time.sleep(60)
                        continue
                else:
                    # Alles ok - Reset backoff
                    if self.restart_attempts > 0:
                        self.restart_attempts = 0
                        logger.info("✅ Ollama recovered successfully")
                
                time.sleep(self.health_check_interval)
            
            except Exception as e:
                logger.exception(f"Monitor loop error: {e}")
                time.sleep(10)
    
    def start(self):
        """Starte Watchdog Service"""
        if self.running:
            logger.warning("Watchdog already running")
            return
        
        self.running = True
        self.monitor_thread = threading.Thread(
            target=self.monitor_loop,
            daemon=True,
            name="OllamaWatchdog"
        )
        self.monitor_thread.start()
        logger.info("✅ OllamaWatchdog service started")
    
    def stop(self):
        """Stoppe Watchdog Service"""
        logger.info("Stopping OllamaWatchdog...")
        self.running = False
        
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        
        logger.info("✅ OllamaWatchdog stopped")
    
    def get_status(self) -> Dict[str, Any]:
        """Get Watchdog Status"""
        return {
            "running": self.is_running(),
            "health": self.check_ollama_health(),
            "last_restart": self.last_restart.isoformat() if self.last_restart else None,
            "restart_attempts": self.restart_attempts,
            "max_restart_attempts": self.max_restart_attempts,
            "ollama_binary": self.ollama_binary,
            "process_id": self.process.pid if self.process else None,
        }


# Singleton
_watchdog_instance: Optional[OllamaWatchdog] = None


def get_ollama_watchdog() -> OllamaWatchdog:
    """Get or create OllamaWatchdog instance"""
    global _watchdog_instance
    if _watchdog_instance is None:
        _watchdog_instance = OllamaWatchdog()
    return _watchdog_instance
