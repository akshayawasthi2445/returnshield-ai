"""
ReturnShield AI — Shopify OAuth2 Flow

Handles the app installation flow:
  1. Merchant clicks "Install" → we redirect to Shopify's OAuth page
  2. Merchant authorizes → Shopify redirects to our callback URL
  3. We exchange the auth code for an access token
  4. We store the merchant and register webhooks
"""

import hashlib
import hmac
import secrets
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.config import settings
from app.database import async_session_factory
from app.models.merchant import Merchant

router = APIRouter(tags=["auth"])

# --- Nonce Store ---

class NonceStore:
    """Base class for OAuth nonce storage."""
    async def add(self, nonce: str) -> None: raise NotImplementedError()
    async def contains(self, nonce: str) -> bool: raise NotImplementedError()
    async def remove(self, nonce: str) -> None: raise NotImplementedError()

class MemoryNonceStore(NonceStore):
    """Fallback in-memory storage for development."""
    def __init__(self): self._nonces = set()
    async def add(self, nonce: str): self._nonces.add(nonce)
    async def contains(self, nonce: str): return nonce in self._nonces
    async def remove(self, nonce: str): self._nonces.discard(nonce)

# Initialize store (in production, use RedisNonceStore)
nonce_store = MemoryNonceStore()


@router.get("/auth/install")
async def install(shop: str) -> RedirectResponse:
    """
    Step 1: Redirect merchant to Shopify's OAuth authorization page.
    """
    if not shop or not shop.endswith(".myshopify.com"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid shop parameter. Must be a .myshopify.com domain.",
        )

    nonce = secrets.token_urlsafe(32)
    await nonce_store.add(nonce)

    params = urlencode({
        "client_id": settings.SHOPIFY_API_KEY,
        "scope": settings.SHOPIFY_SCOPES,
        "redirect_uri": f"{settings.APP_URL}/auth/callback",
        "state": nonce,
    })

    auth_url = f"https://{shop}/admin/oauth/authorize?{params}"
    return RedirectResponse(url=auth_url)


@router.get("/auth/callback")
async def callback(request: Request) -> RedirectResponse:
    """
    Step 2: Handle Shopify's OAuth callback.
    Exchange the temporary code for a permanent access token.
    """
    params = dict(request.query_params)

    # Verify HMAC
    if not _verify_hmac(params):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="HMAC verification failed",
        )

    # Verify nonce
    state = params.get("state", "")
    if not await nonce_store.contains(state):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid state/nonce parameter",
        )
    await nonce_store.remove(state)

    shop = params.get("shop", "")
    code = params.get("code", "")

    if not shop or not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing shop or code parameter",
        )

    # Exchange code for access token
    access_token = await _exchange_code_for_token(shop, code)

    # Store or update merchant
    await _upsert_merchant(shop, access_token)

    # Register webhooks
    await _register_webhooks(shop, access_token)

    # Redirect to app inside Shopify admin
    return RedirectResponse(
        url=f"https://{shop}/admin/apps/{settings.SHOPIFY_API_KEY}"
    )


async def _exchange_code_for_token(shop: str, code: str) -> str:
    """Exchange the temporary auth code for a permanent access token."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"https://{shop}/admin/oauth/access_token",
            json={
                "client_id": settings.SHOPIFY_API_KEY,
                "client_secret": settings.SHOPIFY_API_SECRET,
                "code": code,
            },
        )

    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Failed to exchange code for token: {response.text}",
        )

    data = response.json()
    return data["access_token"]


async def _upsert_merchant(shop_domain: str, access_token: str) -> Merchant:
    """Create or update the merchant record."""
    async with async_session_factory() as session:
        result = await session.execute(
            select(Merchant).where(Merchant.shopify_shop_domain == shop_domain)
        )
        merchant = result.scalar_one_or_none()

        if merchant is None:
            merchant = Merchant(
                shopify_shop_domain=shop_domain,
                shopify_access_token=access_token,
                settings_json={},
            )
            session.add(merchant)
        else:
            merchant.shopify_access_token = access_token

        await session.commit()
        await session.refresh(merchant)
        return merchant


async def _register_webhooks(shop: str, access_token: str) -> None:
    """Register required Shopify webhooks."""
    webhooks = [
        {"topic": "orders/create", "path": "/api/v1/webhooks/orders-create"},
        {"topic": "orders/fulfilled", "path": "/api/v1/webhooks/orders-fulfilled"},
        {"topic": "app/uninstalled", "path": "/api/v1/webhooks/app-uninstalled"},
        {"topic": "refunds/create", "path": "/api/v1/webhooks/refunds-create"},
        {"topic": "customers/redact", "path": "/api/v1/webhooks/customers-redact"},
        {"topic": "customers/data_request", "path": "/api/v1/webhooks/customers-data-request"},
        {"topic": "shop/redact", "path": "/api/v1/webhooks/shop-redact"},
    ]

    async with httpx.AsyncClient() as client:
        for wh in webhooks:
            await client.post(
                f"https://{shop}/admin/api/2024-10/webhooks.json",
                headers={
                    "X-Shopify-Access-Token": access_token,
                    "Content-Type": "application/json",
                },
                json={
                    "webhook": {
                        "topic": wh["topic"],
                        "address": f"{settings.APP_URL}{wh['path']}",
                        "format": "json",
                    }
                },
            )


def _verify_hmac(params: dict) -> bool:
    """Verify the HMAC signature from Shopify's OAuth callback."""
    hmac_value = params.pop("hmac", None)
    if not hmac_value:
        return False

    # Sort remaining params and create query string
    sorted_params = "&".join(
        f"{key}={value}" for key, value in sorted(params.items())
    )

    # Compute HMAC
    computed = hmac.new(
        settings.SHOPIFY_API_SECRET.encode("utf-8"),
        sorted_params.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(computed, hmac_value)
