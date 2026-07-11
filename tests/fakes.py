from copy import deepcopy
from datetime import datetime, timezone
from typing import Any

from app.external_client import (
    ExternalServiceInvalidResponse,
    ExternalServiceTimeout,
    ExternalServiceUnavailable,
)
from app.schemas import ExternalCallResult, QueryRequest, QueryStatus


class FakeRepository:
    def __init__(self) -> None:
        self.records: list[dict[str, Any]] = []
        self.next_id = 1

    async def create_pending_request(self, query_data: QueryRequest) -> dict[str, Any]:
        record = {
            "id": self.next_id,
            "cadastral_number": query_data.cadastral_number,
            "latitude": query_data.latitude,
            "longitude": query_data.longitude,
            "status": QueryStatus.PROCESSING,
            "result": None,
            "external_response": None,
            "error_message": None,
            "created_at": datetime.now(timezone.utc),
            "completed_at": None,
            "duration_ms": None,
        }
        self.next_id += 1
        self.records.append(record)
        return deepcopy(record)

    async def mark_completed(
        self,
        request_id: int,
        result: bool,
        external_response: dict[str, Any],
        duration_ms: int,
    ) -> dict[str, Any]:
        record = self._find(request_id)
        record.update(
            status=QueryStatus.COMPLETED,
            result=result,
            external_response=external_response,
            error_message=None,
            completed_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
        )
        return deepcopy(record)

    async def mark_failed(
        self,
        request_id: int,
        status: QueryStatus,
        error_message: str,
        duration_ms: int,
        external_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        record = self._find(request_id)
        record.update(
            status=status,
            result=None,
            external_response=external_response,
            error_message=error_message,
            completed_at=datetime.now(timezone.utc),
            duration_ms=duration_ms,
        )
        return deepcopy(record)

    async def get_history(
        self,
        cadastral_number: str | None = None,
        status: QueryStatus | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        records = list(reversed(self.records))
        if cadastral_number is not None:
            records = [r for r in records if r["cadastral_number"] == cadastral_number]
        if status is not None:
            records = [r for r in records if r["status"] == status]
        return deepcopy(records[offset : offset + limit]), len(records)

    async def get_by_id(self, request_id: int) -> dict[str, Any] | None:
        try:
            return deepcopy(self._find(request_id))
        except LookupError:
            return None

    def _find(self, request_id: int) -> dict[str, Any]:
        for record in self.records:
            if record["id"] == request_id:
                return record
        raise LookupError(request_id)


class FakeExternalClient:
    def __init__(
        self,
        *,
        result: bool = True,
        error: str | None = None,
    ) -> None:
        self.result = result
        self.error = error

    async def request_result(self, _: QueryRequest) -> ExternalCallResult:
        if self.error == "timeout":
            raise ExternalServiceTimeout("External service timeout")
        if self.error == "unavailable":
            raise ExternalServiceUnavailable("External service connection error")
        if self.error == "invalid":
            raise ExternalServiceInvalidResponse(
                "External service returned invalid response schema",
                response_payload={"result": "true"},
            )
        if self.error == "unexpected":
            raise RuntimeError("sensitive internal failure")
        return ExternalCallResult(
            result=self.result,
            response_payload={"result": self.result},
            status_code=200,
        )
