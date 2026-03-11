"""
ReturnShield AI — Shopify Webhook Handlers

Receives and processes webhooks from Shopify for:
  - orders/create: Trigger return risk prediction
  - orders/fulfilled: Schedule follow-up communications
  - refunds/create: Track actual refund outcomes
  - app/uninstalled: Clean up merchant data
  - customers/redact: Mandatory GDPR webhook
  - customers/data_request: Mandatory GDPR webhook
  - shop/redact: Mandatory GDPR webhook
"""

import hashlib
import hmac
import logging

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select, update

from app.config import settings
from app.database import async_session_factory
from app.models.merchant import Merchant
from app.models.prediction import Prediction
from app.workers.tasks import predict_order_return_risk

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


async def _verify_webhook(request: Request) -> tuple[dict, str]:
    """
    Verify the HMAC signature of a Shopify webhook.

    Returns:
        Tuple of (JSON body, shop domain)
    """
    hmac_header = request.headers.get("X-Shopify-Hmac-Sha256", "")
    shop_domain = request.headers.get("X-Shopify-Shop-Domain", "")

    body = await request.body()

    computed_hmac = hmac.new(
        settings.SHOPIFY_API_SECRET.encode("utf-8"),
        body,
        hashlib.sha256,
    ).hexdigest()

    # Shopify sends base64-encoded HMAC, but we can also compare hex
    import base64

    computed_b64 = base64.b64encode(
        hmac.new(
            settings.SHOPIFY_API_SECRET.encode("utf-8"),
            body,
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    if not hmac.compare_digest(computed_b64, hmac_header):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook HMAC",
        )

    import json

    data = json.loads(body)
    return data, shop_domain


@router.post("/orders-create")
async def handle_order_created(request: Request) -> dict:
    """
    Handle orders/create webhook.

    Triggers the return risk prediction for the new order.
    """
    data, shop_domain = await _verify_webhook(request)

    order_id = data.get("id")
    logger.info(f"New order {order_id} from {shop_domain}")

    # Look up merchant
    async with async_session_factory() as session:
        result = await session.execute(
            select(Merchant).where(Merchant.shopify_shop_domain == shop_domain)
        )
        merchant = result.scalar_one_or_none()

        if merchant is None:
            logger.warning(f"Webhook from unknown shop: {shop_domain}")
            return {"status": "ignored", "reason": "unknown shop"}

        # Queue ML prediction task via Celery with the actual order payload
        predict_order_return_risk.delay(str(merchant.id), order_id, data)

    logger.info(f"Prediction task queued for order {order_id}")
    return {"status": "ok", "order_id": order_id}


@router.post("/orders-fulfilled")
async def handle_order_fulfilled(request: Request) -> dict:
    """
    Handle orders/fulfilled webhook.

    Schedules follow-up communication (e.g., fit check email).
    """
    data, shop_domain = await _verify_webhook(request)

    order_id = data.get("id")
    logger.info(f"Order {order_id} fulfilled from {shop_domain}")

    # TODO: Queue follow-up email via Celery
    # e.g., send a "How does it fit?" survey 7 days after delivery

    return {"status": "ok", "order_id": order_id}


@router.post("/refunds-create")
async def handle_refund_created(request: Request) -> dict:
    """
    Handle refunds/create webhook.

    Updates prediction accuracy tracking.
    """
    data, shop_domain = await _verify_webhook(request)

    order_id = data.get("order_id")
    logger.info(f"Refund for order {order_id} from {shop_domain}")

    # Mark the prediction as "was_returned = True" for model feedback
    async with async_session_factory() as session:
        await session.execute(
            update(Prediction)
            .where(Prediction.shopify_order_id == order_id)
            .values(was_returned=True)
        )
        await session.commit()

    return {"status": "ok", "order_id": order_id}


@router.post("/app-uninstalled")
async def handle_app_uninstalled(request: Request) -> dict:
    """
    Handle app/uninstalled webhook.

    Deactivates the merchant (we don't delete data immediately
    in case they reinstall).
    """
    data, shop_domain = await _verify_webhook(request)

    logger.info(f"App uninstalled by {shop_domain}")

    async with async_session_factory() as session:
        await session.execute(
            update(Merchant)
            .where(Merchant.shopify_shop_domain == shop_domain)
            .values(is_active=False, shopify_access_token="")
        )
        await session.commit()

    return {"status": "ok", "shop": shop_domain}


@router.post("/customers-redact")
async def handle_customers_redact(request: Request) -> dict:
    """
    Mandatory GDPR webhook: customers/redact
    Shopify sends this when a store owner requests that data for a customer is deleted.
    """
    data, shop_domain = await _verify_webhook(request)
    logger.info(f"GDPR: customers/redact received for {shop_domain}")
    
    # TODO: Clear person-identifiable data for this customer
    # customer_id = data.get("customer", {}).get("id")
    
    return {"status": "ok"}


@router.post("/customers-data-request")
async def handle_customers_data_request(request: Request) -> dict:
    """
    Mandatory GDPR webhook: customers/data_request
    Shopify sends this when a customer requests their data from the store owner.
    """
    data, shop_domain = await _verify_webhook(request)
    logger.info(f"GDPR: customers/data_request received for {shop_domain}")
    
    # TODO: Provide customer data to Shopify
    
    return {"status": "ok"}


@router.post("/shop-redact")
async def handle_shop_redact(request: Request) -> dict:
    """
    Mandatory GDPR webhook: shop/redact
    Shopify sends this when a store owner requests that their data is deleted.
    """
    data, shop_domain = await _verify_webhook(request)
    logger.info(f"GDPR: shop/redact received for {shop_domain}")
    
    # TODO: Mark merchant data for deletion
    
    return {"status": "ok"}
