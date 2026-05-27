.PHONY: help install test test-unit test-integration test-api test-coverage lint format clean run dev docker-up docker-down docker-logs

help:
	@echo "HamDong IAM Service - Available Commands"
	@echo "========================================"
	@echo "make install              - Install dependencies"
	@echo "make test                 - Run all tests"
	@echo "make test-unit            - Run unit tests only"
	@echo "make test-integration     - Run integration tests only"
	@echo "make test-api             - Run API tests only"
	@echo "make test-coverage        - Run tests with coverage report"
	@echo "make lint                 - Run code linting"
	@echo "make format               - Format code with black"
	@echo "make clean                - Clean cache and build files"
	@echo "make run                  - Run development server"
	@echo "make dev                  - Run with auto-reload"
	@echo "make docker-up            - Start Docker containers"
	@echo "make docker-down          - Stop Docker containers"
	@echo "make docker-logs          - View Docker logs"

install:
	pip install -r requirements.txt

test:
	pytest -v

test-unit:
	pytest tests/unit/ -v

test-integration:
	pytest tests/integration/ -v

test-api:
	pytest tests/api/ -v

test-coverage:
	pytest --cov=src --cov-report=html --cov-report=term-missing

lint:
	pylint src/

format:
	black src/ tests/

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .pytest_cache -exec rm -rf {} +
	find . -type d -name htmlcov -exec rm -rf {} +
	find . -type f -name .coverage -delete
	find . -type d -name .mypy_cache -exec rm -rf {} +

run:
	uvicorn src.main:app --host 0.0.0.0 --port 8000

dev:
	uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f iam-service
