"""
Price Calculator – Berechnet Preise für Angebote mit ERP-Integration
Unterstützt ERP-Preise mit Fallback auf Schätzpreise
"""

import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

from config import settings
from services.erp_connector import get_erp_connector

logger = logging.getLogger(__name__)


class PriceCalculator:
    """Manages pricing calculations with ERP integration"""
    
    def __init__(self):
        self.erp = get_erp_connector()
        self.vat_rate = settings.VAT_RATE
    
    def calculate_position_price(
        self,
        matched_product: Dict,
        quantity: int = 1,
        discount_percent: float = 0
    ) -> Dict:
        """
        Berechnet Preis für eine Position
        
        Returns:
            {
                "product_id": "...",
                "quantity": 1,
                "unit_price_net": 1250.00,
                "total_net": 1250.00,
                "vat_amount": 101.25,
                "total_gross": 1351.25,
                "discount_percent": 0,
                "discount_amount": 0,
                "currency": "CHF",
                "source": "erp" | "estimate",
                "notes": []
            }
        """
        product_id = matched_product.get("artikel_nr") or matched_product.get("id", "")
        notes = []
        
        if not product_id:
            logger.warning(f"No product ID for price calculation")
            return self._fallback_price(quantity, discount_percent, notes)
        
        # Hole ERP-Preis
        price_info = self.erp.get_price(product_id, quantity)
        
        if not price_info:
            logger.warning(f"No price info for {product_id}, using fallback")
            return self._fallback_price(quantity, discount_percent, notes)
        
        unit_price_net = price_info.get("unit_price_net", 1250.00)
        source = price_info.get("source", "unknown")
        
        if source == "estimate":
            notes.append("Geschätzter Preis (ERP nicht verfügbar)")
        
        # Berechne Gesamtpreis
        total_net = unit_price_net * quantity
        
        # Anwende Rabatt
        if discount_percent > 0:
            discount_amount = total_net * (discount_percent / 100)
            total_net_after_discount = total_net - discount_amount
        else:
            discount_amount = 0
            total_net_after_discount = total_net
        
        # Berechne MwSt
        vat_amount = total_net_after_discount * self.vat_rate
        total_gross = total_net_after_discount + vat_amount
        
        return {
            "product_id": product_id,
            "quantity": quantity,
            "unit_price_net": round(unit_price_net, 2),
            "total_net": round(total_net, 2),
            "discount_percent": discount_percent,
            "discount_amount": round(discount_amount, 2),
            "total_net_after_discount": round(total_net_after_discount, 2),
            "vat_rate": round(self.vat_rate * 100, 1),
            "vat_amount": round(vat_amount, 2),
            "total_gross": round(total_gross, 2),
            "currency": price_info.get("currency", "CHF"),
            "source": source,
            "delivery_days": price_info.get("delivery_days", 21),
            "notes": notes
        }
    
    def calculate_offer_totals(self, positions: List[Dict]) -> Dict:
        """
        Berechnet Gesamtsummen für alle Positionen
        
        Returns:
            {
                "positions_count": 10,
                "total_net": 12500.00,
                "total_discount": 1250.00,
                "total_net_after_discount": 11250.00,
                "total_vat": 911.25,
                "total_gross": 12161.25,
                "currency": "CHF",
                "average_delivery_days": 21,
                "sources": {"erp": 8, "estimate": 2}
            }
        """
        if not positions:
            return self._empty_totals()
        
        total_net = 0
        total_discount = 0
        total_vat = 0
        sources = {}
        delivery_days_list = []
        
        for pos in positions:
            price_calc = pos.get("price_calculation", {})
            
            total_net += price_calc.get("total_net", 0)
            total_discount += price_calc.get("discount_amount", 0)
            total_vat += price_calc.get("vat_amount", 0)
            
            source = price_calc.get("source", "unknown")
            sources[source] = sources.get(source, 0) + 1
            
            delivery_days = price_calc.get("delivery_days", 21)
            if delivery_days:
                delivery_days_list.append(delivery_days)
        
        total_net_after_discount = total_net - total_discount
        total_gross = total_net_after_discount + total_vat
        
        avg_delivery_days = (
            max(delivery_days_list) if delivery_days_list else 21
        )  # Nimm das Maximum als worst-case
        
        return {
            "positions_count": len(positions),
            "total_net": round(total_net, 2),
            "total_discount": round(total_discount, 2),
            "total_net_after_discount": round(total_net_after_discount, 2),
            "total_vat": round(total_vat, 2),
            "total_gross": round(total_gross, 2),
            "currency": "CHF",
            "average_delivery_days": avg_delivery_days,
            "sources": sources
        }
    
    def _fallback_price(
        self,
        quantity: int = 1,
        discount_percent: float = 0,
        notes: List[str] = None
    ) -> Dict:
        """Returns estimated price when ERP is not available"""
        if notes is None:
            notes = []
        
        unit_price_net = 1250.00
        total_net = unit_price_net * quantity
        discount_amount = total_net * (discount_percent / 100) if discount_percent > 0 else 0
        total_net_after_discount = total_net - discount_amount
        vat_amount = total_net_after_discount * self.vat_rate
        total_gross = total_net_after_discount + vat_amount
        
        notes.append("Geschätzter Preis (ERP nicht verfügbar)")
        
        return {
            "product_id": "UNKNOWN",
            "quantity": quantity,
            "unit_price_net": round(unit_price_net, 2),
            "total_net": round(total_net, 2),
            "discount_percent": discount_percent,
            "discount_amount": round(discount_amount, 2),
            "total_net_after_discount": round(total_net_after_discount, 2),
            "vat_rate": round(self.vat_rate * 100, 1),
            "vat_amount": round(vat_amount, 2),
            "total_gross": round(total_gross, 2),
            "currency": "CHF",
            "source": "estimate",
            "delivery_days": 21,
            "notes": notes
        }
    
    def _empty_totals(self) -> Dict:
        """Returns empty totals structure"""
        return {
            "positions_count": 0,
            "total_net": 0.00,
            "total_discount": 0.00,
            "total_net_after_discount": 0.00,
            "total_vat": 0.00,
            "total_gross": 0.00,
            "currency": "CHF",
            "average_delivery_days": 0,
            "sources": {}
        }


# ─────────────────────────────────────────────────────────────────────────────
# SINGLETON INSTANCE
# ─────────────────────────────────────────────────────────────────────────────

_price_calculator_instance = None


def get_price_calculator() -> PriceCalculator:
    """Get or create singleton PriceCalculator instance"""
    global _price_calculator_instance
    if _price_calculator_instance is None:
        _price_calculator_instance = PriceCalculator()
    return _price_calculator_instance
