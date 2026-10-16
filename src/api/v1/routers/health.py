import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Response, status
from sqlalchemy import text

from src.api.v1.schemas.health import HealthCheckResponse, LivenessResponse
from src.core.config import config
from src.core.database import AsyncSessionDependency

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/health", tags=["Health"])

START_TIME = datetime.now(UTC)


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness Check",
    responses={
        200: {"description": "Процесс приложения запущен и отвечает"},
    },
)
async def liveness_check() -> LivenessResponse:
    """
    Проверка живости (Liveness).

    Отвечает на вопрос: "Перезагружать ли контейнер?"
    Не проверяет внешние зависимости (БД), чтобы избежать каскадных перезагрузок
    при временных сбоях базы данных.
    """
    return LivenessResponse(
        status="alive",
        version=config.APP_VERSION,
    )


@router.get(
    "/ready",
    response_model=HealthCheckResponse,
    summary="Readiness Check",
    responses={
        200: {
            "description": "Сервис и БД работают корректно",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "database": "connected",
                        "version": "1.0.0",
                        "uptime_seconds": 3600,
                        "timestamp": "2026-10-02T12:00:00Z",
                    }
                }
            },
        },
        503: {
            "description": "Сервис работает, но БД недоступна",
            "content": {
                "application/json": {
                    "example": {
                        "status": "unhealthy",
                        "database": "disconnected",
                        "version": "1.0.0",
                        "uptime_seconds": 3600,
                        "timestamp": "2026-10-02T12:00:00Z",
                    }
                }
            },
        },
    },
)
async def readiness_check(
    db: AsyncSessionDependency, response: Response
) -> HealthCheckResponse:
    """
    Проверка готовности (Readiness).

    Отвечает на вопрос: "Готов ли сервис обрабатывать запросы?"
    Проверяет подключение к базе данных.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:  # pylint: disable=W0718
        logger.exception("Database health check failed")
        db_ok = False
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    uptime_seconds = (datetime.now(UTC) - START_TIME).total_seconds()

    return HealthCheckResponse(
        status="healthy" if db_ok else "unhealthy",
        database="connected" if db_ok else "disconnected",
        version=config.APP_VERSION,
        uptime_seconds=int(uptime_seconds),
        timestamp=datetime.now(UTC),
    )
