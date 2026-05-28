from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Literal

import numpy as np
from pydantic import BaseModel, Field

from app.perception.face import cosine_similarity


PersonStatus = Literal["active", "pending"]


class Person(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str
    embedding: list[float]
    status: PersonStatus = "active"


class Match(BaseModel):
    person: Person
    similarity: float


class PersonStore:
    """JSON-file-backed store of enrolled persons.

    Persons live in one of two states:

    * ``active`` — included in face-recognition matching.
    * ``pending`` — created by a self-enrollment via a public token; ignored
      by recognition until a carer approves it.
    """

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._lock = threading.Lock()
        self._persons: list[Person] = []
        self._load()

    def _load(self) -> None:
        if not self._path.exists():
            return
        raw = json.loads(self._path.read_text())
        self._persons = [Person(**row) for row in raw]

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(
            json.dumps([p.model_dump() for p in self._persons], indent=2)
        )

    def list(self, status: PersonStatus | None = None) -> list[Person]:
        with self._lock:
            if status is None:
                return list(self._persons)
            return [p for p in self._persons if p.status == status]

    def get(self, person_id: str) -> Person | None:
        with self._lock:
            for p in self._persons:
                if p.id == person_id:
                    return p
        return None

    def add(
        self,
        name: str,
        description: str,
        embedding: np.ndarray,
        *,
        status: PersonStatus = "active",
    ) -> Person:
        person = Person(
            name=name,
            description=description,
            embedding=embedding.astype(float).tolist(),
            status=status,
        )
        with self._lock:
            self._persons.append(person)
            self._save()
        return person

    def set_status(self, person_id: str, status: PersonStatus) -> Person | None:
        with self._lock:
            for p in self._persons:
                if p.id == person_id:
                    p.status = status
                    self._save()
                    return p
        return None

    def delete(self, person_id: str) -> bool:
        with self._lock:
            before = len(self._persons)
            self._persons = [p for p in self._persons if p.id != person_id]
            if len(self._persons) == before:
                return False
            self._save()
            return True

    def find_closest(
        self, embedding: np.ndarray, threshold: float
    ) -> Match | None:
        with self._lock:
            candidates = [p for p in self._persons if p.status == "active"]
        if not candidates:
            return None
        best: Match | None = None
        for p in candidates:
            sim = cosine_similarity(embedding, np.asarray(p.embedding, dtype=np.float32))
            if best is None or sim > best.similarity:
                best = Match(person=p, similarity=sim)
        if best is None or best.similarity < threshold:
            return None
        return best
