"""Tests for POST /v1/recognize-embedding.

The on-device path: the Flutter client computes the face embedding on
the phone (experiment 004) and sends only the 512-d vector. The server
never sees the image, so there's no embedder in this endpoint's flow —
just matching against the PersonStore and LLM-phrasing the result.
"""
from __future__ import annotations

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.perception.face import EMBEDDING_DIM
from app.persons.store import PersonStore
from app.providers.mock import MockProvider
from app.settings import Settings


ADMIN = ("carer", "shhh")


@pytest.fixture(autouse=True)
def wired_app(tmp_path):
    settings = Settings(
        persons_db_path=str(tmp_path / "persons.json"),
        admin_username=ADMIN[0],
        admin_password=ADMIN[1],
    )
    app.state.settings = settings
    app.state.provider = MockProvider(reply="Ese es Rodolfo, tu hijo.")
    app.state.person_store = PersonStore(settings.persons_db_path)
    yield


def _client() -> AsyncClient:
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _admin_client() -> AsyncClient:
    return AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", auth=ADMIN
    )


def _unit_vector(seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    v = rng.standard_normal(EMBEDDING_DIM).astype(np.float32)
    return v / np.linalg.norm(v)


async def test_recognize_embedding_matches_active_person():
    emb = _unit_vector(42)
    app.state.person_store.add("Rodolfo", "tu hijo mayor", emb)

    async with _admin_client() as ac:
        r = await ac.post(
            "/v1/recognize-embedding",
            json={"embedding": emb.tolist(), "language": "es"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["match"] is not None
    assert body["match"]["name"] == "Rodolfo"
    assert body["match"]["similarity"] >= 0.99
    assert body["spoken"] == "Ese es Rodolfo, tu hijo."


async def test_recognize_embedding_no_match_returns_unknown_es():
    app.state.person_store.add("Rodolfo", "tu hijo", _unit_vector(42))
    # High-dim Gaussians from different seeds are near-orthogonal,
    # so this stays well under the 0.45 threshold.
    other = _unit_vector(999)

    async with _admin_client() as ac:
        r = await ac.post(
            "/v1/recognize-embedding",
            json={"embedding": other.tolist(), "language": "es"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["match"] is None
    assert "no reconozco" in body["spoken"].lower()


async def test_recognize_embedding_no_match_returns_unknown_en():
    other = _unit_vector(7)

    async with _admin_client() as ac:
        r = await ac.post(
            "/v1/recognize-embedding",
            json={"embedding": other.tolist(), "language": "en"},
        )

    assert r.status_code == 200
    body = r.json()
    assert body["match"] is None
    assert "don't recognize" in body["spoken"].lower()


async def test_recognize_embedding_does_not_match_pending_person():
    emb = _unit_vector(42)
    app.state.person_store.add("Rodolfo", "tu hijo", emb, status="pending")

    async with _admin_client() as ac:
        r = await ac.post(
            "/v1/recognize-embedding",
            json={"embedding": emb.tolist(), "language": "es"},
        )

    assert r.status_code == 200
    assert r.json()["match"] is None


async def test_recognize_embedding_rejects_wrong_dim():
    async with _admin_client() as ac:
        r = await ac.post(
            "/v1/recognize-embedding",
            json={"embedding": [0.0] * 256, "language": "es"},
        )
    assert r.status_code == 422


async def test_recognize_embedding_requires_admin_auth():
    async with _client() as ac:
        r = await ac.post(
            "/v1/recognize-embedding",
            json={"embedding": [0.0] * EMBEDDING_DIM, "language": "es"},
        )
    assert r.status_code == 401
