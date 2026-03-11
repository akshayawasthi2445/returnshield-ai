"""
ReturnShield AI — Prediction Model

Stores ML predictions for individual orders, including
the return risk score and contributing factors.
"""

import uuid

from sqlalchemy import BigInteger, Float, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Prediction(BaseModel):
    __tablename__ = "predictions"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    shopify_order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )

    # Risk score from 0.0 (low risk) to 1.0 (high risk)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)

    # Factors that contributed to the score
    # e.g. {"size_mismatch_history": 0.3, "product_return_rate": 0.25, ...}
    risk_factors: Mapped[dict] = mapped_column(JSON, default=dict)

    # What action was taken based on the prediction
    action_taken: Mapped[str | None] = mapped_column(String(100))

    # Whether the prediction was accurate (filled in after the fact)
    was_returned: Mapped[bool | None] = mapped_column(default=None)

    # Model version that generated this prediction
    model_version: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    merchant = relationship("Merchant", back_populates="predictions")

    def __repr__(self) -> str:
        return f"<Prediction order={self.shopify_order_id} risk={self.risk_score:.2f}>"
