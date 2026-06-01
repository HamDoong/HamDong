SHELL := /bin/sh

.PHONY: build up down logs ps migrate makemigrations test lint format

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

LOGS_TAIL ?= 200

logs:
	docker compose logs --tail=$(LOGS_TAIL)

ps:
	docker compose ps

migrate:
	docker compose run --rm identity-service python manage.py migrate
	docker compose run --rm group-service python manage.py migrate
	docker compose run --rm expense-service python manage.py migrate
	docker compose run --rm settlement-service python manage.py migrate
	docker compose run --rm media-service python manage.py migrate
	docker compose run --rm notification-service python manage.py migrate

makemigrations:
	docker compose run --rm identity-service python manage.py makemigrations
	docker compose run --rm group-service python manage.py makemigrations
	docker compose run --rm expense-service python manage.py makemigrations
	docker compose run --rm settlement-service python manage.py makemigrations
	docker compose run --rm media-service python manage.py makemigrations
	docker compose run --rm notification-service python manage.py makemigrations

test:
	docker compose run --rm identity-service python manage.py test
	docker compose run --rm group-service python manage.py test
	docker compose run --rm expense-service python manage.py test
	docker compose run --rm settlement-service python manage.py test
	docker compose run --rm media-service python manage.py test
	docker compose run --rm notification-service python manage.py test

# per-service test targets
.PHONY: test-identity test-group test-expense test-settlement test-media test-notification test-integration test-smoke

test-identity:
	docker compose run --rm identity-service python manage.py test

test-group:
	docker compose run --rm group-service python manage.py test

test-expense:
	docker compose run --rm expense-service python manage.py test

test-settlement:
	docker compose run --rm settlement-service python manage.py test

test-media:
	docker compose run --rm media-service python manage.py test

test-notification:
	docker compose run --rm notification-service python manage.py test

test-integration:
	# run a curated integration test suite (to be implemented)
	@echo "Run integration tests inside your environment"

test-smoke:
	./backend/scripts/smoke-test.sh

lint:
	docker compose run --rm identity-service ruff check .
	docker compose run --rm group-service ruff check .
	docker compose run --rm expense-service ruff check .
	docker compose run --rm settlement-service ruff check .
	docker compose run --rm media-service ruff check .
	docker compose run --rm notification-service ruff check .

format:
	docker compose run --rm identity-service black .
	docker compose run --rm group-service black .
	docker compose run --rm expense-service black .
	docker compose run --rm settlement-service black .
	docker compose run --rm media-service black .
	docker compose run --rm notification-service black .

.PHONY: smoke seed test-smoke ci-check

smoke:
	./backend/scripts/smoke-test.sh

seed:
	./backend/scripts/seed-demo-data.sh

test-smoke:
	@echo "Running quick smoke tests..."
	./backend/scripts/smoke-test.sh

ci-check:
	docker compose config >/dev/null
	@echo "docker compose config OK"

.PHONY: restart createsuperuser check dispatch-outbox consume-events run-reminders reset

restart:
	docker compose down && docker compose up -d

createsuperuser:
	docker compose run --rm identity-service python manage.py createsuperuser

check:
	make -C . ci-check

dispatch-outbox:
	docker compose run --rm settlement-service python manage.py dispatch_outbox

consume-events:
	# run a consumer for a service, e.g. notification consumer
	docker compose run --rm notification-service python manage.py run_consumer

run-reminders:
	docker compose run --rm settlement-service python manage.py run_reminder_scheduler

reset:
	./backend/scripts/reset-local.sh
