"""
ReturnShield AI — Customer Portal API

Public-facing endpoints (token-authenticated, not session-token)
for customers to initiate and track returns.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel as PydanticBase
from sqlalchemy import select

from app.database import async_session_factory
from app.models.merchant import Merchant
from app.models.return_item import ReturnItem
from app.models.return_request import ReturnReasonCode, ReturnRequest, ReturnStatus

router = APIRouter(prefix="/portal", tags=["customer-portal"])


# --- Schemas ---


class PortalReturnItemCreate(PydanticBase):
    shopify_line_item_id: int
    product_title: str
    variant_title: str | None = None
    quantity: int = 1
    reason: str | None = None
    size_ordered: str | None = None


class PortalReturnCreate(PydanticBase):
    shopify_order_id: int
    order_name: str | None = None
    customer_email: str
    customer_name: str | None = None
    reason_code: ReturnReasonCode
    reason_detail: str | None = None
    items: list[PortalReturnItemCreate]


class PortalReturnStatus(PydanticBase):
    id: uuid.UUID
    status: ReturnStatus
    reason_code: ReturnReasonCode
    created_at: datetime
    items_count: int


# --- Endpoints ---


@router.get("/{shop_domain}/lookup")
async def lookup_order(
    shop_domain: str,
    order_id: int = Query(...),
    email: str = Query(...),
):
    """
    Look up an order to verify the customer can initiate a return.

    In production, this would call the Shopify API to fetch the order
    and verify it belongs to the given email.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(Merchant).where(
                Merchant.shopify_shop_domain == shop_domain,
                Merchant.is_active == True,
            )
        )
        merchant = result.scalar_one_or_none()

        if merchant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found or ReturnShield not active",
            )

    # TODO: Call Shopify API to verify order exists and belongs to email
    # For now, return a stub
    return {
        "order_found": True,
        "order_id": order_id,
        "order_name": f"#RS{order_id}",
        "eligible_for_return": True,
        "return_window_days": 30,
    }


@router.post("/{shop_domain}/submit", response_model=PortalReturnStatus)
async def submit_return(
    shop_domain: str,
    data: PortalReturnCreate,
):
    """
    Customer submits a return request through the portal.
    """
    async with async_session_factory() as session:
        # Find merchant
        result = await session.execute(
            select(Merchant).where(
                Merchant.shopify_shop_domain == shop_domain,
                Merchant.is_active == True,
            )
        )
        merchant = result.scalar_one_or_none()

        if merchant is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Store not found",
            )

        # Create return request
        return_request = ReturnRequest(
            merchant_id=merchant.id,
            shopify_order_id=data.shopify_order_id,
            shopify_order_name=data.order_name,
            customer_email=data.customer_email,
            customer_name=data.customer_name,
            reason_code=data.reason_code,
            reason_detail=data.reason_detail,
            status=ReturnStatus.PENDING,
        )
        session.add(return_request)
        await session.flush()

        # Add items
        for item in data.items:
            return_item = ReturnItem(
                return_request_id=return_request.id,
                shopify_line_item_id=item.shopify_line_item_id,
                product_title=item.product_title,
                variant_title=item.variant_title,
                quantity=item.quantity,
                reason=item.reason,
                size_ordered=item.size_ordered,
            )
            session.add(return_item)

        await session.commit()
        await session.refresh(return_request)

        return PortalReturnStatus(
            id=return_request.id,
            status=return_request.status,
            reason_code=return_request.reason_code,
            created_at=return_request.created_at,
            items_count=len(data.items),
        )


@router.get("/{shop_domain}/status/{return_id}", response_model=PortalReturnStatus)
async def check_return_status(
    shop_domain: str,
    return_id: uuid.UUID,
    email: str = Query(...),
):
    """
    Customer checks the status of their return request.
    Requires email for verification.
    """
    async with async_session_factory() as session:
        result = await session.execute(
            select(ReturnRequest)
            .join(Merchant)
            .where(
                ReturnRequest.id == return_id,
                Merchant.shopify_shop_domain == shop_domain,
                ReturnRequest.customer_email == email,
            )
        )
        return_request = result.scalar_one_or_none()

        if return_request is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Return request not found",
            )

        items_result = await session.execute(
            select(ReturnItem).where(
                ReturnItem.return_request_id == return_request.id
            )
        )
        items_count = len(items_result.scalars().all())

        return PortalReturnStatus(
            id=return_request.id,
            status=return_request.status,
            reason_code=return_request.reason_code,
            created_at=return_request.created_at,
            items_count=items_count,
        )
