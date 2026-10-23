from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from src.core.enums import WebhookEventType


class WebhookSubscriptionCreate(BaseModel):
    url: HttpUrl
    events: list[WebhookEventType] = Field(
        ..., min_length=1, description="Список событий для подписки"
    )
    secret_key: str = Field(
        ..., min_length=8, description="Секретный ключ для HMAC-подписи"
    )
    retry_count: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Количество попыток повторной отправки",
    )
    timeout: int = Field(
        default=10, ge=1, le=30, description="Таймаут запроса в секундах"
    )


class WebhookSubscriptionUpdate(BaseModel):
    is_active: bool | None = None
    url: HttpUrl | None = None
    events: list[WebhookEventType] | None = None
    secret_key: str | None = Field(default=None, min_length=8)


class WebhookSubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    url: str
    events: list[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class WebhookSubscriptionListResponse(BaseModel):
    items: list[WebhookSubscriptionResponse]
    total: int


class WebhookDeliveryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    event_type: str
    status: str
    attempts: int
    response_status: int | None
    response_body: str | None
    error_message: str | None
    created_at: datetime
    delivered_at: datetime | None


class WebhookDeliveryListResponse(BaseModel):
    items: list[WebhookDeliveryResponse]
    total: int
