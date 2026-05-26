"""Download the smoke-test photos referenced by scripts/similarity_check.py
and the README accuracy table. All sources are Wikimedia Commons (public
domain). Idempotent: existing non-empty files are left alone.
"""
from __future__ import annotations

import sys
import urllib.error
import urllib.request
from pathlib import Path


# Wikimedia rejects requests without a meaningful User-Agent.
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36 "
    "faro-test-fetch"
)

PHOTOS: list[tuple[str, str]] = [
    (
        "einstein_1921.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/d/d3/Albert_Einstein_Head.jpg",
    ),
    (
        "einstein_v2_1920.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/1/10/Albert_Einstein_photo_1920.jpg",
    ),
    (
        "einstein_v3_1921crop.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/4/49/Albert_Einstein_1921_%28re-cropped%29.jpg",
    ),
    (
        "marie_curie.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/c/c8/Marie_Curie_c._1920s.jpg",
    ),
]


def main() -> int:
    dest = Path("test_data")
    dest.mkdir(exist_ok=True)
    failures = 0
    for filename, url in PHOTOS:
        target = dest / filename
        if target.exists() and target.stat().st_size > 0:
            print(f"  skip (already present): {target}")
            continue
        print(f"  fetching {url}")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        try:
            with urllib.request.urlopen(req, timeout=30) as response:
                target.write_bytes(response.read())
        except urllib.error.HTTPError as exc:
            print(f"    ERROR: HTTP {exc.code} — {exc.reason}", file=sys.stderr)
            failures += 1
            continue
        print(f"    -> {target} ({target.stat().st_size / 1024:.0f} KB)")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
