"""
ReturnShield AI — Merchant Model

Represents a Shopify store that has installed ReturnShield AI.
"""

import uuid

from sqlalchemy import BigInteger, Boolean, String, Text
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class Merchant(BaseModel):
    __tablename__ = "merchants"

    shopify_shop_domain: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False, index=True
    )
    shopify_access_token: Mapped[str] = mapped_column(
        Text, nullable=False
    )
    shop_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255))
    plan_name: Mapped[str] = mapped_column(String(50), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings_json: Mapped[dict] = mapped_column(
        JSON, default=dict, server_default="{}"
    )

    # Relationships
    return_requests = relationship("ReturnRequest", back_populates="merchant", lazy="selectin")
    predictions = relationship("Prediction", back_populates="merchant", lazy="selectin")
    fit_profiles = relationship("ProductFitProfile", back_populates="merchant", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Merchant {self.shopify_shop_domain}>"
