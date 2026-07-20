# NutriScan backend (Django 5 + DRF, served via Uvicorn/ASGI).
# Build context is the repo root so the shared pyproject.toml / uv.lock are available.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_PROJECT_ENVIRONMENT=/usr/local

WORKDIR /app

COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Install only the runtime dependency group into the system environment (no dev =
# no torch/mlflow), so python/uvicorn are on PATH and the image stays small.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY backend/ ./backend/

WORKDIR /app/backend
EXPOSE 8000

# Apply migrations, then serve. Overridable by compose for other entrypoints.
CMD ["sh", "-c", "python manage.py migrate --noinput && uvicorn config.asgi:application --host 0.0.0.0 --port 8000"]
