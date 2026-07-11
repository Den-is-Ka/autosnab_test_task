import httpx
import pytest
import pytest_asyncio

from app.main import create_app, get_external_client, get_repository
from tests.fakes import FakeExternalClient, FakeRepository


@pytest.fixture

def repository() -> FakeRepository:
    return FakeRepository()


@pytest.fixture

def external_client() -> FakeExternalClient:
    return FakeExternalClient(result=True)


@pytest.fixture

def app(repository: FakeRepository, external_client: FakeExternalClient):
    application = create_app(enable_lifespan=False)
    application.dependency_overrides[get_repository] = lambda: repository
    application.dependency_overrides[get_external_client] = lambda: external_client
    return application


@pytest_asyncio.fixture
async def client(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as test_client:
        yield test_client
