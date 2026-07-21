# Deployment

The whole stack runs from `docker-compose.yml`, so the fastest path to a
publicly reachable staging API is a small VM. Cloud Run is documented after as
the more scalable option.

> The trained ONNX model (`inference/models/classifier_v1.onnx`, ~77 MB) is
> git-ignored. Produce it once with `uv run python inference/export_onnx.py` and
> copy it to wherever the inference service runs (bind mount on a VM, baked into
> the image for Cloud Run).

## Option A — single VM (recommended for staging)

Any Ubuntu VM with a public IP (GCP `e2-small`, a cheap VPS, …).

```bash
# on the VM
sudo apt-get update && sudo apt-get install -y docker.io docker-compose-plugin git
git clone https://github.com/Shivamchaubey14/nutriscan.git && cd nutriscan

# provide the model + production secrets
mkdir -p inference/models
#   scp your local inference/models/classifier_v1.onnx + classes.json into place
cat > .env <<'EOF'
DJANGO_SECRET_KEY=<a long random string>
DJANGO_DEBUG=0
DJANGO_ALLOWED_HOSTS=<vm-public-ip-or-domain>
MYSQL_DATABASE=nutriscan
MYSQL_PASSWORD=<strong password>
EOF

docker compose up -d --build
docker compose exec backend python manage.py seed_nutrition
```

Open port `8000` in the VM firewall. The API is then at `http://<vm-ip>:8000`
(put nginx + TLS in front for a real domain). Smoke-test it:

```bash
BASE_URL=http://<vm-ip>:8000 ./scripts/demo.sh some-food.jpg
```

## Option B — Cloud Run + Cloud SQL

More moving parts, autoscaling, no VM to babysit.

1. **Managed data**: create a Cloud SQL (MySQL 8) instance and a Memorystore
   (Redis) instance; note their connection details.
2. **Images** → Artifact Registry (bake the model into the inference image for
   this path, since Cloud Run has no bind mounts):
   ```bash
   gcloud auth login && gcloud config set project <PROJECT>
   gcloud artifacts repositories create nutriscan --repository-format=docker --location=<REGION>
   REPO=<REGION>-docker.pkg.dev/<PROJECT>/nutriscan
   docker build -f backend/Dockerfile   -t $REPO/backend:$(git rev-parse --short HEAD) .
   docker build -f inference/Dockerfile -t $REPO/inference:$(git rev-parse --short HEAD) .   # add a COPY for the .onnx
   docker push $REPO/backend:...  && docker push $REPO/inference:...
   ```
3. **Deploy** both services; wire the backend env to Cloud SQL / Memorystore and
   set `INFERENCE_URL` to the inference service URL:
   ```bash
   gcloud run deploy nutriscan-inference --image $REPO/inference:... --region <REGION> --allow-unauthenticated
   gcloud run deploy nutriscan-backend --image $REPO/backend:... --region <REGION> --allow-unauthenticated \
     --set-env-vars DJANGO_DEBUG=0,DJANGO_ALLOWED_HOSTS=<run-domain>,MYSQL_HOST=...,REDIS_URL=...,INFERENCE_URL=<inference-url>
   ```
4. Run `seed_nutrition` once (a one-off Cloud Run job or `gcloud run jobs`).

## Continuous deployment

`.github/workflows/cd.yml` runs on every merge to `main`:

1. **build-and-push** (always) — builds the backend + inference images and pushes
   them to GHCR tagged with the commit SHA and `latest`. Uses the built-in
   `GITHUB_TOKEN`, so this works with no extra setup.
2. **deploy-staging** → **smoke-test** → **deploy-production** (gated) — each
   activates once you configure the target below. Production sits behind a manual
   approval gate (the `production` GitHub Environment).

To turn on auto-deploy to a VM (Option A above), set these on the repo:

| Kind | Name | Value |
|------|------|-------|
| Variable | `STAGING_HOST` / `STAGING_USER` | VM host + SSH user |
| Variable | `STAGING_URL` | public API root (enables the smoke test) |
| Secret | `STAGING_SSH_KEY` | private key for the VM |
| Variable/Secret | `PROD_HOST` / `PROD_USER` / `PROD_SSH_KEY` | same for production |

The VM must have the repo cloned at `~/nutriscan` and a `.env` in place (see
Option A). The deploy step pulls the SHA-tagged images and restarts the stack.

**Rollback**: redeploy a previous commit's images —
`TAG=<previous-sha> docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --no-build`
on the host (or re-run the workflow from that commit).

## Production checklist

- `DJANGO_DEBUG=0` and a real `DJANGO_ALLOWED_HOSTS` (never `*`).
- A strong, secret `DJANGO_SECRET_KEY` (from a secret manager, not `.env` in git).
- TLS in front of the backend.
