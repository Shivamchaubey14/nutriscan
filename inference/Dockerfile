# NutriScan inference service (FastAPI + onnxruntime, torch-free at runtime).
# Build context is the repo root for the shared pyproject.toml / uv.lock.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

# Code + classes.json only; the ONNX weights are provided at deploy time
# (compose mounts ./inference/models), keeping the image small.
COPY inference/ ./inference/

EXPOSE 8001
CMD ["uvicorn", "inference.app:app", "--host", "0.0.0.0", "--port", "8001"]
