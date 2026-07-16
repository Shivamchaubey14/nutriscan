# NutriScan — 30-Day Step-by-Step Build Plan

**Goal:** By Day 30, a working end-to-end product: scan Indian food → recognize → estimate calories → log meals, running behind a production-grade ML stack (CI/CD, model registry, quality gates, monitoring) with a React Native app.

**Assumptions:** ~3–5 focused hours/day, solo builder, free/cheap infra (GitHub Actions free tier, one small cloud VM or Cloud Run, Colab/Kaggle GPU for training). Every day ends with a commit — the green contribution graph is part of the portfolio.

**Rule of the plan:** ship a thin vertical slice early (Day 10), then deepen. Never let the repo go more than 2 days without something runnable.

---

## Phase 1 — Foundation & Data (Days 1–6)

### Day 1 — Repo, tooling, project skeleton
- Create a GitHub **monorepo**: `/backend` (DRF), `/inference` (FastAPI), `/mobile` (RN), `/ml` (training), `/infra` (Docker, CI).
- Python 3.12 + `uv` or `poetry`; add `ruff`, `mypy`, `pytest`, `pre-commit`.
- Write the README skeleton NOW: problem statement, architecture diagram placeholder, planned stack. (Recruiters read READMEs, not code.)
- **Deliverable:** repo with pre-commit hooks passing on a hello-world test.

### Day 2 — CI pipeline first (yes, before the app)
- GitHub Actions workflow: lint + typecheck + pytest on every push/PR; branch protection on `main`.
- Add a Docker build job (even for the empty skeleton).
- Break a test on purpose, watch the PR get blocked, fix it. Now you *know* the gate works.
- **Deliverable:** `.github/workflows/ci.yml`, red-then-green PR.

### Day 3 — Dataset audit & download
- Download candidate datasets: Food-101 (base/Western), Indian food datasets from Kaggle (search "indian food images"), fruits/vegetables datasets.
- Write `/ml/notebooks/01_data_audit.ipynb`: class counts, image quality, overlap between datasets, class imbalance chart.
- Decide the **v1 label set**: pick ~60–80 classes (top Indian dishes + 20 fruits/veg). Write it down in `ml/labels.yaml` — scope discipline is the difference between shipping and not.
- **Deliverable:** data audit notebook + frozen `labels.yaml`.

### Day 4 — Nutrition database
- Load IFCT 2017 food composition data + USDA FDC subset into PostgreSQL (tables: `food`, `nutrient`, `food_nutrient`, `portion_unit`).
- Write the mapping table: each of your ~70 vision classes → IFCT/USDA food id + default household portions (katori/piece/cup with grams).
- This mapping is tedious and *exactly* the domain work that makes the project yours. Budget the whole day.
- **Deliverable:** `nutrition` Postgres schema + seeded data + mapping YAML.

