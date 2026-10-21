from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.v1.schemas.batch import (
    BatchExternalCreate,
    BatchResponse,
    BatchUpdate,
)
from src.api.v1.schemas.report import ReportRequest, ReportTaskResponse
from src.api.v1.schemas.task import AggregateAsyncRequest, TaskProgressResponse
from src.core.database import AsyncSessionDependency, get_async_session
from src.core.limiter import limiter
from src.data.models.batch import Batch
from src.domain.services.batch import BatchService
from src.tasks.aggregation import aggregate_products_batch
from src.tasks.reports import generate_batch_report

router = APIRouter(prefix="/batches", tags=["Batch"])


@router.post(
    "",
    response_model=list[BatchResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Создание сменных заданий",
)
@limiter.limit("20 per minute")
async def create_batches(
    request: Request,
    payload: list[BatchExternalCreate],
    session: AsyncSessionDependency,
) -> list[BatchResponse]:
    service = BatchService(session)

    batches = [
        Batch(
            is_closed=item.status_closing,
            task_description=item.task_description,
            work_center_id=item.work_center_id,
            shift=item.shift,
            team=item.team,
            batch_number=item.batch_number,
            batch_date=item.batch_date,
            nomenclature=item.nomenclature,
            ekn_code=item.ekn_code,
            shift_start=item.shift_start,
            shift_end=item.shift_end,
        )
        for item in payload
    ]
    created_batches = await service.create_batches_bulk(batches)

    return [
        BatchResponse.model_validate(b, from_attributes=True)
        for b in created_batches
    ]


@router.get(
    "/{batch_id}",
    response_model=BatchResponse,
    summary="Получение партии по ID",
)
@limiter.limit("100 per minute")
async def get_batch(
    request: Request,
    batch_id: int,
    session: AsyncSessionDependency,
) -> BatchResponse:
    service = BatchService(session)
    batch = await service.get_batch_by_id(batch_id, load_products=True)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Партия не найдена"
        )
    return BatchResponse.model_validate(batch, from_attributes=True)


@router.patch(
    "/{batch_id}",
    response_model=BatchResponse,
    summary="Обновление партии",
)
@limiter.limit("60 per minute")
async def update_batch(
    request: Request,
    batch_id: int,
    payload: BatchUpdate,
    session: AsyncSessionDependency,
) -> BatchResponse:
    service = BatchService(session)

    update_data = payload.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нет данных для обновления",
        )

    batch = await service.update_batch(batch_id, update_data)
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Партия не найдена"
        )

    return BatchResponse.model_validate(batch, from_attributes=True)


@router.get(
    "",
    response_model=list[BatchResponse],
    summary="Список партий с фильтрацией",
)
@limiter.limit("100 per minute")
async def list_batches(
    request: Request,
    is_closed: bool = Query(None),
    batch_number: int = Query(None),
    batch_date: date = Query(None),
    work_center_id: int = Query(None),
    shift: str = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_session),
) -> list[BatchResponse]:
    service = BatchService(session)
    batches = await service.list_batches(
        is_closed=is_closed,
        batch_number=batch_number,
        batch_date=batch_date,
        work_center_id=str(work_center_id) if work_center_id else None,
        shift=shift,
        offset=offset,
        limit=limit,
    )
    return [
        BatchResponse.model_validate(b, from_attributes=True) for b in batches
    ]


@router.post(
    "/{batch_id}/aggregate-async",
    response_model=TaskProgressResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("20 per minute")
async def aggregate_batch_async(
    request: Request,
    batch_id: int,
    payload: AggregateAsyncRequest,
) -> TaskProgressResponse:
    task = aggregate_products_batch.delay(
        batch_id=batch_id,
        unique_codes=payload.unique_codes,
        user_id=payload.user_id,
    )

    return TaskProgressResponse(
        task_id=task.id, status="PENDING", message="Aggregation task started"
    )


@router.post(
    "/{batch_id}/reports",
    response_model=ReportTaskResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit("20 per minute")
async def create_batch_report(
    request: Request,
    batch_id: int,
    payload: ReportRequest,
) -> ReportTaskResponse:
    task = generate_batch_report.delay(
        batch_id=batch_id, format=payload.format, user_email=payload.email
    )

    return ReportTaskResponse(task_id=task.id, status="PENDING")
