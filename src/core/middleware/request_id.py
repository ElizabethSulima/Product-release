import uuid
from collections.abc import Awaitable, Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Добавляет уникальный request_id к каждому запросу.

    Если request_id уже есть в заголовке (от upstream), использует его.
    Иначе генерирует новый UUID.
    """

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        # Проверяем, есть ли уже request_id (от load balancer, API gateway)
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

        # Сохраняем в state для доступа в эндпоинтах
        request.state.request_id = request_id

        # Передаём дальше
        response = await call_next(request)

        # Добавляем request_id в ответ
        response.headers["X-Request-ID"] = request_id
        return response
