from typing import Any

from pydantic import BaseModel, Field


class CompareBatchesRequest(BaseModel):
    batch_ids: list[int] = Field(
        ...,
        min_length=2,
        max_length=10,
        description="ID партий для сравнения (от 2 до 10)",
    )


class CompareBatchesResponse(BaseModel):
    batches: list[dict[str, Any]]
    average: dict[str, float]
