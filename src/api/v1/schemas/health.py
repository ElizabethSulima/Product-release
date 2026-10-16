from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class HealthCheckResponse(BaseModel):
    """Схема ответа для проверки готовности (Readiness) сервиса"""

    status: Literal["healthy", "unhealthy"] = Field(
        ..., description="Общий статус готовности сервиса"
    )
    database: Literal["connected", "disconnected"] = Field(
        ..., description="Статус подключения к базе данных"
    )
    version: str = Field(..., description="Версия приложения")
    uptime_seconds: int = Field(
        ..., description="Время работы приложения в секундах"
    )
    timestamp: datetime = Field(..., description="Текущее время сервера (UTC)")


class LivenessResponse(BaseModel):
    """Схема ответа для проверки живости (Liveness) сервиса"""

    status: Literal["alive"] = Field(
        ..., description="Статус процесса (процесс запущен и отвечает)"
    )
    version: str = Field(..., description="Версия приложения")
