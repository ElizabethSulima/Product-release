from datetime import date, datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models.base import BaseModel


class Batch(BaseModel):
    """
    Модель производственной партии (сменного задания)
    """

    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(primary_key=True)

    is_closed: Mapped[bool] = mapped_column(
        server_default=sa.false(), nullable=False
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    task_description: Mapped[str] = mapped_column(sa.Text, nullable=False)
    work_center_id: Mapped[int] = mapped_column(
        sa.ForeignKey("work_centers.id"), nullable=False
    )
    shift: Mapped[str] = mapped_column(sa.String(length=100), nullable=False)
    team: Mapped[str] = mapped_column(sa.String(length=100), nullable=False)

    batch_number: Mapped[int] = mapped_column(nullable=False, index=True)
    batch_date: Mapped[date] = mapped_column(
        sa.Date, nullable=False, index=True
    )

    nomenclature: Mapped[str] = mapped_column(
        sa.String(length=255), nullable=False
    )
    ekn_code: Mapped[str] = mapped_column(
        sa.String(length=100), nullable=False
    )

    shift_start: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )
    shift_end: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),  # pylint: disable=E1102
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),  # pylint: disable=E1102
        onupdate=sa.func.now(),  # pylint: disable=E1102
    )

    products: Mapped[list["Product"]] = relationship(back_populates="batch")
    work_center: Mapped["WorkCenter"] = relationship(back_populates="batches")

    __table_args__ = (
        sa.UniqueConstraint(
            "batch_number", "batch_date", name="uq_batch_number_date"
        ),
        sa.Index("idx_batch_closed", "is_closed"),
        sa.Index("idx_batch_shift_times", "shift_start", "shift_end"),
    )

    def __repr__(self) -> str:
        return f"<Batch(id={self.id}, batch_number={self.batch_number})>"
