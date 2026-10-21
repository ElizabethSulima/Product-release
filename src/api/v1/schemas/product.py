from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ProductCreate(BaseModel):
    """
    Схема для создания продукта
    """

    batch_id: int
    unique_code: str = Field(max_length=50)
    ekn_code: str = Field(max_length=100)


class ProductResponse(BaseModel):
    """
    Схема для ответа клиенту
    """

    model_config = ConfigDict(from_attributes=True)

    id: int
    unique_code: str
    is_aggregated: bool
    aggregated_at: datetime | None = None


class AggregateRequest(BaseModel):
    """
    Запрос на агрегацию продукции в партии.
    Принимает список уникальных кодов продукции.
    """

    unique_codes: list[str] = Field(
        ...,
        min_length=1,
        description="Список unique_code продукции для агрегации",
    )