### Day 5 — Data pipeline & versioning
- Set up **DVC** (or a simple manifest-based approach) for dataset versioning.
- Write `ml/prepare_data.py`: merge sources, dedupe, split train/val/**frozen test** (stratified). The frozen test set (~2–3k images) never changes after today — it's what your quality gates measure against.
- **Deliverable:** versioned dataset v1 with reproducible split script.

### Day 6 — Baseline model (fast and dumb on purpose)
- Fine-tune a small pretrained classifier (EfficientNetV2-S or ResNet-50) for a few epochs on Colab/Kaggle GPU.
- Set up **MLflow** (local or free hosted) — log params, metrics, artifacts from run #1 onward.
- Record baseline Top-1/Top-5 on the frozen test set. Whatever it is (probably 60–70%), that's your reference line.
- **Deliverable:** MLflow experiment with baseline model artifact + metrics.

---

## Phase 2 — Backend & Inference Service (Days 7–12)

### Day 7 — DRF async skeleton
- Django 5 project with ASGI (Uvicorn), custom user model, JWT auth (`djangorestframework-simplejwt`), health endpoint.
- Apps: `accounts`, `scans`, `nutrition`, `logs`.
- Dockerize; add Postgres + Redis via `docker-compose`.
- **Deliverable:** `docker compose up` → running API with `/health` and auth endpoints, tests in CI.

### Day 8 — Inference microservice
- FastAPI service in `/inference`: export Day 6 model to **ONNX**, serve `/predict` (image in → top-k labels + confidences out).
- Add INT8 quantization; benchmark latency CPU vs unquantized (save the numbers — great README chart later).
- **Deliverable:** Dockerized inference service, `/predict` under ~300 ms CPU for one image.

### Day 9 — The /scan endpoint (async end-to-end)
- DRF async view: accept multipart image → call inference service with `httpx.AsyncClient` → resolve nutrition from Postgres → return the SRS §7 response shape (items, portion default, kcal **range**, confidence, model_version).
- Use `sync_to_async` carefully around ORM writes; cache nutrition lookups in Redis.
- Write integration tests with a mocked inference service.
- **Deliverable:** `POST /api/v1/scan/` returns real predictions on a test image.

### Day 10 — 🏁 Vertical slice checkpoint
- Wire everything: upload a photo of poha via `curl`/Postman → get label + calories back from the full stack.
- Deploy backend + inference to your VM/Cloud Run (manual deploy is fine today).
- Record a 30-second screen capture of the working API. First proof-of-life artifact.
- **Deliverable:** publicly reachable staging API + demo GIF in README.

### Day 11 — Feedback + history endpoints
- `POST /scan/{id}/feedback/` (confirm/correct labels — this feeds retraining later).
- `GET/POST /log/` meal logging, `GET /log/summary/` daily totals vs goal.
- `GET /foods/search/` manual search over the nutrition DB (trigram index).
- **Deliverable:** full v1 API surface, tested.

### Day 12 — CD pipeline
- Extend GitHub Actions: on merge to `main` → build images tagged with commit SHA → push to registry → deploy to staging automatically → smoke test hits `/health` and a canned `/scan`.
- Production deploy behind a manual approval step.
- **Deliverable:** merge-to-deploy working; rollback = redeploy previous SHA (document it).

---

## Phase 3 — Mobile App (Days 13–18)

### Day 13 — RN project + design system
- Init React Native (or Expo — recommended for speed) with TypeScript.
- Implement the **theme file** from your design system: Inter font, all color tokens, spacing (XS–Section), radii, shadows, light + dark palettes. Build `Button` (primary/secondary/success), `Chip`, `Card` components against the tokens.
- **Deliverable:** a storybook-style demo screen rendering every token/component in both themes.

### Day 14 — Auth + navigation
- Bottom tab navigation (Home / Scan FAB / History / Profile) per SRS §8.5.
- Login/register/OTP screens wired to the JWT endpoints; secure token storage; guest mode.
- **Deliverable:** working auth flow against staging.

### Day 15 — Camera & scan flow
- Camera screen (VisionCamera or Expo Camera): capture, gallery pick, compress client-side, upload to `/scan/`.
- Processing states using your status colors (queued → processing → done/failed).
- **Deliverable:** photo taken on a real phone hits staging and returns a result.

### Day 16 — Result bottom sheet
- 28 px-radius bottom sheet: detected items, confidence chips (High/Medium/Low → success/warning/error colors), portion stepper/slider in household units, live-updating kcal range and macros, IFCT/USDA source badge.
- Low-confidence path: top-3 candidate picker (FR-3) wired to the feedback endpoint.
- **Deliverable:** the money screen — this is your demo-video centerpiece.

### Day 17 — Home & history
- Home: daily calorie progress ring (Primary gradient), meal cards, scan FAB.
- History: day list, edit/delete entries, simple weekly bar chart.
- **Deliverable:** log-a-meal loop complete: scan → adjust → save → see totals.

### Day 18 — Polish + dark mode pass
- Dark theme QA on every screen, empty states, error toasts, loading skeletons.
- Profile screen: calorie goal, units, data-contribution consent toggle (NFR-5).
- **Deliverable:** APK build shared to your own phone; second demo GIF for README.

---

## Phase 4 — Real ML Depth (Days 19–25)

### Day 19–20 — Better model, proper training
- Full fine-tune with augmentation (RandAugment, mixup), class-imbalance handling, cosine LR schedule; try EfficientNetV2-S vs ViT-S — pick by frozen-test Top-1, tracked in MLflow.
- Target: **Top-1 ≥ 80%, Top-5 ≥ 92%** on the frozen set.
- **Deliverable:** production candidate model + comparison table in MLflow.

### Day 21 — Multi-item detection
- Fine-tune YOLOv8-s on plate images for your label set (or start with 10 most common combos — thali reality check).
- Pipeline: detector crops → classifier per crop. Cap at 4 items/frame (SRS risk table).
- **Deliverable:** multi-item scan works on a thali photo.

### Day 22 — Portion estimation v1 + OCR fallback
- Portion heuristic: class-conditional priors (a katori of dal ≈ 150 g) adjusted by bounding-box relative area; always user-adjustable, always a range.
- Barcode → Open Food Facts lookup; PaddleOCR on nutrition panels; routing logic (barcode → lookup, dense text → OCR, else vision).
- **Deliverable:** packaged-product scan path works.

### Day 23 — Model quality gate in CI
- The flagship MLOps feature: a GitHub Actions job that evaluates any candidate model on the frozen test set and **blocks promotion** unless it beats production Top-1 and meets the latency budget (load-test step with `locust`/`k6`).
- Promotion = tag in MLflow registry → CD deploys new ONNX to inference service (canary if you have time, blue-green flip if not).
- Demonstrate: submit a deliberately worse model, screenshot the blocked pipeline. **That screenshot goes in the README.**
- **Deliverable:** gated model CD, proven with a failed + a passed promotion.

### Day 24 — Monitoring & drift
- Prometheus metrics from both services (latency, error rate, confidence histogram); Grafana dashboard.
- Evidently: weekly job comparing predicted-class distribution vs reference; alert on drift.
- Simulate drift (feed 200 dessert images), capture the alert firing.
- **Deliverable:** dashboard screenshots + simulated drift alert (README material again).

### Day 25 — Retraining pipeline
- Airflow or Dagster (or a scheduled GitHub Action, honestly fine at this scale): pull accumulated feedback corrections → merge into dataset vNext → retrain → auto-evaluate against the gate → register candidate.
- Run the whole loop once manually end-to-end.
- **Deliverable:** documented, runnable retraining DAG — the "system that improves itself" story.

---

## Phase 5 — Hardening & Portfolio (Days 26–30)

### Day 26 — Load testing & performance
- `k6`/`locust` against staging: find p95 at 25/50/100 rps; fix the top bottleneck (usually image decode or ORM N+1); add Redis caching where it pays.
- **Deliverable:** latency table before/after in README.

### Day 27 — Security & privacy pass
- Rate limiting (per-user + per-IP), upload size/type validation, JWT rotation check, 24 h image deletion job, dependency audit (`pip-audit`, `npm audit`).
- **Deliverable:** short SECURITY.md noting what's handled and known gaps (honesty > pretending).

### Day 28 — Documentation day
- Final README: architecture diagram, demo GIFs, metrics table, the blocked-pipeline screenshot, drift alert, latency numbers, "design decisions & trade-offs" section, "what I'd do next".
- Write the blog post: pick ONE hard problem ("How I built a CI gate that stops bad models from deploying" or "Why Indian food breaks Western food classifiers").
- **Deliverable:** README you'd be proud to send with a job application + published post (dev.to/Medium/LinkedIn).

### Day 29 — Demo video + release
- 2–3 minute video: open app → scan real food → adjust portion → log → show Grafana + a model promotion in Actions. Talk over it.
- Tag `v1.0.0`, production deploy through your own pipeline, build a shareable APK (and TestFlight if you have an Apple account).
- **Deliverable:** public release + video linked at the top of the README.

### Day 30 — Retro & job-hunt packaging
- Write RETRO.md: what you'd redo, what surprised you (interviewers love asking this — pre-write your answers).
- Update resume + LinkedIn: 3 bullet points with numbers ("p95 1.8 s at 50 rps", "Top-1 84% on 70-class Indian food set", "CI gate blocked 2 regressing models").
- List 10 target companies (incl. NZ agritech: Halter, LIC, Fonterra digital) and send the first 3 applications with the project linked.
- **Deliverable:** the project is now working *for* you.

---

## Weekly checkpoints (don't skip)

| End of | You must have | If behind, cut |
|---|---|---|
| Week 1 (D6) | Data + baseline model + CI | Fancy datasets — 40 classes is fine |
| Week 2 (D12) | Deployed API returning real predictions | Detection (classify single item only) |
| Week 3 (D18) | App on your phone doing the full loop | Charts, guest mode |
| Week 4 (D25) | Quality gate + monitoring proven | Airflow (use scheduled Action), canary (use blue-green) |
| Day 30 | README + video + first applications | Nothing. These ARE the point. |

## Scope-cut priority (when reality hits)
Cut in this order: OCR fallback → multi-item detection → retraining automation (keep it manual but documented) → weekly charts. **Never cut:** CI/CD, the model quality gate, monitoring, the README, the demo video — those are what get you hired.
