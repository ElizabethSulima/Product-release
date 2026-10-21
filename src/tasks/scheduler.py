import asyncio
from datetime import UTC, datetime, timedelta

from sqlalchemy import update

from src.celery_app import celery_app
from src.data.models.batch import Batch
from src.storage.minio_service import minio_service
from src.tasks.aggregation import AsyncSessionLocal


@celery_app.task  # type: ignore[untyped-decorator]
def auto_close_expired_batches() -> None:
    """Закрывает партии, у которых shift_end < now()"""

    async def _close() -> None:
        now = datetime.now(UTC)
        async with AsyncSessionLocal() as session:
            stmt = (
                update(Batch)
                .where(Batch.shift_end < now, Batch.is_closed.is_(False))
                .values(is_closed=True, closed_at=now)
            )
            await session.execute(stmt)
            await session.commit()

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


@celery_app.task  # type: ignore[untyped-decorator]
def retry_failed_webhooks() -> None:
    """Повторная отправка неудачных webhook delivery"""
    pass
