"""End-to-end smoke for the on-device path (experiment 004).

Emulates the Flutter pipeline in pure Python so the conversion +
preprocessing path can be measured without a phone:

1. Server-style embedding: full insightface pipeline (5-point landmark
   alignment via buffalo_s, then ONNX MobileFaceNet). What the server
   does behind /v1/recognize.

2. Phone-style embedding: just the bounding box → 1.1x square crop →
   linear resize to 112x112 → RGB normalize to [-1,1] → TFLite
   (the same .tflite the Flutter app bundles). What the app does
   in lib/face/embedder.dart.

Reports:
  - cos(server, phone) on the test image: tells us how much the
    preprocessing divergence (alignment vs no alignment) costs us
    in similarity terms.

If FARO_BASE_URL is set, also posts to the live backend:
  - POST /v1/recognize with the original bytes
  - POST /v1/recognize-embedding with the phone-side vector
  - prints both responses for visual comparison

Usage from the repo root:

    .venv/bin/python scripts/smoke_recognize_embedding.py \\
        [enroll_image] [recognize_image]

Defaults: enroll=test_data/yo.jpg, recognize=test_data/yo2.jpg.

If FARO_BASE_URL + FARO_ADMIN_USERNAME + FARO_ADMIN_PASSWORD are set,
the script also enrolls and posts. Otherwise it runs purely locally.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import cv2
import numpy as np
import tensorflow as tf
from insightface.app import FaceAnalysis
from PIL import Image, ImageOps

from app.perception.face import MobileFaceNetEmbedder, cosine_similarity

REPO_ROOT = Path(__file__).resolve().parent.parent
TFLITE_MODEL = REPO_ROOT / "app-flutter" / "assets" / "models" / "mobilefacenet.tflite"


def _load_rgb(path: Path) -> np.ndarray:
    img = Image.open(path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    return np.array(img)


def _bbox_largest(detector: FaceAnalysis, rgb: np.ndarray) -> tuple[int, int, int, int]:
    bgr = rgb[:, :, ::-1]
    faces = detector.get(bgr)
    if not faces:
        sys.exit("No face detected — try a clearer photo.")
    f = max(faces, key=lambda f: (f.bbox[2] - f.bbox[0]) * (f.bbox[3] - f.bbox[1]))
    x1, y1, x2, y2 = f.bbox.astype(int).tolist()
    return x1, y1, x2, y2


def _phone_style_crop(rgb: np.ndarray, bbox: tuple[int, int, int, int]) -> np.ndarray:
    x1, y1, x2, y2 = bbox
    w, h = x2 - x1, y2 - y1
    cx, cy = x1 + w / 2, y1 + h / 2
    side = max(w, h) * 1.1
    half = side / 2
    L = max(0, int(cx - half))
    T = max(0, int(cy - half))
    R = min(rgb.shape[1], int(cx + half))
    B = min(rgb.shape[0], int(cy + half))
    crop = rgb[T:B, L:R]
    return cv2.resize(crop, (112, 112), interpolation=cv2.INTER_LINEAR)


def _phone_embed(rgb_crop: np.ndarray, interp: tf.lite.Interpreter) -> np.ndarray:
    normed = (rgb_crop.astype(np.float32) - 127.5) / 127.5
    nhwc = normed[np.newaxis, :, :, :]
    in_info = interp.get_input_details()[0]
    out_info = interp.get_output_details()[0]
    interp.set_tensor(in_info["index"], nhwc.astype(in_info["dtype"]))
    interp.invoke()
    raw = interp.get_tensor(out_info["index"]).reshape(-1).astype(np.float32)
    return raw / (np.linalg.norm(raw) + 1e-12)


def _maybe_post(
    base_url: str,
    user: str,
    password: str,
    enroll_path: Path,
    recognize_path: Path,
    phone_embedding: np.ndarray,
) -> None:
    import requests

    auth = (user, password)
    name = f"smoke_{enroll_path.stem}"

    with enroll_path.open("rb") as f:
        r = requests.post(
            f"{base_url}/v1/persons",
            auth=auth,
            files={"image": (enroll_path.name, f, "image/jpeg")},
            data={"name": name, "description": "smoke test from 004.10"},
            timeout=30,
        )
    if r.status_code not in (200, 201):
        print(f"  enroll failed ({r.status_code}): {r.text}")
        return
    pid = r.json()["id"]
    print(f"  enrolled as id={pid}")

    try:
        with recognize_path.open("rb") as f:
            r1 = requests.post(
                f"{base_url}/v1/recognize",
                auth=auth,
                files={"image": (recognize_path.name, f, "image/jpeg")},
                data={"language": "es"},
                timeout=30,
            )
        print("  /v1/recognize:           ", r1.json())

        r2 = requests.post(
            f"{base_url}/v1/recognize-embedding",
            auth=auth,
            json={"embedding": phone_embedding.tolist(), "language": "es"},
            timeout=30,
        )
        print("  /v1/recognize-embedding: ", r2.json())
    finally:
        requests.delete(f"{base_url}/v1/persons/{pid}", auth=auth, timeout=10)
        print(f"  cleaned up id={pid}")


def main() -> None:
    args = sys.argv[1:]
    enroll_path = Path(args[0] if len(args) > 0 else "test_data/yo.jpg")
    recognize_path = Path(args[1] if len(args) > 1 else "test_data/yo2.jpg")
    if not TFLITE_MODEL.exists():
        sys.exit(
            f"{TFLITE_MODEL} missing — run scripts/convert_mobilefacenet_to_tflite.py first."
        )

    print(f"Enroll image:    {enroll_path}")
    print(f"Recognize image: {recognize_path}")

    print("\n• Loading insightface buffalo_s detector + ONNX recogniser…")
    detector = FaceAnalysis(name="buffalo_s", allowed_modules=["detection"])
    detector.prepare(ctx_id=-1, det_size=(640, 640))

    print("• Loading bundled TFLite (mirrors what the app loads on-device)…")
    interp = tf.lite.Interpreter(model_path=str(TFLITE_MODEL))
    interp.allocate_tensors()

    server_embedder = MobileFaceNetEmbedder()

    def server_embed(path: Path) -> np.ndarray:
        emb = server_embedder.embed(path.read_bytes())
        if emb is None:
            sys.exit(f"Server-side embed failed (no face) for {path}")
        return emb

    def phone_embed_path(path: Path) -> np.ndarray:
        rgb = _load_rgb(path)
        bbox = _bbox_largest(detector, rgb)
        crop = _phone_style_crop(rgb, bbox)
        return _phone_embed(crop, interp)

    print("\nComputing four embeddings on (enroll, recognize)…")
    s_enroll = server_embed(enroll_path)
    s_recog = server_embed(recognize_path)
    p_enroll = phone_embed_path(enroll_path)
    p_recog = phone_embed_path(recognize_path)
    phone_emb = p_recog  # for the live POST below

    matrix = [
        ("server enroll  vs  server recognize", cosine_similarity(s_enroll, s_recog)),
        ("phone enroll   vs  phone recognize",  cosine_similarity(p_enroll, p_recog)),
        ("server enroll  vs  phone recognize",  cosine_similarity(s_enroll, p_recog)),
        ("server recog.  vs  phone recognize",  cosine_similarity(s_recog, p_recog)),
    ]
    print()
    print("Similarity matrix")
    print("-" * 60)
    for label, value in matrix:
        verdict = "MATCH" if value >= 0.45 else "no match"
        print(f"  {label:<42}  {value:+.4f}  {verdict}")
    print()
    print("Reading guide")
    print("-" * 60)
    print(
        "  row 1 — baseline: same person, both server-side. ≥ 0.45 expected.\n"
        "  row 2 — phone path consistent with itself.\n"
        "  row 3 — enrol server, recognise phone. THIS is the deployed shape\n"
        "          if a person was enrolled via the 002 web form and then\n"
        "          recognised from the Flutter app.\n"
        "  row 4 — same photo, different preprocessing. Tells us the pure\n"
        "          alignment delta between server (5-pt landmarks) and\n"
        "          phone (simple bbox square crop)."
    )

    base = os.environ.get("FARO_BASE_URL")
    user = os.environ.get("FARO_ADMIN_USERNAME")
    pwd = os.environ.get("FARO_ADMIN_PASSWORD")
    if base and user and pwd:
        print(f"\n— posting to live backend at {base} —")
        _maybe_post(base, user, pwd, enroll_path, recognize_path, phone_emb)
    else:
        print(
            "\nFARO_BASE_URL / FARO_ADMIN_USERNAME / FARO_ADMIN_PASSWORD not set;"
            " skipping live POSTs.\n"
            "To exercise the wire too:\n"
            "  FARO_BASE_URL=http://localhost:8000 \\\n"
            "  FARO_ADMIN_USERNAME=carer FARO_ADMIN_PASSWORD=... \\\n"
            "  .venv/bin/python scripts/smoke_recognize_embedding.py"
        )


if __name__ == "__main__":
    main()
