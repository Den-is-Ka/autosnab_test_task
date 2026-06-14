from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_ping():
    response = client.get("/ping")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_result():
    response = client.get("/result")

    assert response.status_code == 200
    assert "result" in response.json()
    assert isinstance(response.json()["result"], bool)


def test_query_validation_invalid_cadastral_number():
    response = client.post(
        "/query",
        json={
            "cadastral_number": "bad-number",
            "latitude": 56.8389,
            "longitude": 60.6057,
        },
    )

    assert response.status_code == 422


def test_query_validation_invalid_latitude():
    response = client.post(
        "/query",
        json={
            "cadastral_number": "66:41:0101001:123",
            "latitude": 120,
            "longitude": 60.6057,
        },
    )

    assert response.status_code == 422


def test_query_validation_invalid_longitude():
    response = client.post(
        "/query",
        json={
            "cadastral_number": "66:41:0101001:123",
            "latitude": 56.8389,
            "longitude": 300,
        },
    )

    assert response.status_code == 422
