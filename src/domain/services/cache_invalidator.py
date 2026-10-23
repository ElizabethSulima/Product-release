from src.core.cache import cache


async def invalidate_dashboard_cache() -> None:
    """Инвалидация общей статистики"""
    await cache.delete("dashboard_stats")


async def invalidate_batches_list_cache() -> None:
    """Инвалидация всех вариантов списка партий (с разными фильтрами)"""
    await cache.delete_pattern("batches_list:*")


async def invalidate_batch_cache(batch_id: int) -> None:
    """Инвалидация кэша конкретной партии"""
    await cache.delete(f"batch_detail:{batch_id}")
    await cache.delete(f"batch_statistics:{batch_id}")


async def on_batch_created() -> None:
    """Вызывается при создании партии"""
    await invalidate_dashboard_cache()
    await invalidate_batches_list_cache()


async def on_batch_updated(batch_id: int) -> None:
    """Вызывается при обновлении партии"""
    await invalidate_batch_cache(batch_id)
    await invalidate_dashboard_cache()
    await invalidate_batches_list_cache()


async def on_batch_deleted(batch_id: int) -> None:
    """Вызывается при удалении партии"""
    await invalidate_batch_cache(batch_id)
    await invalidate_dashboard_cache()
    await invalidate_batches_list_cache()


async def on_product_aggregated(batch_id: int) -> None:
    """Вызывается при агрегации продукции"""
    await invalidate_batch_cache(batch_id)
    await invalidate_dashboard_cache()
