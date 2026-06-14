import re
from datetime import datetime

from pydantic import BaseModel, Field, field_validator


CADASTRAL_NUMBER_PATTERN = r"^\d+:\d+:\d+:\d+$"


class QueryRequest(BaseModel):
    cadastral_number: str = Field(
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
        value = value.strip()

        if not re.match(CADASTRAL_NUMBER_PATTERN, value):
            raise ValueError(
                "Cadastral number must match format: numbers:numbers:numbers:numbers"
            )

        return value


class ResultResponse(BaseModel):
    result: bool


class HistoryItem(BaseModel):
    id: int
    cadastral_number: str
    latitude: float
    longitude: float
    result: bool
    created_at: datetime
