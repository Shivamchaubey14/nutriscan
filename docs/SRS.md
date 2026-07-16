# Software Requirements Specification (SRS)

## NutriScan — AI-Powered Food Recognition & Calorie Estimation App

| | |
|---|---|
| **Document Version** | 1.0 |
| **Date** | 16 July 2026 |
| **Status** | Draft for Review |
| **Prepared For** | NutriScan Product & Engineering Team |

---

## 1. Introduction

### 1.1 Purpose
This document specifies the functional, non-functional, ML, and design requirements for **NutriScan**, a mobile application that allows a user to scan food items (cooked dishes, fruits, vegetables, and packaged products) using their phone camera and receive AI-generated identification and nutritional information (calories and macronutrients) in real time.

It is intended for developers, ML engineers, designers, and reviewers involved in building, testing, and maintaining the system.

### 1.2 Scope
NutriScan will:

- Recognize food items from a camera image (single or multiple items per frame).
- Estimate portion size with a user-adjustable confidence range.
- Compute calories and macronutrients (protein, carbohydrates, fat, fiber) using the IFCT (Indian Food Composition Tables) and USDA FoodData Central databases.
- Fall back to OCR + barcode lookup for packaged products.
- Track a user's daily/weekly nutrition history.
- Operate as a production-grade ML system: versioned models, automated retraining, drift monitoring, CI/CD with model-quality gates.

Out of scope for v1.0: medical/clinical dietary advice, meal planning, social features, wearable integrations.

### 1.3 Definitions & Abbreviations

| Term | Meaning |
|---|---|
| DRF | Django REST Framework (async views/ASGI) |
| RN | React Native |
| IFCT | Indian Food Composition Tables (NIN, Hyderabad) |
| OFF | Open Food Facts database |
| Top-1 / Top-5 | Model accuracy where the correct label is the first / among the first five predictions |
| MAPE | Mean Absolute Percentage Error |
| PSS | Portion Size Estimation |
| VLM | Vision-Language Model |

### 1.4 References
- IFCT 2017, National Institute of Nutrition, Hyderabad
- USDA FoodData Central API
- Open Food Facts API
- Food-101, IndianFood-Net and related public datasets (Kaggle)

---

## 2. Overall Description

### 2.1 Product Perspective
NutriScan is a new, standalone system composed of:

1. **Mobile client** — React Native (iOS + Android).
2. **API backend** — Django REST Framework running on ASGI (async views) behind Uvicorn/Gunicorn.
3. **ML inference service** — a separate FastAPI (or TorchServe/ONNX Runtime) microservice that hosts the vision models, called asynchronously by the DRF backend.
4. **Data & MLOps plane** — training pipelines, experiment tracking, model registry, monitoring.

Separating inference from the DRF app keeps Django deployments independent of model deployments and lets the GPU-serving layer scale on its own.

### 2.2 User Classes

| User | Description |
|---|---|
| Guest | Can scan and view results without an account (limited history) |
| Registered User | Full history, daily goals, personalization |
| Admin / ML Engineer | Reviews flagged predictions, manages model versions, monitors drift dashboards |

### 2.3 Operating Environment
- Mobile: Android 9+ / iOS 15+, React Native ≥ 0.74.
- Backend: Python 3.12, Django 5.x + DRF with ASGI, PostgreSQL 16, Redis 7.
- Inference: Dockerized ONNX Runtime / PyTorch service on a GPU or CPU-optimized instance.
- Cloud-agnostic; reference deployment on a single k8s cluster or Cloud Run + a GPU VM.

### 2.4 Assumptions & Constraints
- Single-image calorie estimation has irreducible error (hidden oil, sauces, density). All calorie outputs MUST be presented as ranges with a confidence indicator, never as exact clinical values.
- Internet connectivity is required for v1.0 (on-device inference is a v2 consideration).
- Primary food domain: Indian cuisine + common fruits/vegetables; Western dishes supported via base datasets.

---

## 3. System Architecture

```
[React Native App]
   │  HTTPS (JWT)
   ▼
[DRF Async API  ── PostgreSQL / Redis]
   │  async HTTP (httpx)                 ┌────────────────────────┐
   ├──────────────► [ML Inference Service │ classifier + detector  │
   │                  (FastAPI/ONNX)      │ + portion estimator    │
   │                                      └────────────────────────┘
   ├──────────────► [OCR + Barcode Service] ──► Open Food Facts / cache
   │
   └──────────────► [Nutrition Resolver] ──► IFCT / USDA tables (Postgres)

[Airflow/Dagster] → retraining pipeline → [MLflow Registry] → CI/CD gate → deploy
[Evidently + Prometheus/Grafana] ← prediction logs, drift & latency metrics
```

