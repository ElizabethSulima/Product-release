from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from src.data.models.batch import Batch
from src.data.models.work_center import WorkCenter

pytestmark = pytest.mark.anyio


@patch("src.api.v1.routers.batches.trigger_webhook")
@patch("src.api.v1.routers.batches.on_batch_created")
async def test_create_batches(
    mock_on_created: AsyncMock,
    mock_webhook: MagicMock,
    client: AsyncClient,
    valid_batch_payload: list[dict],
    test_work_center: WorkCenter,
):
    """Тест создания одной или нескольких партий"""
    response = await client.post("/api/v1/batches", json=valid_batch_payload)

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["batch_number"] == 99999
    assert data[0]["nomenclature"] == "Тестовая номенклатура"

    mock_on_created.assert_awaited_once()
    mock_webhook.assert_called_once()


async def test_get_batch_by_id(client: AsyncClient, db_batch: Batch):
    """Тест получения партии по ID"""
    response = await client.get(f"/api/v1/batches/{db_batch.id}")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == db_batch.id
    assert data["batch_number"] == 88888


@patch("src.api.v1.routers.batches.trigger_webhook")
@patch("src.api.v1.routers.batches.on_batch_updated")
async def test_update_batch(
    mock_on_updated: AsyncMock,
    mock_webhook: MagicMock,
    client: AsyncClient,
    db_batch: Batch,
    test_work_center: WorkCenter,
):
    """Тест обновления партии"""
    update_payload = {
        "is_closed": True,
        "task_description": "Обновленное задание",
    }

    response = await client.patch(
        f"/api/v1/batches/{db_batch.id}", json=update_payload
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["is_closed"] is True
    assert data["task_description"] == "Обновленное задание"

    mock_on_updated.assert_awaited_once_with(db_batch.id)
    mock_webhook.assert_called_once()


async def test_update_batch_empty_payload(
    client: AsyncClient,
    db_batch: Batch,
    test_work_center: WorkCenter,
):
    """Тест обновления пустым payload (должен вернуть 400)"""
    response = await client.patch(f"/api/v1/batches/{db_batch.id}", json={})
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "Нет данных для обновления" in response.json()["detail"]


async def test_list_batches(
    client: AsyncClient,
    db_batch: Batch,
    test_work_center: WorkCenter,
):
    """Тест получения списка партий с фильтрацией"""
    response = await client.get("/api/v1/batches?limit=10&offset=0")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 1

    response_filtered = await client.get("/api/v1/batches?shift=Ночь")
    assert response_filtered.status_code == status.HTTP_200_OK
    assert len(response_filtered.json()) >= 1


@patch("src.api.v1.routers.batches.aggregate_products_batch.delay")
async def test_aggregate_batch_async(
    mock_celery_delay: MagicMock,
    client: AsyncClient,
    db_batch: Batch,
    test_work_center: WorkCenter,
):
    """Тест запуска асинхронной агрегации"""
    mock_task = MagicMock()
    mock_task.id = "test-task-id-123"
    mock_celery_delay.return_value = mock_task

    payload = {"unique_codes": ["code1", "code2"], "user_id": 42}
    response = await client.post(
        f"/api/v1/batches/{db_batch.id}/aggregate-async", json=payload
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["task_id"] == "test-task-id-123"
    assert data["status"] == "PENDING"
    mock_celery_delay.assert_called_once_with(
        batch_id=db_batch.id, unique_codes=["code1", "code2"], user_id=42
    )


@patch("src.api.v1.routers.batches.generate_batch_report.delay")
async def test_create_batch_report(
    mock_celery_delay: MagicMock,
    client: AsyncClient,
    db_batch: Batch,
    test_work_center: WorkCenter,
):
    """Тест запуска генерации отчета"""
    mock_task = MagicMock()
    mock_task.id = "report-task-id-456"
    mock_celery_delay.return_value = mock_task

    payload = {"format": "excel", "email": "test@example.com"}
    response = await client.post(
        f"/api/v1/batches/{db_batch.id}/reports", json=payload
    )

    assert response.status_code == status.HTTP_202_ACCEPTED
    data = response.json()
    assert data["task_id"] == "report-task-id-456"
    mock_celery_delay.assert_called_once_with(
        batch_id=db_batch.id, format="excel", user_email="test@example.com"
    )


@patch("src.domain.services.batch.BatchService.get_batch_statistics_cached")
async def test_get_batch_statistics(
    mock_get_stats: AsyncMock,
    client: AsyncClient,
    db_batch: Batch,
    test_work_center: WorkCenter,
):
    """Тест получения статистики партии"""
    mock_get_stats.return_value = {
        "total_products": 150,
        "defect_rate": 0.02,
        "status": "completed",
    }

    response = await client.get(f"/api/v1/batches/{db_batch.id}/statistics")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["total_products"] == 150
    mock_get_stats.assert_awaited_once_with(db_batch.id)


async def test_get_batch_statistics_not_found(client: AsyncClient):
    """Тест статистики для несуществующей партии"""
    response = await client.get("/api/v1/batches/9999999/statistics")
    assert response.status_code == status.HTTP_404_NOT_FOUND


async def test_get_batch_not_found(client: AsyncClient):
    """Тест получения несуществующей партии"""
    response = await client.get("/api/v1/batches/9999999")
    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Партия не найдена"
