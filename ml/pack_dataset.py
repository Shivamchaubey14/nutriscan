"""Pack dataset v1 into a single zip for upload to Google Drive → Colab.

ml/data/raw/ holds ~122k images across every source, but dataset v1 uses only
the ~27.9k referenced by the split manifests (after filtering + dedupe). This
copies just those, preserving their relative paths, and zips them — so the
Drive upload is a couple of GB instead of the whole raw tree. On Colab the zip
unzips straight into ml/data/raw/ and train_finetune.py finds every image.

Run:    uv run python ml/pack_dataset.py
Output: ml/data/nutriscan_dataset_v1.zip   (unzip into ml/data/raw/ on Colab)
"""

import csv
import shutil
from pathlib import Path

ML_DIR = Path(__file__).parent
RAW = ML_DIR / "data" / "raw"
MANIFESTS = ML_DIR / "manifests"
PACK = ML_DIR / "data" / "pack"
ZIP_BASE = ML_DIR / "data" / "nutriscan_dataset_v1"


def manifest_paths() -> set[str]:
    """Every image path referenced by the train/val/test manifests."""
    paths: set[str] = set()
    for split in ("train", "val", "test"):
        with open(MANIFESTS / f"{split}_v1.csv", encoding="utf-8") as f:
            paths.update(row["path"] for row in csv.DictReader(f))
    return paths


def main() -> None:
    paths = manifest_paths()
    if PACK.exists():
        shutil.rmtree(PACK)

    raw_root = RAW.resolve()
    pack_root = PACK.resolve()
    copied = 0
    missing: list[str] = []
    for rel in sorted(paths):
        # Guard against absolute / "../" manifest entries escaping the dataset roots.
        src = (RAW / rel).resolve()
        if not src.is_relative_to(raw_root):
            raise SystemExit(f"unsafe manifest path escapes ml/data/raw/: {rel!r}")
        if not src.exists():
            missing.append(rel)
            continue
        dst = pack_root / src.relative_to(raw_root)
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1

    print(f"packed {copied}/{len(paths)} images", flush=True)
    if missing:
        # Fail closed — an incomplete zip would silently train on fewer images.
        raise SystemExit(f"{len(missing)} referenced images missing (first 5: {missing[:5]})")

    archive = shutil.make_archive(str(ZIP_BASE), "zip", root_dir=str(PACK))
    size_mb = Path(archive).stat().st_size / 1e6
    print(f"wrote {archive} ({size_mb:.0f} MB) — upload this to Drive: MyDrive/nutriscan/")


if __name__ == "__main__":
    main()
