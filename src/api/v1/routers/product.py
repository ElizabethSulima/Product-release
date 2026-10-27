from typing import Any

from fastapi import APIRouter, HTTPException, Request, status

from src.api.v1.schemas.product import (
    AggregateRequest,
    ProductCreate,
    ProductResponse,
)
from src.core.database import AsyncSessionDependency
from src.core.limiter import limiter
from src.data.models.product import Product
from src.domain.services.batch import BatchService
from src.domain.services.product import ProductService

router = APIRouter(prefix="", tags=["Products"])


@router.post(
    "/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Добавление продукции",
)
@limiter.limit("100 per minute")
async def create_product(
    request: Request,
    payload: ProductCreate,
    session: AsyncSessionDependency,
) -> ProductResponse:
    batch_service = BatchService(session)
    product_service = ProductService(session)

    batch = await batch_service.get_batch_by_id(payload.batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Партия не найдена")

    product = Product(
        batch_id=payload.batch_id,
        unique_code=payload.unique_code,
    )
    created_product = await product_service.create_product(product)
    return ProductResponse.model_validate(
        created_product, from_attributes=True
    )


@router.post(
    "/{batch_id}/aggregate",
    summary="Агрегация продукции в партии",
)
@limiter.limit("30 per minute")
async def aggregate_products(
    request: Request,
    batch_id: int,
    payload: AggregateRequest,
    session: AsyncSessionDependency,
) -> dict[str, Any]:
    batch_service = BatchService(session)
    product_service = ProductService(session)

    batch = await batch_service.get_batch_by_id(batch_id)
    if not batch:
        raise HTTPException(status_code=404, detail="Партия не найдена")

    updated_count = await product_service.aggregate_products(
        batch_id=batch_id,
        unique_codes=payload.unique_codes,
    )

    return {
        "batch_id": batch_id,
        "aggregated_count": updated_count,
        "requested_count": len(payload.unique_codes),
    }
