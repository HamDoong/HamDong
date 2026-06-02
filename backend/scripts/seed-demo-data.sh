#!/usr/bin/env bash
set -euo pipefail

BASE_URL=${BASE_URL:-http://localhost:8080}
echo "Seeding demo data (manual placeholders)..."
echo "1) Request OTP for +15555550123"
curl -s -X POST "$BASE_URL/api/v1/auth/otp/request/" -H "Content-Type: application/json" -d '{"phone_number":"+15555550123"}'

echo "Seed script finished. Follow backend/api-tests/hamdong.http for interactive flow."
