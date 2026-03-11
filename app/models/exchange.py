"""
ReturnShield AI — Exchange Model

Represents an exchange where a return is converted
to a new order instead of a refund.
"""

import enum
import uuid

from sqlalchemy import BigInteger, Enum, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ExchangeStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class Exchange(BaseModel):
    __tablename__ = "exchanges"

    return_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_requests.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    new_shopify_order_id: Mapped[int | None] = mapped_column(BigInteger)
    status: Mapped[ExchangeStatus] = mapped_column(
        Enum(ExchangeStatus), default=ExchangeStatus.PENDING, nullable=False
    )
    new_product_title: Mapped[str | None] = mapped_column(String(500))
    new_variant_title: Mapped[str | None] = mapped_column(String(255))
    value_difference: Mapped[float | None] = mapped_column(
        Numeric(10, 2), default=0
    )

    # Relationships
    return_request = relationship("ReturnRequest", back_populates="exchange")

    def __repr__(self) -> str:
        return f"<Exchange return={self.return_request_id} status={self.status}>"
