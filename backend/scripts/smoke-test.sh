#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8080}
set -e

echo "Checking HTTP health endpoints..."
for svc in auth groups expenses settlements media notifications; do
  url="$BASE_URL/api/v1/${svc}/health/"
  echo -n "Checking $url... "
  status=$(curl -s -o /dev/null -w "%{http_code}" "$url" || true)
  if [ "$status" != "200" ]; then
    echo "FAILED ($status)"
    exit 1
  fi
  echo "OK"
done

echo "Checking TCP services..."
# RabbitMQ management
if timeout 3 bash -c "</dev/tcp/localhost/15672" 2>/dev/null; then
  echo "RabbitMQ management reachable"
else
  echo "RabbitMQ management unreachable"; exit 1
fi

# Postgres
if timeout 3 bash -c "</dev/tcp/localhost/5432" 2>/dev/null; then
  echo "Postgres reachable"
else
  echo "Postgres unreachable"; exit 1
fi

# Redis
if timeout 3 bash -c "</dev/tcp/localhost/6379" 2>/dev/null; then
  echo "Redis reachable"
else
  echo "Redis unreachable"; exit 1
fi

echo "Smoke test complete."
