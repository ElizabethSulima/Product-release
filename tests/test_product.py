from unittest.mock import AsyncMock, patch

import pytest
from fastapi import status
from httpx import AsyncClient

from src.data.models.batch import Batch

pytestmark = pytest.mark.anyio


async def test_create_product_success(
    client: AsyncClient, db_batch: Batch, valid_product_payload: dict
):
    """Тест успешного создания продукта в существующей партии"""
    response = await client.post(
        "/api/v1/products", json=valid_product_payload
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    assert data["id"] == 1
    assert data["unique_code"] == "UNIQUE-CODE-12345"
    assert data["is_aggregated"] is False
    assert data["aggregated_at"] is None


async def test_create_product_batch_not_found(
    client: AsyncClient, valid_product_payload: dict
):
    """Тест создания продукта для несуществующей партии (должен вернуть 404)"""
    payload = valid_product_payload.copy()
    payload["batch_id"] = 999999

    response = await client.post("/api/v1/products", json=payload)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Партия не найдена"


@patch("src.domain.services.product.ProductService.aggregate_products")
async def test_aggregate_products_success(
    mock_aggregate: AsyncMock,
    client: AsyncClient,
    db_batch: Batch,
    valid_aggregate_payload: dict,
):
    """Тест успешной агрегации продукции в партии"""
    mock_aggregate.return_value = 2

    response = await client.post(
        f"/api/v1/{db_batch.id}/aggregate", json=valid_aggregate_payload
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    assert data["batch_id"] == db_batch.id
    assert data["aggregated_count"] == 2
    assert data["requested_count"] == 3

    mock_aggregate.assert_awaited_once_with(
        batch_id=db_batch.id, unique_codes=["CODE-1", "CODE-2", "CODE-3"]
    )


async def test_aggregate_products_batch_not_found(
    client: AsyncClient, valid_aggregate_payload: dict
):
    """Тест агрегации для несуществующей партии (должен вернуть 404)"""
    fake_batch_id = 999999

    response = await client.post(
        f"/api/v1/{fake_batch_id}/aggregate", json=valid_aggregate_payload
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert response.json()["detail"] == "Партия не найдена"
