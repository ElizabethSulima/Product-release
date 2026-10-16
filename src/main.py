"""
Product release control system - Точка входа приложения.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded

from src.api.v1.routers import health
from src.core.config import config
from src.core.limiter import limiter

logger = logging.getLogger(__name__)


@asynccontextmanager
# async def lifespan(app: FastAPI) -> AsyncIterator[None]:
#     """
#     Lifecycle manager для FastAPI.

#     Выполняется при:
#     - startup: настройка логирования
#     - shutdown: закрытие подключений к БД
#     """
#     # Startup
#     app.state.ol_client = OpenLibraryClient(
#         base_url=settings.OPENLIBRARY_BASE_URL,
#         timeout=settings.OPENLIBRARY_TIMEOUT,
#     )
#     logger.info("Application started")
#     yield

#     # Shutdown
#     await app.state.ol_client.close()
#     await dispose_engine()
#     logger.info("Application stopped")


def setup_middleware(app: FastAPI) -> None:
    """
    Настроить middleware для приложения.

    Порядок важен: middleware выполняются в обратном порядке добавления.
    """
    # 1. Request ID - должен быть первым, чтобы все логи имели request_id
    # app.add_middleware(RequestIDMiddleware)

    # # 2. Request logging - логирует все запросы
    # app.add_middleware(RequestLoggingMiddleware)

    # 3. CORS - настраивается один раз
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=config.CORS_ALLOW_CREDENTIALS,
        allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "X-Request-ID"],
    )

    if config.is_production:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=config.CORS_ORIGINS,
        )


async def rate_limit_exceeded_handler(
    request: Request, exc: Exception
) -> JSONResponse:
    """
    Обработчик превышения лимита запросов (Rate Limit)
    """
    request_id = getattr(request.state, "request_id", "unknown")

    return JSONResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content={
            "detail": "Too Many Requests",
            "error": str(exc),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )


def create_app() -> FastAPI:
    """
    Фабрика для создания экземпляра приложения.
    Необходима для корректной работы тестов (dependency_overrides).
    """

    app = FastAPI(
        title=config.APP_NAME,
        version=config.APP_VERSION,
        docs_url=config.docs_url if not config.is_production else None,
        redoc_url=config.redoc_url if not config.is_production else None,
        openapi_url=(config.openapi_url if not config.is_production else None),
        description="Система контроля заданий на выпуск продукции",
        # lifespan=lifespan,
    )

    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)

    setup_middleware(app)
    # register_exception_handlers(app)

    # app.include_router(
    #     books.router,
    #     prefix=config.API_V1_PREFIX,
    # )
    app.include_router(
        health.router,
        prefix=config.API_V1_PREFIX,
    )

    # app.include_router(auth.router, prefix=config.API_V1_PREFIX)

    @app.get("/")
    @limiter.limit("200 per minute")
    async def root(request: Request) -> dict[str, str | None]:
        """Корневой эндпоинт."""
        response: dict[str, str | None] = {
            "message": "Welcome to Library Catalog API",
            "version": config.APP_VERSION,
        }
        if not config.is_production:
            response["docs"] = "/docs"
        return response

    return app


app_fast = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app_fast, host="0.0.0.0", port=8000)
