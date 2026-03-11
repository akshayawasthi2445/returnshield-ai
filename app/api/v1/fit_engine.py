"""
ReturnShield AI — Fit Engine API

Endpoints for managing product fit profiles and
generating smart size guides from return data.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel as PydanticBase
from sqlalchemy import select

from app.dependencies import CurrentMerchant, DbSession
from app.models.product_fit import ProductFitProfile

router = APIRouter(prefix="/fit", tags=["fit-engine"])


# --- Schemas ---


class FitProfileResponse(PydanticBase):
    id: uuid.UUID
    shopify_product_id: int
    product_title: str
    size_distribution: dict
    return_by_size: dict
    recommended_mappings: dict
    avg_return_rate: float | None
    total_orders_analyzed: int
    last_trained: datetime | None

    class Config:
        from_attributes = True


class FitProfileUpdate(PydanticBase):
    recommended_mappings: dict | None = None


class GenerateFitRequest(PydanticBase):
    shopify_product_id: int
    product_title: str


# --- Endpoints ---


@router.get("/{product_id}", response_model=FitProfileResponse)
async def get_fit_profile(
    product_id: int,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Get the fit profile for a specific product."""
    result = await db.execute(
        select(ProductFitProfile).where(
            ProductFitProfile.shopify_product_id == product_id,
            ProductFitProfile.merchant_id == merchant.id,
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No fit profile found for product {product_id}",
        )

    return FitProfileResponse.model_validate(profile)


@router.get("", response_model=list[FitProfileResponse])
async def list_fit_profiles(
    merchant: CurrentMerchant,
    db: DbSession,
):
    """List all fit profiles for the merchant."""
    result = await db.execute(
        select(ProductFitProfile)
        .where(ProductFitProfile.merchant_id == merchant.id)
        .order_by(ProductFitProfile.avg_return_rate.desc().nullslast())
    )
    profiles = result.scalars().all()
    return [FitProfileResponse.model_validate(p) for p in profiles]


@router.post("/generate", response_model=FitProfileResponse, status_code=status.HTTP_201_CREATED)
async def generate_fit_profile(
    data: GenerateFitRequest,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """
    Generate or regenerate a fit profile for a product.

    Analyzes existing return data for the product and creates
    size distribution, per-size return rates, and recommendations.
    """
    # Check if profile exists
    result = await db.execute(
        select(ProductFitProfile).where(
            ProductFitProfile.shopify_product_id == data.shopify_product_id,
            ProductFitProfile.merchant_id == merchant.id,
        )
    )
    existing = result.scalar_one_or_none()

    # TODO: Run actual ML analysis on return data
    # For now, create a stub profile
    fit_data = {
        "size_distribution": {"XS": 50, "S": 150, "M": 300, "L": 200, "XL": 100},
        "return_by_size": {"XS": 0.18, "S": 0.12, "M": 0.05, "L": 0.08, "XL": 0.20},
        "recommended_mappings": {
            "runs_small": ["XS", "S"],
            "true_to_size": ["M", "L"],
            "runs_large": ["XL"],
        },
        "avg_return_rate": 0.106,
    }

    if existing:
        existing.size_distribution = fit_data["size_distribution"]
        existing.return_by_size = fit_data["return_by_size"]
        existing.recommended_mappings = fit_data["recommended_mappings"]
        existing.avg_return_rate = fit_data["avg_return_rate"]
        existing.total_orders_analyzed = 800
        existing.last_trained = datetime.utcnow()
        await db.flush()
        await db.refresh(existing)
        return FitProfileResponse.model_validate(existing)
    else:
        profile = ProductFitProfile(
            merchant_id=merchant.id,
            shopify_product_id=data.shopify_product_id,
            product_title=data.product_title,
            size_distribution=fit_data["size_distribution"],
            return_by_size=fit_data["return_by_size"],
            recommended_mappings=fit_data["recommended_mappings"],
            avg_return_rate=fit_data["avg_return_rate"],
            total_orders_analyzed=800,
            last_trained=datetime.utcnow(),
        )
        db.add(profile)
        await db.flush()
        await db.refresh(profile)
        return FitProfileResponse.model_validate(profile)


@router.put("/{product_id}", response_model=FitProfileResponse)
async def update_fit_profile(
    product_id: int,
    data: FitProfileUpdate,
    merchant: CurrentMerchant,
    db: DbSession,
):
    """Update a fit profile's configuration (e.g., manual size mappings)."""
    result = await db.execute(
        select(ProductFitProfile).where(
            ProductFitProfile.shopify_product_id == product_id,
            ProductFitProfile.merchant_id == merchant.id,
        )
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No fit profile for product {product_id}",
        )

    if data.recommended_mappings is not None:
        profile.recommended_mappings = data.recommended_mappings

    await db.flush()
    await db.refresh(profile)

    return FitProfileResponse.model_validate(profile)
