"""
ReturnShield AI — Returns API

CRUD endpoints for managing return requests.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel as PydanticBase
from sqlalchemy import func, select

from app.dependencies import CurrentMerchant, DbSession
from app.models.return_item import ReturnItem
from app.models.return_request import (
    ResolutionType,
    ReturnReasonCode,
    ReturnRequest,
    ReturnStatus,
)

router = APIRouter(prefix="/returns", tags=["returns"])


# --- Pydantic Schemas ---


class ReturnItemCreate(PydanticBase):
    shopify_line_item_id: int
    shopify_product_id: int | None = None
    product_title: str
    variant_title: str | None = None
    sku: str | None = None
    quantity: int = 1
    reason: str | None = None
    size_ordered: str | None = None


class ReturnCreate(PydanticBase):
    shopify_order_id: int
    shopify_order_name: str | None = None
    customer_email: str | None = None
    customer_name: str | None = None
    reason_code: ReturnReasonCode
    reason_detail: str | None = None
    resolution_type: ResolutionType | None = None
    items: list[ReturnItemCreate]


class ReturnUpdate(PydanticBase):
    status: ReturnStatus | None = None
    resolution_type: ResolutionType | None = None
    refund_amount: float | None = None


class ReturnItemResponse(PydanticBase):
    id: uuid.UUID
    product_title: str
    variant_title: str | None
    quantity: int
    reason: str | None
    size_ordered: str | None
    size_recommended: str | None

    class Config:
        from_attributes = True


class ReturnResponse(PydanticBase):
    id: uuid.UUID
    shopify_order_id: int
    shopify_order_name: str | None
    customer_email: str | None
    customer_name: str | None
    status: ReturnStatus
    reason_code: ReturnReasonCode
    reason_detail: str | None
    resolution_type: ResolutionType | None
    refund_amount: float | None
    risk_score: float | None
    created_at: datetime
    items: list[ReturnItemResponse]

    class Config:
        from_attributes = True


class ReturnListResponse(PydanticBase):
    returns: list[ReturnResponse]
    total: int
    page: int
    page_size: int


# --- Endpoints ---


@router.get("", response_model=ReturnListResponse)
async def list_returns(
    merchant: CurrentMerchant,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status_filter: ReturnStatus | None = None,
):
    """List all return requests for the authenticated merchant."""
    query = select(ReturnRequest).where(
        ReturnRequest.merchant_id == merchant.id
    )

    if status_filter:
        query = query.where(ReturnRequest.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    # Paginate
    query = query.order_by(ReturnRequest.created_at.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    returns = result.scalars().all()

    return ReturnListResponse(
        returns=[ReturnResponse.model_validate(r) for r in returns],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=ReturnResponse, status_code=status.HTTP_201_CREATED)
async def create_return(
    data: ReturnCreate,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Create a new return request."""
    return_request = ReturnRequest(
        merchant_id=merchant.id,
        shopify_order_id=data.shopify_order_id,
        shopify_order_name=data.shopify_order_name,
        customer_email=data.customer_email,
        customer_name=data.customer_name,
        reason_code=data.reason_code,
        reason_detail=data.reason_detail,
        resolution_type=data.resolution_type,
        status=ReturnStatus.PENDING,
    )
    db.add(return_request)
    await db.flush()

    # Add items
    for item_data in data.items:
        item = ReturnItem(
            return_request_id=return_request.id,
            shopify_line_item_id=item_data.shopify_line_item_id,
            shopify_product_id=item_data.shopify_product_id,
            product_title=item_data.product_title,
            variant_title=item_data.variant_title,
            sku=item_data.sku,
            quantity=item_data.quantity,
            reason=item_data.reason,
            size_ordered=item_data.size_ordered,
        )
        db.add(item)

    await db.flush()
    await db.refresh(return_request)

    return ReturnResponse.model_validate(return_request)


@router.get("/{return_id}", response_model=ReturnResponse)
async def get_return(
    return_id: uuid.UUID,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Get a single return request by ID."""
    result = await db.execute(
        select(ReturnRequest).where(
            ReturnRequest.id == return_id,
            ReturnRequest.merchant_id == merchant.id,
        )
    )
    return_request = result.scalar_one_or_none()

    if return_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    return ReturnResponse.model_validate(return_request)


@router.patch("/{return_id}", response_model=ReturnResponse)
async def update_return(
    return_id: uuid.UUID,
    data: ReturnUpdate,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Update a return request (status, resolution, refund amount)."""
    result = await db.execute(
        select(ReturnRequest).where(
            ReturnRequest.id == return_id,
            ReturnRequest.merchant_id == merchant.id,
        )
    )
    return_request = result.scalar_one_or_none()

    if return_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if data.status is not None:
        return_request.status = data.status
    if data.resolution_type is not None:
        return_request.resolution_type = data.resolution_type
    if data.refund_amount is not None:
        return_request.refund_amount = data.refund_amount

    await db.flush()
    await db.refresh(return_request)

    return ReturnResponse.model_validate(return_request)


@router.post("/{return_id}/approve", response_model=ReturnResponse)
async def approve_return(
    return_id: uuid.UUID,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Approve a pending return request."""
    result = await db.execute(
        select(ReturnRequest).where(
            ReturnRequest.id == return_id,
            ReturnRequest.merchant_id == merchant.id,
        )
    )
    return_request = result.scalar_one_or_none()

    if return_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if return_request.status != ReturnStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot approve return with status: {return_request.status}",
        )

    return_request.status = ReturnStatus.APPROVED
    await db.flush()
    await db.refresh(return_request)

    return ReturnResponse.model_validate(return_request)


@router.post("/{return_id}/reject", response_model=ReturnResponse)
async def reject_return(
    return_id: uuid.UUID,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Reject a pending return request."""
    result = await db.execute(
        select(ReturnRequest).where(
            ReturnRequest.id == return_id,
            ReturnRequest.merchant_id == merchant.id,
        )
    )
    return_request = result.scalar_one_or_none()

    if return_request is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Return request not found",
        )

    if return_request.status != ReturnStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot reject return with status: {return_request.status}",
        )

    return_request.status = ReturnStatus.REJECTED
    await db.flush()
    await db.refresh(return_request)

    return ReturnResponse.model_validate(return_request)
