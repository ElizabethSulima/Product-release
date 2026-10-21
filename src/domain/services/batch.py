from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.batch import Batch
from src.data.repositories.batch import BatchRepository


class BatchService:
    """Сервис для бизнес-логики производственных партий"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = BatchRepository(session)

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
