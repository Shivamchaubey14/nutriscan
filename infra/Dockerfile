# Skeleton image — proves the Docker build path in CI.
# Will be replaced by per-service Dockerfiles (backend, inference) as they land.
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN pip install --no-cache-dir uv && uv sync --locked --no-dev

COPY . .

CMD ["python", "-c", "print('nutriscan skeleton image ok')"]
