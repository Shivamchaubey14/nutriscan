"""Train the Day-6 baseline classifier on dataset v1 and log it to MLflow.

Fast-and-dumb on purpose (BUILD_PLAN Day 6): an ImageNet-pretrained
EfficientNetV2-S backbone stays frozen; its 1280-d penultimate features are
computed once per split (cached under ml/data/features/, git-ignored) and a
linear head is trained on them. Backbone + head assemble into one module for
the Day-8 ONNX export. Every run logs params, per-epoch metrics and artifacts
to local MLflow (./mlruns), and the frozen-test Top-1/Top-5 goes to
ml/metrics/baseline_v1.json — the reference line all later models must beat.

Run:  uv run python ml/train_baseline.py [--epochs 40]
"""

import argparse
import csv
import json
from pathlib import Path

import mlflow
import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision.models import (  # type: ignore[import-untyped]
    EfficientNet_V2_S_Weights,
    efficientnet_v2_s,
)

ML_DIR = Path(__file__).parent
RAW = ML_DIR / "data" / "raw"
FEATURES = ML_DIR / "data" / "features"
MANIFESTS = ML_DIR / "manifests"
MODELS = ML_DIR / "models"
METRICS = ML_DIR / "metrics"
WEIGHTS = EfficientNet_V2_S_Weights.IMAGENET1K_V1


class ManifestDataset(Dataset[tuple[torch.Tensor, int]]):
    """Images + integer labels straight from a split manifest CSV."""

    def __init__(self, manifest: Path, class_to_idx: dict[str, int]) -> None:
        with open(manifest, encoding="utf-8") as f:
            self.rows = list(csv.DictReader(f))
        self.class_to_idx = class_to_idx
        self.transform = WEIGHTS.transforms()

    def __len__(self) -> int:
        return len(self.rows)

    def __getitem__(self, i: int) -> tuple[torch.Tensor, int]:
        row = self.rows[i]
        with Image.open(RAW / row["path"]) as im:
            x = self.transform(im.convert("RGB"))
        return x, self.class_to_idx[row["label"]]


def read_classes() -> list[str]:
    with open(MANIFESTS / "train_v1.csv", encoding="utf-8") as f:
        return sorted({r["label"] for r in csv.DictReader(f)})


def embed_split(split: str, class_to_idx: dict[str, int], batch_size: int) -> Path:
    """Compute (or reuse) frozen-backbone features for one split."""
    out = FEATURES / f"{split}_effv2s.npz"
    if out.exists():
        return out
    backbone = efficientnet_v2_s(weights=WEIGHTS)
    backbone.classifier = nn.Identity()
    backbone.eval()

    ds = ManifestDataset(MANIFESTS / f"{split}_v1.csv", class_to_idx)
    loader = DataLoader(ds, batch_size=batch_size, num_workers=4, pin_memory=False)
    feats: list[np.ndarray] = []
    labels: list[np.ndarray] = []
    with torch.no_grad():
        for i, (x, y) in enumerate(loader):
            feats.append(backbone(x).numpy())
            labels.append(y.numpy())
            if i % 20 == 0:
                print(f"{split}: batch {i}/{len(loader)}", flush=True)
    FEATURES.mkdir(parents=True, exist_ok=True)
    np.savez(out, x=np.concatenate(feats), y=np.concatenate(labels))
    return out


def top_k_accuracy(logits: torch.Tensor, y: torch.Tensor, k: int) -> float:
    top = logits.topk(k, dim=1).indices
    return float((top == y.unsqueeze(1)).any(dim=1).float().mean())


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    torch.manual_seed(args.seed)

    classes = read_classes()
    class_to_idx = {c: i for i, c in enumerate(classes)}
    splits = {s: embed_split(s, class_to_idx, args.batch_size) for s in ("train", "val", "test")}
    data = {s: np.load(p) for s, p in splits.items()}
    tensors = {
        s: (torch.from_numpy(d["x"]).float(), torch.from_numpy(d["y"]).long())
        for s, d in data.items()
    }
    x_train, y_train = tensors["train"]

    head = nn.Linear(x_train.shape[1], len(classes))
    opt = torch.optim.AdamW(head.parameters(), lr=args.lr, weight_decay=1e-4)
    loss_fn = nn.CrossEntropyLoss(label_smoothing=0.1)

    mlflow.set_experiment("baseline")
    with mlflow.start_run(run_name="effv2s-linear-probe"):
        mlflow.log_params(
            {
                "arch": "efficientnet_v2_s (frozen) + linear head",
                "epochs": args.epochs,
                "lr": args.lr,
                "seed": args.seed,
                "n_classes": len(classes),
                "n_train": len(y_train),
            }
        )
        best_val, best_state = 0.0, head.state_dict()
        for epoch in range(args.epochs):
            head.train()
            perm = torch.randperm(len(y_train))
            for i in range(0, len(perm), 512):
                idx = perm[i : i + 512]
                opt.zero_grad()
                loss = loss_fn(head(x_train[idx]), y_train[idx])
                loss.backward()
                opt.step()
            head.eval()
            with torch.no_grad():
                val_top1 = top_k_accuracy(head(tensors["val"][0]), tensors["val"][1], 1)
            mlflow.log_metric("val_top1", val_top1, step=epoch)
            if val_top1 > best_val:
                best_val = val_top1
                best_state = {k: v.clone() for k, v in head.state_dict().items()}
            print(f"epoch {epoch}: val_top1={val_top1:.4f}", flush=True)

        head.load_state_dict(best_state)
        head.eval()
        with torch.no_grad():
            logits = head(tensors["test"][0])
        metrics = {
            "test_top1": top_k_accuracy(logits, tensors["test"][1], 1),
            "test_top5": top_k_accuracy(logits, tensors["test"][1], 5),
            "val_top1_best": best_val,
        }
        mlflow.log_metrics(metrics)

        MODELS.mkdir(parents=True, exist_ok=True)
        torch.save({"head": head.state_dict(), "classes": classes}, MODELS / "baseline_v1.pt")
        METRICS.mkdir(parents=True, exist_ok=True)
        report = {
            "model": "efficientnet_v2_s frozen + linear head",
            "dataset_version": 1,
            "seed": args.seed,
            **{k: round(v, 4) for k, v in metrics.items()},
        }
        (METRICS / "baseline_v1.json").write_text(
            json.dumps(report, indent=2) + "\n", encoding="utf-8"
        )
        mlflow.log_artifact(str(METRICS / "baseline_v1.json"))
        mlflow.log_artifact(str(MODELS / "baseline_v1.pt"))
        print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
