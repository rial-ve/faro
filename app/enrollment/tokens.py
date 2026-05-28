from __future__ import annotations

import json
import secrets
import threading
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field


def _new_token() -> str:
    # 32 url-safe chars ≈ 192 bits of entropy; not guessable in practice.
    return secrets.token_urlsafe(24)


class EnrollmentToken(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    token: str = Field(default_factory=_new_token)
    label: str = ""
    created_at: float = Field(default_factory=time.time)


class TokenStore:
    """JSON-file-backed store of enrollment tokens.

    A token authorizes anyone with the link to add persons in the
    ``pending`` state. Tokens are revocable by id.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._tokens: list[EnrollmentToken] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text())
        self._tokens = [EnrollmentToken(**row) for row in raw]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([t.model_dump() for t in self._tokens], indent=2)
        )

    def list(self) -> list[EnrollmentToken]:
        with self._lock:
            return list(self._tokens)

    def create(self, label: str = "") -> EnrollmentToken:
        t = EnrollmentToken(label=label)
        with self._lock:
            self._tokens.append(t)
            self._save()
        return t

    def revoke(self, token_id: str) -> bool:
        with self._lock:
            before = len(self._tokens)
            self._tokens = [t for t in self._tokens if t.id != token_id]
            if len(self._tokens) == before:
                return False
            self._save()
            return True

    def is_valid(self, token: str) -> bool:
        with self._lock:
            return any(
                secrets.compare_digest(t.token, token) for t in self._tokens
            )
