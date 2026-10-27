import uuid
from collections.abc import AsyncGenerator, AsyncIterator
from datetime import date, datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

import fakeredis.aioredis
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.engine import URL
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    create_async_engine,
)
from sqlalchemy.pool import StaticPool

import src.core.cache as cache_module
from src.celery_app import celery_app
from src.core.config import config
from src.core.database import get_async_session
from src.data.models.base import BaseModel
from src.data.models.batch import Batch
from src.data.models.webhook import WebhookSubscription
from src.data.models.work_center import WorkCenter
from src.main import create_app

TEST_DATABASE_URL = URL.create(
    drivername="postgresql+psycopg",
    username=config.POSTGRES_USER,
    password=config.POSTGRES_PASSWORD.get_secret_value(),
    host="localhost",
    port=config.POSTGRES_PORT,
    database=f"{config.POSTGRES_DB}_test",
)

ROUTER_MODULE_PATH = "src.api.v1.routers.files.minio_service"


@pytest.fixture(scope="function")
def engine() -> AsyncEngine:
    return create_async_engine(
        TEST_DATABASE_URL,
        poolclass=StaticPool,
        echo=False,
    )


@pytest.fixture(scope="function")
async def setup_db(engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """Создает и удаляет таблицы до и после каждого теста"""
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(BaseModel.metadata.drop_all)


@pytest.fixture
async def db_session(
    setup_db: None, engine: AsyncEngine
) -> AsyncIterator[AsyncSession]:
    """Свежая сессия с откатом транзакции (Rollback) после каждого теста"""
    async with engine.connect() as connection, connection.begin() as transaction:
        session = AsyncSession(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )
        try:
            yield session
        finally:
            await session.close()
            await transaction.rollback()


@pytest.fixture
async def fake_redis() -> AsyncGenerator[fakeredis.aioredis.FakeRedis, None]:
    """Изолированный инстанс Redis для каждого теста"""
    redis = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield redis
    await redis.flushall()


@pytest.fixture
def app(
    db_session: AsyncSession, fake_redis: fakeredis.aioredis.FakeRedis
) -> FastAPI:
    """Сборка приложения с подменой зависимостей"""
    app = create_app()

    async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
        yield db_session

    app.dependency_overrides[get_async_session] = override_get_db
    cache_module.redis_client = fake_redis
    return app


@pytest.fixture
async def client(app: FastAPI) -> AsyncGenerator[AsyncClient, None]:
    """Асинхронный клиент для тестов API"""
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


@pytest.fixture
async def auth_headers(db_session: AsyncSession) -> dict[str, str]:
    """
    Генерирует заголовки авторизации
    """
    token = "test_dummy_token"
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def celery_always_eager():
    """
    Заставляет Celery выполнять задачи синхронно в том же процессе
    """
    celery_app.conf.update(task_always_eager=True, task_eager_propagates=True)
    yield
    celery_app.conf.update(task_always_eager=False)


@pytest.fixture
def mock_minio_service():
    """
    Мокает экземпляр minio_service, чтобы не делать
    реальные запросы к хранилищу
    """
    with patch(ROUTER_MODULE_PATH) as mock:
        mock.upload_file_bytes.return_value = (
            "https://fake-presigned-url.com/file.xlsx",
            "2026-11-03T12:00:00Z",
        )
        mock.list_files.return_value = []
        mock.delete_file.return_value = None

        mock_client = MagicMock()
        mock_client.presigned_get_object.return_value = (
            "https://fake-presigned-url.com/download/file.xlsx"
        )
        mock.client = mock_client

        yield mock


@pytest.fixture
async def test_batch(db_session: AsyncSession) -> Batch:
    """Фабрика для создания тестовой партии"""
    batch = Batch(name=f"Test Batch {uuid.uuid4()}", status="active")
    db_session.add(batch)
    await db_session.flush()
    return batch


@pytest.fixture(autouse=True)
async def reset_rate_limiter(
    fake_redis: fakeredis.aioredis.FakeRedis,
):
    """
    Очищает хранилище rate limiter перед каждым тестом.
    """
    await fake_redis.flushall()


@pytest.fixture
async def test_work_center(db_session: AsyncSession) -> WorkCenter:
    """Создает тестовый рабочий центр, чтобы удовлетворить внешний ключ"""
    wc = WorkCenter(
        id=1,
        name="Тестовый цех",
        identifier="TEST-WC-001",
    )
    db_session.add(wc)
    await db_session.flush()
    return wc


@pytest.fixture
def valid_batch_payload() -> list[dict[str, Any]]:
    """Валидный payload для создания партии"""
    return [
        {
            "status_closing": False,
            "task_description": "Тестовое задание",
            "work_center_id": "1",
            "РабочийЦентр": "Тестовый цех 1",
            "shift": "День",
            "team": "Бригада 1",
            "batch_number": 99999,
            "batch_date": "2026-10-27",
            "nomenclature": "Тестовая номенклатура",
            "ekn_code": "ЕКН-123",
            "shift_start": "2026-10-27T08:00:00+00:00",
            "shift_end": "2026-10-27T16:00:00+00:00",
        }
    ]


@pytest.fixture
async def db_batch(
    db_session: AsyncSession, test_work_center: WorkCenter
) -> Batch:
    """Создает партию напрямую в БД для тестов GET/PATCH/DELETE"""
    batch = Batch(
        is_closed=False,
        task_description="DB Test Batch",
        work_center_id=test_work_center.id,
        shift="Ночь",
        team="Бригада 2",
        batch_number=88888,
        batch_date=date(2026, 10, 26),
        nomenclature="Номенклатура из БД",
        ekn_code="ЕКН-TEST",
        shift_start=datetime(2026, 10, 26, 20, 0, 0, tzinfo=timezone.utc),
        shift_end=datetime(2026, 10, 27, 4, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(batch)
    await db_session.flush()
    await db_session.refresh(batch)
    return batch


@pytest.fixture
def valid_product_payload(db_batch: Batch) -> dict[str, Any]:
    """
    Валидный payload для создания продукта, привязанный к существующей партии
    """
    return {
        "batch_id": db_batch.id,
        "unique_code": "UNIQUE-CODE-12345",
    }


@pytest.fixture
def valid_aggregate_payload() -> dict[str, Any]:
    """Валидный payload для агрегации"""
    return {"unique_codes": ["CODE-1", "CODE-2", "CODE-3"]}


@pytest.fixture
def valid_webhook_payload() -> dict[str, Any]:
    """Валидный payload для создания подписки на вебхуки"""
    return {
        "url": "https://example.com/webhook-receiver",
        "events": ["batch_created", "batch_updated"],
        "secret_key": "super_secret_key_123",
        "retry_count": 3,
        "timeout": 10,
    }


@pytest.fixture
async def db_webhook_subscription(
    db_session: AsyncSession,
) -> WebhookSubscription:
    """Создает тестовую подписку в БД для тестов GET, PATCH, DELETE"""
    subscription = WebhookSubscription(
        url="https://example.com/existing-webhook",
        events=["batch_created"],
        secret_key="test_secret_key",
        is_active=True,
        retry_count=5,
        timeout=15,
    )
    db_session.add(subscription)
    await db_session.flush()
    await db_session.refresh(subscription)
    return subscription


@pytest.fixture
def mock_dashboard_stats() -> dict[str, Any]:
    """Моканные данные для дашборда"""
    return {
        "total_batches": 150,
        "active_batches": 12,
        "total_products": 50000,
        "aggregated_products": 48500,
        "overall_aggregation_rate": 97.0,
        "top_performing_work_centers": [
            {"name": "Цех 1", "rate": 99.5},
            {"name": "Цех 2", "rate": 98.2},
        ],
    }


@pytest.fixture
def mock_batch_stats() -> dict[str, Any]:
    """Моканные данные для статистики конкретной партии"""
    return {
        "batch_info": {
            "id": 1,
            "batch_number": 88888,
            "work_center": "Цех 1",
            "shift": "Ночь",
        },
        "production_stats": {
            "total_products": 1500,
            "aggregated": 1450,
            "aggregation_rate": 96.67,
        },
        "timeline": {
            "shift_start": "2026-10-26T20:00:00Z",
            "shift_end": "2026-10-27T04:00:00Z",
            "shift_duration_hours": 8.0,
            "products_per_hour": 187.5,
        },
    }


@pytest.fixture
def mock_batch_stats_2() -> dict[str, Any]:
    """Вторая моканная партия для сравнения"""
    return {
        "batch_info": {
            "id": 2,
            "batch_number": 99999,
            "work_center": "Цех 2",
            "shift": "День",
        },
        "production_stats": {
            "total_products": 2000,
            "aggregated": 1900,
            "aggregation_rate": 95.0,
        },
        "timeline": {
            "shift_start": "2026-10-27T08:00:00Z",
            "shift_end": "2026-10-27T16:00:00Z",
            "shift_duration_hours": 8.0,
            "products_per_hour": 250.0,
        },
    }
