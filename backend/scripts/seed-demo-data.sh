#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

cat <<EOF
HamDong demo helper

This project uses API-based demo setup instead of direct database seeding.
Direct seeding could bypass events, outbox rows, and projections.

Steps:
1. Start the stack:
   docker compose -f backend/docker-compose.yml up --build

2. Open:
   api-tests/hamdong.http

3. Run the OTP request steps. If DEBUG=true, copy each debug_otp value into:
   @aliOtp
   @saraOtp
   @rezaOtp

4. Continue the REST Client flow through group, expense, balance, settlement plan, report-paid, confirm, and final balance.

Optional quick check:
EOF

curl -fsS -X POST "$BASE_URL/api/v1/auth/otp/request/" \
  -H "Content-Type: application/json" \
  -d '{"phone_number":"09120000001"}' || true

echo
echo "If the stack is running with DEBUG=true, copy the returned debug_otp into api-tests/hamdong.http."
