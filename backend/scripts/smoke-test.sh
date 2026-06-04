#!/usr/bin/env bash
set -e

BASE_URL="${BASE_URL:-http://localhost:8080}"

check_endpoint() {
  local endpoint="$1"
  echo "Checking $BASE_URL$endpoint"
  curl -fsS "$BASE_URL$endpoint" > /dev/null
}

check_endpoint "/api/v1/auth/health/"
check_endpoint "/api/v1/groups/health/"
check_endpoint "/api/v1/expenses/health/"
check_endpoint "/api/v1/settlements/health/"
check_endpoint "/api/v1/media/health/"
check_endpoint "/api/v1/notifications/health/"

echo "All gateway health checks passed."
