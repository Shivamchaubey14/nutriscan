"""Full fine-tune of a pretrained backbone on dataset v1 (BUILD_PLAN Day 19-20).

Unlike the Day-6 baseline (frozen features + linear probe), this fine-tunes the
*whole* backbone with proper training tricks:

  * RandAugment + the model's native train transform (timm)
  * mixup / cutmix with soft-target cross-entropy
  * class-imbalance handling via a WeightedRandomSampler (inverse frequency)
  * AdamW + cosine LR with linear warmup
  * mixed precision (AMP) on CUDA

It is backbone-agnostic so the Day 19-20 bake-off (EfficientNetV2-S vs ViT-S)
is one flag: `--backbone effv2s|vits`. Every run logs params, per-epoch metrics
and the model artifact to local MLflow; the frozen-test Top-1/Top-5 is written to
ml/metrics/<backbone>_v1.json to sit next to the baseline for comparison.

This machine is CPU-only, so the real training runs on a cloud GPU (see
ml/README.md → "Fine-tuning on a GPU"). Locally it is exercised as a smoke test:

    uv run python ml/train_finetune.py --backbone effv2s --epochs 1 --limit 32 \
        --batch-size 8 --num-workers 0 --mixup-alpha 0 --cutmix-alpha 0 --no-mlflow
"""

from __future__ import annotations

import argparse
import csv
import json
import random
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

import mlflow
import numpy as np
import timm
import torch
from PIL import Image
from timm.data import Mixup, create_transform, resolve_data_config  # type: ignore[attr-defined]
from timm.loss import SoftTargetCrossEntropy  # type: ignore[attr-defined]
from torch import nn
from torch.utils.data import DataLoader, Dataset, WeightedRandomSampler

ML_DIR = Path(__file__).parent
RAW = ML_DIR / "data" / "raw"
MANIFESTS = ML_DIR / "manifests"
MODELS = ML_DIR / "models"
METRICS = ML_DIR / "metrics"

# timm model names (ImageNet-21k pretrained, fine-tuned on 1k) for the bake-off.
BACKBONES = {
    "effv2s": "tf_efficientnetv2_s.in21k_ft_in1k",
    "vits": "vit_small_patch16_224.augreg_in21k_ft_in1k",
}

Transform = Callable[[Image.Image], torch.Tensor]


class ManifestDataset(Dataset[tuple[torch.Tensor, int]]):
    """Images + integer labels from a split manifest, with a supplied transform."""

    def __init__(self, manifest: Path, class_to_idx: dict[str, int], transform: Transform) -> None:
        with open(manifest, encoding="utf-8") as f:
            self.rows = list(csv.DictReader(f))
        self.class_to_idx = class_to_idx
        self.transform = transform

    def __len__(self) -> int:
        return len(self.rows)

    def labels(self) -> list[int]:
        return [self.class_to_idx[r["label"]] for r in self.rows]

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        row = self.rows[i]
        with Image.open(RAW / row["path"]) as im:
            x = self.transform(im.convert("RGB"))
        return x, self.class_to_idx[row["label"]]


def read_classes() -> list[str]:
    with open(MANIFESTS / "train_v1.csv", encoding="utf-8") as f:
        return sorted({r["label"] for r in csv.DictReader(f)})


def imbalance_sampler(labels: list[int], n_classes: int) -> WeightedRandomSampler:
    """Sample inversely to class frequency so thin classes aren't drowned out."""
    counts = Counter(labels)
    class_weight = {c: len(labels) / (n_classes * counts[c]) for c in counts}
    weights = [class_weight[y] for y in labels]
    return WeightedRandomSampler(weights, num_samples=len(labels), replacement=True)


@torch.no_grad()
def evaluate(
    model: nn.Module, loader: DataLoader[tuple[torch.Tensor, int]], device: torch.device
) -> tuple[float, float]:
    model.eval()
    top1 = top5 = total = 0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        logits = model(x)
        top = logits.topk(5, dim=1).indices
        hits = top == y.unsqueeze(1)
        top1 += int(hits[:, 0].sum())
        top5 += int(hits.any(dim=1).sum())
        total += y.numel()
    return top1 / total, top5 / total


def build_loaders(
    class_to_idx: dict[str, int], data_cfg: dict[str, Any], args: argparse.Namespace
) -> tuple[
    DataLoader[tuple[torch.Tensor, int]],
    DataLoader[tuple[torch.Tensor, int]],
    DataLoader[tuple[torch.Tensor, int]],
]:
    train_tf: Transform = create_transform(
        **data_cfg, is_training=True, auto_augment="rand-m9-mstd0.5"
    )
    eval_tf: Transform = create_transform(**data_cfg, is_training=False)

    train_ds = ManifestDataset(MANIFESTS / "train_v1.csv", class_to_idx, train_tf)
    val_ds = ManifestDataset(MANIFESTS / "val_v1.csv", class_to_idx, eval_tf)
    test_ds = ManifestDataset(MANIFESTS / "test_v1.csv", class_to_idx, eval_tf)

    if args.limit:  # smoke test: a handful of images, no weighted sampler
        train_ds.rows = train_ds.rows[: args.limit]
        val_ds.rows = val_ds.rows[: args.limit]
        test_ds.rows = test_ds.rows[: args.limit]
        sampler: WeightedRandomSampler | None = None
    else:
        sampler = imbalance_sampler(train_ds.labels(), len(class_to_idx))

    common = {"batch_size": args.batch_size, "num_workers": args.num_workers, "pin_memory": True}
    train_loader: DataLoader[tuple[torch.Tensor, int]] = DataLoader(
        train_ds, sampler=sampler, shuffle=sampler is None, drop_last=False, **common
    )
    val_loader: DataLoader[tuple[torch.Tensor, int]] = DataLoader(val_ds, shuffle=False, **common)
    test_loader: DataLoader[tuple[torch.Tensor, int]] = DataLoader(test_ds, shuffle=False, **common)
    return train_loader, val_loader, test_loader


