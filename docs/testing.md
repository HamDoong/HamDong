# Testing

How to run tests and troubleshoot common failures.

Run all tests (via backend Makefile):

    make -C backend test

Run per-service tests:

    make -C backend test-identity
    make -C backend test-notification
    make -C backend test-group
    make -C backend test-expense
    make -C backend test-media
    make -C backend test-settlement

Integration tests:

    make -C backend test-integration

Smoke tests:

    make -C backend test-smoke

API tests with VS Code REST Client:

1. Open `api-tests/hamdong.http` in VS Code.
2. Set `@baseUrl` if your gateway runs on a different port.
3. Run requests in order and replace variables as needed.

Troubleshooting:
- Check service logs with `make -C backend logs`.
- Ensure migrations are applied: `make -C backend migrate`.
- If tests fail due to external services, run them with mocks or use docker compose to bring up dependencies.
