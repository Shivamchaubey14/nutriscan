# ml

Training pipelines, data audit notebooks, dataset versioning (manifest-based), and the label set.
Datasets and model weights are git-ignored — only code, configs, and manifests live here.

## Models

- `train_baseline.py` — Day-6 baseline: frozen EfficientNetV2-S features + linear probe.
  Reference line on the frozen test: **Top-1 86.1% / Top-5 97.1%** (`metrics/baseline_v1.json`).
- `train_finetune.py` — full fine-tune (RandAugment, mixup, class-imbalance sampler, AdamW +
  cosine LR with warmup, AMP). Backbone-agnostic for the EfficientNetV2-S vs ViT-S bake-off.

## Fine-tuning on a GPU

This dev machine is CPU-only, so `train_finetune.py` is authored and smoke-tested locally but the
real training runs on a cloud GPU (Colab / Kaggle free tier). The dataset is regenerable from the
committed manifests (`manifests/*_v1.csv`) — sync `ml/data/raw/` and the manifests to the GPU box,
then:

```bash
# EfficientNetV2-S
python ml/train_finetune.py --backbone effv2s --epochs 15 --batch-size 64

# ViT-S (same data, same protocol — compare by frozen-test Top-1 in MLflow)
python ml/train_finetune.py --backbone vits --epochs 15 --batch-size 64
```

Each run logs params + per-epoch metrics to MLflow and writes `metrics/<backbone>_v1.json` and
`models/<backbone>_v1.pt`. Pick the production candidate by frozen-test Top-1; it must beat the
86.1% baseline to be worth shipping. Pull the winning `.pt` + metrics back for the Day-8-style
ONNX export.

Local smoke test (correctness only, not real accuracy):

```bash
python ml/train_finetune.py --backbone effv2s --epochs 1 --limit 32 \
    --batch-size 8 --num-workers 0 --mixup-alpha 0 --no-mlflow
```