**Request flow (happy path):** RN app uploads image → DRF async view validates + enqueues → calls inference service via `httpx.AsyncClient` → gets labels + bounding boxes + portion estimate → resolves nutrition from IFCT/USDA → returns structured result. Target end-to-end p95 ≤ 2.5 s.

---

## 4. Functional Requirements

### 4.1 Scanning & Recognition
- **FR-1**: The user SHALL be able to capture a photo or pick one from the gallery.
- **FR-2**: The system SHALL detect one or more food items per image (object detection), returning label, confidence, and bounding box for each.
- **FR-3**: If classifier confidence < 0.55, the app SHALL show the top-3 candidates and ask the user to confirm ("Is this poha or upma?"). Confirmations are logged as labeled training data.
- **FR-4**: For packaged products, the system SHALL route to barcode lookup (OFF) or OCR of the nutrition panel instead of the vision model. Routing decision: barcode detected → lookup; dense text detected → OCR; else → vision model.
- **FR-5**: Unrecognized items SHALL return a graceful "couldn't identify" state with a manual search fallback.

### 4.2 Portion & Nutrition Estimation
- **FR-6**: The system SHALL estimate portion size in household units (katori, cup, piece, slice) with a default grammage, displayed as an adjustable slider/stepper.
- **FR-7**: Calorie and macro values SHALL update in real time as the user adjusts the portion.
- **FR-8**: All nutrition values SHALL display as a range (e.g., "240–310 kcal") with a confidence chip (High / Medium / Low).
- **FR-9**: Nutrition resolution SHALL prefer IFCT for Indian foods and USDA for others; the source SHALL be shown in the detail view.

### 4.3 History & Goals
- **FR-10**: Registered users SHALL see a daily log (breakfast/lunch/dinner/snack) with per-meal and daily totals.
- **FR-11**: Users SHALL be able to set a daily calorie goal; the home screen SHALL show progress (consumed vs goal).
- **FR-12**: Users SHALL be able to edit or delete logged entries.

### 4.4 Accounts
- **FR-13**: Email/phone + OTP or OAuth sign-in; JWT access/refresh tokens.
- **FR-14**: Guest mode with local-only history (last 7 days), upgradeable to an account.

### 4.5 Feedback Loop (critical for ML)
- **FR-15**: Every result screen SHALL include a lightweight "correct / wrong" control; corrections capture the true label.
- **FR-16**: User-confirmed labels and corrections SHALL be stored (with consent) as candidate training data for the next retraining cycle.

---

## 5. Non-Functional Requirements

| ID | Requirement | Target |
|---|---|---|
| NFR-1 | End-to-end scan latency (p95) | ≤ 2.5 s |
| NFR-2 | Inference service latency (p95) | ≤ 800 ms |
| NFR-3 | API availability | ≥ 99.5 % monthly |
| NFR-4 | Concurrent scans supported (v1) | 100 rps burst |
| NFR-5 | Image privacy | Images deleted from hot storage within 24 h unless user opts in to contribute |
| NFR-6 | Security | TLS 1.3, JWT with rotation, OWASP ASVS L1, rate limiting per user/IP |
| NFR-7 | Accessibility | WCAG AA contrast; dynamic type support in RN |
| NFR-8 | Observability | Structured logs, Prometheus metrics, trace IDs propagated DRF → inference |

---

## 6. Machine Learning Requirements

### 6.1 Models

| Component | v1 Choice | Notes |
|---|---|---|
| Food detector | YOLOv8-s or RT-DETR fine-tuned | Multi-item plates |
| Classifier | EfficientNetV2-S or ViT-S fine-tuned | Indian food + Food-101 base; exported to ONNX, INT8-quantized |
| Portion estimator | Heuristic v1 (class-conditional priors + bounding-box area & reference-object cues), learned regressor v2 | Always user-adjustable |
| OCR | PaddleOCR / Tesseract | Nutrition panels |

### 6.2 Data
- **ML-1**: Training data = public datasets (Food-101, Indian food datasets on Kaggle) + scraped/curated Indian dish images + user-contributed labeled images (opt-in).
- **ML-2**: Nutrition ground truth = IFCT 2017 tables (primary for Indian foods) + USDA FDC.
- **ML-3**: A validation holdout of ≥ 3,000 images, stratified by cuisine and lighting conditions, SHALL be frozen and versioned (DVC).

