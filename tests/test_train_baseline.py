"""Unit tests for ml/train_baseline.py helpers (no training run required)."""

import csv
import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import torch
from PIL import Image

ROOT = Path(__file__).parent.parent


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "train_baseline", ROOT / "ml" / "train_baseline.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


train_baseline = _load_module()


def test_top_k_accuracy() -> None:
    logits = torch.tensor([[0.9, 0.05, 0.05], [0.1, 0.2, 0.7], [0.3, 0.4, 0.3]])
    y = torch.tensor([0, 1, 1])
    assert train_baseline.top_k_accuracy(logits, y, 1) == pytest.approx(2 / 3)
    assert train_baseline.top_k_accuracy(logits, y, 2) == 1.0


def test_manifest_dataset(tmp_path: Path, monkeypatch: object) -> None:
    img_dir = tmp_path / "src" / "apple"
    img_dir.mkdir(parents=True)
    Image.new("RGB", (300, 200), (255, 0, 0)).save(img_dir / "a.jpg")
    manifest = tmp_path / "train_v1.csv"
    with open(manifest, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["sha256", "path", "label", "source"])
        w.writeheader()
        w.writerow({"sha256": "x", "path": "src/apple/a.jpg", "label": "apple", "source": "src"})
    train_baseline.RAW = tmp_path  # type: ignore[attr-defined]
    ds = train_baseline.ManifestDataset(manifest, {"apple": 0})
    assert len(ds) == 1
    x, y = ds[0]
    assert y == 0
    assert x.shape[0] == 3 and x.ndim == 3
