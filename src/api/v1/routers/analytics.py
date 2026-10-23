from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from src.api.v1.schemas.analytic import (
    CompareBatchesRequest,
    CompareBatchesResponse,
)
from src.core.database import AsyncSessionDependency
from src.core.limiter import limiter
from src.domain.services.analytics import AnalyticsService
from src.domain.services.batch import BatchService

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/dashboard",
    summary="Статистика дашборда (из кэша Redis)",
)
@limiter.limit("20 per minute")
async def get_dashboard(
    request: Request,
    session: AsyncSessionDependency,
) -> dict[str, Any]:
    service = AnalyticsService(session)
    return await service.get_dashboard_statistics()


@router.get(
    "/batches/{batch_id}/statistics",
    summary="Статистика конкретной партии",
)
@limiter.limit("30 per minute")
async def get_batch_statistics(
    request: Request,
    batch_id: int,
    session: AsyncSessionDependency,
) -> dict[str, Any]:
    """Получить статистику партии (TTL: 5 минут)"""
    service = BatchService(session)
    stats = await service.get_batch_statistics_cached(batch_id)
    if stats is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Партия не найдена",
        )
    return stats


@router.post(
    "/compare-batches",
    response_model=CompareBatchesResponse,
    summary="Сравнение партий",
)
@limiter.limit("30 per minute")
async def compare_batches(
    request: Request,
    payload: CompareBatchesRequest,
    session: AsyncSessionDependency,
) -> CompareBatchesResponse:
    service = BatchService(session)

    comparison: list[dict[str, Any]] = []
    for batch_id in payload.batch_ids:
        stats = await service.get_batch_statistics_cached(batch_id)
        if stats is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Партия с id {batch_id} не найдена",
            )

        comparison.append(
            {
                "batch_id": stats["batch_info"]["id"],
                "batch_number": stats["batch_info"]["batch_number"],
                "total_products": stats["production_stats"]["total_products"],
                "aggregated": stats["production_stats"]["aggregated"],
                "rate": stats["production_stats"]["aggregation_rate"],
                "duration_hours": stats["timeline"]["shift_duration_hours"],
                "products_per_hour": stats["timeline"]["products_per_hour"],
            }
        )
    total_items = len(comparison)
    avg_rate = (
        round(sum(c["rate"] for c in comparison) / total_items, 2)
        if total_items > 0
        else 0.0
    )
    avg_pph = (
        round(sum(c["products_per_hour"] for c in comparison) / total_items, 2)
        if total_items > 0
        else 0.0
    )

    return CompareBatchesResponse(
        batches=comparison,
        average={
            "aggregation_rate": avg_rate,
            "products_per_hour": avg_pph,
        },
    )
