"""
ReturnShield AI — Analytics API

Dashboard and reporting endpoints showing return trends,
revenue impact, and product-level return analysis.
"""

from datetime import datetime, timedelta

from fastapi import APIRouter, Query
from pydantic import BaseModel as PydanticBase
from sqlalchemy import case, func, select

from app.dependencies import CurrentMerchant, DbSession
from app.models.exchange import Exchange
from app.models.prediction import Prediction
from app.models.return_item import ReturnItem
from app.models.return_request import ReturnReasonCode, ReturnRequest, ReturnStatus

router = APIRouter(prefix="/analytics", tags=["analytics"])


# --- Schemas ---


class OverviewResponse(PydanticBase):
    total_returns: int
    pending_returns: int
    approved_returns: int
    total_exchanges: int
    exchange_rate: float  # % of returns converted to exchanges
    avg_risk_score: float
    high_risk_orders: int
    revenue_saved_by_exchanges: float


class ReturnTrendPoint(PydanticBase):
    date: str
    count: int


class ReturnTrendsResponse(PydanticBase):
    trends: list[ReturnTrendPoint]
    period_days: int


class ReasonBreakdown(PydanticBase):
    reason: str
    count: int
    percentage: float


class ReasonsResponse(PydanticBase):
    reasons: list[ReasonBreakdown]
    total: int


class ProductReturnInfo(PydanticBase):
    product_title: str
    shopify_product_id: int | None
    return_count: int
    top_reason: str | None


class ProductReturnsResponse(PydanticBase):
    products: list[ProductReturnInfo]


# --- Endpoints ---


@router.get("/overview", response_model=OverviewResponse)
async def get_overview(
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Get the dashboard overview with key metrics."""
    # Total returns
    total_result = await db.execute(
        select(func.count(ReturnRequest.id)).where(
            ReturnRequest.merchant_id == merchant.id
        )
    )
    total_returns = total_result.scalar() or 0

    # Returns by status
    status_result = await db.execute(
        select(ReturnRequest.status, func.count(ReturnRequest.id))
        .where(ReturnRequest.merchant_id == merchant.id)
        .group_by(ReturnRequest.status)
    )
    status_counts = dict(status_result.all())
    pending = status_counts.get(ReturnStatus.PENDING, 0)
    approved = status_counts.get(ReturnStatus.APPROVED, 0)

    # Exchanges
    exchange_result = await db.execute(
        select(func.count(Exchange.id))
        .join(ReturnRequest)
        .where(ReturnRequest.merchant_id == merchant.id)
    )
    total_exchanges = exchange_result.scalar() or 0
    exchange_rate = (total_exchanges / total_returns * 100) if total_returns > 0 else 0.0

    # Revenue saved (sum of exchange value differences that are positive)
    saved_result = await db.execute(
        select(func.coalesce(func.sum(Exchange.value_difference), 0))
        .join(ReturnRequest)
        .where(ReturnRequest.merchant_id == merchant.id)
    )
    revenue_saved = float(saved_result.scalar() or 0)

    # Predictions
    pred_result = await db.execute(
        select(
            func.coalesce(func.avg(Prediction.risk_score), 0),
            func.count(case((Prediction.risk_score > 0.7, 1))),
        ).where(Prediction.merchant_id == merchant.id)
    )
    pred_row = pred_result.one()
    avg_risk = float(pred_row[0])
    high_risk = int(pred_row[1])

    return OverviewResponse(
        total_returns=total_returns,
        pending_returns=pending,
        approved_returns=approved,
        total_exchanges=total_exchanges,
        exchange_rate=round(exchange_rate, 1),
        avg_risk_score=round(avg_risk, 3),
        high_risk_orders=high_risk,
        revenue_saved_by_exchanges=revenue_saved,
    )


@router.get("/trends", response_model=ReturnTrendsResponse)
async def get_return_trends(
    merchant: CurrentMerchant,
    db: DbSession,
    days: int = Query(30, ge=7, le=365),
):
    """Get return count trends over the specified period."""
    start_date = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(ReturnRequest.created_at).label("date"),
            func.count(ReturnRequest.id).label("count"),
        )
        .where(
            ReturnRequest.merchant_id == merchant.id,
            ReturnRequest.created_at >= start_date,
        )
        .group_by(func.date(ReturnRequest.created_at))
        .order_by(func.date(ReturnRequest.created_at))
    )

    trends = [
        ReturnTrendPoint(date=str(row.date), count=row.count)
        for row in result.all()
    ]

    return ReturnTrendsResponse(trends=trends, period_days=days)


@router.get("/reasons", response_model=ReasonsResponse)
async def get_return_reasons(
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Get breakdown of return reasons."""
    result = await db.execute(
        select(
            ReturnRequest.reason_code,
            func.count(ReturnRequest.id).label("count"),
        )
        .where(ReturnRequest.merchant_id == merchant.id)
        .group_by(ReturnRequest.reason_code)
        .order_by(func.count(ReturnRequest.id).desc())
    )
    rows = result.all()
    total = sum(r.count for r in rows)

    reasons = [
        ReasonBreakdown(
            reason=row.reason_code.value if row.reason_code else "unknown",
            count=row.count,
            percentage=round(row.count / total * 100, 1) if total > 0 else 0,
        )
        for row in rows
    ]

    return ReasonsResponse(reasons=reasons, total=total)


@router.get("/products", response_model=ProductReturnsResponse)
async def get_product_returns(
    merchant: CurrentMerchant,
    db: DbSession,
    limit: int = Query(20, ge=1, le=100),
):
    """Get products with the highest return counts."""
    result = await db.execute(
        select(
            ReturnItem.product_title,
            ReturnItem.shopify_product_id,
            func.count(ReturnItem.id).label("return_count"),
        )
        .join(ReturnRequest)
        .where(ReturnRequest.merchant_id == merchant.id)
        .group_by(ReturnItem.product_title, ReturnItem.shopify_product_id)
        .order_by(func.count(ReturnItem.id).desc())
        .limit(limit)
    )

    products = [
        ProductReturnInfo(
            product_title=row.product_title,
            shopify_product_id=row.shopify_product_id,
            return_count=row.return_count,
            top_reason=None,  # TODO: subquery for top reason per product
        )
        for row in result.all()
    ]

    return ProductReturnsResponse(products=products)
