from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.webhook import WebhookDelivery, WebhookSubscription
from src.data.repositories.webhook import WebhookRepository


class WebhookService:
    """Сервис для работы с подписками и доставками вебхуков"""

    def __init__(self, session: AsyncSession) -> None:
        self.repository = WebhookRepository(session)

    async def create_subscription(
        self,
        url: str,
        events: list[str],
        secret_key: str,
        retry_count: int = 3,
        timeout: int = 10,
    ) -> WebhookSubscription:
        """Создать подписку"""
        return await self.repository.create_subscription(
            url=url,
            events=events,
            secret_key=secret_key,
            retry_count=retry_count,
            timeout=timeout,
        )

    async def get_subscription(
        self, subscription_id: int
    ) -> WebhookSubscription | None:
        """Получить подписку по ID"""
        return await self.repository.get_subscription_by_id(subscription_id)

    async def list_subscriptions(
        self, offset: int = 0, limit: int = 100
    ) -> tuple[list[WebhookSubscription], int]:
        """Получить список подписок"""
        return await self.repository.list_subscriptions(
            offset=offset, limit=limit
        )

    async def update_subscription(
        self, subscription_id: int, update_data: dict[str, Any]
    ) -> WebhookSubscription | None:
        """Обновить подписку"""
        return await self.repository.update_subscription(
            subscription_id, update_data
        )

    async def delete_subscription(self, subscription_id: int) -> bool:
        """Удалить подписку"""
        return await self.repository.delete_subscription(subscription_id)

    async def list_deliveries(
        self, subscription_id: int, offset: int = 0, limit: int = 100
    ) -> tuple[list[WebhookDelivery], int]:
        """Получить историю доставок"""
        return await self.repository.list_deliveries_by_subscription(
            subscription_id, offset=offset, limit=limit
        )
