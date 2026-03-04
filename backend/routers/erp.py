"""
ERP Router – ERP Integration Endpoints
GET  /api/erp/health             – Health check
GET  /api/erp/price/{product_id} – Get price
GET  /api/erp/availability/{product_id} – Get availability
POST /api/erp/prices             – Bulk price query
"""

import logging
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from services.erp_connector import get_erp_connector

logger = logging.getLogger(__name__)

router = APIRouter()
erp = get_erp_connector()


# ─────────────────────────────────────────────────────────────────────────────
# MODELS
# ─────────────────────────────────────────────────────────────────────────────

class BulkPriceRequest(BaseModel):
    product_ids: list[str]


# ─────────────────────────────────────────────────────────────────────────────
# ENDPOINTS
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/erp/health")
async def erp_health_check():
    """Check ERP system health"""
    is_healthy = erp.health_check()
    return {
        "status": "ok" if is_healthy else "unavailable",
        "enabled": erp.enabled,
        "connected": is_healthy
    }


@router.get("/erp/price/{product_id}")
async def get_erp_price(
    product_id: str,
    quantity: int = Query(1, ge=1)
):
    """Get price for a single product"""
    try:
        price_info = erp.get_price(product_id, quantity)
        
        if not price_info:
            raise HTTPException(
                status_code=404,
                detail=f"Price not found for product {product_id}"
            )
        
        return price_info
    
    except Exception as e:
        logger.error(f"Error fetching price for {product_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch price: {str(e)}"
        )


@router.get("/erp/availability/{product_id}")
async def get_erp_availability(product_id: str):
    """Get availability/stock info for a product"""
    try:
        availability_info = erp.get_availability(product_id)
        
        if not availability_info:
            raise HTTPException(
                status_code=404,
                detail=f"Availability not found for product {product_id}"
            )
        
        return availability_info
    
    except Exception as e:
        logger.error(f"Error fetching availability for {product_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch availability: {str(e)}"
        )


@router.post("/erp/prices")
async def get_erp_prices_bulk(request: BulkPriceRequest):
    """Get prices for multiple products in one request"""
    try:
        prices = erp.get_bulk_prices(request.product_ids)
        
        return {
            "count": len(prices),
            "prices": prices
        }
    
    except Exception as e:
        logger.error(f"Error fetching bulk prices: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch prices: {str(e)}"
        )
