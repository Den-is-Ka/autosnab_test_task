from typing import Any

import httpx
from pydantic import ValidationError

from app.config import settings
from app.schemas import ExternalCallResult, QueryRequest, ResultResponse


class ExternalServiceError(Exception):
    """Base exception for expected external service failures."""


class ExternalServiceTimeout(ExternalServiceError):
    pass


class ExternalServiceUnavailable(ExternalServiceError):
    pass


class ExternalServiceInvalidResponse(ExternalServiceError):
    def __init__(self, message: str, response_payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.response_payload = response_payload


class ExternalServiceClient:
    def __init__(self, http_client: httpx.AsyncClient):
        self.http_client = http_client

    async def request_result(self, query_data: QueryRequest) -> ExternalCallResult:
        try:
            response = await self.http_client.post(
                settings.external_server_url,
                json=query_data.model_dump(),
            )
            response.raise_for_status()
        except httpx.TimeoutException as error:
            raise ExternalServiceTimeout("External service timeout") from error
        except httpx.HTTPStatusError as error:
            raise ExternalServiceUnavailable(
                f"External service returned HTTP {error.response.status_code}"
            ) from error
        except httpx.RequestError as error:
            raise ExternalServiceUnavailable(
                f"External service connection error: {error.__class__.__name__}"
            ) from error

        try:
            payload = response.json()
        except ValueError as error:
            raise ExternalServiceInvalidResponse(
                "External service returned invalid JSON"
            ) from error

        if not isinstance(payload, dict):
            raise ExternalServiceInvalidResponse(
                "External service response must be a JSON object"
            )

        try:
            validated = ResultResponse.model_validate(payload)
        except ValidationError as error:
            raise ExternalServiceInvalidResponse(
                "External service returned invalid response schema",
                response_payload=payload,
            ) from error

        return ExternalCallResult(
            result=validated.result,
            response_payload=payload,
            status_code=response.status_code,
        )
