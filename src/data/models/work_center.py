from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models.base import BaseModel

if TYPE_CHECKING:
    from .batch import Batch


class WorkCenter(BaseModel):
    """
    Модель рабочего центра
    """

    __tablename__ = "work_centers"

    id: Mapped[int] = mapped_column(primary_key=True)
    identifier: Mapped[str] = mapped_column(
        sa.String(length=255), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(sa.String(length=255), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),  # pylint: disable=E1102
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),  # pylint: disable=E1102
        onupdate=sa.func.now(),  # pylint: disable=E1102
    )

    batches: Mapped[list[Batch]] = relationship(back_populates="work_center")

    def __repr__(self) -> str:
        return f"<WorkCenter(id={self.id}, identifier='{self.identifier}')>"
