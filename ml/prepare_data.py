"""Build dataset v1: merge raw sources into deduped, quality-filtered split manifests.

Pipeline (policy frozen by the Day-3 audit, ml/labels.yaml):
1. Discover class folders under ml/data/raw/ across all sources; map folder
   names to labels via the `aliases:` in labels.yaml; keep frozen classes only.
2. Drop undecodable images and images with min side < 128 px.
3. Dedupe by exact bytes (sha256), then by perceptual hash (pHash) so the same
   photo recompressed or resized across sources counts once. Curated datasets
   win over scraped images when duplicates collide.
4. `backfill:` classes that still end up under 150 images are excluded from the
   split (labels.yaml itself stays frozen).
5. Deterministic stratified split: per class, test = clamp(15%, 10, 50) and
   val = clamp(15%, 10, 100), remainder train. Rows are keyed by sha256, so the
   frozen test manifest survives file moves.

Manifests (train/val/test CSV + dataset_v1.json with counts and content hashes)
are written to ml/manifests/ and committed — that is the dataset version.

Run:  uv run python ml/prepare_data.py
"""

import argparse
import csv
import hashlib
import io
import json
import random
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import imagehash
import yaml
from PIL import Image

ML_DIR = Path(__file__).parent
IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp"}
# Lower number wins when duplicates collide across sources.
SOURCE_PRIORITY = {"scraped": 1}


@dataclass(frozen=True)
class ImageRecord:
    sha256: str
    path: str  # relative to the raw dir, POSIX separators
    label: str
    source: str
    phash: str


def normalize(name: str) -> str:
    return name.strip().lower().replace(" ", "_").replace("-", "_")


def discover(
    raw_dir: Path, classes: set[str], aliases: dict[str, str]
) -> list[tuple[Path, str, str]]:
    """Yield (file, label, source) for every candidate image of a kept class."""
    out: list[tuple[Path, str, str]] = []
    for source_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        for d in sorted(source_dir.rglob("*")):
            if not d.is_dir():
                continue
            label = aliases.get(normalize(d.name), normalize(d.name))
            if label not in classes:
                continue
            out.extend(
                (f, label, source_dir.name)
                for f in sorted(d.iterdir())
                if f.is_file() and f.suffix.lower() in IMG_EXTS
            )
    return out


def probe(args: tuple[str, str, str, str, int]) -> ImageRecord | None:
    """Hash + quality-check one image; None means dropped."""
    path, rel, label, source, min_side = args
    try:
        data = Path(path).read_bytes()
        with Image.open(io.BytesIO(data)) as im:
            if min(im.size) < min_side:
                return None
            ph = str(imagehash.phash(im))
    except Exception:
        return None
    return ImageRecord(hashlib.sha256(data).hexdigest(), rel, label, source, ph)


def dedupe(records: list[ImageRecord]) -> list[ImageRecord]:
    """Keep one record per exact hash, then per perceptual hash."""

    def priority(r: ImageRecord) -> tuple[int, str]:
        return (SOURCE_PRIORITY.get(r.source, 0), r.path)

    kept: dict[str, ImageRecord] = {}
    for r in sorted(records, key=priority):
        kept.setdefault(r.sha256, r)
    by_phash: dict[str, ImageRecord] = {}
    for r in sorted(kept.values(), key=priority):
        by_phash.setdefault(r.phash, r)
    return list(by_phash.values())


def split(
    records: list[ImageRecord], seed: int, test_cap: int, val_cap: int
) -> dict[str, list[ImageRecord]]:
    by_label: dict[str, list[ImageRecord]] = defaultdict(list)
    for r in records:
        by_label[r.label].append(r)

    splits: dict[str, list[ImageRecord]] = {"train": [], "val": [], "test": []}
    for label in sorted(by_label):
        rows = sorted(by_label[label], key=lambda r: r.sha256)
        random.Random(f"{seed}:{label}").shuffle(rows)
        n = len(rows)
        n_test = min(max(round(n * 0.15), 10), test_cap)
        n_val = min(max(round(n * 0.15), 10), val_cap)
        splits["test"].extend(rows[:n_test])
        splits["val"].extend(rows[n_test : n_test + n_val])
        splits["train"].extend(rows[n_test + n_val :])
    for rows in splits.values():
        rows.sort(key=lambda r: (r.label, r.sha256))
    return splits


def build_manifests(
    raw_dir: Path,
    out_dir: Path,
    seed: int = 42,
    min_side: int = 128,
    min_backfill: int = 150,
    test_cap: int = 50,
    val_cap: int = 100,
    workers: int = 1,
) -> dict[str, Any]:
    spec = yaml.safe_load((ML_DIR / "labels.yaml").read_text(encoding="utf-8"))
    classes: set[str] = set(spec["classes"])
    aliases: dict[str, str] = spec.get("aliases", {})
    backfill: set[str] = set(spec.get("backfill", []))

    candidates = discover(raw_dir, classes, aliases)
    jobs = [
        (str(f), f.relative_to(raw_dir).as_posix(), label, source, min_side)
        for f, label, source in candidates
    ]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            probed = list(pool.map(probe, jobs, chunksize=64))
    else:
        probed = [probe(j) for j in jobs]
    records = dedupe([r for r in probed if r is not None])

    counts: dict[str, int] = defaultdict(int)
    for r in records:
        counts[r.label] += 1
    excluded = sorted(c for c in backfill if counts[c] < min_backfill)
    records = [r for r in records if r.label not in excluded]

    splits = split(records, seed, test_cap, val_cap)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_hashes: dict[str, str] = {}
    for name, rows in splits.items():
        path = out_dir / f"{name}_v1.csv"
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["sha256", "path", "label", "source"])
            writer.writeheader()
            for r in rows:
                row = asdict(r)
                row.pop("phash")
                writer.writerow(row)
        manifest_hashes[name] = hashlib.sha256(path.read_bytes()).hexdigest()

    stats: dict[str, Any] = {
        "dataset_version": 1,
        "seed": seed,
        "filters": {"min_side": min_side, "min_backfill": min_backfill},
        "n_candidates": len(candidates),
        "n_after_filter_dedupe": sum(counts.values()),
        "classes": len(set(counts) - set(excluded)),
        "excluded_backfill_classes": excluded,
        "split_counts": {k: len(v) for k, v in splits.items()},
        "manifest_sha256": manifest_hashes,
    }
    (out_dir / "dataset_v1.json").write_text(json.dumps(stats, indent=2) + "\n", encoding="utf-8")
    return stats


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", type=Path, default=ML_DIR / "data" / "raw")
    parser.add_argument("--out", type=Path, default=ML_DIR / "manifests")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    stats = build_manifests(args.raw, args.out, seed=args.seed, workers=args.workers)
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
