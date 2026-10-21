import asyncio
import os
import tempfile
from datetime import datetime
from typing import Any

import pandas as pd
from celery.app.task import Task
from sqlalchemy import select

from src.celery_app import celery_app
from src.data.models.batch import Batch
from src.storage.minio_service import minio_service
from src.tasks.aggregation import AsyncSessionLocal


@celery_app.task(bind=True)  # type: ignore[untyped-decorator]
def export_batches_to_file(
    self: Task, filters: dict[str, Any], format: str = "excel"
) -> dict[str, Any]:
    """Экспорт списка партий в файл и загрузка в MinIO"""

    async def _process_export() -> dict[str, Any]:
        async with AsyncSessionLocal() as session:
            stmt = select(Batch)
            if "is_closed" in filters:
                stmt = stmt.where(Batch.is_closed == filters["is_closed"])
            if "date_from" in filters:
                stmt = stmt.where(Batch.batch_date >= filters["date_from"])
            if "date_to" in filters:
                stmt = stmt.where(Batch.batch_date <= filters["date_to"])

            result = await session.execute(stmt)
            batches = result.scalars().all()

            data = [
                {
                    "НомерПартии": b.batch_number,
                    "ДатаПартии": b.batch_date.isoformat(),
                    "Номенклатура": b.nomenclature,
                    "РабочийЦентр": b.work_center,
                }
                for b in batches
            ]

            df = pd.DataFrame(data)

            ext = "xlsx" if format == "excel" else "csv"
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{ext}"
            ) as tmp_file:
                if format == "excel":
                    df.to_excel(tmp_file.name, index=False)
                else:
                    df.to_csv(tmp_file.name, index=False)
                tmp_path = tmp_file.name

            object_name = f"exports/batches_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
            with open(tmp_path, "rb") as f:
                file_bytes = f.read()

            url, _ = minio_service.upload_file_bytes(
                bucket="exports",
                file_bytes=file_bytes,
                object_name=object_name,
                content_type=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    if format == "excel"
                    else "text/csv"
                ),
            )

            os.remove(tmp_path)

            return {
                "success": True,
                "file_url": url,
                "total_batches": len(batches),
            }

    return asyncio.run(_process_export())
