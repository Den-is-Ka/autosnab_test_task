import re
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, StrictBool, field_validator

CADASTRAL_NUMBER_PATTERN = r"^\d{1,3}:\d{1,3}:\d{1,10}:\d{1,10}$"


class QueryStatus(str, Enum):
    PROCESSING = "processing"
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    FAILED = "failed"


class QueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    cadastral_number: str = Field(
        min_length=7,
        max_length=100,
        examples=["66:41:0101001:123"],
        description="Кадастровый номер в формате числа:числа:числа:числа",
    )
    latitude: float = Field(
        ge=-90,
        le=90,
        examples=[56.8389],
        description="Широта от -90 до 90",
    )
    longitude: float = Field(
        ge=-180,
        le=180,
        examples=[60.6057],
        description="Долгота от -180 до 180",
    )

    @field_validator("cadastral_number")
    @classmethod
    def validate_cadastral_number(cls, value: str) -> str:
        if not re.fullmatch(CADASTRAL_NUMBER_PATTERN, value):
            raise ValueError(
                "Cadastral number must match format: numbers:numbers:numbers:numbers"
            )
        return value


class ResultResponse(BaseModel):
    result: StrictBool


class ExternalCallResult(BaseModel):
    result: StrictBool
    response_payload: dict[str, Any]
    status_code: int


class HistoryItem(BaseModel):
    id: int
    cadastral_number: str
    latitude: float
    longitude: float
    status: QueryStatus
    result: bool | None
    external_response: dict[str, Any] | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    duration_ms: int | None = None


class HistoryResponse(BaseModel):
    items: list[HistoryItem]
    total: int
    limit: int
    offset: int


class ErrorDetail(BaseModel):
    request_id: int
    status: QueryStatus
    message: str
