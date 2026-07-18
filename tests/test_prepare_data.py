"""Unit tests for the ml/prepare_data.py pipeline on a tiny synthetic dataset."""

import csv
import importlib.util
import json
import random
from pathlib import Path
from types import ModuleType
from typing import cast

import pytest
from PIL import Image

ROOT = Path(__file__).parent.parent


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("prepare_data", ROOT / "ml" / "prepare_data.py")
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


prepare_data = _load_module()


def _make_image(path: Path, seed: int, size: int = 200) -> None:
    rng = random.Random(seed)
    im = Image.new("RGB", (size, size))
    im.putdata(
        [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(size**2)]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path, "JPEG")


@pytest.fixture(scope="module")
def raw_dir(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Two sources; apple has 30 images + 1 exact dupe + 1 tiny + 1 corrupt."""
    raw = tmp_path_factory.mktemp("raw")
    for i in range(30):
        _make_image(raw / "src-a" / "apple" / f"{i}.jpg", seed=i)
    for i in range(30):
        _make_image(raw / "src-b" / "banana" / f"{i}.jpg", seed=1000 + i)
    # exact duplicate of an apple image in the other source
    dupe = raw / "src-b" / "apple" / "dupe.jpg"
    dupe.parent.mkdir(parents=True)
    dupe.write_bytes((raw / "src-a" / "apple" / "0.jpg").read_bytes())
    _make_image(raw / "src-a" / "apple" / "tiny.jpg", seed=99, size=64)
    (raw / "src-a" / "apple" / "corrupt.jpg").write_bytes(b"not an image")
    return raw


def _run(raw: Path, out: Path) -> dict[str, object]:
    return cast(dict[str, object], prepare_data.build_manifests(raw, out, seed=42, workers=1))


def test_filter_and_dedupe(raw_dir: Path, tmp_path: Path) -> None:
    stats = _run(raw_dir, tmp_path)
    # 30 apples (dupe, tiny, corrupt all dropped) + 30 bananas
    assert stats["n_after_filter_dedupe"] == 60


def test_split_disjoint_and_stratified(raw_dir: Path, tmp_path: Path) -> None:
    _run(raw_dir, tmp_path)
    rows: dict[str, list[dict[str, str]]] = {}
    for split in ("train", "val", "test"):
        with open(tmp_path / f"{split}_v1.csv", encoding="utf-8") as f:
            rows[split] = list(csv.DictReader(f))
    hashes = [r["sha256"] for split_rows in rows.values() for r in split_rows]
    assert len(hashes) == len(set(hashes)), "images leak between splits"
    for split_rows in rows.values():
        labels = {r["label"] for r in split_rows}
        assert labels == {"apple", "banana"}, "split is not stratified"
    # 30 per class: test = max(round(4.5), 10) = 10, val = 10, train = 10
    assert len(rows["test"]) == 20
    assert len(rows["val"]) == 20
    assert len(rows["train"]) == 20


def test_deterministic(raw_dir: Path, tmp_path: Path) -> None:
    a = _run(raw_dir, tmp_path / "a")
    b = _run(raw_dir, tmp_path / "b")
    assert a["manifest_sha256"] == b["manifest_sha256"]


def test_version_json_written(raw_dir: Path, tmp_path: Path) -> None:
    stats = _run(raw_dir, tmp_path)
    on_disk = json.loads((tmp_path / "dataset_v1.json").read_text(encoding="utf-8"))
    assert on_disk == stats
