from datetime import date
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.batch import Batch


class BatchRepository:
    """Репозиторий для работы с производственными партиями"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, batch: Batch) -> Batch:
        """
        Создать партию
        """
        self.session.add(batch)
        await self.session.flush()
        await self.session.refresh(batch)
        return batch

    async def create_many(self, batches: list[Batch]) -> list[Batch]:
        """
        Массовое создание партий
        """
        self.session.add_all(batches)
        await self.session.flush()
        for batch in batches:
            await self.session.refresh(batch)
        return batches

    async def get_by_id(
        self, batch_id: int, load_products: bool = False
    ) -> Batch | None:
        """
        Получить партию по ID
        """
        if load_products:
            stmt = (
                sa.select(Batch)
                .options(selectinload(Batch.products))
                .where(Batch.id == batch_id)
            )
            return cast(Batch | None, await self.session.scalar(stmt))
        return await self.session.get(Batch, batch_id)

    async def update(self, batch_id: int, **data: Any) -> Batch | None:
        """
        Обновить партию
        """
        batch = await self.get_by_id(batch_id)
        if batch is None:
            return None

        for key, value in data.items():
            setattr(batch, key, value)

        await self.session.flush()
        await self.session.refresh(batch)
        return batch

    async def delete(self, batch_id: int) -> bool:
        """
        Удалить партию
        """
        batch = await self.get_by_id(batch_id)
        if batch is None:
            return False

        await self.session.delete(batch)
        await self.session.flush()
        return True

    async def find_by_batch_number_and_date(
        self, batch_number: int, batch_date: date
    ) -> Batch | None:
        """
        Найти партию по уникальному ключу (batch_number, batch_date)
        """
        stmt = sa.select(Batch).where(
            Batch.batch_number == batch_number,
            Batch.batch_date == batch_date,
        )
        return cast(Batch | None, await self.session.scalar(stmt))

    async def find_by_filters(
        self,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: str | None = None,
        shift: str | None = None,
        offset: int = 0,
        limit: int = 20,
    ) -> list[Batch]:
        """
        Поиск партий с фильтрацией и пагинацией
        """
        stmt = sa.select(Batch)

        if is_closed is not None:
            stmt = stmt.where(Batch.is_closed == is_closed)
        if batch_number is not None:
            stmt = stmt.where(Batch.batch_number == batch_number)
        if batch_date is not None:
            stmt = stmt.where(Batch.batch_date == batch_date)
        if work_center_id is not None:
            stmt = stmt.where(Batch.work_center_id == work_center_id)
        if shift is not None:
            stmt = stmt.where(Batch.shift == shift)

        stmt = (
            stmt.order_by(Batch.created_at.desc()).offset(offset).limit(limit)
        )

        result = await self.session.scalars(stmt)
        return list(result.all())
