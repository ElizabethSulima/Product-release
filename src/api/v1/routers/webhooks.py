from fastapi import APIRouter, HTTPException, Query, Request, status

from src.api.v1.schemas.webhook import (
    WebhookDeliveryListResponse,
    WebhookDeliveryResponse,
    WebhookSubscriptionCreate,
    WebhookSubscriptionListResponse,
    WebhookSubscriptionResponse,
    WebhookSubscriptionUpdate,
)
from src.core.database import AsyncSessionDependency
from src.core.limiter import limiter
from src.domain.services.webhook import WebhookService

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post(
    "",
    response_model=WebhookSubscriptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Создание подписки на вебхуки",
)
@limiter.limit("30 per minute")
async def create_webhook_subscription(
    request: Request,
    payload: WebhookSubscriptionCreate,
    session: AsyncSessionDependency,
) -> WebhookSubscriptionResponse:
    """Создать новую подписку на вебхуки"""
    service = WebhookService(session)

    events_as_strings = [str(event) for event in payload.events]

    subscription = await service.create_subscription(
        url=str(payload.url),
        events=events_as_strings,
        secret_key=payload.secret_key,
        retry_count=payload.retry_count,
        timeout=payload.timeout,
    )

    return WebhookSubscriptionResponse.model_validate(
        subscription, from_attributes=True
    )


@router.get(
    "",
    response_model=WebhookSubscriptionListResponse,
    summary="Список подписок",
)
@limiter.limit("20 per minute")
async def list_webhook_subscriptions(
    request: Request,
    session: AsyncSessionDependency,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> WebhookSubscriptionListResponse:
    """Получить список всех подписок"""
    service = WebhookService(session)
    subscriptions, total = await service.list_subscriptions(
        offset=offset, limit=limit
    )

    return WebhookSubscriptionListResponse(
        items=[
            WebhookSubscriptionResponse.model_validate(
                sub, from_attributes=True
            )
            for sub in subscriptions
        ],
        total=total,
    )


@router.patch(
    "/{subscription_id}",
    response_model=WebhookSubscriptionResponse,
    summary="Обновление подписки",
)
@limiter.limit("30 per minute")
async def update_webhook_subscription(
    request: Request,
    subscription_id: int,
    payload: WebhookSubscriptionUpdate,
    session: AsyncSessionDependency,
) -> WebhookSubscriptionResponse:
    """Обновить параметры подписки"""
    service = WebhookService(session)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных для обновления",
        )

    if "events" in update_data and update_data["events"] is not None:
        update_data["events"] = [str(event) for event in update_data["events"]]

    if "url" in update_data and update_data["url"] is not None:
        update_data["url"] = str(update_data["url"])

    subscription = await service.update_subscription(
        subscription_id, update_data
    )
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена",
        )

    return WebhookSubscriptionResponse.model_validate(
        subscription, from_attributes=True
    )


@router.delete(
    "/{subscription_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление подписки",
)
@limiter.limit("40 per minute")
async def delete_webhook_subscription(
    request: Request,
    subscription_id: int,
    session: AsyncSessionDependency,
) -> None:
    """Удалить подписку и всю историю доставок"""
    service = WebhookService(session)

    deleted = await service.delete_subscription(subscription_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена",
        )


@router.get(
    "/{subscription_id}/deliveries",
    response_model=WebhookDeliveryListResponse,
    summary="История доставок",
)
@limiter.limit("30 per minute")
async def list_webhook_deliveries(
    request: Request,
    session: AsyncSessionDependency,
    subscription_id: int,
    offset: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
) -> WebhookDeliveryListResponse:
    """Получить историю доставок для конкретной подписки"""
    service = WebhookService(session)

    subscription = await service.get_subscription(subscription_id)
    if not subscription:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Подписка не найдена",
        )

    deliveries, total = await service.list_deliveries(
        subscription_id, offset=offset, limit=limit
    )

    return WebhookDeliveryListResponse(
        items=[
            WebhookDeliveryResponse.model_validate(
                delivery, from_attributes=True
            )
            for delivery in deliveries
        ],
        total=total,
    )
