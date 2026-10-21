from typing import Any

from pydantic import BaseModel


class TaskProgressResponse(BaseModel):
    """
    Схема для прогресса
    """

    task_id: str
    status: str
    result: dict[str, Any] | None = None
    message: str | None = None


class AggregateAsyncRequest(BaseModel):
    """
    Схема для агрегации
    """

    unique_codes: list[str]
    user_id: int | None = None
