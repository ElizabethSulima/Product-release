from datetime import UTC, datetime
from typing import Any, cast

from sqlalchemy.ext.asyncio import AsyncSession

from src.core.cache import cache
from src.data.repositories.batch import BatchRepository
from src.data.repositories.product import ProductRepository


class AnalyticsService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.batch_repo = BatchRepository(session)
        self.product_repo = ProductRepository(session)

    async def get_dashboard_statistics(self) -> dict[str, Any]:
        """
        Расширенная статистика дашборда (TTL: 300 сек)
        """
        cache_key = "dashboard_stats"

        cached_data = await cache.get(cache_key)
        if cached_data is not None:
            return cast(dict[str, Any], cached_data)

        total_batches = await self.batch_repo.count_all()
        active_batches = await self.batch_repo.count_active()
        closed_batches = await self.batch_repo.count_closed()
        total_products = await self.product_repo.count_all()
        aggregated_products = await self.product_repo.count_aggregated()
        aggregation_rate = (
            round((aggregated_products / total_products * 100), 2)
            if total_products > 0
            else 0.0
        )

        batches_created_today = await self.batch_repo.count_created_today()
        batches_closed_today = await self.batch_repo.count_closed_today()
        products_added_today = (
            await self.product_repo.count_products_added_today()
        )
        products_aggregated_today = (
            await self.product_repo.count_aggregated_today()
        )

        batches_by_shift = await self.batch_repo.count_by_shift()
        products_by_shift = await self.product_repo.count_products_by_shift()

        by_shift: dict[str, dict[str, int]] = {}
        all_shifts = set(batches_by_shift.keys()) | set(
            products_by_shift.keys()
        )
        for shift in all_shifts:
            by_shift[shift] = {
                "batches": batches_by_shift.get(shift, 0),
                "products": products_by_shift.get(shift, {}).get(
                    "products", 0
                ),
                "aggregated": products_by_shift.get(shift, {}).get(
                    "aggregated", 0
                ),
            }

        top_wc_raw = await self.batch_repo.top_work_centers(limit=5)
        wc_ids = [int(wc["id"]) for wc in top_wc_raw]
        aggregated_by_wc = (
            await self.product_repo.count_aggregated_by_work_center(wc_ids)
        )

        top_work_centers: list[dict[str, Any]] = []
        for wc in top_wc_raw:
            wc_id = int(wc["id"])
            products_count = wc["products_count"]
            aggregated_count = aggregated_by_wc.get(wc_id, 0)
            wc_rate = (
                round((aggregated_count / products_count * 100), 2)
                if products_count > 0
                else 0.0
            )
            top_work_centers.append(
                {
                    "id": wc["identifier"],
                    "name": wc["name"],
                    "batches_count": wc["batches_count"],
                    "products_count": products_count,
                    "aggregation_rate": wc_rate,
                }
            )

        result: dict[str, Any] = {
            "summary": {
                "total_batches": total_batches,
                "active_batches": active_batches,
                "closed_batches": closed_batches,
                "total_products": total_products,
                "aggregated_products": aggregated_products,
                "aggregation_rate": aggregation_rate,
            },
            "today": {
                "batches_created": batches_created_today,
                "batches_closed": batches_closed_today,
                "products_added": products_added_today,
                "products_aggregated": products_aggregated_today,
            },
            "by_shift": by_shift,
            "top_work_centers": top_work_centers,
            "cached_at": datetime.now(UTC).isoformat(),
        }

        await cache.set(cache_key, result, ttl=300)
        return result
