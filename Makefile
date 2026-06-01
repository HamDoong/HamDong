SHELL := /bin/sh

LOGS_TAIL ?= 200

.PHONY: build up down restart logs ps migrate makemigrations createsuperuser test test-identity test-notification test-group test-expense test-media test-settlement test-integration test-smoke lint format check seed dispatch-outbox consume-events run-reminders reset

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

restart:
	docker compose down
	docker compose up -d

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

createsuperuser:
	docker compose run --rm identity-service python manage.py createsuperuser

test:
	docker compose run --rm identity-service python manage.py test
	docker compose run --rm group-service python manage.py test
	docker compose run --rm expense-service python manage.py test
	docker compose run --rm settlement-service python manage.py test
	docker compose run --rm media-service python manage.py test
	docker compose run --rm notification-service python manage.py test

# per-service test targets

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
	@echo "Run integration tests inside your environment"

test-smoke:
	scripts/smoke-test.sh

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

check:
	docker compose config >/dev/null
	@echo "docker compose config OK"

seed:
	scripts/seed-demo-data.sh

dispatch-outbox:
	docker compose run --rm settlement-service python manage.py dispatch_outbox

consume-events:
	docker compose run --rm notification-service python manage.py run_consumer

run-reminders:
	docker compose run --rm settlement-service python manage.py run_reminder_scheduler

reset:
	scripts/reset-local.sh
