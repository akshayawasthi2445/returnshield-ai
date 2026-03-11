"""
ReturnShield AI — FastAPI Dependencies

Reusable dependencies for DB sessions and authenticated merchant context.
"""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.session_token import verify_session_token
from app.database import get_db_session
from app.models.merchant import Merchant

# Type alias for injecting DB sessions
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


async def get_current_merchant(
    request: Request,
    db: DbSession,
) -> Merchant:
    """
    Extract the Shopify session token from the request,
    verify it, and return the corresponding Merchant record.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        # Dev bypass
        from app.config import settings
        if settings.APP_ENV == "development" and request.headers.get("X-Dev-Bypass"):
            result = await db.execute(select(Merchant).limit(1))
            merchant = result.scalar_one_or_none()
            if merchant: return merchant

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
        )

    token = auth_header.removeprefix("Bearer ").strip()
    # Skip token verification in dev if X-Dev-Bypass is present
    from app.config import settings
    if settings.APP_ENV == "development" and request.headers.get("X-Dev-Bypass"):
        payload = {"dest": "https://test-shop.myshopify.com"}
    else:
        payload = verify_session_token(token)

    shop_domain = payload.get("dest", "").replace("https://", "").replace("http://", "")
    if not shop_domain:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token: missing shop domain",
        )

    result = await db.execute(
        select(Merchant).where(Merchant.shopify_shop_domain == shop_domain)
    )
    merchant = result.scalar_one_or_none()

    if merchant is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Merchant not found for shop: {shop_domain}",
        )

    return merchant


# Type alias for injecting authenticated merchant
CurrentMerchant = Annotated[Merchant, Depends(get_current_merchant)]
