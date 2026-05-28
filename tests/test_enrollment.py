"""Tests for the self-enrollment flow: tokens, public form, approval, and
the interaction with face recognition (pending persons must NOT match).
"""
from __future__ import annotations

import hashlib

import numpy as np
import pytest
from httpx import ASGITransport, AsyncClient

from app.enrollment.tokens import TokenStore
from app.main import app
from app.persons.store import PersonStore
from app.providers.mock import MockProvider
from app.settings import Settings


# ---------------------------------------------------------------------------
# Hermetic, deterministic stand-in for InsightFaceEmbedder.
# ---------------------------------------------------------------------------


class MockEmbedder:
    """Deterministic content-addressable embedder for tests.

    The same bytes always produce the same unit vector; different bytes
    produce different vectors. ``b"NO_FACE"`` returns None to exercise the
    "no face detected" branch.
    """

    name = "mock-embedder"

    def embed(self, image_bytes: bytes) -> np.ndarray | None:
        if image_bytes == b"NO_FACE":
            return None
        seed = int.from_bytes(hashlib.sha256(image_bytes).digest()[:8], "big")
        rng = np.random.default_rng(seed)
        v = rng.standard_normal(512).astype(np.float32)
        return v / np.linalg.norm(v)


# ---------------------------------------------------------------------------
# Per-test fixture: fresh app.state.*, with stores on a tmp path
# ---------------------------------------------------------------------------


ADMIN = ("carer", "shhh")


@pytest.fixture(autouse=True)
def wired_app(tmp_path):
    settings = Settings(
        persons_db_path=str(tmp_path / "persons.json"),
        tokens_db_path=str(tmp_path / "tokens.json"),
        admin_username=ADMIN[0],
        admin_password=ADMIN[1],
    )
    app.state.settings = settings
    app.state.provider = MockProvider(reply="Ese es ya está identificado.")
    app.state.face_embedder = MockEmbedder()
    app.state.person_store = PersonStore(settings.persons_db_path)
    app.state.token_store = TokenStore(settings.tokens_db_path)
    yield