def cosine_warmup(
    optimizer: torch.optim.Optimizer, warmup: int, total: int
) -> torch.optim.lr_scheduler.LRScheduler:
    warmup = min(warmup, max(total - 1, 1))
    schedulers = [
        torch.optim.lr_scheduler.LinearLR(optimizer, start_factor=0.01, total_iters=warmup),
        torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=max(total - warmup, 1)),
    ]
    return torch.optim.lr_scheduler.SequentialLR(optimizer, schedulers, milestones=[warmup])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--backbone", choices=list(BACKBONES), default="effv2s")
    parser.add_argument("--epochs", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--lr", type=float, default=5e-4)
    parser.add_argument("--weight-decay", type=float, default=0.05)
    parser.add_argument("--warmup-epochs", type=int, default=2)
    parser.add_argument("--mixup-alpha", type=float, default=0.2)
    parser.add_argument("--cutmix-alpha", type=float, default=1.0)
    parser.add_argument("--label-smoothing", type=float, default=0.1)
    parser.add_argument("--num-workers", type=int, default=4)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--limit", type=int, default=0, help="cap images/split for a CPU smoke test"
    )
    parser.add_argument("--no-mlflow", action="store_true")
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    use_amp = device.type == "cuda"
    classes = read_classes()
    class_to_idx = {c: i for i, c in enumerate(classes)}

    model: nn.Module = timm.create_model(
        BACKBONES[args.backbone], pretrained=True, num_classes=len(classes)
    )
    model.to(device)
    data_cfg: dict[str, Any] = resolve_data_config({}, model=model)  # type: ignore[no-untyped-call]
    train_loader, val_loader, test_loader = build_loaders(class_to_idx, data_cfg, args)

    mixup_on = (args.mixup_alpha > 0 or args.cutmix_alpha > 0) and not args.limit
    mixup_fn = (
        Mixup(  # type: ignore[no-untyped-call]
            mixup_alpha=args.mixup_alpha,
            cutmix_alpha=args.cutmix_alpha,
            label_smoothing=args.label_smoothing,
            num_classes=len(classes),
        )
        if mixup_on
        else None
    )
    train_criterion: nn.Module = (
        SoftTargetCrossEntropy()  # type: ignore[no-untyped-call]
        if mixup_on
        else nn.CrossEntropyLoss(label_smoothing=args.label_smoothing)
    )

    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = cosine_warmup(optimizer, args.warmup_epochs, args.epochs)
    scaler = torch.amp.GradScaler(device.type, enabled=use_amp)

    if not args.no_mlflow:
        mlflow.set_experiment("finetune")
        mlflow.start_run(run_name=f"{args.backbone}-finetune")
        mlflow.log_params(
            {
                "backbone": BACKBONES[args.backbone],
                "epochs": args.epochs,
                "batch_size": args.batch_size,
                "lr": args.lr,
                "weight_decay": args.weight_decay,
                "warmup_epochs": args.warmup_epochs,
                "mixup_alpha": args.mixup_alpha if mixup_on else 0.0,
                "cutmix_alpha": args.cutmix_alpha if mixup_on else 0.0,
                "label_smoothing": args.label_smoothing,
                "n_classes": len(classes),
                "device": device.type,
            }
        )

    best_val, best_state = 0.0, model.state_dict()
    for epoch in range(args.epochs):
        model.train()
        running = 0.0
        for x, y in train_loader:
            x, y = x.to(device), y.to(device)
            if mixup_fn is not None:
                x, y = mixup_fn(x, y)
            optimizer.zero_grad()
            with torch.amp.autocast(device_type=device.type, enabled=use_amp):
                loss = train_criterion(model(x), y)
            scaler.scale(loss).backward()
            scaler.step(optimizer)
            scaler.update()
            running += loss.item()
        scheduler.step()

        val_top1, val_top5 = evaluate(model, val_loader, device)
        if not args.no_mlflow:
            mlflow.log_metrics(
                {
                    "train_loss": running / max(len(train_loader), 1),
                    "val_top1": val_top1,
                    "val_top5": val_top5,
                },
                step=epoch,
            )
        if val_top1 >= best_val:
            best_val = val_top1
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        print(f"epoch {epoch}: val_top1={val_top1:.4f} val_top5={val_top5:.4f}", flush=True)

    model.load_state_dict(best_state)
    test_top1, test_top5 = evaluate(model, test_loader, device)
    report = {
        "model": BACKBONES[args.backbone],
        "dataset_version": 1,
        "seed": args.seed,
        "val_top1_best": round(best_val, 4),
        "test_top1": round(test_top1, 4),
        "test_top5": round(test_top5, 4),
    }

    MODELS.mkdir(parents=True, exist_ok=True)
    torch.save(
        {"state_dict": best_state, "classes": classes, "backbone": args.backbone},
        MODELS / f"{args.backbone}_v1.pt",
    )
    METRICS.mkdir(parents=True, exist_ok=True)
    (METRICS / f"{args.backbone}_v1.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )

    if not args.no_mlflow:
        mlflow.log_metrics({"test_top1": test_top1, "test_top5": test_top5})
        mlflow.log_artifact(str(METRICS / f"{args.backbone}_v1.json"))
        mlflow.log_artifact(str(MODELS / f"{args.backbone}_v1.pt"))
        mlflow.end_run()
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
