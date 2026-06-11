#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

check_endpoint() {
  local endpoint="$1"
  echo "Checking ${BASE_URL}${endpoint}"
  curl -fsS "${BASE_URL}${endpoint}" > /dev/null
}

check_endpoint "/api/v1/auth/health/"
check_endpoint "/api/v1/groups/health/"
check_endpoint "/api/v1/expenses/health/"
check_endpoint "/api/v1/media/health/"
check_endpoint "/api/v1/settlements/health/"
check_endpoint "/api/v1/notifications/health/"

check_tcp() {
  local name="$1"
  local port="$2"

  echo "Checking ${name} on localhost:${port}"
  timeout 3 bash -c "</dev/tcp/localhost/${port}" 2>/dev/null
}

check_tcp "RabbitMQ management" "15672"
check_tcp "PostgreSQL" "5432"
check_tcp "Redis" "6379"

echo "All gateway and TCP health checks passed."