def _client() -> AsyncClient:
    """Unauthenticated client — used for public /enroll/{token} endpoints."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _admin_client() -> AsyncClient:
    """Admin client — sends Basic Auth on every request."""
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test", auth=ADMIN)


# ---------------------------------------------------------------------------
# Token CRUD
# ---------------------------------------------------------------------------


async def test_create_token_returns_id_token_and_label():
    async with _admin_client() as ac:
        r = await ac.post("/v1/enrollment-tokens", json={"label": "abuela"})
    assert r.status_code == 201
    body = r.json()
    assert body["label"] == "abuela"
    assert len(body["id"]) == 12
    assert len(body["token"]) >= 30  # url-safe token


async def test_list_tokens_returns_created_token():
    async with _admin_client() as ac:
        await ac.post("/v1/enrollment-tokens", json={"label": "a"})
        await ac.post("/v1/enrollment-tokens", json={"label": "b"})
        r = await ac.get("/v1/enrollment-tokens")
    assert r.status_code == 200
    assert {t["label"] for t in r.json()} == {"a", "b"}


async def test_revoke_token_removes_it():
    async with _admin_client() as ac:
        created = (await ac.post("/v1/enrollment-tokens", json={"label": "x"})).json()
        r = await ac.delete(f"/v1/enrollment-tokens/{created['id']}")
        assert r.status_code == 204
        listed = (await ac.get("/v1/enrollment-tokens")).json()
    assert listed == []


async def test_revoke_unknown_token_returns_404():
    async with _admin_client() as ac:
        r = await ac.delete("/v1/enrollment-tokens/does-not-exist")
    assert r.status_code == 404


async def test_token_endpoints_require_admin_auth():
    async with _client() as ac:
        r = await ac.post("/v1/enrollment-tokens", json={"label": "x"})
    assert r.status_code == 401


# ---------------------------------------------------------------------------
# Public form
# ---------------------------------------------------------------------------


async def test_get_enroll_with_valid_token_returns_form():
    async with _admin_client() as admin, _client() as pub:
        token = (await admin.post("/v1/enrollment-tokens", json={"label": ""})).json()["token"]
        r = await pub.get(f"/enroll/{token}")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "<form" in r.text
    assert 'name="image"' in r.text
    assert "no se guarda" in r.text.lower()  # privacy notice present


async def test_get_enroll_with_invalid_token_returns_invalid_page():
    async with _client() as pub:
        r = await pub.get("/enroll/not-a-real-token")
    assert r.status_code == 200
    assert "inválido" in r.text.lower() or "expirado" in r.text.lower()
    assert "<form" not in r.text


async def test_post_enroll_with_valid_token_creates_pending_person():
    async with _admin_client() as admin, _client() as pub:
        token = (await admin.post("/v1/enrollment-tokens", json={})).json()["token"]

        r = await pub.post(
            f"/enroll/{token}",
            data={"name": "Rodolfo Campos", "description": "tu hijo mayor"},
            files={"image": ("yo.jpg", b"FAKE_RODOLFO_BYTES", "image/jpeg")},
        )
        assert r.status_code == 200
        assert "listo" in r.text.lower() or "recibimos" in r.text.lower()

        pending = (await admin.get("/v1/persons", params={"status": "pending"})).json()
        active = (await admin.get("/v1/persons", params={"status": "active"})).json()

    assert len(pending) == 1
    assert pending[0]["name"] == "Rodolfo Campos"
    assert pending[0]["description"] == "tu hijo mayor"
    assert pending[0]["status"] == "pending"
    assert active == []


async def test_post_enroll_with_invalid_token_does_not_create_person():
    async with _admin_client() as admin, _client() as pub:
        r = await pub.post(
            "/enroll/not-a-real-token",
            data={"name": "X", "description": "y"},
            files={"image": ("x.jpg", b"BYTES", "image/jpeg")},
        )
        assert r.status_code == 200
        assert "inválido" in r.text.lower() or "expirado" in r.text.lower()
        persons = (await admin.get("/v1/persons")).json()
    assert persons == []


async def test_post_enroll_with_no_face_re_renders_form_with_error():
    async with _admin_client() as admin, _client() as pub:
        token = (await admin.post("/v1/enrollment-tokens", json={})).json()["token"]
        r = await pub.post(
            f"/enroll/{token}",
            data={"name": "X", "description": "y"},
            files={"image": ("blank.jpg", b"NO_FACE", "image/jpeg")},
        )
        assert r.status_code == 200
        assert "<form" in r.text
        assert "rostro" in r.text.lower()
        persons = (await admin.get("/v1/persons")).json()
    assert persons == []


# ---------------------------------------------------------------------------
# Approval and recognition gating
# ---------------------------------------------------------------------------


async def test_approve_changes_status_from_pending_to_active():
    async with _admin_client() as admin, _client() as pub:
        token = (await admin.post("/v1/enrollment-tokens", json={})).json()["token"]
        await pub.post(
            f"/enroll/{token}",
            data={"name": "X", "description": "y"},
            files={"image": ("a.jpg", b"BYTES_A", "image/jpeg")},
        )
        pending = (await admin.get("/v1/persons", params={"status": "pending"})).json()
        person_id = pending[0]["id"]

        r = await admin.post(f"/v1/persons/{person_id}/approve")
        assert r.status_code == 200
        assert r.json()["status"] == "active"

        active = (await admin.get("/v1/persons", params={"status": "active"})).json()
    assert len(active) == 1
    assert active[0]["id"] == person_id


async def test_approve_unknown_person_returns_404():
    async with _admin_client() as ac:
        r = await ac.post("/v1/persons/does-not-exist/approve")
    assert r.status_code == 404


async def test_recognize_does_not_match_pending_person():
    async with _admin_client() as admin, _client() as pub:
        token = (await admin.post("/v1/enrollment-tokens", json={})).json()["token"]
        await pub.post(
            f"/enroll/{token}",
            data={"name": "X", "description": "y"},
            files={"image": ("a.jpg", b"BYTES_RODOLFO", "image/jpeg")},
        )
        r = await admin.post(
            "/v1/recognize",
            data={"language": "es"},
            files={"image": ("a.jpg", b"BYTES_RODOLFO", "image/jpeg")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["match"] is None
    assert "no reconozco" in body["spoken"].lower()


async def test_recognize_matches_after_approval():
    async with _admin_client() as admin, _client() as pub:
        token = (await admin.post("/v1/enrollment-tokens", json={})).json()["token"]
        await pub.post(
            f"/enroll/{token}",
            data={"name": "Rodolfo", "description": "tu hijo mayor"},
            files={"image": ("a.jpg", b"BYTES_RODOLFO", "image/jpeg")},
        )
        pending = (await admin.get("/v1/persons", params={"status": "pending"})).json()
        await admin.post(f"/v1/persons/{pending[0]['id']}/approve")

        # Recognize with the SAME bytes — MockEmbedder is deterministic so
        # similarity will be 1.0, well above the 0.5 threshold.
        r = await admin.post(
            "/v1/recognize",
            data={"language": "es"},
            files={"image": ("a.jpg", b"BYTES_RODOLFO", "image/jpeg")},
        )
    assert r.status_code == 200
    body = r.json()
    assert body["match"] is not None
    assert body["match"]["name"] == "Rodolfo"
    assert body["match"]["similarity"] >= 0.99
