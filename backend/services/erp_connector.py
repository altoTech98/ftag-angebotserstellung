"""
ERP Connector – Bohr ERP System Integration für Preisabzüge & Verfügbarkeit
Handles Preise, Verfügbarkeit und Lieferzeitabfragen mit Caching und Fallback
"""

import logging
import json
from typing import Optional, Dict, List, Tuple
from datetime import datetime
import requests
from requests.auth import HTTPBasicAuth

from config import settings
from services.memory_cache import get_memory_cache
from services.exceptions import FrankTuerenError

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# Cache-Instanz
# ─────────────────────────────────────────────────────────────────────────────

erp_cache = get_memory_cache()


# ─────────────────────────────────────────────────────────────────────────────
# ERP CONNECTOR
# ─────────────────────────────────────────────────────────────────────────────

class ERPConnector:
    """Manages all ERP (Bohr) integration"""
    
    def __init__(self):
        self.enabled = settings.ERP_ENABLED
        self.base_url = settings.ERP_BOHR_URL
        self.api_key = settings.ERP_BOHR_API_KEY
        self.username = settings.ERP_BOHR_USERNAME
        self.password = settings.ERP_BOHR_PASSWORD
        self.timeout = settings.ERP_REQUEST_TIMEOUT
        self.use_cache = settings.ERP_USE_CACHE
        self.fallback_enabled = settings.ERP_FALLBACK_TO_ESTIMATE
        self._session = None
        
        if self.enabled:
            logger.info(f"ERP Connector initialized: {self.base_url}")
    
    def _init_session(self):
        """Lazy-load HTTP session with auth"""
        if self._session is None:
            self._session = requests.Session()
            
            # Configure authentication
            if self.api_key:
                self._session.headers.update({"Authorization": f"Bearer {self.api_key}"})
            elif self.username and self.password:
                self._session.auth = HTTPBasicAuth(self.username, self.password)
        
        return self._session
    
    def get_price(self, product_id: str, quantity: int = 1) -> Optional[Dict]:
        """
        Holt Preis für Produkt von ERP
        
        Returns:
            {
                "product_id": "...",
                "quantity": 1,
                "unit_price_net": 1250.00,
                "unit_price_gross": 1500.00,
                "currency": "CHF",
                "discount_percent": 0,
                "available": True,
                "stock": 5,
                "delivery_days": 14,
                "source": "erp" | "estimate" | "cache",
                "cached_at": "2025-01-15T10:30:00Z",
                "expires_at": "2025-01-15T11:30:00Z",
            }
        """
        if not self.enabled:
            return self._fallback_price(product_id, quantity)
        
        # Check cache first
        cache_key = f"erp_price_{product_id}_{quantity}"
        if self.use_cache:
            cached = erp_cache.get(cache_key)
            if cached:
                logger.debug(f"ERP price cache hit: {product_id}")
                return cached
        
        try:
            result = self._query_bohr_price(product_id, quantity)
            
            # Cache result
            if self.use_cache and result:
                erp_cache.store(cache_key, result, ttl_seconds=settings.ERP_PRICE_CACHE_TTL_SECONDS)
            
            return result
        
        except Exception as e:
            logger.warning(f"ERP price query failed for {product_id}: {str(e)}")
            
            if self.fallback_enabled:
                return self._fallback_price(product_id, quantity)
            else:
                raise FrankTuerenError(f"ERP price lookup failed: {str(e)}")
    
    def get_availability(self, product_id: str) -> Optional[Dict]:
        """
        Holt Verfügbarkeit & Lieferzeit von ERP
        
        Returns:
            {
                "product_id": "...",
                "available": True,
                "stock_quantity": 5,
                "warehouse_location": "A-15-3",
                "delivery_days": 14,
                "next_stock": None,
                "source": "erp" | "estimate",
                "cached_at": "2025-01-15T10:30:00Z",
            }
        """
        if not self.enabled:
            return self._fallback_availability(product_id)
        
        cache_key = f"erp_availability_{product_id}"
        if self.use_cache:
            cached = erp_cache.get(cache_key)
            if cached:
                logger.debug(f"ERP availability cache hit: {product_id}")
                return cached
        
        try:
            result = self._query_bohr_availability(product_id)
            
            if self.use_cache and result:
                erp_cache.store(cache_key, result, ttl_seconds=settings.ERP_PRICE_CACHE_TTL_SECONDS)
            
            return result
        
        except Exception as e:
            logger.warning(f"ERP availability query failed for {product_id}: {str(e)}")
            
            if self.fallback_enabled:
                return self._fallback_availability(product_id)
            else:
                raise FrankTuerenError(f"ERP availability lookup failed: {str(e)}")
    
    def get_bulk_prices(self, product_ids: List[str]) -> Dict[str, Dict]:
        """
        Holt Preise für mehrere Produkte gleichzeitig
        
        Returns:
            {
                "product_id_1": {...price dict...},
                "product_id_2": {...price dict...},
            }
        """
        results = {}
        
        for product_id in product_ids:
            price = self.get_price(product_id)
            if price:
                results[product_id] = price
        
        return results
    
    def update_prices_in_matched_positions(self, matched_positions: List[Dict]) -> List[Dict]:
        """
        Ergänzt matched_positions mit aktuellen ERP-Preisen
        
        Modifiziert matched_positions in-place und gibt aktualisierte Liste zurück
        """
        if not self.enabled:
            logger.info("ERP disabled, skipping price update")
            return matched_positions
        
        updated = []
        
        for position in matched_positions:
            # Position hat Format: {..., "matched_product": {...product_data...}}
            matched_product = position.get("matched_product", {})
            product_id = matched_product.get("artikel_nr") or matched_product.get("id")
            
            if not product_id:
                # Kein ERP-Preis möglich
                position["erp_info"] = {
                    "available": False,
                    "reason": "No product ID found"
                }
                updated.append(position)
                continue
            
            # Versuche ERP-Daten zu laden
            price_info = self.get_price(product_id, quantity=1)
            availability_info = self.get_availability(product_id)
            
            if price_info or availability_info:
                position["erp_info"] = {
                    "price": price_info,
                    "availability": availability_info,
                    "last_updated": datetime.utcnow().isoformat(),
                }
            else:
                position["erp_info"] = {
                    "available": False,
                    "reason": "ERP lookup failed, using estimate"
                }
            
            updated.append(position)
        
        return updated
    
    # ─────────────────────────────────────────────────────────────────────────
    # BOHR ERP API QUERIES
    # ─────────────────────────────────────────────────────────────────────────
    
    def _query_bohr_price(self, product_id: str, quantity: int = 1) -> Optional[Dict]:
        """
        Queries Bohr ERP for price
        
        ACHTUNG: Diese Methode muss an echte Bohr-API angepasst werden!
        Beispiel-Implementierung basiert auf typischen REST-APIs
        """
        try:
            session = self._init_session()
            
            # Endpoint: /api/v1/products/{product_id}/pricing?quantity={quantity}
            url = f"{self.base_url}/api/v1/products/{product_id}/pricing"
            params = {"quantity": quantity}
            
            response = session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            # Standardisiere Response
            return {
                "product_id": product_id,
                "quantity": quantity,
                "unit_price_net": float(data.get("netto", 0)),
                "unit_price_gross": float(data.get("brutto", 0)),
                "currency": data.get("currency", "CHF"),
                "discount_percent": float(data.get("rabatt", 0)),
                "available": True,
                "stock": int(data.get("bestand", 0)),
                "delivery_days": int(data.get("lieferzeit_tage", 14)),
                "source": "erp",
                "cached_at": datetime.utcnow().isoformat(),
                "expires_at": None,  # TTL wird vom cache gesetzt
            }
        
        except requests.RequestException as e:
            logger.error(f"Bohr API request failed: {str(e)}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse Bohr response: {str(e)}")
            raise
    
    def _query_bohr_availability(self, product_id: str) -> Optional[Dict]:
        """Queries Bohr ERP for stock/availability"""
        try:
            session = self._init_session()
            
            url = f"{self.base_url}/api/v1/products/{product_id}/availability"
            
            response = session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            data = response.json()
            
            return {
                "product_id": product_id,
                "available": data.get("verfuegbar", False),
                "stock_quantity": int(data.get("menge", 0)),
                "warehouse_location": data.get("lagerort", ""),
                "delivery_days": int(data.get("lieferzeit_tage", 14)),
                "next_stock": data.get("naechste_lieferung"),
                "source": "erp",
                "cached_at": datetime.utcnow().isoformat(),
            }
        
        except requests.RequestException as e:
            logger.error(f"Bohr availability request failed: {str(e)}")
            raise
        except (KeyError, ValueError) as e:
            logger.error(f"Failed to parse Bohr availability response: {str(e)}")
            raise
    
    # ─────────────────────────────────────────────────────────────────────────
    # FALLBACK (Schätzpreise wenn ERP nicht verfügbar)
    # ─────────────────────────────────────────────────────────────────────────
    
    def _fallback_price(self, product_id: str, quantity: int = 1) -> Dict:
        """Returns estimated price when ERP is unavailable"""
        # FALLBACK: Dummy-Preise für Entwicklung
        # In Produktion: aus statischen Katalog oder Default-Liste laden
        
        logger.debug(f"Using fallback price for {product_id}")
        
        return {
            "product_id": product_id,
            "quantity": quantity,
            "unit_price_net": 1250.00,  # Dummy CHF
            "unit_price_gross": 1500.00,
            "currency": "CHF",
            "discount_percent": 0,
            "available": True,
            "stock": 999,  # Unbegrenzt angenommen
            "delivery_days": 21,  # Standard 3 Wochen
            "source": "estimate",
            "cached_at": datetime.utcnow().isoformat(),
            "expires_at": None,
            "note": "ERP price not available, using estimate"
        }
    
    def _fallback_availability(self, product_id: str) -> Dict:
        """Returns estimated availability when ERP is unavailable"""
        logger.debug(f"Using fallback availability for {product_id}")
        
        return {
            "product_id": product_id,
            "available": True,
            "stock_quantity": 999,  # Annahme: verfügbar
            "warehouse_location": "Lager",
            "delivery_days": 21,
            "next_stock": None,
            "source": "estimate",
            "cached_at": datetime.utcnow().isoformat(),
            "note": "ERP availability not available, assuming in stock"
        }
    
    def health_check(self) -> bool:
        """Prüft Verbindung zu Bohr ERP"""
        if not self.enabled:
            logger.info("ERP health check: disabled")
            return False
        
        try:
            session = self._init_session()
            url = f"{self.base_url}/api/v1/health"
            response = session.get(url, timeout=self.timeout)
            
            is_healthy = response.status_code == 200
            logger.info(f"ERP health check: {'OK' if is_healthy else 'FAILED'}")
            return is_healthy
        
        except Exception as e:
            logger.error(f"ERP health check failed: {str(e)}")
            return False


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

_erp_connector_instance = None


def get_erp_connector() -> ERPConnector:
    """Get or create singleton ERPConnector instance"""
    global _erp_connector_instance
    if _erp_connector_instance is None:
        _erp_connector_instance = ERPConnector()
    return _erp_connector_instance
