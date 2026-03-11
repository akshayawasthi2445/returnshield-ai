"""
ReturnShield AI — Return Request Model

Represents a customer-initiated return request.
"""

import enum
import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ReturnStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    IN_TRANSIT = "in_transit"
    RECEIVED = "received"
    REFUNDED = "refunded"
    EXCHANGED = "exchanged"
    CLOSED = "closed"


class ReturnReasonCode(str, enum.Enum):
    WRONG_SIZE = "wrong_size"
    DEFECTIVE = "defective"
    NOT_AS_DESCRIBED = "not_as_described"
    CHANGED_MIND = "changed_mind"
    ARRIVED_LATE = "arrived_late"
    WRONG_ITEM = "wrong_item"
    OTHER = "other"


class ResolutionType(str, enum.Enum):
    REFUND = "refund"
    EXCHANGE = "exchange"
    STORE_CREDIT = "store_credit"


class ReturnRequest(BaseModel):
    __tablename__ = "return_requests"

    merchant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("merchants.id"), nullable=False, index=True
    )
    shopify_order_id: Mapped[int] = mapped_column(
        BigInteger, nullable=False, index=True
    )
    shopify_order_name: Mapped[str | None] = mapped_column(String(50))
    customer_email: Mapped[str | None] = mapped_column(String(255))
    customer_name: Mapped[str | None] = mapped_column(String(255))

    status: Mapped[ReturnStatus] = mapped_column(
        Enum(ReturnStatus), default=ReturnStatus.PENDING, nullable=False
    )
    reason_code: Mapped[ReturnReasonCode] = mapped_column(
        Enum(ReturnReasonCode), nullable=False
    )
    reason_detail: Mapped[str | None] = mapped_column(Text)
    resolution_type: Mapped[ResolutionType | None] = mapped_column(
        Enum(ResolutionType)
    )
    refund_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    risk_score: Mapped[float | None] = mapped_column(Numeric(3, 2))

    # Relationships
    merchant = relationship("Merchant", back_populates="return_requests")
    items = relationship("ReturnItem", back_populates="return_request", lazy="selectin")
    exchange = relationship("Exchange", back_populates="return_request", uselist=False)

    def __repr__(self) -> str:
        return f"<ReturnRequest order={self.shopify_order_id} status={self.status}>"
