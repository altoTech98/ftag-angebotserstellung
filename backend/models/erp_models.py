"""
Pydantic Models für ERP-Integration
Type-safe Datenvalidierung und Dokumentation
"""

from typing import Optional, List
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class AvailabilityStatusModel(str, Enum):
    """Verfügbarkeitsstatus"""
    AVAILABLE = "available"
    LIMITED = "limited"
    UNAVAILABLE = "unavailable"
    ON_ORDER = "on_order"
    DISCONTINUED = "discontinued"
    UNKNOWN = "unknown"


class DeliveryTypeModel(str, Enum):
    """Lieferart"""
    STOCK = "stock"
    MADE_TO_ORDER = "made_to_order"
    SPECIAL_ORDER = "special_order"


# ─────────────────────────────────────────────────────────────────────────────
# REQUEST MODELS
# ─────────────────────────────────────────────────────────────────────────────

class PriceRequestModel(BaseModel):
    """Request: Hole Preis für Produkt"""
    product_id: str = Field(..., description="Bohr-Produkt-ID")
    quantity: int = Field(1, ge=1, description="Bestellmenge")
    customer_id: Optional[str] = Field(None, description="Optional Kunden-ID für Rabatte")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "DOOR-001",
                "quantity": 5,
                "customer_id": "CUST-12345"
            }
        }


class BatchPriceRequestModel(BaseModel):
    """Request: Hole Preise für mehrere Produkte"""
    product_ids: List[str] = Field(..., description="Liste von Produkt-IDs", min_items=1, max_items=100)
    quantity: int = Field(1, ge=1, description="Bestellmenge")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_ids": ["DOOR-001", "DOOR-002", "DOOR-003"],
                "quantity": 5
            }
        }


class AvailabilityRequestModel(BaseModel):
    """Request: Check Verfügbarkeit"""
    product_id: str = Field(..., description="Bohr-Produkt-ID")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "DOOR-001"
            }
        }


class ProductSearchRequestModel(BaseModel):
    """Request: Suche Produkte"""
    query: str = Field(..., description="Suchbegriff", min_length=1, max_length=100)
    limit: int = Field(10, ge=1, le=100, description="Max. Ergebnisse")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Stahlrahmentür",
                "limit": 10
            }
        }


# ─────────────────────────────────────────────────────────────────────────────
# RESPONSE MODELS
# ─────────────────────────────────────────────────────────────────────────────

class PriceInfoResponseModel(BaseModel):
    """Response: Preisangabe"""
    product_id: str
    description: str
    unit_price: float = Field(..., description="Einzelpreis CHF (exkl. MwSt.)")
    quantity: int = Field(1, description="Bestellmenge")
    discount_percent: float = Field(0.0, ge=0, le=100, description="Rabatt in %")
    net_total: float = Field(..., description="Nettobetrag CHF")
    gross_total: float = Field(..., description="Bruttobetrag CHF")
    vat_percent: float = Field(7.7, description="MwSt.-Satz in %")
    margin_percent: Optional[float] = Field(None, description="Gewinnmarge in %")
    currency: str = "CHF"
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "DOOR-001",
                "description": "Stahlrahmentür T30",
                "unit_price": 1250.00,
                "quantity": 5,
                "discount_percent": 10.0,
                "net_total": 5625.00,
                "gross_total": 6061.13,
                "vat_percent": 7.7,
                "margin_percent": 25.0,
                "currency": "CHF"
            }
        }


class AvailabilityInfoResponseModel(BaseModel):
    """Response: Verfügbarkeitsinformation"""
    product_id: str
    status: AvailabilityStatusModel
    quantity_available: int = Field(0, ge=0, description="Verfügbare Menge auf Lager")
    delivery_type: DeliveryTypeModel
    delivery_days: int = Field(21, ge=1, description="Lieferzeit in Tagen")
    special_notes: str = Field("", description="Spezielle Notizen/Hinweise")
    last_updated: datetime = Field(default_factory=datetime.now, description="Letzte Aktualisierung")
    
    class Config:
        json_schema_extra = {
            "example": {
                "product_id": "DOOR-001",
                "status": "available",
                "quantity_available": 12,
                "delivery_type": "stock",
                "delivery_days": 2,
                "special_notes": "Standardlagerware",
                "last_updated": "2025-01-15T10:30:00Z"
            }
        }


class PriceAndAvailabilityResponseModel(BaseModel):
    """Response: Kombination Preis + Verfügbarkeit"""
    price: Optional[PriceInfoResponseModel] = None
    availability: Optional[AvailabilityInfoResponseModel] = None
    status: str = "success"  # "success", "not_found", "error"
    error_message: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "price": {
                    "product_id": "DOOR-001",
                    "description": "Stahlrahmentür T30",
                    "unit_price": 1250.00,
                    "quantity": 5,
                    "discount_percent": 10.0,
                    "net_total": 5625.00,
                    "gross_total": 6061.13,
                    "vat_percent": 7.7,
                    "margin_percent": 25.0,
                    "currency": "CHF"
                },
                "availability": {
                    "product_id": "DOOR-001",
                    "status": "available",
                    "quantity_available": 12,
                    "delivery_type": "stock",
                    "delivery_days": 2,
                    "special_notes": "Standardlagerware",
                    "last_updated": "2025-01-15T10:30:00Z"
                },
                "status": "success",
                "error_message": None
            }
        }


class ProductSearchResponseModel(BaseModel):
    """Response: Produktsuche"""
    query: str
    total_results: int
    results: List[dict] = Field(default_factory=list, description="Gefundene Produkte")
    status: str = "success"
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "Stahlrahmentür",
                "total_results": 3,
                "results": [
                    {
                        "product_id": "DOOR-001",
                        "description": "Stahlrahmentür T30",
                        "unit_price": 1250.00
                    }
                ],
                "status": "success"
            }
        }


class ERPHealthResponseModel(BaseModel):
    """Response: ERP Gesundheitsstatus"""
    connected: bool
    base_url: str
    last_error: Optional[str] = None
    cache_size: int = Field(0, description="Anzahl gecachter Produkte")
    timestamp: datetime = Field(default_factory=datetime.now)
    
    class Config:
        json_schema_extra = {
            "example": {
                "connected": True,
                "base_url": "https://bohr.example.com",
                "last_error": None,
                "cache_size": 1234,
                "timestamp": "2025-01-15T10:30:00Z"
            }
        }


class BatchPriceResponseModel(BaseModel):
    """Response: Batch-Preisabfrage"""
    total_requested: int
    total_found: int
    prices: dict = Field(default_factory=dict, description="product_id -> PriceInfo")
    status: str = "success"
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_requested": 3,
                "total_found": 2,
                "prices": {
                    "DOOR-001": {
                        "product_id": "DOOR-001",
                        "description": "Stahlrahmentür T30",
                        "unit_price": 1250.00,
                        "quantity": 5,
                        "discount_percent": 10.0,
                        "net_total": 5625.00,
                        "gross_total": 6061.13,
                        "vat_percent": 7.7,
                        "margin_percent": 25.0,
                        "currency": "CHF"
                    }
                },
                "status": "success"
            }
        }
