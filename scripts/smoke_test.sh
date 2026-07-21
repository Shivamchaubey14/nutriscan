#!/usr/bin/env bash
# Post-deploy smoke test: the API is healthy and the scan pipeline responds.
# Used by CD after a staging deploy; also runnable by hand.
#   BASE_URL=https://staging.example.com ./scripts/smoke_test.sh
set -euo pipefail

BASE_URL="${BASE_URL:?set BASE_URL to the deployed API root}"
EMAIL="${SMOKE_EMAIL:-smoke@nutriscan.app}"
PASSWORD="${SMOKE_PASSWORD:-sup3rSecret!pw}"
IMAGE="${1:-backend/tests/fixtures/smoke.jpg}"

echo "→ /health"
code=$(curl -s -o /dev/null -w "%{http_code}" "$BASE_URL/health/")
[ "$code" = "200" ] || { echo "health check failed: HTTP $code" >&2; exit 1; }

echo "→ auth"
curl -s -o /dev/null -X POST "$BASE_URL/api/v1/auth/register/" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" || true
TOKEN=$(curl -s -X POST "$BASE_URL/api/v1/auth/token/" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$EMAIL\",\"password\":\"$PASSWORD\"}" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['access'])")

echo "→ /scan"
curl -s -X POST "$BASE_URL/api/v1/scan/" \
  -H "Authorization: Bearer $TOKEN" \
  -F "image=@$IMAGE" \
  | python3 -c "import sys, json; d = json.load(sys.stdin); assert d.get('candidates'), 'no predictions returned'; print('smoke OK — model responded:', d['candidates'][0]['label'])"
