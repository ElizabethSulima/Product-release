import asyncio
import logging
from typing import Any

from celery.app.task import Task
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.celery_app import celery_app
from src.core.config import config
from src.data.models.product import Product
from src.domain.services.cache_invalidator import on_product_aggregated

logger = logging.getLogger(__name__)

engine = create_async_engine(
    config.database_url,
    pool_size=config.TASK_POOL_SIZE,
    max_overflow=config.TASK_MAX_OVERFLOW,
)
AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False)


@celery_app.task(bind=True, max_retries=3)  # type: ignore[untyped-decorator]
def aggregate_products_batch(
    self: Task, batch_id: int, unique_codes: list[str]
) -> dict[str, Any]:
    """
    Асинхронная массовая агрегация продукции
    """
    chunk_size = 100

    try:
        result = asyncio.run(
            _process_aggregation(batch_id, unique_codes, chunk_size, self)
        )
        return result

    except Exception as exc:
        logger.error("Ошибка агрегации партии %s: %s", batch_id, exc)
        raise self.retry(exc=exc, countdown=60)


async def _process_aggregation(
    batch_id: int,
    unique_codes: list[str],
    chunk_size: int,
    task_instance: Task,
) -> dict[str, Any]:
    """
    Внутренняя асинхронная логика агрегации
    """
    aggregated_count = 0
    failed_count = 0
    errors: list[dict[str, str]] = []
    total = len(unique_codes)

    async with AsyncSessionLocal() as session:
        for i in range(0, total, chunk_size):
            chunk = unique_codes[i : i + chunk_size]

            stmt = select(Product).where(
                Product.batch_id == batch_id, Product.unique_code.in_(chunk)
            )
            result = await session.execute(stmt)
            products = result.scalars().all()

            found_codes = {p.unique_code: p for p in products}

            codes_to_update: list[str] = []
            for code in chunk:
                product = found_codes.get(code)

                if not product:
                    failed_count += 1
                    errors.append(
                        {"code": code, "reason": "not found in batch"}
                    )
                elif product.is_aggregated:
                    failed_count += 1
                    errors.append(
                        {"code": code, "reason": "already aggregated"}
                    )
                else:
                    codes_to_update.append(code)

            if codes_to_update:
                await session.execute(
                    update(Product)
                    .where(Product.unique_code.in_(codes_to_update))
                    .values(is_aggregated=True)
                )
                await session.commit()
                await on_product_aggregated(batch_id)
                aggregated_count += len(codes_to_update)

            current_processed = i + len(chunk)
            progress = int((current_processed / total) * 100)

            task_instance.update_state(
                state="PROGRESS",
                meta={
                    "current": current_processed,
                    "total": total,
                    "progress": progress,
                },
            )

    return {
        "success": failed_count == 0,
        "total": total,
        "aggregated": aggregated_count,
        "failed": failed_count,
        "errors": errors,
    }
