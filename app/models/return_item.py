"""
ReturnShield AI — Return Item Model

Represents an individual line item within a return request.
"""

import uuid

from sqlalchemy import BigInteger, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel


class ReturnItem(BaseModel):
    __tablename__ = "return_items"

    return_request_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("return_requests.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shopify_line_item_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    shopify_product_id: Mapped[int | None] = mapped_column(BigInteger)
    product_title: Mapped[str] = mapped_column(String(500), nullable=False)
    variant_title: Mapped[str | None] = mapped_column(String(255))
    sku: Mapped[str | None] = mapped_column(String(100))
    quantity: Mapped[int] = mapped_column(default=1)
    reason: Mapped[str | None] = mapped_column(Text)
    size_ordered: Mapped[str | None] = mapped_column(String(50))
    size_recommended: Mapped[str | None] = mapped_column(String(50))

    # Relationships
    return_request = relationship("ReturnRequest", back_populates="items")

    def __repr__(self) -> str:
        return f"<ReturnItem {self.product_title} ({self.variant_title})>"
