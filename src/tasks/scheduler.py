import asyncio
import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from src.celery_app import celery_app
from src.core.webhook_dispatcher import trigger_webhook
from src.data.models.batch import Batch
from src.data.models.webhook import WebhookDelivery, WebhookSubscription
from src.storage.minio_service import minio_service
from src.tasks.aggregation import AsyncSessionLocal
from src.tasks.webhooks import send_webhook_delivery

logger = logging.getLogger(__name__)


@celery_app.task  # type: ignore[untyped-decorator]
def auto_close_expired_batches() -> None:
    """Закрывает партии, у которых shift_end < now()"""

    async def _close() -> int:
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as session:
            select_stmt = select(Batch).where(
                Batch.shift_end < now, Batch.is_closed.is_(False)
            )
            result = await session.execute(select_stmt)
            batches_to_close = result.scalars().all()

            stmt = (
                update(Batch)
                .where(Batch.shift_end < now, Batch.is_closed.is_(False))
                .values(is_closed=True, closed_at=now)
            )
            await session.execute(stmt)
            await session.commit()

            for batch in batches_to_close:
                trigger_webhook(
                    event_type="batch_closed",
                    data={
                        "id": batch.id,
                        "batch_number": str(batch.batch_number),
                        "closed_at": now.isoformat(),
                    },
                )

        return len(batches_to_close)

    asyncio.run(_close())


@celery_app.task  # type: ignore[untyped-decorator]
def cleanup_old_files() -> None:
    """Удаляет файлы старше 30 дней из MinIO"""

    buckets = ["reports", "exports", "imports"]
    threshold = datetime.now(UTC) - timedelta(days=30)

    for bucket in buckets:
        files = minio_service.list_files(bucket=bucket)
        for f in files:
            if f["last_modified"]:
                last_mod = datetime.fromisoformat(
                    f["last_modified"].replace("Z", "+00:00")
                )
                if last_mod < threshold:
                    minio_service.delete_file(
                        bucket=bucket, object_name=f["object_name"]
                    )


@celery_app.task  # type: ignore[untyped-decorator]
def update_cached_statistics() -> None:
    """Обновляет кэшированную статистику в Redis"""
    # from src.core.redis_client import redis_client
    # asyncio.run(_update_stats())
    pass


async def _retry_failed() -> dict[str, int]:
    """Внутренняя асинхронная логика"""

    async with AsyncSessionLocal() as session:
        stmt = (
            select(WebhookDelivery)
            .options(selectinload(WebhookDelivery.subscription))
            .where(
                WebhookDelivery.status == "failed",
                WebhookDelivery.attempts < WebhookSubscription.retry_count,
            )
            .join(
                WebhookSubscription,
                WebhookDelivery.subscription_id == WebhookSubscription.id,
            )
            .where(WebhookSubscription.is_active.is_(True))
        )
        result = await session.execute(stmt)
        failed_deliveries = result.scalars().all()

        retried_count = 0
        for delivery in failed_deliveries:
            delivery.status = "pending"
            delivery.error_message = None
            await session.flush()
            send_webhook_delivery.delay(delivery.id)
            retried_count += 1

        await session.commit()

    logger.info(
        "Повторно отправлено %s проваленных webhook доставок", retried_count
    )
    return {"retried": retried_count}


@celery_app.task  # type: ignore[untyped-decorator]
def retry_failed_webhooks() -> dict[str, int]:
    """
    Повторная отправка неудачных webhook доставок.
    Находит все доставки со статусом 'failed', у которых ещё есть попытки,
    и ставит их в очередь заново.

    Запускается: каждые 15 минут через Celery Beat.
    """
    return asyncio.run(_retry_failed())
