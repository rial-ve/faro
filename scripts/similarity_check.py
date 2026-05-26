"""Quick empirical check: how does cosine similarity behave for
same-person-different-photos vs. different-person?"""
from pathlib import Path

from app.perception.face import InsightFaceEmbedder, cosine_similarity


def main() -> None:
    embedder = InsightFaceEmbedder()
    embedder._load()

    photos = {
        "Einstein 1921 (enrolada)":  "test_data/einstein_1921.jpg",
        "Einstein 1920":              "test_data/einstein_v2_1920.jpg",
        "Einstein 1921 re-crop":      "test_data/einstein_v3_1921crop.jpg",
        "Marie Curie (otra persona)": "test_data/marie_curie.jpg",
    }

    embeddings = {}
    for name, path in photos.items():
        emb = embedder.embed(Path(path).read_bytes())
        if emb is None:
            print(f"  NO FACE detected in {name}")
            continue
        embeddings[name] = emb

    ref_name = "Einstein 1921 (enrolada)"
    ref = embeddings[ref_name]

    header = "pareja".ljust(60) + "  cosine sim  verdict (umbral 0.5)"
    print()
    print(header)
    print("-" * len(header))
    for other_name, other in embeddings.items():
        if other_name == ref_name:
            continue
        sim = cosine_similarity(ref, other)
        verdict = "MATCH" if sim >= 0.5 else "no match"
        label = f"{ref_name}  vs  {other_name}"
        print(f"{label.ljust(60)}  {sim:+.4f}      {verdict}")


if __name__ == "__main__":
    main()
