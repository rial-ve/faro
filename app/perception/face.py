"""Face detection + embedding.

Same role as ``LLMProvider`` but for vision: a single protocol with a
server-side implementation (insightface / ONNX Runtime) that mirrors what
will run on the phone via ONNX Runtime Mobile.
"""
from __future__ import annotations

import io
from typing import Any, Protocol

import numpy as np
from PIL import Image, ImageOps


EMBEDDING_DIM = 512


class FaceEmbedder(Protocol):
    name: str

    def embed(self, image_bytes: bytes) -> np.ndarray | None:
        """Return a 512-d L2-normalized embedding for the largest face, or
        None if no face is detected."""
        ...


class InsightFaceEmbedder:
    """ArcFace via insightface (`buffalo_l`). 512-d embeddings, CPU ONNX."""

    name = "insightface-buffalo_l"

    def __init__(self, model_name: str = "buffalo_l") -> None:
        self._model_name = model_name
        self._app: Any = None

    def _load(self) -> Any:
        if self._app is not None:
            return self._app
        from insightface.app import FaceAnalysis

        app = FaceAnalysis(
            name=self._model_name,
            providers=["CPUExecutionProvider"],
            allowed_modules=["detection", "recognition"],
        )
        app.prepare(ctx_id=-1, det_size=(640, 640))
        self._app = app
        return app

    def embed(self, image_bytes: bytes) -> np.ndarray | None:
        img = Image.open(io.BytesIO(image_bytes))
        img = ImageOps.exif_transpose(img).convert("RGB")
        # insightface expects BGR HxWx3 numpy
        rgb = np.array(img)
        bgr = rgb[:, :, ::-1]
        faces = self._load().get(bgr)
        if not faces:
            return None
        # Pick the largest face by bounding-box area
        face = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
        emb = np.asarray(face.normed_embedding, dtype=np.float32)
        return emb


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-12))
