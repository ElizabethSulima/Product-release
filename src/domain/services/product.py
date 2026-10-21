from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from src.data.models.product import Product
from src.data.repositories.product import ProductRepository


class ProductService:
    """Сервис для бизнес-логики продукции"""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repository = ProductRepository(session)

    async def create_product(self, product: Product) -> Product:
        """Создать продукт"""
        return await self.repository.create(product)

    async def create_products_bulk(
        self, products: list[Product]
    ) -> list[Product]:
        """Массовое создание продуктов"""
        return await self.repository.create_many(products)

    async def get_product_by_id(self, product_id: int) -> Product | None:
        """Получить продукт по ID"""
        return await self.repository.get_by_id(product_id)

    async def get_product_by_unique_code(
        self, unique_code: str
    ) -> Product | None:
        """Найти продукт по уникальному коду"""
        return await self.repository.get_by_unique_code(unique_code)

    async def aggregate_products(
        self, batch_id: int, unique_codes: list[str]
    ) -> int:
        """
        Агрегировать продукцию в партии.

        Args:
            batch_id: ID партии
            unique_codes: список unique_code для агрегации

        Returns:
            количество агрегированных продуктов
        """
        now = datetime.now(UTC)
        return await self.repository.aggregate_by_unique_codes(
            batch_id=batch_id,
            unique_codes=unique_codes,
            aggregated_at=now,
        )

    async def get_products_by_batch_id(self, batch_id: int) -> list[Product]:
        """Получить все продукты партии."""
        return await self.repository.find_by_batch_id(batch_id)

    async def count_products_in_batch(self, batch_id: int) -> int:
        """Подсчитать количество продуктов в партии."""
        return await self.repository.count_by_batch_id(batch_id)
