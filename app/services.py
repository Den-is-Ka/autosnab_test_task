import logging
from dataclasses import dataclass
from time import perf_counter
from typing import Any, Protocol

from app.external_client import (
    ExternalServiceClient,
    ExternalServiceInvalidResponse,
    ExternalServiceTimeout,
    ExternalServiceUnavailable,
)
from app.schemas import ExternalCallResult, QueryRequest, QueryStatus

logger = logging.getLogger(__name__)


class RepositoryProtocol(Protocol):
    async def create_pending_request(self, query_data: QueryRequest) -> dict[str, Any]: ...

    async def mark_completed(
        self,
        request_id: int,
        result: bool,
        external_response: dict[str, Any],
        duration_ms: int,
    ) -> dict[str, Any]: ...

    async def mark_failed(
        self,
        request_id: int,
        status: QueryStatus,
        error_message: str,
        duration_ms: int,
        external_response: dict[str, Any] | None = None,
    ) -> dict[str, Any]: ...


class ExternalClientProtocol(Protocol):
    async def request_result(self, query_data: QueryRequest) -> ExternalCallResult: ...


@dataclass(slots=True)
class QueryProcessingError(Exception):
    status_code: int
    request_id: int
    status: QueryStatus
    message: str


class QueryService:
    def __init__(
        self,
        repository: RepositoryProtocol,
        external_client: ExternalClientProtocol | ExternalServiceClient,
    ) -> None:
        self.repository = repository
        self.external_client = external_client

    async def execute(self, query_data: QueryRequest) -> dict[str, Any]:
        pending_record = await self.repository.create_pending_request(query_data)
        request_id = pending_record["id"]
        started_at = perf_counter()

        logger.info(
            "External query started request_id=%s cadastral_number=%s",
            request_id,
            query_data.cadastral_number,
        )

        try:
            external_result = await self.external_client.request_result(query_data)
        except ExternalServiceTimeout as error:
            duration_ms = self._duration_ms(started_at)
            await self.repository.mark_failed(
                request_id=request_id,
                status=QueryStatus.TIMEOUT,
                error_message=str(error),
                duration_ms=duration_ms,
            )
            logger.warning("External query timed out request_id=%s", request_id)
            raise QueryProcessingError(
                status_code=504,
                request_id=request_id,
                status=QueryStatus.TIMEOUT,
                message=str(error),
            ) from error
        except ExternalServiceInvalidResponse as error:
            duration_ms = self._duration_ms(started_at)
            await self.repository.mark_failed(
                request_id=request_id,
                status=QueryStatus.FAILED,
                error_message=str(error),
                duration_ms=duration_ms,
                external_response=error.response_payload,
            )
            logger.warning("Invalid external response request_id=%s", request_id)
            raise QueryProcessingError(
                status_code=502,
                request_id=request_id,
                status=QueryStatus.FAILED,
                message=str(error),
            ) from error
        except ExternalServiceUnavailable as error:
            duration_ms = self._duration_ms(started_at)
            await self.repository.mark_failed(
                request_id=request_id,
                status=QueryStatus.FAILED,
                error_message=str(error),
                duration_ms=duration_ms,
            )
            logger.warning("External service unavailable request_id=%s", request_id)
            raise QueryProcessingError(
                status_code=502,
                request_id=request_id,
                status=QueryStatus.FAILED,
                message=str(error),
            ) from error
        except Exception as error:
            duration_ms = self._duration_ms(started_at)
            safe_message = "Unexpected external service error"
            await self.repository.mark_failed(
                request_id=request_id,
                status=QueryStatus.FAILED,
                error_message=safe_message,
                duration_ms=duration_ms,
            )
            logger.exception("Unexpected external error request_id=%s", request_id)
            raise QueryProcessingError(
                status_code=502,
                request_id=request_id,
                status=QueryStatus.FAILED,
                message=safe_message,
            ) from error

        duration_ms = self._duration_ms(started_at)
        completed_record = await self.repository.mark_completed(
            request_id=request_id,
            result=external_result.result,
            external_response=external_result.response_payload,
            duration_ms=duration_ms,
        )
        logger.info(
            "External query completed request_id=%s result=%s duration_ms=%s",
            request_id,
            external_result.result,
            duration_ms,
        )
        return completed_record

    @staticmethod
    def _duration_ms(started_at: float) -> int:
        return max(0, round((perf_counter() - started_at) * 1000))
