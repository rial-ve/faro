import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.providers.mock import MockProvider
from app.settings import Settings


ADMIN = ("carer", "shhh")


@pytest.fixture(autouse=True)
def _wired():
    app.state.settings = Settings(admin_username=ADMIN[0], admin_password=ADMIN[1])
    app.state.provider = MockProvider(reply="hello")
    yield


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _admin_client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test", auth=ADMIN)


async def test_healthz_is_public():
    async with _client() as ac:
        r = await ac.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_models_endpoint_reports_provider():
    async with _admin_client() as ac:
        r = await ac.get("/v1/models")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "mock"
    assert body["quantization"] == "none"


async def test_chat_completions_returns_generation_result():
    async with _admin_client() as ac:
        r = await ac.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "hello"
    assert body["stop_reason"] == "stop"


async def test_chat_completions_rejects_out_of_range_temperature():
    async with _admin_client() as ac:
        r = await ac.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 9.0,
            },
        )
    assert r.status_code == 422


# ---------------------------------------------------------------------------
# Auth behavior on admin routes
# ---------------------------------------------------------------------------


async def test_admin_route_without_credentials_returns_401():
    async with _client() as ac:
        r = await ac.get("/v1/models")
    assert r.status_code == 401


async def test_admin_route_with_wrong_credentials_returns_401():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", auth=("carer", "wrong")
    ) as ac:
        r = await ac.get("/v1/models")
    assert r.status_code == 401


async def test_admin_route_returns_503_when_credentials_not_configured():
    app.state.settings = Settings(admin_username="", admin_password="")
    async with _admin_client() as ac:
        r = await ac.get("/v1/models")
    assert r.status_code == 503
