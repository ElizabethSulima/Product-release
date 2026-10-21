from datetime import datetime
from typing import Any, cast

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.product import Product


class ProductRepository:
    """Репозиторий для работы с продукцией"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, product: Product) -> Product:
        """Создать продукт"""
        self.session.add(product)
        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def create_many(self, products: list[Product]) -> list[Product]:
        """Массовое создание продуктов"""
        self.session.add_all(products)
        await self.session.flush()
        for product in products:
            await self.session.refresh(product)
        return products

    async def get_by_id(self, product_id: int) -> Product | None:
        """Получить продукт по ID"""
        return await self.session.get(Product, product_id)

    async def get_by_unique_code(self, unique_code: str) -> Product | None:
        """Найти продукт по уникальному коду"""
        stmt = sa.select(Product).where(Product.unique_code == unique_code)
        return cast(Product | None, await self.session.scalar(stmt))

    async def update(self, product_id: int, **data: Any) -> Product | None:
        """Обновить продукт"""
        product = await self.get_by_id(product_id)
        if product is None:
            return None

        for key, value in data.items():
            setattr(product, key, value)

        await self.session.flush()
        await self.session.refresh(product)
        return product

    async def delete(self, product_id: int) -> bool:
        """Удалить продукт"""
        product = await self.get_by_id(product_id)
        if product is None:
            return False

        await self.session.delete(product)
        await self.session.flush()
        return True

    async def find_by_batch_id(self, batch_id: int) -> list[Product]:
        """Найти все продукты по batch_id"""
        stmt = sa.select(Product).where(Product.batch_id == batch_id)
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def aggregate_by_unique_codes(
        self, batch_id: int, unique_codes: list[str], aggregated_at: datetime
    ) -> int:
        """
        Агрегировать продукцию по списку unique_code
        """
        stmt = sa.select(Product).where(
            Product.batch_id == batch_id,
            Product.unique_code.in_(unique_codes),
            Product.is_aggregated.is_(False),
        )
        result = await self.session.scalars(stmt)
        products = list(result.all())

        for product in products:
            product.is_aggregated = True
            product.aggregated_at = aggregated_at

        await self.session.flush()
        return len(products)

    async def count_by_batch_id(self, batch_id: int) -> int:
        """Подсчитать количество продуктов в партии"""
        stmt = (
            sa.select(sa.func.count())  # pylint: disable=E1102
            .select_from(Product)
            .where(Product.batch_id == batch_id)
        )
        return await self.session.scalar(stmt) or 0
