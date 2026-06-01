#!/usr/bin/env bash
set -euo pipefail

HOSTS=(
  "http://localhost:8080/api/v1/auth/health/"
  "http://localhost:8080/api/v1/groups/health/"
  "http://localhost:8080/api/v1/expenses/health/"
  "http://localhost:8080/api/v1/settlements/health/"
  "http://localhost:8080/api/v1/media/health/"
  "http://localhost:8080/api/v1/notifications/health/"
)

for url in "${HOSTS[@]}"; do
  echo -n "Waiting for $url... "
  until curl -sSf "$url" >/dev/null; do
    printf '.'; sleep 2
  done
  echo "OK"
done

echo "All services reachable."
