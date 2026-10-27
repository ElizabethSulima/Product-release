from typing import Any

from fastapi import APIRouter

from src.api.v1.schemas.task import TaskProgressResponse
from src.celery_app import celery_app

router = APIRouter(prefix="/tasks", tags=["Tasks"])


@router.get("/{task_id}", response_model=TaskProgressResponse)
async def get_task_status(task_id: str) -> dict[str, Any]:
    """Получение статуса задачи Celery"""
    task = celery_app.AsyncResult(task_id)

    response = {
        "task_id": task.id,
        "status": task.status,
        "result": None,
        "message": None,
    }

    if task.status == "PENDING":
        response["message"] = "Task is waiting to be processed"
    elif task.status == "PROGRESS":
        response["result"] = task.info
    elif task.status == "SUCCESS":
        response["result"] = task.result
    elif task.status == "FAILURE":
        response["result"] = None
        response["message"] = f"Task failed: {task.info}"
    else:
        response["status"] = task.status

    return response
