from datetime import datetime

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.data.models.base import BaseModel


class WebhookSubscription(BaseModel):
    """
    Модель подписки на вебхуки
    """

    __tablename__ = "webhook_subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    url: Mapped[str] = mapped_column(sa.String(length=2048), nullable=False)
    events: Mapped[list[str]] = mapped_column(ARRAY(sa.String), nullable=False)
    secret_key: Mapped[str] = mapped_column(
        sa.String(length=255), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        server_default=sa.true(), nullable=False
    )

    retry_count: Mapped[int] = mapped_column(
        server_default=sa.text("3"), nullable=False
    )
    timeout: Mapped[int] = mapped_column(
        server_default=sa.text("10"), nullable=False
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

    deliveries: Mapped[list["WebhookDelivery"]] = relationship(
        back_populates="subscription"
    )

    def __repr__(self) -> str:
        return f"<WebhookSubscription(id={self.id}, url='{self.url}')>"


class WebhookDelivery(BaseModel):
    """
    Модель истории доставок вебхуков
    """

    __tablename__ = "webhook_deliveries"

    id: Mapped[int] = mapped_column(primary_key=True)
    subscription_id: Mapped[int] = mapped_column(
        sa.ForeignKey("webhook_subscriptions.id"), nullable=False
    )
    event_type: Mapped[str] = mapped_column(
        sa.String(length=100), nullable=False
    )
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)  # type: ignore[type-arg]
    status: Mapped[str] = mapped_column(sa.String(length=50), nullable=False)
    attempts: Mapped[int] = mapped_column(
        server_default=sa.text("0"), nullable=False
    )
    response_status: Mapped[int | None] = mapped_column(nullable=True)
    response_body: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error_message: Mapped[str | None] = mapped_column(sa.Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        server_default=sa.func.now(),  # pylint: disable=E1102
    )
    delivered_at: Mapped[datetime | None] = mapped_column(
        sa.DateTime(timezone=True), nullable=True
    )

    subscription: Mapped["WebhookSubscription"] = relationship(
        back_populates="deliveries"
    )

    def __repr__(self) -> str:
        return f"<WebhookDelivery(id={self.id}, status='{self.status}')>"
