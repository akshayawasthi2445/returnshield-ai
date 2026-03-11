"""
ReturnShield AI — Predictions API

Endpoints for viewing and triggering return risk predictions.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel as PydanticBase
from sqlalchemy import func, select

from app.dependencies import CurrentMerchant, DbSession
from app.ml.return_predictor import ReturnPredictor
from app.models.prediction import Prediction

router = APIRouter(prefix="/predictions", tags=["predictions"])

# Singleton predictor instance
_predictor = ReturnPredictor()


# --- Schemas ---


class PredictionResponse(PydanticBase):
    id: uuid.UUID
    shopify_order_id: int
    risk_score: float
    risk_factors: dict
    action_taken: str | None
    was_returned: bool | None
    model_version: str | None
    created_at: datetime

    class Config:
        from_attributes = True


class PredictionListResponse(PydanticBase):
    predictions: list[PredictionResponse]
    total: int


class BatchPredictRequest(PydanticBase):
    order_ids: list[int]


class BatchPredictResponse(PydanticBase):
    results: list[dict]


# --- Endpoints ---


@router.get("", response_model=PredictionListResponse)
async def list_predictions(
    merchant: CurrentMerchant,
    db: DbSession,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    min_risk: float = Query(0.0, ge=0.0, le=1.0),
):
    """List predictions for the merchant, optionally filtered by min risk score."""
    query = select(Prediction).where(
        Prediction.merchant_id == merchant.id,
        Prediction.risk_score >= min_risk,
    )

    count_query = select(func.count()).select_from(query.subquery())
    total = (await db.execute(count_query)).scalar() or 0

    query = query.order_by(Prediction.risk_score.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)

    result = await db.execute(query)
    predictions = result.scalars().all()

    return PredictionListResponse(
        predictions=[PredictionResponse.model_validate(p) for p in predictions],
        total=total,
    )


@router.get("/{order_id}", response_model=PredictionResponse)
async def get_prediction(
    order_id: int,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Get the prediction for a specific order."""
    result = await db.execute(
        select(Prediction).where(
            Prediction.shopify_order_id == order_id,
            Prediction.merchant_id == merchant.id,
        )
    )
    prediction = result.scalar_one_or_none()

    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No prediction found for order {order_id}",
        )

    return PredictionResponse.model_validate(prediction)


@router.post("/batch", response_model=BatchPredictResponse)
async def batch_predict(
    data: BatchPredictRequest,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """
    Run predictions for multiple orders.

    Uses the ML model to score each order's return risk.
    """
    results = []

    for order_id in data.order_ids:
        # Generate prediction using ML model
        score, factors = _predictor.predict(order_id=order_id, merchant_id=str(merchant.id))

        # Determine action
        if score > 0.7:
            action = "flag_high_risk"
        elif score > 0.5:
            action = "send_size_check"
        else:
            action = "none"

        # Store prediction
        prediction = Prediction(
            merchant_id=merchant.id,
            shopify_order_id=order_id,
            risk_score=score,
            risk_factors=factors,
            action_taken=action,
            model_version=_predictor.version,
        )
        db.add(prediction)

        results.append({
            "order_id": order_id,
            "risk_score": score,
            "risk_factors": factors,
            "action": action,
        })

    await db.flush()

    return BatchPredictResponse(results=results)
