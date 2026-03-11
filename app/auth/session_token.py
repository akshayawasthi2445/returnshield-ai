"""
ReturnShield AI — Shopify Session Token Verification

Shopify App Bridge generates JWTs (session tokens) that authenticate
requests from the embedded app. This module verifies those tokens.
"""

import jwt
from fastapi import HTTPException, status

from app.config import settings


def verify_session_token(token: str) -> dict:
    """
    Verify a Shopify session token (JWT).

    Session tokens are signed with the app's API secret using HS256.
    We validate:
      - Signature (using SHOPIFY_API_SECRET)
      - Expiration (exp claim)
      - Issuer format (iss must be a Shopify shop URL)
      - Audience (aud must match our API key)

    Returns:
        dict: The decoded JWT payload.

    Raises:
        HTTPException: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.SHOPIFY_API_SECRET,
            algorithms=["HS256"],
            audience=settings.SHOPIFY_API_KEY,
            options={
                "verify_exp": True,
                "verify_aud": True,
                "require": ["exp", "nbf", "iss", "dest", "sub", "aud"],
            },
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token has expired",
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session token audience mismatch",
        )
    except jwt.DecodeError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
        )
    except jwt.InvalidTokenError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Session token error: {e}",
        )

    # Validate issuer is a Shopify admin URL
    iss = payload.get("iss", "")
    if not iss.startswith("https://") or "/admin" not in iss:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token issuer",
        )

    return payload
