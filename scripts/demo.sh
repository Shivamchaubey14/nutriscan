#!/usr/bin/env bash
# End-to-end demo: register -> JWT -> scan a food photo -> calorie range.
#
# Point it at a running stack (docker compose up) or your staging URL:
#   BASE_URL=http://localhost:8000 ./scripts/demo.sh ml/data/raw/food-101/images/pizza/1005649.jpg
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8000}"
EMAIL="${DEMO_EMAIL:-demo@nutriscan.app}"
PASSWORD="${DEMO_PASSWORD:-sup3rSecret!pw}"
IMAGE="${1:-}"

if [ -z "$IMAGE" ] || [ ! -f "$IMAGE" ]; then
  echo "usage: BASE_URL=<url> $0 <path-to-food-image>" >&2
  exit 1
fi

echo "→ register $EMAIL (ok if it already exists)"
curl -s -o /dev/null -X POST "$BASE_URL/api/v1/auth/register/" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" || true

echo "→ obtain JWT"
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/token/" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python -c "import sys, json; print(json.load(sys.stdin)['access'])")

echo "→ scan $IMAGE"
curl -s -X POST "$BASE_URL/api/v1/scan/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@$IMAGE" | python -m json.tool
