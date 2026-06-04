#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

echo "HamDong demo seed helper"
echo "1) Start the stack: docker compose -f backend/docker-compose.yml up --build"
echo "2) Use api-tests/hamdong.http for the full interactive scenario."
echo "3) This helper only requests the first OTP for Ali."

curl -fsS -X POST "$BASE_URL/api/v1/auth/otp/request/" \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"09120000001"}'

echo
echo "If DEBUG=true, copy debug_otp from the response into api-tests/hamdong.http."
