#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://localhost:8080}"

cat <<'EOF'
HamDong demo helper

This script intentionally does not seed the database directly.
The demo should go through the API so events, outbox rows, consumers, and projections are exercised.

Recommended flow:
1. Copy environment files:
   cp .env.example .env

2. Start the stack:
   docker compose -f docker-compose.yml up --build

3. Open:
   api-tests/hamdong.http

4. Run the OTP request steps for Ali, Sara, and Reza.
   If DEBUG=true, copy each returned debug_otp value into:
   @aliOtp
   @saraOtp
   @rezaOtp

5. Continue through:
   group creation
   invite creation
   invite acceptance
   optional receipt upload
   expense creation
   balances
   settlement-plan generate/activate
   report-paid
   confirm
   final balances
EOF

echo
echo "Optional quick OTP request:"
curl -fsS -X POST "${BASE_URL}/api/v1/auth/otp/request/"   -H "Content-Type: application/json"   -d '{"phone_number":"09120000001"}' || true

echo
echo "If DEBUG=true, copy debug_otp into api-tests/hamdong.http."
