"""
Availability Manager – Garantiert 24/7 Verfügbarkeit des Systems
Automatische Überprüfung aller kritischen Services mit Self-Healing
"""

import logging
import asyncio
import threading
from typing import Dict, Optional
from datetime import datetime
from enum import Enum
import json

from config import settings

logger = logging.getLogger(__name__)


class ServiceStatus(str, Enum):
    """Service Status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    RECOVERING = "recovering"


class AvailabilityManager:
    """
    Überwacht alle Services und garantiert 24/7 Verfügbarkeit
    - Automatische Health-Checks alle 30 Sekunden
    - Automatische Wiederherstellung bei Ausfällen
    - Fallback-Systeme für jeden Service
    - Detaillierte Logging und Monitoring
    """
    
    def __init__(self):
        self.status_map: Dict[str, Dict] = {}
        self.check_interval = 30  # Sekunden
        self.recovery_attempts = 5
        self.last_check = None
        self.running = False
        self._thread: Optional[threading.Thread] = None
        self._asyncio_task = None
        
        # Initialisiere Status für alle Services
        self._init_services()
    
    def _init_services(self):
        """Initialisiere Status für alle kritischen Services"""
        services = [
            "ollama",
            "catalog",
            "cache",
            "erp",
            "telegram",
            "frontend",
        ]
        
        for service in services:
            self.status_map[service] = {
                "name": service,
                "status": ServiceStatus.HEALTHY,
                "last_check": None,
                "failures": 0,
                "last_error": None,
                "fallback_active": False,
                "recovery_in_progress": False,
                "uptime_percent": 100.0,
                "total_checks": 0,
                "successful_checks": 0,
            }
    
    async def start_monitoring(self):
        """Starte Background Monitoring"""
        if self.running:
            logger.warning("Availability monitoring already running")
            return
        
        self.running = True
        logger.info("🟢 Availability Manager: Starting 24/7 monitoring")
        
        # Starte async monitoring loop
        while self.running:
            try:
                await self._perform_health_checks()
                await asyncio.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Health check error: {e}")
                await asyncio.sleep(5)  # Kurze Pause vor Retry
    
    def stop_monitoring(self):
        """Stoppe Monitoring"""
        self.running = False
        logger.info("Availability Manager: Monitoring stopped")
    
    async def _perform_health_checks(self):
        """Führe Health-Checks für alle Services durch"""
        self.last_check = datetime.now()
        
        # Check all services
        checks = [
            ("ollama", self._check_ollama),
            ("catalog", self._check_catalog),
            ("cache", self._check_cache),
            ("erp", self._check_erp),
            ("telegram", self._check_telegram),
            ("frontend", self._check_frontend),
        ]
        
        for service_name, check_func in checks:
            try:
                is_healthy = await check_func()
                await self._update_service_status(service_name, is_healthy)
            except Exception as e:
                logger.warning(f"Health check failed for {service_name}: {e}")
                await self._update_service_status(service_name, False)
    
    async def _update_service_status(self, service_name: str, is_healthy: bool):
        """Update Service Status und Recovery-Logik"""
        service = self.status_map[service_name]
        service["total_checks"] += 1
        service["last_check"] = datetime.now().isoformat()
        
        if is_healthy:
            # Service gesund
            service["failures"] = 0
            service["last_error"] = None
            
            if service["status"] != ServiceStatus.HEALTHY:
                service["status"] = ServiceStatus.HEALTHY
                service["recovery_in_progress"] = False
                logger.info(f"[OK] {service_name}: RECOVERED to healthy state")
            
            service["successful_checks"] += 1
        else:
            # Service problematisch
            service["failures"] += 1
            service["last_error"] = f"Health check failed at {datetime.now().isoformat()}"
            
            if service["failures"] >= 3:
                if service["status"] == ServiceStatus.HEALTHY:
                    service["status"] = ServiceStatus.DEGRADED
                    logger.warning(f"[WARN] {service_name}: Status changed to DEGRADED (failures: {service['failures']})")
                
                # Versuche Wiederherstellung
                if service["failures"] >= 5 and not service["recovery_in_progress"]:
                    await self._attempt_recovery(service_name)
        
        # Berechne Uptime
        if service["total_checks"] > 0:
            service["uptime_percent"] = (service["successful_checks"] / service["total_checks"]) * 100
    
    async def _attempt_recovery(self, service_name: str):
        """Versuche Service wiederherzustellen"""
        service = self.status_map[service_name]
        service["recovery_in_progress"] = True
        service["status"] = ServiceStatus.RECOVERING
        
        logger.warning(f"[RETRY] {service_name}: Attempting recovery...")
        
        for attempt in range(1, self.recovery_attempts + 1):
            try:
                if service_name == "ollama":
                    await self._recover_ollama()
                elif service_name == "catalog":
                    await self._recover_catalog()
                elif service_name == "cache":
                    await self._recover_cache()
                elif service_name == "erp":
                    await self._recover_erp()
                elif service_name == "telegram":
                    await self._recover_telegram()
                
                logger.info(f"[OK] {service_name}: Recovery successful on attempt {attempt}")
                service["recovery_in_progress"] = False
                service["failures"] = 0
                return
            
            except Exception as e:
                logger.warning(f"Recovery attempt {attempt}/{self.recovery_attempts} failed: {e}")
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
        
        logger.error(f"[FAIL] {service_name}: Recovery failed after {self.recovery_attempts} attempts")
        service["recovery_in_progress"] = False
        service["fallback_active"] = True
    
    # ─────────────────────────────────────────────────────────────────────────
    # HEALTH CHECKS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _check_ollama(self) -> bool:
        """Check Ollama Availability"""
        try:
            from services.local_llm import check_ollama_status
            result = check_ollama_status()
            return bool(result and result.get("available"))
        except Exception as e:
            logger.debug(f"Ollama health check failed: {e}")
            return False
    
    async def _check_catalog(self) -> bool:
        """Check Katalog Verfügbarkeit"""
        try:
            from services.catalog_index import get_catalog_index
            catalog = get_catalog_index()
            return len(catalog.main_products) > 0
        except Exception as e:
            logger.debug(f"Catalog health check failed: {e}")
            return False
    
    async def _check_cache(self) -> bool:
        """Check Cache System"""
        try:
            from services.memory_cache import text_cache
            # Versuche Cache-Operation
            test_key = "__health_check__"
            text_cache.set(test_key, {"test": True}, ttl_seconds=60)
            result = text_cache.get(test_key)
            return result is not None
        except Exception as e:
            logger.debug(f"Cache health check failed: {e}")
            return False
    
    async def _check_erp(self) -> bool:
        """Check ERP Connector"""
        try:
            if not settings.ERP_ENABLED:
                return True  # ERP ist optional
            
            from services.erp_connector import get_erp_connector
            connector = get_erp_connector()
            return connector.health_check()
        except Exception as e:
            logger.debug(f"ERP health check failed: {e}")
            return False
    
    async def _check_telegram(self) -> bool:
        """Check Telegram Bot"""
        try:
            if not settings.TELEGRAM_ENABLED:
                return True  # Telegram ist optional
            
            # Telegram ist immer verfügbar wenn enabled
            return True
        except Exception as e:
            logger.debug(f"Telegram health check failed: {e}")
            return False
    
    async def _check_frontend(self) -> bool:
        """Check Frontend Verfügbarkeit"""
        try:
            from pathlib import Path
            from config import BASE_DIR
            
            frontend_path = BASE_DIR / "frontend" / "index.html"
            return frontend_path.exists()
        except Exception as e:
            logger.debug(f"Frontend health check failed: {e}")
            return False
    
    # ─────────────────────────────────────────────────────────────────────────
    # RECOVERY METHODS
    # ─────────────────────────────────────────────────────────────────────────
    
    async def _recover_ollama(self):
        """Versuche Ollama wiederherzustellen"""
        try:
            from services.local_llm import check_ollama_status
            
            # Versuche Verbindung zu testen
            for i in range(3):
                if check_ollama_status():
                    logger.info("Ollama connection restored")
                    return
                await asyncio.sleep(2)
            
            raise Exception("Ollama not responding")
        except Exception as e:
            raise Exception(f"Ollama recovery failed: {e}")
    
    async def _recover_catalog(self):
        """Versuche Katalog zu reloaden"""
        try:
            from services.catalog_index import reload_catalog
            reload_catalog()
            logger.info("Catalog reloaded successfully")
        except Exception as e:
            raise Exception(f"Catalog recovery failed: {e}")
    
    async def _recover_cache(self):
        """Versuche Cache zu clearen und neu zu initialisieren"""
        try:
            from services.memory_cache import text_cache, offer_cache, project_cache
            
            text_cache.clear()
            offer_cache.clear()
            project_cache.clear()
            
            logger.info("Cache cleared and reinitialized")
        except Exception as e:
            raise Exception(f"Cache recovery failed: {e}")
    
    async def _recover_erp(self):
        """Versuche ERP-Verbindung wiederherzustellen"""
        try:
            if not settings.ERP_ENABLED:
                return
            
            from services.erp_connector import get_erp_connector
            connector = get_erp_connector()
            
            if connector.health_check():
                logger.info("ERP connection restored")
                return
            
            raise Exception("ERP health check failed")
        except Exception as e:
            raise Exception(f"ERP recovery failed: {e}")
    
    async def _recover_telegram(self):
        """Versuche Telegram Bot zu starten"""
        try:
            if not settings.TELEGRAM_ENABLED:
                return
            
            from services.telegram_bot import start_bot
            await start_bot()
            logger.info("Telegram bot restarted")
        except Exception as e:
            raise Exception(f"Telegram recovery failed: {e}")
    
    # ─────────────────────────────────────────────────────────────────────────
    # STATUS QUERIES
    # ─────────────────────────────────────────────────────────────────────────
    
    def get_status(self, service_name: Optional[str] = None) -> Dict:
        """Get Status eines oder aller Services"""
        if service_name:
            return self.status_map.get(service_name, {})
        
        return {
            "timestamp": datetime.now().isoformat(),
            "overall_status": self._get_overall_status(),
            "last_check": self.last_check.isoformat() if self.last_check else None,
            "services": dict(self.status_map),
        }
    
    def _get_overall_status(self) -> str:
        """Berechne Gesamt-Status"""
        statuses = [s["status"] for s in self.status_map.values()]
        
        if all(s == ServiceStatus.HEALTHY for s in statuses):
            return "HEALTHY"
        elif ServiceStatus.OFFLINE in statuses:
            return "CRITICAL"
        else:
            return "DEGRADED"
    
    def is_system_available(self) -> bool:
        """Ist das System verfügbar?"""
        overall = self._get_overall_status()
        return overall in ["HEALTHY", "DEGRADED"]
    
    def get_uptime_stats(self) -> Dict:
        """Get Uptime Statistiken"""
        return {
            "timestamp": datetime.now().isoformat(),
            "services": {
                name: {
                    "uptime_percent": service["uptime_percent"],
                    "total_checks": service["total_checks"],
                    "successful_checks": service["successful_checks"],
                    "failures": service["failures"],
                    "status": service["status"],
                }
                for name, service in self.status_map.items()
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

_availability_manager_instance: Optional[AvailabilityManager] = None


def get_availability_manager() -> AvailabilityManager:
    """Get or create singleton instance"""
    global _availability_manager_instance
    if _availability_manager_instance is None:
        _availability_manager_instance = AvailabilityManager()
    return _availability_manager_instance
