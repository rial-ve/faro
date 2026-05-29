"""Side-by-side empirical comparison of the two face embedders on the same
fixture set. Used by experiment 003 to validate that MobileFaceNet
preserves the separation between same-person and different-person.
"""
from __future__ import annotations

import time
from pathlib import Path

from app.perception.face import (
    FaceEmbedder,
    InsightFaceEmbedder,
    MobileFaceNetEmbedder,
    cosine_similarity,
)


PHOTOS = {
    "Einstein 1921 (enrolada)":  "test_data/einstein_1921.jpg",
    "Einstein 1920":              "test_data/einstein_v2_1920.jpg",
    "Einstein 1921 re-crop":      "test_data/einstein_v3_1921crop.jpg",
    "Marie Curie (otra persona)": "test_data/marie_curie.jpg",
}

REF_NAME = "Einstein 1921 (enrolada)"
THRESHOLD = 0.5


def _embed_all(embedder: FaceEmbedder, photos: dict[str, str]) -> tuple[dict, float]:
    """Return (embeddings, avg_embed_time_ms)."""
    embeddings: dict[str, object] = {}
    timings: list[float] = []
    for name, path in photos.items():
        bytes_ = Path(path).read_bytes()
        t0 = time.perf_counter()
        emb = embedder.embed(bytes_)
        elapsed_ms = (time.perf_counter() - t0) * 1000
        if emb is None:
            print(f"  NO FACE detected in {name} (embedder={embedder.name})")
            continue
        embeddings[name] = emb
        timings.append(elapsed_ms)
    avg_ms = sum(timings) / len(timings) if timings else 0.0
    return embeddings, avg_ms


def _print_table(label: str, embeddings: dict, avg_ms: float) -> None:
    print()
    print(f"━━ {label} ━━  (avg embed: {avg_ms:.0f} ms/face)")
    ref = embeddings[REF_NAME]
    header = "pareja".ljust(60) + "  cosine sim  verdict"
    print(header)
    print("-" * len(header))
    for other_name, other in embeddings.items():
        if other_name == REF_NAME:
            continue
        sim = cosine_similarity(ref, other)
        verdict = "MATCH" if sim >= THRESHOLD else "no match"
        row = f"{REF_NAME}  vs  {other_name}"
        print(f"{row.ljust(60)}  {sim:+.4f}      {verdict}")


def _summary(label: str, embeddings: dict) -> dict[str, float]:
    ref = embeddings[REF_NAME]
    same_sims = []
    diff_sims = []
    for other_name, other in embeddings.items():
        if other_name == REF_NAME:
            continue
        sim = cosine_similarity(ref, other)
        if "Curie" in other_name:
            diff_sims.append(sim)
        else:
            same_sims.append(sim)
    return {
        "min_same": min(same_sims),
        "max_same": max(same_sims),
        "max_diff": max(diff_sims),
        "gap": min(same_sims) - max(diff_sims),
    }


def _print_comparison(buffalo: dict, mobile: dict) -> None:
    print()
    print("━━ comparación contra criterios del test card 003 ━━")
    header = f"{'métrica':<28}  {'buffalo_l':>12}  {'mobilefacenet':>16}  criterio"
    print(header)
    print("-" * len(header))

    def row(label: str, key: str, criterion: str, fmt: str = "+.4f") -> None:
        b, m = buffalo[key], mobile[key]
        print(f"{label:<28}  {b:>+12.4f}  {m:>+16.4f}  {criterion}")

    row("similitud mín misma persona",  "min_same", "MobileFaceNet ≥ 0.4")
    row("similitud máx misma persona",  "max_same", "—")
    row("similitud máx distinta",       "max_diff", "MobileFaceNet < 0.2")
    row("gap (mín misma − máx dist.)",  "gap",      "MobileFaceNet > 0.2")


def main() -> None:
    print("Loading embedders (downloads buffalo_s / buffalo_l on first run)...")
    buf = InsightFaceEmbedder()
    mob = MobileFaceNetEmbedder()
    buf._load()
    mob._load()
    print("loaded")

    buf_embeddings, buf_avg = _embed_all(buf, PHOTOS)
    mob_embeddings, mob_avg = _embed_all(mob, PHOTOS)

    _print_table("InsightFace buffalo_l (ResNet-50, 166 MB)", buf_embeddings, buf_avg)
    _print_table("MobileFaceNet buffalo_s (13 MB)",           mob_embeddings, mob_avg)

    buf_sum = _summary("buffalo_l", buf_embeddings)
    mob_sum = _summary("mobilefacenet", mob_embeddings)
    _print_comparison(buf_sum, mob_sum)


if __name__ == "__main__":
    main()
