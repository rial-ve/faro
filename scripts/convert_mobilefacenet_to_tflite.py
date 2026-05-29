"""Convert MobileFaceNet ONNX → TFLite for the on-device path.

The server runs `w600k_mbf.onnx` from insightface's buffalo_s pack
(experiment 003). The Flutter app needs the same model in TFLite form
so the two ends produce embeddings in the same vector space.

Pipeline:

1. Locate `w600k_mbf.onnx` (downloaded by insightface on first server
   run; default cache path).
2. Convert ONNX → TFLite NHWC float32 via onnx2tf.
3. Sanity-check the conversion by feeding a synthetic input through
   both runtimes (onnxruntime and TFLite) and comparing cosine
   similarity. Anything below 0.999 is suspicious — the two engines
   should be numerically identical up to floating-point noise.
4. Copy the resulting TFLite into `app-flutter/assets/models/`.

Run from the repo root:

    .venv/bin/python scripts/convert_mobilefacenet_to_tflite.py
"""
from __future__ import annotations

import os
import shutil
import sys
from pathlib import Path

import numpy as np
import onnx2tf
import onnxruntime as ort
import tensorflow as tf

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ONNX = Path.home() / ".insightface" / "models" / "buffalo_s" / "w600k_mbf.onnx"
WORK_DIR = REPO_ROOT / "build" / "tflite-conversion"
TARGET = REPO_ROOT / "app-flutter" / "assets" / "models" / "mobilefacenet.tflite"


def convert() -> Path:
    if not SOURCE_ONNX.exists():
        sys.exit(
            f"Could not find {SOURCE_ONNX}. Run the server once to let "
            "insightface download the buffalo_s pack, then retry."
        )

    if WORK_DIR.exists():
        shutil.rmtree(WORK_DIR)
    WORK_DIR.mkdir(parents=True)

    print(f"Converting {SOURCE_ONNX} → {WORK_DIR}")
    onnx2tf.convert(
        input_onnx_file_path=str(SOURCE_ONNX),
        output_folder_path=str(WORK_DIR),
        copy_onnx_input_output_names_to_tflite=True,
        output_signaturedefs=False,
        not_use_onnxsim=False,
    )

    candidates = sorted(WORK_DIR.glob("*float32.tflite"))
    if not candidates:
        sys.exit("onnx2tf finished but no float32.tflite was produced.")
    return candidates[0]


def sanity_check(tflite_path: Path) -> None:
    """Run a random input through ONNX and TFLite, compare cosine similarity."""
    rng = np.random.default_rng(0)
    nchw = rng.standard_normal((1, 3, 112, 112)).astype(np.float32)

    ort_sess = ort.InferenceSession(str(SOURCE_ONNX), providers=["CPUExecutionProvider"])
    onnx_input_name = ort_sess.get_inputs()[0].name
    onnx_out = ort_sess.run(None, {onnx_input_name: nchw})[0].reshape(-1)

    interp = tf.lite.Interpreter(model_path=str(tflite_path))
    interp.allocate_tensors()
    in_info = interp.get_input_details()[0]
    out_info = interp.get_output_details()[0]
    nhwc = np.transpose(nchw, (0, 2, 3, 1)).astype(in_info["dtype"])
    interp.set_tensor(in_info["index"], nhwc)
    interp.invoke()
    tflite_out = interp.get_tensor(out_info["index"]).reshape(-1)

    def l2(x: np.ndarray) -> np.ndarray:
        return x / (np.linalg.norm(x) + 1e-12)

    cos = float(np.dot(l2(onnx_out), l2(tflite_out)))
    print(f"cosine(onnx, tflite) on random input = {cos:.6f}")
    if cos < 0.999:
        sys.exit(
            f"Conversion drift too high (cos={cos:.4f}). Bail before bundling."
        )


def main() -> None:
    tflite_path = convert()
    sanity_check(tflite_path)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(tflite_path, TARGET)
    size_mb = os.path.getsize(TARGET) / (1024 * 1024)
    print(f"Wrote {TARGET} ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()
