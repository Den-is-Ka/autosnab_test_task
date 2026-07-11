import httpx
import pytest

from app.config import settings
from emulator.main import app


@pytest.mark.asyncio
async def test_emulator_returns_boolean(monkeypatch):
    monkeypatch.setattr(settings, "emulator_min_delay_seconds", 0)
    monkeypatch.setattr(settings, "emulator_max_delay_seconds", 0)
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://emulator") as client:
        response = await client.post(
            "/result",
            json={
                "cadastral_number": "66:41:0101001:123",
                "latitude": 56.8389,
                "longitude": 60.6057,
            },
        )
    assert response.status_code == 200
    assert isinstance(response.json()["result"], bool)
