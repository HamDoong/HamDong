#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8080}
echo "Checking health endpoints..."
for svc in auth groups expenses settlements media notifications; do
  url="$BASE_URL/api/v1/${svc}/health/"
  echo -n "Checking $url... " 
  status=$(curl -s -o /dev/null -w "%{http_code}" "$url" || true)
  echo "$status"
done

echo "Smoke test complete."
