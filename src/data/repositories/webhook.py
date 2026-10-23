from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.webhook import WebhookDelivery, WebhookSubscription


class WebhookRepository:
    """Репозиторий для работы с подписками и доставками вебхуков"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_subscription(
        self,
        url: str,
        events: list[str],
        secret_key: str,
        retry_count: int = 3,
        timeout: int = 10,
    ) -> WebhookSubscription:
        """Создать новую подписку"""
        subscription = WebhookSubscription(
            url=url,
            events=events,
            secret_key=secret_key,
            retry_count=retry_count,
            timeout=timeout,
        )
        self.session.add(subscription)
        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def get_subscription_by_id(
        self, subscription_id: int
    ) -> WebhookSubscription | None:
        """Получить подписку по ID"""
        return await self.session.get(WebhookSubscription, subscription_id)

    async def list_subscriptions(
        self, offset: int = 0, limit: int = 100
    ) -> tuple[list[WebhookSubscription], int]:
        """Получить список подписок с общим количеством"""
        count_stmt = sa.select(
            sa.func.count()  # pylint: disable=E1102
        ).select_from(WebhookSubscription)
        total = await self.session.scalar(count_stmt) or 0

        list_stmt = (
            sa.select(WebhookSubscription)
            .order_by(WebhookSubscription.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(list_stmt)
        subscriptions = list(result.scalars().all())

        return subscriptions, total

    async def update_subscription(
        self, subscription_id: int, update_data: dict[str, Any]
    ) -> WebhookSubscription | None:
        """Обновить подписку"""
        subscription = await self.get_subscription_by_id(subscription_id)
        if subscription is None:
            return None

        for key, value in update_data.items():
            setattr(subscription, key, value)

        await self.session.flush()
        await self.session.refresh(subscription)
        return subscription

    async def delete_subscription(self, subscription_id: int) -> bool:
        """Удалить подписку (каскадно удалятся все доставки)"""
        subscription = await self.get_subscription_by_id(subscription_id)
        if subscription is None:
            return False

        await self.session.delete(subscription)
        await self.session.flush()
        return True

    async def list_deliveries_by_subscription(
        self, subscription_id: int, offset: int = 0, limit: int = 100
    ) -> tuple[list[WebhookDelivery], int]:
        """Получить историю доставок для подписки"""
        count_stmt = (
            sa.select(sa.func.count())  # pylint: disable=E1102
            .select_from(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == subscription_id)
        )
        total = await self.session.scalar(count_stmt) or 0

        list_stmt = (
            sa.select(WebhookDelivery)
            .where(WebhookDelivery.subscription_id == subscription_id)
            .order_by(WebhookDelivery.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.session.execute(list_stmt)
        deliveries = list(result.scalars().all())

        return deliveries, total

    async def get_active_subscriptions_by_event(
        self, event_type: str
    ) -> list[WebhookSubscription]:
        """Получить все активные подписки на конкретный тип события"""
        stmt = sa.select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True),
            WebhookSubscription.events.any(event_type),  # type: ignore[arg-type]
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