### 6.3 Quality Gates (enforced in CI/CD)
- **ML-4**: A new classifier SHALL NOT be promoted unless Top-1 ≥ current production Top-1 and Top-5 ≥ 92 % on the frozen holdout.
- **ML-5**: Detector mAP@50 SHALL NOT regress by more than 1 point.
- **ML-6**: Inference latency budget (NFR-2) SHALL be validated in CI via load test before promotion.

### 6.4 Monitoring & Retraining
- **ML-7**: Log every prediction (label, confidence, latency, model version) — never the raw image beyond retention policy.
- **ML-8**: Drift detection (Evidently): alert when the distribution of predicted classes or mean confidence shifts beyond thresholds week-over-week (e.g., festival-season foods appearing).
- **ML-9**: Scheduled retraining pipeline (Airflow/Dagster) runs monthly or on drift alert: ingest corrections → retrain → evaluate against gates → register in MLflow → staged rollout (10 % → 100 %).
- **ML-10**: One-click rollback to the previous model version.

---

## 7. API Specification (representative)

Base: `/api/v1/` — all views async DRF (`adrf` or Django 5 async views), auth via JWT.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/scan/` | multipart image upload → returns scan result (items[], portions, nutrition, confidence, model_version) |
| GET | `/scan/{id}/` | Retrieve a past scan |
| POST | `/scan/{id}/feedback/` | Correct / confirm labels |
| GET | `/foods/search/?q=` | Manual food search (IFCT/USDA) |
| GET/POST | `/log/` | Daily nutrition log entries |
| GET | `/log/summary/?date=` | Daily totals vs goal |
| POST | `/auth/…` | Register / login / refresh |

**Async requirement**: `/scan/` SHALL use non-blocking I/O end-to-end (`httpx.AsyncClient` to inference & OCR services, `asyncpg`-backed ORM operations where possible or `sync_to_async` for ORM writes) so a slow model call never blocks the worker.

Example response (abridged):

```json
{
  "scan_id": "a1b2",
  "model_version": "clf-2026.07.1",
  "items": [
    {
      "label": "poha",
      "confidence": 0.91,
      "portion": { "unit": "katori", "grams": 150, "adjustable": true },
      "nutrition": {
        "kcal": { "min": 180, "max": 230 },
        "protein_g": 4.2, "carbs_g": 38.5, "fat_g": 5.1,
        "source": "IFCT"
      }
    }
  ]
}
```

---

## 8. UI / UX Design System

Typeface: **Inter** (all weights below).

### 8.1 Typography

| Usage | Size | Weight |
|---|---|---|
| Display | 36–40 | Bold |
| H1 | 30–32 | Bold |
| H2 | 26 | SemiBold |
| H3 | 22 | SemiBold |
| Title | 18 | SemiBold |
| Subtitle | 16 | Medium |
| Body | 16 | Regular |
| Secondary | 14 | Regular |
| Caption | 12 | Medium |
| Button | 16 | SemiBold |

### 8.2 Color Palette

| Purpose | Color |
|---|---|
| Primary | #0066FF |
| Secondary | #32C759 |
| Accent | #FFC83D |
| Background | #F8FAFC |
| Surface | #F1F5F9 |
| Card | #FFFFFF |
| Heading | #0F172A |
| Body | #334155 |
| Caption | #64748B |
| Border | #E2E8F0 |
| Success | #22C55E |
| Warning | #F59E0B |
| Error | #EF4444 |

**Gradients** — Primary: #0066FF → #4F8CFF · Success: #32C759 → #8BEA73 · Premium: #0066FF → #32C759

**Semantic mapping for NutriScan**: confidence High = Success, Medium = Warning, Low = Error; calorie-goal progress ring uses the Primary gradient; "within goal" state uses the Success gradient.

### 8.3 Buttons

| Style | Spec |
|---|---|
| Primary | Background #0066FF, text #FFFFFF, radius 16 px, medium elevation |
| Secondary | Background #FFFFFF, border #0066FF, text #0066FF |
| Success | Background #32C759, text #FFFFFF |

### 8.4 Status Colors (scan pipeline states)

| State | Color |
|---|---|
| Uploaded / queued | #3B82F6 |
| Processing | #F59E0B |
| Awaiting confirmation | #8B5CF6 |
| Completed | #22C55E |
| Failed | #EF4444 |

### 8.5 Navigation & Icons
- Bottom navigation: background #FFFFFF, selected #0066FF, unselected #94A3B8.
- Icons: primary #0F172A, active #0066FF, success #22C55E, warning #F59E0B, inactive #94A3B8.
- Tabs (v1): Home · Scan (center FAB) · History · Profile.

### 8.6 Dark Mode

| Token | Color |
|---|---|
| Background | #0B1220 |
| Surface | #111827 |
| Card | #1E293B |
| Primary | #3B82F6 |
| Text | #FFFFFF |
| Secondary text | #CBD5E1 |
| Border | #334155 |

### 8.7 Spacing, Radius, Shadows

Spacing tokens: XS 4 · S 8 · M 12 · L 16 · XL 24 · XXL 32 · Section 48 (px).

| Component | Radius |
|---|---|
| Chips | 12 px |
| Buttons | 16 px |
| Cards | 20 px |
| Bottom sheet | 28 px |
| Search bar | 18 px |
| Input fields | 16 px |

Shadows — Light: `0 4px 12px rgba(15,23,42,0.08)` · Medium: `0 10px 25px rgba(15,23,42,0.12)` · Large: `0 20px 40px rgba(15,23,42,0.16)`.

### 8.8 Key Screens (v1)
1. **Home** — daily calorie ring (Primary gradient), meal cards, scan FAB.
2. **Scan** — camera view, capture, processing state (status colors), result bottom sheet (28 px radius) with items, portion sliders, confidence chips.
3. **Confirm** — top-3 candidates when confidence is low (FR-3).
4. **History** — day list + weekly chart.
5. **Food detail** — full macro breakdown, data source badge (IFCT/USDA), feedback control.
6. **Profile/Settings** — goals, units, dark mode, data-contribution consent.

---

## 9. DevOps, CI/CD & MLOps

- **CI (GitHub Actions, on every PR)**: ruff + mypy, pytest (API), RN lint + Jest, Docker build.
- **CD (on merge to main)**: build & push images (tagged by commit SHA) → deploy to staging → smoke tests → manual approval → production.
- **Model CD**: separate pipeline — evaluate candidate against quality gates (ML-4…6) → register in MLflow → canary 10 % traffic → auto-promote or auto-rollback on error/latency regression.
- **Infra as code**: Terraform; secrets via cloud secret manager.
- **Monitoring**: Prometheus + Grafana dashboards (latency, error rate, model confidence distribution), Evidently drift reports, Sentry for app/API errors.

---

## 10. Milestones (indicative, 8 weeks)

| Week | Deliverable |
|---|---|
| 1 | Data collection & labeling plan; IFCT/USDA nutrition DB loaded; design tokens implemented in RN theme |
| 2–3 | Baseline classifier + detector fine-tuned; frozen holdout; MLflow tracking |
| 4 | Inference service (ONNX) + DRF async `/scan/` endpoint; portion heuristic v1 |
| 5 | RN app: scan flow + result sheet + history; OCR/barcode fallback |
| 6 | CI/CD with model-quality gate; staging deployment |
| 7 | Monitoring + drift dashboards; feedback loop live |
| 8 | Load testing, dark mode, polish; production release + README/architecture write-up |

---

## 11. Risks & Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| Portion estimation error | Misleading calories | Ranges + user-adjustable portions (FR-6/8); never present exact values |
| Indian-food data scarcity | Poor accuracy on core domain | Curated scraping + user feedback loop (FR-15/16); active-learning labeling |
| GPU cost | Budget overrun | INT8 ONNX on CPU for v1; batch/cached inference; scale-to-zero |
| Mixed dishes (thali) | Detection complexity | v1 supports up to 4 items/frame; explicit "add item manually" escape hatch |
| Django ORM blocking in async views | Latency under load | `sync_to_async` boundaries, connection pooling, Redis caching of nutrition lookups |
| Privacy concerns over food images | Trust/regulatory | 24 h hot-storage deletion, explicit opt-in for training contribution (NFR-5) |

---

## 12. Acceptance Criteria (v1.0 release)

1. Top-1 ≥ 80 % and Top-5 ≥ 92 % on the frozen Indian-food holdout.
2. p95 scan latency ≤ 2.5 s at 50 rps sustained.
3. Full scan → adjust portion → log meal flow works on Android and iOS builds.
4. CI blocks merges on failing tests; model promotion blocked when gates fail (demonstrated).
5. Drift alert fires in a simulated drift scenario and appears in Grafana.
6. Light and dark themes match the design tokens in §8.
