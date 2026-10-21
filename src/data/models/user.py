from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from src.data.models.base import BaseModel


class User(BaseModel):
    """
    Модель пользователя
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    external_id: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Внешний идентификатор из внешней системы",
    )
    name: Mapped[str] = mapped_column(
        sa.String(255),
        unique=True,
        index=True,
        nullable=False,
        comment="Внешний идентификатор из внешней системы",
    )
    email: Mapped[str] = mapped_column(unique=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),  # pylint: disable=E1102
    )
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),  # pylint: disable=E1102
        onupdate=sa.func.now(),  # pylint: disable=E1102
    )

    def __repr__(self) -> str:
        return f"<User(id={self.id}, external_id={self.external_id}, name={self.name})>"
