import asyncio
import logging
from datetime import UTC, datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import async_sessionmaker

from src.core.database import engine
from src.data.models.webhook import WebhookDelivery, WebhookSubscription
from src.tasks.webhooks import send_webhook_delivery

logger = logging.getLogger(__name__)


def trigger_webhook(event_type: str, data: dict[str, Any]) -> None:
    """
    Триггер отправки webhook события всем активным подписчикам
    """
    try:
        asyncio.run(_dispatch_webhook(event_type, data))
    except Exception as exc:
        logger.error(
            "Ошибка диспетчеризации webhook события %s: %s",
            event_type,
            exc,
        )


async def _dispatch_webhook(event_type: str, data: dict[str, Any]) -> None:
    """
    Внутренняя асинхронная логика диспетчеризации
    """
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        payload: dict[str, Any] = {
            "event": event_type,
            "data": data,
            "timestamp": datetime.now(UTC).isoformat(),
        }

        stmt = sa.select(WebhookSubscription).where(
            WebhookSubscription.is_active.is_(True),
            WebhookSubscription.events.any(event_type),  # type: ignore[arg-type]
        )
        result = await session.execute(stmt)
        subscriptions = result.scalars().all()

        if not subscriptions:
            logger.debug("Нет активных подписок на событие %s", event_type)
            return

        delivery_ids: list[int] = []
        for subscription in subscriptions:
            delivery = WebhookDelivery(
                subscription_id=subscription.id,
                event_type=event_type,
                payload=payload,
                status="pending",
                attempts=0,
            )
            session.add(delivery)
            await session.flush()
            delivery_ids.append(delivery.id)

        await session.commit()

        for delivery_id in delivery_ids:
            send_webhook_delivery.delay(delivery_id)

        logger.info(
            "Создано %s доставок для события %s",
            len(delivery_ids),
            event_type,
        )
