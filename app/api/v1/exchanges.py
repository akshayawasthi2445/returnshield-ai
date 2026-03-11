"""
ReturnShield AI — Exchanges API

Endpoints for converting returns into exchanges (revenue retention).
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel as PydanticBase
from sqlalchemy import select

from app.dependencies import CurrentMerchant, DbSession
from app.models.exchange import Exchange, ExchangeStatus
from app.models.return_request import ReturnRequest, ReturnStatus

router = APIRouter(prefix="/exchanges", tags=["exchanges"])


# --- Schemas ---


class ExchangeCreate(PydanticBase):
    return_request_id: uuid.UUID
    new_product_title: str | None = None
    new_variant_title: str | None = None
    value_difference: float = 0.0


class ExchangeResponse(PydanticBase):
    id: uuid.UUID
    return_request_id: uuid.UUID
    new_shopify_order_id: int | None
    status: ExchangeStatus
    new_product_title: str | None
    new_variant_title: str | None
    value_difference: float | None
    created_at: datetime

    class Config:
        from_attributes = True


# --- Endpoints ---


@router.post("", response_model=ExchangeResponse, status_code=status.HTTP_201_CREATED)
async def create_exchange(
    data: ExchangeCreate,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Initiate an exchange for an approved return."""
    # Verify the return belongs to this merchant and is approved
    result = await db.execute(
        select(ReturnRequest).where(
            ReturnRequest.id == data.return_request_id,
            ReturnRequest.merchant_id == merchant.id,
        )
    )
    return_request = result.scalar_one_or_none()

    if return_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if return_request.status not in (ReturnStatus.PENDING, ReturnStatus.APPROVED):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create exchange for return with status: {return_request.status}",
        )

    # Check no existing exchange
    existing = await db.execute(
        select(Exchange).where(Exchange.return_request_id == data.return_request_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An exchange already exists for this return",
        )

    exchange = Exchange(
        return_request_id=data.return_request_id,
        new_product_title=data.new_product_title,
        new_variant_title=data.new_variant_title,
        value_difference=data.value_difference,
        status=ExchangeStatus.PENDING,
    )
    db.add(exchange)

    # Update return status
    return_request.status = ReturnStatus.EXCHANGED
    return_request.resolution_type = "exchange"

    await db.flush()
    await db.refresh(exchange)

    # TODO: Create a new Shopify draft order via Shopify API

    return ExchangeResponse.model_validate(exchange)


@router.get("/{exchange_id}", response_model=ExchangeResponse)
async def get_exchange(
    exchange_id: uuid.UUID,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Get exchange details."""
    result = await db.execute(
        select(Exchange)
        .join(ReturnRequest)
        .where(
            Exchange.id == exchange_id,
            ReturnRequest.merchant_id == merchant.id,
        )
    )
    exchange = result.scalar_one_or_none()

    if exchange is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exchange not found",
        )

    return ExchangeResponse.model_validate(exchange)
