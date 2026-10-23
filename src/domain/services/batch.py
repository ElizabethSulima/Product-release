import hashlib
from datetime import UTC, date, datetime, timedelta
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import cache
from src.data.models.batch import Batch
from src.data.repositories.batch import BatchRepository
from src.data.repositories.product import ProductRepository


class BatchService:
    """Сервис для бизнес-логики производственных партий"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BatchRepository(session)
        self.product_repository = ProductRepository(session)

    async def create_batch(self, batch: Batch) -> Batch:
        """Создать партию"""
        return await self.repository.create(batch)

    async def create_batches_bulk(self, batches: list[Batch]) -> list[Batch]:
        """Массовое создание партий"""
        return await self.repository.create_many(batches)

    async def get_batch_by_id(
        self, batch_id: int, load_products: bool = False
    ) -> Batch | None:
        """Получить партию по ID"""
        return await self.repository.get_by_id(
            batch_id, load_products=load_products
        )

    async def update_batch(
        self, batch_id: int, update_data: dict[str, Any]
    ) -> Batch | None:
        """
        Обновить партию.

        Автоматически управляет closed_at в зависимости от is_closed:
        - Если is_closed=True → closed_at = now()
        - Если is_closed=False → closed_at = None
        """
        if "is_closed" in update_data:
            new_is_closed = update_data["is_closed"]
            if new_is_closed:
                update_data["closed_at"] = datetime.now(UTC)
            else:
                update_data["closed_at"] = None

        return await self.repository.update(batch_id, **update_data)

    async def delete_batch(self, batch_id: int) -> bool:
        """Удалить партию"""
        return await self.repository.delete(batch_id)

    async def list_batches(
        self,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: str | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Batch]:
        """Получить список партий с фильтрацией"""
        return await self.repository.find_by_filters(
            is_closed=is_closed,
            batch_number=batch_number,
            batch_date=batch_date,
            work_center_id=work_center_id,
            shift=shift,
            offset=offset,
            limit=limit,
        )

    async def list_batches_cached(
        self,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: str | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Список партий с кэшированием (TTL: 60 сек)"""
        params_str = f"{is_closed}_{batch_number}_{batch_date}_{work_center_id}_{shift}_{offset}_{limit}"
        params_hash = hashlib.md5(params_str.encode()).hexdigest()
        cache_key = f"batches_list:{params_hash}"

        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            return cast(list[dict[str, Any]], cached_data)

        batches = await self.repository.find_by_filters(
            is_closed=is_closed,
            batch_number=batch_number,
            batch_date=batch_date,
            work_center_id=work_center_id,
            shift=shift,
            offset=offset,
            limit=limit,
        )
        serialized = [
            {
                "id": b.id,
                "batch_number": b.batch_number,
                "batch_date": (
                    b.batch_date.isoformat() if b.batch_date else None
                ),
                "nomenclature": b.nomenclature,
                "is_closed": b.is_closed,
                "work_center_id": b.work_center_id,
                "shift": b.shift,
                "team": b.team,
            }
            for b in batches
        ]

        await cache.set(cache_key, serialized, ttl=60)
        return serialized

    async def get_batch_with_products_cached(
        self, batch_id: int
    ) -> dict[str, Any] | None:
        """Детали партии с продуктами (TTL: 600 сек)"""
        cache_key = f"batch_detail:{batch_id}"

        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            return cast(dict[str, Any] | None, cached_data)

        batch = await self.repository.get_by_id(batch_id, load_products=True)
        if batch is None:
            return None

        result = {
            "id": batch.id,
            "batch_number": batch.batch_number,
            "batch_date": (
                batch.batch_date.isoformat() if batch.batch_date else None
            ),
            "nomenclature": batch.nomenclature,
            "is_closed": batch.is_closed,
            "work_center_id": batch.work_center_id,
            "shift": batch.shift,
            "team": batch.team,
            "products": (
                [
                    {
                        "id": p.id,
                        "unique_code": p.unique_code,
                        "is_aggregated": p.is_aggregated,
                    }
                    for p in batch.products
                ]
                if batch.products
                else []
            ),
        }

        await cache.set(cache_key, result, ttl=600)
        return result

    async def get_batch_statistics_cached(
        self, batch_id: int
    ) -> dict[str, Any] | None:
        """
        Расширенная статистика партии (TTL: 300 сек).
        Включает batch_info, production_stats, timeline, team_performance.
        """
        cache_key = f"batch_statistics:{batch_id}"

        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            return cast(dict[str, Any] | None, cached_data)

        batch = await self.repository.get_by_id(batch_id)
        if batch is None:
            return None

        total_products = await self.product_repository.count_by_batch_id(
            batch_id
        )
        aggregated = (
            await self.product_repository.count_by_batch_id_aggregated(
                batch_id
            )
        )
        remaining = total_products - aggregated
        rate = (
            round((aggregated / total_products * 100), 2)
            if total_products > 0
            else 0.0
        )

        now = datetime.now(UTC)
        shift_duration_hours = 0.0
        elapsed_hours = 0.0
        products_per_hour = 0.0
        estimated_completion: str | None = None

        if batch.shift_start and batch.shift_end:
            shift_duration_hours = round(
                (batch.shift_end - batch.shift_start).total_seconds() / 3600, 2
            )
            elapsed_hours = round(
                max(0, (now - batch.shift_start).total_seconds() / 3600), 2
            )
            elapsed_hours = min(elapsed_hours, shift_duration_hours)

            if elapsed_hours > 0:
                products_per_hour = round(aggregated / elapsed_hours, 2)

            if products_per_hour > 0 and remaining > 0:
                hours_to_complete = remaining / products_per_hour
                completion_time = now + timedelta(hours=hours_to_complete)
                estimated_completion = completion_time.isoformat()

        efficiency_score = 0.0
        if (
            shift_duration_hours > 0
            and total_products > 0
            and products_per_hour > 0
        ):
            planned_speed = total_products / shift_duration_hours
            efficiency_score = round(
                (products_per_hour / planned_speed) * 100, 2
            )

        result: dict[str, Any] = {
            "batch_info": {
                "id": batch.id,
                "batch_number": batch.batch_number,
                "batch_date": (
                    batch.batch_date.isoformat() if batch.batch_date else None
                ),
                "is_closed": batch.is_closed,
            },
            "production_stats": {
                "total_products": total_products,
                "aggregated": aggregated,
                "remaining": remaining,
                "aggregation_rate": rate,
            },
            "timeline": {
                "shift_duration_hours": shift_duration_hours,
                "elapsed_hours": elapsed_hours,
                "products_per_hour": products_per_hour,
                "estimated_completion": estimated_completion,
            },
            "team_performance": {
                "team": batch.team,
                "avg_products_per_hour": products_per_hour,
                "efficiency_score": efficiency_score,
            },
        }

        await cache.set(cache_key, result, ttl=300)
        return result
