from pydantic import BaseModel


class ReportRequest(BaseModel):
    format: str = "excel"
    email: str | None = None


class ReportTaskResponse(BaseModel):
    task_id: str
    status: str
