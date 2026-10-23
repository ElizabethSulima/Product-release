from datetime import UTC, date, datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.data.models.batch import Batch
from src.data.models.product import Product
from src.data.models.work_center import WorkCenter


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

    async def count_all(self) -> int:
        """Подсчитать общее количество партий"""
        stmt = sa.select(sa.func.count()).select_from(  # pylint: disable=E1102
            Batch
        )
        return await self.session.scalar(stmt) or 0

    async def count_active(self) -> int:
        """Подсчитать количество активных (не закрытых) партий"""
        stmt = (
            sa.select(sa.func.count())  # pylint: disable=E1102
            .select_from(Batch)
            .where(Batch.is_closed.is_(False))
        )
        return await self.session.scalar(stmt) or 0

    async def count_closed(self) -> int:
        """Подсчитать количество закрытых партий"""
        stmt = (
            sa.select(sa.func.count())  # pylint: disable=E1102
            .select_from(Batch)
            .where(Batch.is_closed.is_(True))
        )
        return await self.session.scalar(stmt) or 0

    async def count_created_today(self) -> int:
        """Подсчитать количество партий, созданных сегодня"""

        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            sa.select(sa.func.count())  # pylint: disable=E1102
            .select_from(Batch)
            .where(Batch.created_at >= today_start)
        )
        return await self.session.scalar(stmt) or 0

    async def count_closed_today(self) -> int:
        """Подсчитать количество партий, закрытых сегодня"""

        today_start = datetime.now(UTC).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        stmt = (
            sa.select(sa.func.count())  # pylint: disable=E1102
            .select_from(Batch)
            .where(
                Batch.closed_at.isnot(None),
                Batch.closed_at >= today_start,
            )
        )
        return await self.session.scalar(stmt) or 0

    async def count_by_shift(self) -> dict[str, int]:
        """Подсчитать количество партий по сменам"""
        stmt = sa.select(
            Batch.shift, sa.func.count(Batch.id)  # pylint: disable=E1102
        ).group_by(Batch.shift)
        result = await self.session.execute(stmt)
        return {str(row[0] or "unknown"): int(row[1]) for row in result.all()}

    async def count_by_filters(
        self,
        is_closed: bool | None = None,
        batch_number: int | None = None,
        batch_date: date | None = None,
        work_center_id: str | None = None,
        shift: str | None = None,
    ) -> int:
        """Подсчитать количество партий с фильтрами"""
        stmt = sa.select(sa.func.count()).select_from(  # pylint: disable=E1102
            Batch
        )

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

        return await self.session.scalar(stmt) or 0

    async def top_work_centers(self, limit: int = 5) -> list[dict[str, Any]]:
        """Топ рабочих центров по количеству продукции"""

        stmt = (
            sa.select(
                WorkCenter.id,
                WorkCenter.identifier,
                WorkCenter.name,
                sa.func.count(  # pylint: disable=E1102
                    sa.distinct(Batch.id)
                ).label("batches_count"),
                sa.func.count(Product.id).label(  # pylint: disable=E1102
                    "products_count"
                ),
            )
            .join(Batch, Batch.work_center_id == WorkCenter.id)
            .join(Product, Product.batch_id == Batch.id, isouter=True)
            .group_by(WorkCenter.id, WorkCenter.identifier, WorkCenter.name)
            .order_by(sa.text("products_count DESC"))
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return [
            {
                "id": str(row.id),
                "identifier": row.identifier,
                "name": row.name,
                "batches_count": int(row.batches_count),
                "products_count": int(row.products_count),
            }
            for row in result.all()
        ]
