"""Unit tests for ml/train_finetune.py helpers (no backbone download / training)."""

import importlib.util
from pathlib import Path
from types import ModuleType

import pytest
import torch

ROOT = Path(__file__).parent.parent


def _load_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location(
        "train_finetune", ROOT / "ml" / "train_finetune.py"
    )
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


train_finetune = _load_module()


def test_imbalance_sampler_upweights_rare_classes() -> None:
    # class 0 has 3 samples, class 1 has 1 — the rare one must sample more often.
    labels = [0, 0, 0, 1]
    sampler = train_finetune.imbalance_sampler(labels, n_classes=2)
    weights = sampler.weights.tolist()
    assert weights[3] > weights[0]
    # weight = N / (n_classes * count) -> 4/(2*3) and 4/(2*1)
    assert weights[0] == pytest.approx(4 / 6)
    assert weights[3] == pytest.approx(4 / 2)


def test_cosine_warmup_ramps_then_decays() -> None:
    param = torch.nn.Parameter(torch.zeros(1))
    opt = torch.optim.SGD([param], lr=1.0)
    scheduler = train_finetune.cosine_warmup(opt, warmup=2, total=10)

    lrs = []
    for _ in range(10):
        lrs.append(opt.param_groups[0]["lr"])
        opt.step()
        scheduler.step()

    assert lrs[0] < lrs[2]  # warms up
    assert lrs[2] > lrs[-1]  # then decays
    assert lrs[-1] < 0.1  # cosine has driven it near zero by the end
