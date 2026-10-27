from unittest.mock import MagicMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

pytestmark = pytest.mark.anyio

ROUTER_MODULE_PATH = "src.api.v1.routers.tasks.celery_app.AsyncResult"


@patch(ROUTER_MODULE_PATH)
async def test_get_task_status_pending(
    mock_async_result: MagicMock, client: AsyncClient
):
    """Тест получения статуса задачи, которая ещё не начала выполняться (PENDING)"""
    mock_task = MagicMock()
    mock_task.id = "test-task-123"
    mock_task.status = "PENDING"
    mock_task.info = None
    mock_task.result = None

    mock_async_result.return_value = mock_task

    response = await client.get("/api/v1/tasks/test-task-123")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["task_id"] == "test-task-123"
    assert data["status"] == "PENDING"
    assert data["result"] is None
    assert data["message"] == "Task is waiting to be processed"


@patch(ROUTER_MODULE_PATH)
async def test_get_task_status_success(
    mock_async_result: MagicMock, client: AsyncClient
):
    """Тест получения статуса успешно завершённой задачи (SUCCESS)"""
    mock_task = MagicMock()
    mock_task.id = "test-task-456"
    mock_task.status = "SUCCESS"
    mock_task.result = {"file_url": "https://minio.local/reports/report.xlsx"}

    mock_async_result.return_value = mock_task

    response = await client.get("/api/v1/tasks/test-task-456")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["task_id"] == "test-task-456"
    assert data["status"] == "SUCCESS"
    assert data["result"] == {
        "file_url": "https://minio.local/reports/report.xlsx"
    }
    assert data["message"] is None


@patch(ROUTER_MODULE_PATH)
async def test_get_task_status_failure(
    mock_async_result: MagicMock, client: AsyncClient
):
    """Тест получения статуса упавшей задачи (FAILURE)"""
    mock_task = MagicMock()
    mock_task.id = "test-task-789"
    mock_task.status = "FAILURE"
    mock_task.info = ValueError("Database connection timeout")

    mock_async_result.return_value = mock_task

    response = await client.get("/api/v1/tasks/test-task-789")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["task_id"] == "test-task-789"
    assert data["status"] == "FAILURE"
    assert data["result"] is None
    assert "Task failed: Database connection timeout" in data["message"]


@patch(ROUTER_MODULE_PATH)
async def test_get_task_status_progress(
    mock_async_result: MagicMock, client: AsyncClient
):
    """Тест получения статуса задачи в процессе выполнения (PROGRESS)"""
    mock_task = MagicMock()
    mock_task.id = "test-task-999"
    mock_task.status = "PROGRESS"
    mock_task.info = {"current": 50, "total": 100, "percent": 50}

    mock_async_result.return_value = mock_task

    response = await client.get("/api/v1/tasks/test-task-999")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["status"] == "PROGRESS"
    assert data["result"] == {"current": 50, "total": 100, "percent": 50}
