"""Scrape web images for the thin `backfill:` classes in labels.yaml.

Curated-scraping mitigation from SRS ML-1: these classes have ~50 usable images
in the public datasets, below the 150-image bar for the frozen split. Uses
DuckDuckGo image search (ddgs); every download is decoded with PIL and must
pass a min-side check before it is kept, so broken or junk files never land.
Images go to ml/data/raw/scraped/<class>/ (git-ignored) and still pass through
prepare_data.py's dedupe and filters like every other source.

Run:  uv run python ml/scrape_backfill.py [--per-class 160]
"""

import argparse
import io
import time
from pathlib import Path

import requests
import yaml
from ddgs import DDGS
from PIL import Image

ML_DIR = Path(__file__).parent
OUT_DIR = ML_DIR / "data" / "raw" / "scraped"
MIN_SIDE = 128
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

QUERIES: dict[str, list[str]] = {
    "poha": [
        "poha indian breakfast dish",
        "kanda poha plate",
        "poha recipe homemade",
        "aval upma flattened rice dish",
        "indori poha with sev",
        "batata poha maharashtrian",
    ],
    "kachori": [
        "kachori indian snack",
        "khasta kachori",
        "pyaz kachori rajasthani",
        "kachori chaat plate",
    ],
    "pani_puri": [
        "pani puri plate",
        "golgappa indian street food",
        "puchka bengali street food",
        "pani puri serving",
    ],
    "dal_tadka": [
        "dal tadka bowl",
        "yellow dal fry indian",
        "toor dal tadka restaurant",
        "dal fry with rice indian",
        "dal tadka dhaba style",
        "moong dal tadka",
    ],
    "chana_masala": [
        "chana masala dish",
        "chole curry bowl",
        "punjabi chole masala",
        "chickpea curry indian homemade",
    ],
    "palak_paneer": [
        "palak paneer bowl",
        "saag paneer dish",
        "palak paneer restaurant style",
        "spinach paneer curry",
        "palak paneer with roti thali",
        "palak paneer homemade curry",
    ],
    "paneer_butter_masala": [
        "paneer butter masala",
        "paneer makhani curry",
        "paneer butter masala restaurant",
        "shahi paneer dish",
        "paneer butter masala with naan",
        "paneer makhani kadhai bowl",
    ],
    "aloo_gobi": [
        "aloo gobi sabzi",
        "aloo gobi dry curry",
        "aloo gobhi masala homemade",
        "potato cauliflower indian sabji",
    ],
    "bhindi_masala": [
        "bhindi masala dish",
        "bhindi fry indian okra",
        "bhindi do pyaza",
        "okra masala indian homemade",
        "bhindi ki sabji",
        "kurkuri bhindi crispy okra",
    ],
    "butter_chicken": [
        "butter chicken curry",
        "murgh makhani dish",
        "butter chicken restaurant bowl",
        "creamy butter chicken naan",
    ],
    "chicken_biryani": [
        "chicken biryani plate",
        "hyderabadi chicken biryani",
        "chicken dum biryani handi",
        "chicken biryani homemade",
    ],
    "gulab_jamun": [
        "gulab jamun bowl",
        "gulab jamun indian sweet",
        "gulab jamun with syrup",
        "gulab jamun dessert plate",
    ],
    "rasgulla": [
        "rasgulla bowl",
        "bengali rasgulla sweet",
        "rasgulla in syrup",
        "sponge rasgulla dessert",
        "rasgulla odisha chhena sweet",
        "rasgulla serving plate mithai",
    ],
    "gajar_halwa": [
        "gajar ka halwa bowl",
        "carrot halwa indian dessert",
        "gajar halwa garnished",
        "gajrela punjabi dessert",
    ],
    "lassi": [
        "lassi glass indian drink",
        "sweet lassi punjabi",
        "mango lassi glass",
        "lassi with malai traditional",
        "kulhad lassi dhaba",
        "rose lassi drink indian",
    ],
}


def fetch_image(url: str) -> bytes | None:
    """Download and verify one image; None unless it decodes and is big enough."""
    try:
        resp = requests.get(url, timeout=10, headers=HEADERS)
        resp.raise_for_status()
        data = resp.content
        with Image.open(io.BytesIO(data)) as im:
            if min(im.size) < MIN_SIDE:
                return None
            im.load()
        return data
    except Exception:
        return None


def scrape_class(cls: str, queries: list[str], target: int) -> int:
    out = OUT_DIR / cls
    out.mkdir(parents=True, exist_ok=True)
    saved = len(list(out.glob("*.jpg")))
    if saved >= target:
        return saved
    seen_urls: set[str] = set()
    for query in queries:
        if saved >= target:
            break
        with DDGS() as ddgs:
            # The default aggregate backend returns query-unrelated junk
            # (verified 2026-07-18); bing is the one that actually works.
            results = list(ddgs.images(query, max_results=target * 2, backend="bing"))
        for r in results:
            if saved >= target:
                break
            url = r.get("image")
            if not url or url in seen_urls:
                continue
            seen_urls.add(url)
            data = fetch_image(url)
            if data is None:
                continue
            (out / f"{saved:06d}.jpg").write_bytes(data)
            saved += 1
        time.sleep(3)  # be polite between queries
    return saved


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--per-class", type=int, default=160)
    args = parser.parse_args()

    backfill: list[str] = yaml.safe_load((ML_DIR / "labels.yaml").read_text(encoding="utf-8"))[
        "backfill"
    ]
    missing = set(backfill) - set(QUERIES)
    if missing:
        raise SystemExit(f"No queries defined for backfill classes: {sorted(missing)}")

    for cls in backfill:
        n = scrape_class(cls, QUERIES[cls], args.per_class)
        print(f"{cls}: {n} images", flush=True)


if __name__ == "__main__":
    main()
