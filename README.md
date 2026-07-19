# NutriScan

**Point. Scan. Know.** — Scan your plate with your phone camera and get AI-generated food
identification, portion estimates, and calorie/macro ranges in seconds. Built for Indian
cuisine first (poha, dal tadka, idli sambar…), with Western dishes supported via base datasets.

> 🚧 Work in progress — being built as a production-grade ML system: versioned models,
> automated retraining, CI/CD with model-quality gates, and drift monitoring.

## Status

- **Label set frozen**: 59 classes (Indian dishes + produce + common Western dishes),
  validated by a 5-source data audit ([`ml/labels.yaml`](ml/labels.yaml)).
- **Dataset v1 frozen**: 27,860 images, 58 classes — train 23,122 / val 2,658 /
  test 1,944, deterministic content-hash split ([`ml/manifests/`](ml/manifests/)).
  Thin classes backfilled by web scraping with a zero-shot CLIP junk filter.
- **Nutrition DB seeded**: MySQL schema with all 542 IFCT 2017 foods + USDA FNDDS
  survey foods, every vision class mapped to a food id with household portions
  (katori/piece/glass in grams) — [`backend/db/`](backend/db/).
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
