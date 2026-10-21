from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models.base import BaseModel

if TYPE_CHECKING:
    from .batch import Batch


class Product(BaseModel):
    """
    Модель единицы продукции в партии
    """

    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    unique_code: Mapped[str] = mapped_column(
        sa.String(length=255), unique=True, nullable=False, index=True
    )
    batch_id: Mapped[int] = mapped_column(
        sa.ForeignKey("batches.id"), nullable=False, index=True
    )

    is_aggregated: Mapped[bool] = mapped_column(
        server_default=sa.false(), nullable=False, index=True
    )
    aggregated_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),  # pylint: disable=E1102
    )

    batch: Mapped[Batch] = relationship(back_populates="products")

    __table_args__ = (
        sa.Index("idx_product_batch_aggregated", "batch_id", "is_aggregated"),
    )

    def __repr__(self) -> str:
        return f"<Product(id={self.id}, unique_code='{self.unique_code}')>"
