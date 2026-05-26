from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path

import numpy as np
from pydantic import BaseModel, Field

from app.perception.face import cosine_similarity


class Person(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str
    embedding: list[float]


class Match(BaseModel):
    person: Person
    similarity: float


class PersonStore:
    """JSON-file-backed store of enrolled persons.

    SQLite would be overkill at this scale and the embeddings are small
    enough that linear scan is fine for the MVP. The on-device store will
    mirror this shape (likely SQLite there for durability).
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

    def list(self) -> list[Person]:
        with self._lock:
            return list(self._persons)

    def add(self, name: str, description: str, embedding: np.ndarray) -> Person:
        person = Person(
            name=name,
            description=description,
            embedding=embedding.astype(float).tolist(),
        )
        with self._lock:
            self._persons.append(person)
            self._save()
        return person

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
            candidates = list(self._persons)
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
