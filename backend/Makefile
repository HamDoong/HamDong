SHELL := /bin/sh

.PHONY: build up down logs ps migrate makemigrations test lint format

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

logs:
	docker compose logs -f

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
