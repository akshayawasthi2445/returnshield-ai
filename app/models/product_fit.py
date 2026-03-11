"""
ReturnShield AI — Product Fit Profile Model

Stores size/fit intelligence derived from return data
for each product. Used to generate smart size guides.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ProductFitProfile(BaseModel):
    __tablename__ = "product_fit_profiles"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    shopify_product_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    product_title: Mapped[str] = mapped_column(String(500), nullable=False)

    # Size distribution: {"S": 120, "M": 340, "L": 200, "XL": 90}
    size_distribution: Mapped[dict] = mapped_column(JSON, default=dict)

    # Return rates by size: {"S": 0.15, "M": 0.05, "L": 0.08, "XL": 0.22}
    return_by_size: Mapped[dict] = mapped_column(JSON, default=dict)

    # Recommended size mappings:
    # {"too_small": {"S": "M", "M": "L"}, "too_large": {"XL": "L"}}
    recommended_mappings: Mapped[dict] = mapped_column(JSON, default=dict)

    # Overall return rate for this product
    avg_return_rate: Mapped[float | None] = mapped_column(Float)

    # Total orders analyzed
    total_orders_analyzed: Mapped[int] = mapped_column(default=0)

    # When the fit profile was last updated by the ML pipeline
    last_trained: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Relationships
    merchant = relationship("Merchant", back_populates="fit_profiles")

    def __repr__(self) -> str:
        return f"<ProductFitProfile product={self.shopify_product_id} rate={self.avg_return_rate}>"
