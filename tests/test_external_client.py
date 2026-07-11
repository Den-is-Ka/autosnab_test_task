import httpx
import pytest

from app.external_client import (
    ExternalServiceClient,
    ExternalServiceInvalidResponse,
    ExternalServiceTimeout,
    ExternalServiceUnavailable,
)
from app.schemas import QueryRequest

QUERY = QueryRequest(
    cadastral_number="66:41:0101001:123",
    latitude=56.8389,
    longitude=60.6057,
)


@pytest.mark.asyncio
async def test_external_client_accepts_boolean_result():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"result": False})
    )
    async with httpx.AsyncClient(transport=transport) as http_client:
        result = await ExternalServiceClient(http_client).request_result(QUERY)
    assert result.result is False


@pytest.mark.asyncio
async def test_external_client_rejects_string_boolean():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, json={"result": "true"})
    )
    async with httpx.AsyncClient(transport=transport) as http_client:
        with pytest.raises(ExternalServiceInvalidResponse):
            await ExternalServiceClient(http_client).request_result(QUERY)


@pytest.mark.asyncio
async def test_external_client_maps_timeout():
    def handler(request):
        raise httpx.ReadTimeout("timeout", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as http_client:
        with pytest.raises(ExternalServiceTimeout):
            await ExternalServiceClient(http_client).request_result(QUERY)


@pytest.mark.asyncio
async def test_external_client_maps_http_error():
    transport = httpx.MockTransport(
        lambda request: httpx.Response(500, json={"detail": "failure"})
    )
    async with httpx.AsyncClient(transport=transport) as http_client:
        with pytest.raises(ExternalServiceUnavailable):
            await ExternalServiceClient(http_client).request_result(QUERY)
