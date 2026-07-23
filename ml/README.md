# ml

Training pipelines, data audit notebooks, dataset versioning (manifest-based), and the label set.
Datasets and model weights are git-ignored — only code, configs, and manifests live here.

## Models

- `train_baseline.py` — Day-6 baseline: frozen EfficientNetV2-S features + linear probe.
  Reference line on the frozen test: **Top-1 86.1% / Top-5 97.1%** (`metrics/baseline_v1.json`).
- `train_finetune.py` — full fine-tune (RandAugment, mixup, class-imbalance sampler, AdamW +
  cosine LR with warmup, AMP). Backbone-agnostic for the EfficientNetV2-S vs ViT-S bake-off.

## Fine-tuning on a GPU (Colab)

This dev machine is CPU-only, so `train_finetune.py` is authored and smoke-tested locally but the
real training runs on **Google Colab** (`notebooks/train_finetune_colab.ipynb`). The steps:

1. **Pack the dataset** locally — only the ~27.9k images the manifests reference, not the whole
   122k raw tree:
   ```bash
   uv run python ml/pack_dataset.py   # -> ml/data/nutriscan_dataset_v1.zip
   ```
2. **Upload** that zip to Drive at `MyDrive/nutriscan/nutriscan_dataset_v1.zip`.
3. Open `notebooks/train_finetune_colab.ipynb` in Colab, set **Runtime → GPU**, and run it. It
   clones this repo (for the code + manifests), unzips the dataset, and trains both backbones:
   ```bash
   python ml/train_finetune.py --backbone effv2s --epochs 15 --batch-size 64
   python ml/train_finetune.py --backbone vits   --epochs 15 --batch-size 64
   ```

Each run logs params + per-epoch metrics to MLflow and writes `metrics/<backbone>_v1.json` and
`models/<backbone>_v1.pt`. The notebook prints a comparison and copies the artifacts back to
`MyDrive/nutriscan/results`. Pick the production candidate by frozen-test Top-1; it must beat the
**86.1%** baseline to be worth shipping. Pull the winning `.pt` + metrics back for the Day-8-style
ONNX export.

Local smoke test (correctness only, not real accuracy):

```bash
python ml/train_finetune.py --backbone effv2s --epochs 1 --limit 32 \
    --batch-size 8 --num-workers 0 --mixup-alpha 0 --cutmix-alpha 0 --no-mlflow
```
