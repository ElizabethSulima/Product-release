import pytest
from fastapi import status
from httpx import AsyncClient

from src.data.models.webhook import WebhookSubscription

pytestmark = pytest.mark.anyio


async def test_create_webhook_subscription(
    client: AsyncClient, valid_webhook_payload: dict
):
    """Тест успешного создания подписки на вебхуки"""
    response = await client.post(
        "/api/v1/webhooks", json=valid_webhook_payload
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["url"] == valid_webhook_payload["url"]
    assert data["events"] == valid_webhook_payload["events"]
    assert data["is_active"] is True

    assert "id" in data
    assert data["id"] is not None

    if "retry_count" in data:
        assert data["retry_count"] == valid_webhook_payload["retry_count"]
    if "timeout" in data:
        assert data["timeout"] == valid_webhook_payload["timeout"]


async def test_list_webhook_subscriptions(
    client: AsyncClient, db_webhook_subscription: WebhookSubscription
):
    """Тест получения списка подписок"""
    response = await client.get("/api/v1/webhooks?limit=10&offset=0")

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] >= 1


async def test_update_webhook_subscription_success(
    client: AsyncClient,
    db_webhook_subscription: WebhookSubscription,
    valid_webhook_payload: dict,
):
    """Тест успешного обновления параметров подписки"""
    update_payload = {"url": "https://new-example.com/webhook", "timeout": 30}

    response = await client.patch(
        f"/api/v1/webhooks/{db_webhook_subscription.id}", json=update_payload
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["url"] == "https://new-example.com/webhook"
    if "retry_count" in data:
        assert data["retry_count"] == valid_webhook_payload["retry_count"]
    if "timeout" in data:
        assert data["timeout"] == valid_webhook_payload["timeout"]


async def test_update_webhook_subscription_empty_payload(
    client: AsyncClient, db_webhook_subscription: WebhookSubscription
):
    """Тест обновления пустым payload (должен вернуть 400)"""
    response = await client.patch(
        f"/api/v1/webhooks/{db_webhook_subscription.id}", json={}
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "Нет данных для обновления"


async def test_update_webhook_subscription_not_found(client: AsyncClient):
    """Тест обновления несуществующей подписки"""
    response = await client.patch(
        "/api/v1/webhooks/999999",
        json={"url": "https://nonexistent.example.com/webhook"},
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Подписка не найдена"


async def test_delete_webhook_subscription_success(
    client: AsyncClient, db_webhook_subscription: WebhookSubscription
):
    """Тест успешного удаления подписки"""
    response = await client.delete(
        f"/api/v1/webhooks/{db_webhook_subscription.id}"
    )
    assert response.status_code == status.HTTP_204_NO_CONTENT


async def test_delete_webhook_subscription_not_found(client: AsyncClient):
    """Тест удаления несуществующей подписки"""
    response = await client.delete("/api/v1/webhooks/999999")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Подписка не найдена"


async def test_list_webhook_deliveries_success(
    client: AsyncClient, db_webhook_subscription: WebhookSubscription
):
    """Тест получения истории доставок для существующей подписки"""
    response = await client.get(
        f"/api/v1/webhooks/{db_webhook_subscription.id}/deliveries?limit=10&offset=0"
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert "items" in data
    assert "total" in data
    assert isinstance(data["items"], list)
    assert data["total"] == 0


async def test_list_webhook_deliveries_subscription_not_found(
    client: AsyncClient,
):
    """Тест получения истории доставок для несуществующей подписки"""
    response = await client.get("/api/v1/webhooks/999999/deliveries")

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Подписка не найдена"
