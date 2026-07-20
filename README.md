# NutriScan

**Point. Scan. Know.** — Scan your plate with your phone camera and get AI-generated food
identification, portion estimates, and calorie/macro ranges in seconds. Built for Indian
cuisine first (poha, dal tadka, idli sambar…), with Western dishes supported via base datasets.

> 🚧 Work in progress — being built as a production-grade ML system: versioned models,
> automated retraining, CI/CD with model-quality gates, and drift monitoring.

## Demo

> 🎬 Demo GIF coming soon — recorded from `scripts/demo.sh` (add it as `docs/demo.gif`).

**Live staging API:** _coming soon_ · run it yourself in 2 minutes → [Quickstart](#quickstart).

`POST /api/v1/scan/` with a food photo returns a calorie **range**, never fake precision:

```json
{
  "scan_id": "91c70862",
  "model_version": "baseline_v1",
  "needs_confirmation": false,
  "items": [
    {
      "label": "pizza",
      "confidence": 0.90,
      "portion": { "unit": "slice", "grams": 110, "adjustable": true },
      "nutrition": {
        "kcal": { "min": 240, "max": 345 },
        "protein_g": 12.5, "carbs_g": 36.7, "fat_g": 10.7, "source": "USDA"
      }
    }
  ],
  "candidates": [{ "label": "pizza", "confidence": 0.90 }, "…top-3"]
}
```

## Quickstart

```bash
docker compose up -d --build                              # backend + inference + MySQL + Redis
docker compose exec backend python manage.py seed_nutrition
BASE_URL=http://localhost:8000 ./scripts/demo.sh ml/data/raw/food-101/images/pizza/1005649.jpg
```

Deploying to a public staging host? See [docs/DEPLOY.md](docs/DEPLOY.md).

## Status

- **Label set frozen**: 59 classes (Indian dishes + produce + common Western dishes),
  validated by a 5-source data audit ([`ml/labels.yaml`](ml/labels.yaml)).
- **Dataset v1 frozen**: 27,860 images, 58 classes — train 23,122 / val 2,658 /
  test 1,944, deterministic content-hash split ([`ml/manifests/`](ml/manifests/)).
  Thin classes backfilled by web scraping with a zero-shot CLIP junk filter.
- **Nutrition DB seeded**: MySQL schema with all 542 IFCT 2017 foods + USDA FNDDS
  survey foods, every vision class mapped to a food id with household portions
  (katori/piece/glass in grams) — [`backend/db/`](backend/db/).
- **Baseline classifier**: EfficientNetV2-S, **86% top-1 / 97% top-5** on the frozen
  test set, exported to ONNX and served under ~130 ms/image on CPU.
- **Vertical slice working**: authenticated `POST /scan/` runs photo → inference service
  (async `httpx`) → nutrition lookup → calorie range, end to end across the compose stack.
- **CI gate live**: branch protection with required lint + type + test + Docker
  builds; every change lands via PR.

## Why

Single-image calorie estimation has irreducible error (hidden oil, sauces, density), and most
food-recognition models are trained on Western dishes. NutriScan tackles both: nutrition is
always shown as a **range with a confidence indicator** (never fake precision), and the model
is fine-tuned on Indian food with a user-feedback loop that feeds retraining.

## Architecture

*(diagram coming soon)*

```
[React Native App]
   │  HTTPS (JWT)
   ▼
[DRF Async API ── MySQL / Redis]
   ├──► [ML Inference Service (FastAPI / ONNX)] — classifier + detector + portion estimator
   ├──► [OCR + Barcode Service] ──► Open Food Facts / cache
   └──► [Nutrition Resolver] ──► IFCT / USDA tables (MySQL)

[Retraining pipeline] → [MLflow Registry] → CI/CD quality gate → deploy
[Drift & latency monitoring] ← prediction logs
```

## Stack

| Layer | Tech |
|---|---|
| Mobile | React Native (Expo) + TypeScript |
| API | Django 5 + DRF (async views, ASGI/Uvicorn), JWT auth |
| Inference | FastAPI + ONNX Runtime (INT8-quantized) |
| Models | EfficientNetV2-S / ViT-S classifier, YOLOv8-s detector |
| Data | MySQL 8, Redis 7, IFCT 2017 + USDA FDC nutrition tables |
| MLOps | MLflow, DVC, Evidently, Prometheus + Grafana |
| CI/CD | GitHub Actions with model-quality gates |

## Repo layout

```
backend/    Django REST API (accounts, scans, nutrition, logs)
inference/  FastAPI model-serving microservice
mobile/     React Native app
ml/         Training pipelines, notebooks, dataset tooling
infra/      Docker, compose, CI/CD, deployment
docs/       SRS, build plan, design reference
tests/      Repo-level tests
```

## Development setup

Requires Python ≥ 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
uv sync            # create venv + install dev tooling
uv run pre-commit install
uv run pytest      # run tests
uv run ruff check  # lint
uv run mypy .      # typecheck
```

## Design

The app follows a warm sage-green & cream design system — see
[docs/design/DESIGN.md](docs/design/DESIGN.md) and the screen cards in `docs/design/`.

## Docs

- [Software Requirements Specification](docs/SRS.md)
- [Build plan](docs/BUILD_PLAN.md)
