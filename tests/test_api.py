import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.providers.mock import MockProvider


@pytest.fixture(autouse=True)
def _mock_provider():
    app.state.provider = MockProvider(reply="hello")
    yield


async def test_healthz():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        r = await ac.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


async def test_models_endpoint_reports_provider():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        r = await ac.get("/v1/models")
    assert r.status_code == 200
    body = r.json()
    assert body["provider"] == "mock"
    assert body["quantization"] == "none"


async def test_chat_completions_returns_generation_result():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "hi"}]},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["text"] == "hello"
    assert body["stop_reason"] == "stop"


async def test_chat_completions_rejects_out_of_range_temperature():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        r = await ac.post(
            "/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "hi"}],
                "temperature": 9.0,
            },
        )
    assert r.status_code == 422
