from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.anyio


@patch(
    "src.api.v1.routers.analytics.AnalyticsService.get_dashboard_statistics"
)
async def test_get_dashboard_success(
    mock_get_dashboard: AsyncMock,
    client: AsyncClient,
    mock_dashboard_stats: dict,
):
    """Тест успешного получения статистики дашборда"""
    mock_get_dashboard.return_value = mock_dashboard_stats

    response = await client.get("/api/v1/analytics/dashboard")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["total_batches"] == 150
    assert data["active_batches"] == 12
    assert data["overall_aggregation_rate"] == 97.0
    assert len(data["top_performing_work_centers"]) == 2

    mock_get_dashboard.assert_awaited_once()


@patch("src.api.v1.routers.analytics.BatchService.get_batch_statistics_cached")
async def test_get_batch_statistics_success(
    mock_get_stats: AsyncMock, client: AsyncClient, mock_batch_stats: dict
):
    """Тест успешного получения статистики конкретной партии"""
    mock_get_stats.return_value = mock_batch_stats

    response = await client.get("/api/v1/analytics/batches/1/statistics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["batch_info"]["id"] == 1
    assert data["batch_info"]["batch_number"] == 88888
    assert data["production_stats"]["total_products"] == 1500
    assert data["production_stats"]["aggregation_rate"] == 96.67
    assert data["timeline"]["shift_duration_hours"] == 8.0

    mock_get_stats.assert_awaited_once_with(1)


@patch("src.api.v1.routers.analytics.BatchService.get_batch_statistics_cached")
async def test_get_batch_statistics_not_found(
    mock_get_stats: AsyncMock, client: AsyncClient
):
    """Тест получения статистики для несуществующей партии"""
    mock_get_stats.return_value = None
    response = await client.get("/api/v1/analytics/batches/999999/statistics")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Партия не найдена"


@patch("src.api.v1.routers.analytics.BatchService.get_batch_statistics_cached")
async def test_compare_batches_success(
    mock_get_stats: AsyncMock,
    client: AsyncClient,
    mock_batch_stats: dict,
    mock_batch_stats_2: dict,
):
    """Тест успешного сравнения двух партий с проверкой логики агрегации"""

    def side_effect(batch_id: int):
        if batch_id == 1:
            return mock_batch_stats
        elif batch_id == 2:
            return mock_batch_stats_2
        return None

    mock_get_stats.side_effect = side_effect

    payload = {"batch_ids": [1, 2]}
    response = await client.post(
        "/api/v1/analytics/compare-batches", json=payload
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "batches" in data
    assert "average" in data
    assert len(data["batches"]) == 2

    batch_1 = data["batches"][0]
    assert batch_1["batch_id"] == 1
    assert batch_1["batch_number"] == 88888
    assert batch_1["total_products"] == 1500
    assert batch_1["aggregated"] == 1450
    assert batch_1["rate"] == 96.67
    assert batch_1["products_per_hour"] == 187.5

    batch_2 = data["batches"][1]
    assert batch_2["batch_id"] == 2
    assert batch_2["rate"] == 95.0
    assert batch_2["products_per_hour"] == 250.0

    assert data["average"]["aggregation_rate"] == 95.84
    assert data["average"]["products_per_hour"] == 218.75
    assert mock_get_stats.await_count == 2


@patch("src.api.v1.routers.analytics.BatchService.get_batch_statistics_cached")
async def test_compare_batches_one_not_found(
    mock_get_stats: AsyncMock, client: AsyncClient, mock_batch_stats: dict
):
    """Тест сравнения, когда одна из партий не найдена"""

    def side_effect(batch_id: int):
        if batch_id == 1:
            return mock_batch_stats
        return None

    mock_get_stats.side_effect = side_effect

    payload = {"batch_ids": [1, 999]}
    response = await client.post(
        "/api/v1/analytics/compare-batches", json=payload
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "Партия с id 999 не найдена" in response.json()["detail"]


async def test_compare_batches_empty_list(client: AsyncClient):
    """Тест сравнения с пустым списком ID (должен вернуть пустой результат)"""
    payload = {"batch_ids": []}
    response = await client.post(
        "/api/v1/analytics/compare-batches", json=payload
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    error_detail = response.json()["detail"]
    assert any("batch_ids" in str(err) for err in error_detail)
