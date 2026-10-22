import asyncio
import os
import tempfile
from typing import Any

import httpx
import pandas as pd
from celery.app.task import Task
from sqlalchemy import select

from src.celery_app import celery_app
from src.core.webhook_dispatcher import trigger_webhook
from src.data.models.batch import Batch
from src.tasks.aggregation import AsyncSessionLocal


@celery_app.task(bind=True, max_retries=1)  # type: ignore[untyped-decorator]
def import_batches_from_file(
    self: Task, file_url: str, user_id: int
) -> dict[str, Any]:
    """Импорт партий из Excel/CSV файла по presigned URL"""

    async def _process_import() -> dict[str, Any]:

        with tempfile.NamedTemporaryFile(
            delete=False, suffix=".xlsx"
        ) as tmp_file:
            async with httpx.AsyncClient() as client:
                response = await client.get(file_url)
                response.raise_for_status()
                tmp_file.write(response.content)
            tmp_path = tmp_file.name

        try:
            if tmp_path.endswith(".csv"):
                df = pd.read_csv(tmp_path)
            else:
                df = pd.read_excel(tmp_path)

            total_rows = len(df)
            created = 0
            skipped = 0
            errors = []

            async with AsyncSessionLocal() as session:
                for index, row in df.iterrows():
                    row_num = index + 2

                    try:
                        stmt = select(Batch).where(
                            Batch.batch_number == str(row["НомерПартии"]),
                            Batch.batch_date == row["ДатаПартии"],
                        )
                        result = await session.execute(stmt)
                        if result.scalar_one_or_none():
                            skipped += 1
                            errors.append(
                                {
                                    "row": row_num,
                                    "error": "Duplicate batch number and date",
                                }
                            )
                            continue

                        new_batch = Batch(
                            batch_number=str(row["НомерПартии"]),
                            batch_date=row["ДатаПартии"],
                            nomenclature=row["Номенклатура"],
                            work_center=row["РабочийЦентр"],
                            created_by=user_id,
                        )
                        session.add(new_batch)
                        created += 1

                        if created % 50 == 0:
                            await session.commit()

                    except Exception as e:
                        skipped += 1
                        errors.append({"row": row_num, "error": str(e)})

                await session.commit()
            trigger_webhook(
                event_type="import_completed",
                data={
                    "total_rows": total_rows,
                    "created": created,
                    "skipped": skipped,
                    "errors": errors[:50],
                },
            )

            return {
                "success": True,
                "total_rows": total_rows,
                "created": created,
                "skipped": skipped,
                "errors": errors,
            }
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    self.update_state(
        state="PROGRESS", meta={"current": "Processing", "total": "Pending"}
    )

    return asyncio.run(_process_import())
