from unittest.mock import AsyncMock

import pytest
from fastapi import status
from httpx import AsyncClient

from src.core.database import get_async_session
from src.main import app_fast

pytestmark = pytest.mark.anyio


def test_app_imports():
    """Проверка, что основное приложение успешно импортируется"""

    assert app_fast.title == "PRODUCT CONTROL SYSTEM"


async def test_health_check_live(client: AsyncClient):
    """
    Проверяет Liveness: процесс приложения запущен и отвечает.
    Не зависит от БД.
    """
    response = await client.get("/api/v1/health/live")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "alive"
    assert "version" in data
    assert data["version"] is not None


async def test_health_check_ready_healthy(client: AsyncClient):
    """
    Проверяет Readiness в нормальном состоянии:
    Сервис и БД работают корректно (использует реальную тестовую БД из фикстур).
    """
    response = await client.get("/api/v1/health/ready")

    assert response.status_code == status.HTTP_200_OK

    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert "version" in data
    assert data["uptime_seconds"] >= 0
    assert "timestamp" in data


async def test_health_check_ready_unhealthy(client: AsyncClient, app):
    """
    Проверяет Readiness при сбое БД:
    Сервис должен вернуть 503 Service Unavailable.
    """
    mock_session = AsyncMock()
    mock_session.execute.side_effect = Exception(
        "Simulated Database Connection Failure"
    )

    async def override_failing_db():
        yield mock_session

    app.dependency_overrides[get_async_session] = override_failing_db

    try:
        response = await client.get("/api/v1/health/ready")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE

        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["database"] == "disconnected"
        assert "version" in data
        assert data["uptime_seconds"] >= 0
        assert "timestamp" in data

    finally:
        app.dependency_overrides.clear()
