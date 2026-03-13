"""
ReturnShield AI — Pre-Flight Diagnostics API

Provides endpoints for system health monitoring and webhook simulation.
"""

import logging
import time
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.config import settings
from app.workers.celery_app import celery_app

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/diagnostics", tags=["diagnostics"])


@router.get("/health")
async def get_system_health(db: AsyncSession = Depends(get_db_session)) -> Dict[str, Any]:
    """Check health of Database, Redis, and Celery."""
    health = {
        "database": "disconnected",
        "redis": "disconnected",
        "celery": "unknown",
        "timestamp": time.time()
    }

    # 1. Check Database
    try:
        await db.execute(text("SELECT 1"))
        health["database"] = "connected"
    except Exception as e:
        logger.error(f"Diagnostics: DB Health Check failed: {e}")

    # 2. Check Redis (via Celery broker)
    try:
        # Simple check if we can connect to the broker
        with celery_app.connection() as conn:
            conn.ensure_connection(max_retries=1)
            health["redis"] = "connected"
    except Exception as e:
        logger.error(f"Diagnostics: Redis Health Check failed: {e}")

    # 3. Check Celery Workers
    try:
        inspect = celery_app.control.inspect()
        active = inspect.active()
        if active:
            health["celery"] = f"active ({len(active)} workers)"
        else:
            health["celery"] = "no active workers"
    except Exception as e:
        logger.warning(f"Diagnostics: Celery Health Check failed: {e}")

    return health


@router.post("/simulate-webhook")
async def simulate_webhook(topic: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Simulate a Shopify webhook for testing purposes.
    Bypasses HMAC verification.
    """
    logger.info(f"Simulating webhook: {topic}")
    
    from app.api.v1.webhooks import handle_order_created, handle_refund_created
    
    # This is a bit of a hack to reuse the existing logic without actual HTTP request
    # In a real app, you might want to refactor the business logic out of the route
    
    if topic == "orders/create":
        # We simulate the call to the handler
        # For simplicity in testing, we just queue the task directly if it's a mock
        from app.workers.tasks import predict_order_return_risk
        
        order_id = payload.get("id", 12345)
        merchant_id = "test-merchant" # Use a default or lookup first active
        
        predict_order_return_risk.delay(merchant_id, order_id, payload)
        
        return {"status": "simulated", "topic": topic, "order_id": order_id}
    
    raise HTTPException(status_code=400, detail=f"Simulation for topic {topic} not implemented")
