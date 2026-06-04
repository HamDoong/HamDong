# Testing

## Start Services

```bash
docker compose -f backend/docker-compose.yml up --build
```

## Run Service Tests

```bash
docker compose -f backend/docker-compose.yml exec identity-service pytest
docker compose -f backend/docker-compose.yml exec group-service pytest
docker compose -f backend/docker-compose.yml exec expense-service pytest
docker compose -f backend/docker-compose.yml exec media-service pytest
docker compose -f backend/docker-compose.yml exec settlement-service pytest
docker compose -f backend/docker-compose.yml exec notification-service pytest
```

## Run Smoke Test

```bash
BASE_URL=http://localhost:8080 backend/scripts/smoke-test.sh
```

## Run REST Client API Tests

Open these files in VS Code with the REST Client extension:

- `api-tests/identity.http`
- `api-tests/group.http`
- `api-tests/expense.http`
- `api-tests/media.http`
- `api-tests/settlement.http`
- `api-tests/notification.http`
- `api-tests/hamdong.http`

## Recommended Verification Order

1. health endpoints through the gateway
2. OTP login
3. group + invite flow
4. expense create/list/detail
5. balances / debts
6. smart settlement plan
7. reminder and event-worker checks

## Swagger Checks

Verify these pages load after startup:

- `http://localhost:8001/api/docs/`
- `http://localhost:8002/api/docs/`
- `http://localhost:8003/api/docs/`
- `http://localhost:8004/api/docs/`
- `http://localhost:8005/api/docs/`
- `http://localhost:8006/api/docs/`

## Notes

- `api-tests/hamdong.http` is the main demo walkthrough.
- If `DEBUG=true`, copy `debug_otp` values into the request variables manually.
- If the media receipt fixture is missing, skip the optional upload step or add `api-tests/fixtures/receipt.jpg`.
- Because balances and reminders depend on async consumers, wait a few seconds after publishing expense/settlement-changing requests before running the next dependent request.
