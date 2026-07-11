import pytest

from app.main import get_external_client
from tests.fakes import FakeExternalClient

VALID_PAYLOAD = {
    "cadastral_number": "66:41:0101001:123",
    "latitude": 56.8389,
    "longitude": 60.6057,
}


@pytest.mark.asyncio
async def test_ping(client):
    response = await client.get("/ping")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cadastral_number", "bad-number"),
        ("latitude", 120),
        ("latitude", -91),
        ("longitude", 181),
        ("longitude", -181),
    ],
)
async def test_query_validation(client, field, value):
    payload = VALID_PAYLOAD | {field: value}
    response = await client.post("/query", json=payload)
    assert response.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("external_result", [True, False])
async def test_query_saves_successful_result(
    app,
    client,
    repository,
    external_result,
):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        result=external_result
    )

    response = await client.post("/query", json=VALID_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "completed"
    assert body["result"] is external_result
    assert body["external_response"] == {"result": external_result}
    assert body["completed_at"] is not None
    assert len(repository.records) == 1


@pytest.mark.asyncio
async def test_timeout_is_saved_in_history(app, client, repository):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        error="timeout"
    )

    response = await client.post("/query", json=VALID_PAYLOAD)

    assert response.status_code == 504
    assert response.json()["detail"]["request_id"] == 1
    assert repository.records[0]["status"].value == "timeout"
    assert repository.records[0]["result"] is None
    assert repository.records[0]["error_message"] == "External service timeout"


@pytest.mark.asyncio
@pytest.mark.parametrize("error", ["unavailable", "invalid"])
async def test_external_failure_is_saved(app, client, repository, error):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(error=error)

    response = await client.post("/query", json=VALID_PAYLOAD)

    assert response.status_code == 502
    assert repository.records[0]["status"].value == "failed"
    assert repository.records[0]["result"] is None
    assert repository.records[0]["error_message"]


@pytest.mark.asyncio
async def test_history_filter_and_pagination(app, client, repository):
    first = VALID_PAYLOAD
    second = VALID_PAYLOAD | {"cadastral_number": "77:01:0001001:10"}

    await client.post("/query", json=first)
    await client.post("/query", json=second)
    await client.post("/query", json=first)

    response = await client.get(
        "/history",
        params={
            "cadastral_number": first["cadastral_number"],
            "limit": 1,
            "offset": 0,
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["limit"] == 1
    assert len(body["items"]) == 1
    assert body["items"][0]["cadastral_number"] == first["cadastral_number"]


@pytest.mark.asyncio
async def test_history_item_not_found(client):
    response = await client.get("/history/999")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_unexpected_external_error_is_safely_saved(app, client, repository):
    app.dependency_overrides[get_external_client] = lambda: FakeExternalClient(
        error="unexpected"
    )

    response = await client.post("/query", json=VALID_PAYLOAD)

    assert response.status_code == 502
    assert response.json()["detail"]["message"] == "Unexpected external service error"
    assert repository.records[0]["status"].value == "failed"
    assert repository.records[0]["error_message"] == "Unexpected external service error"
    assert "sensitive" not in response.text
