.PHONY: help install lint test run clean docker-build docker-up docker-down \
        docs-up docs-down viz-up viz-down \
        prod-build prod-up prod-down prod-init

VENV := venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
KEDRO := $(VENV)/bin/kedro

help:
	@echo "Usage: make [target]"
	@echo ""
	@echo "Kedro targets:"
	@echo "  install          Create venv and install dependencies"
	@echo "  lint             Run flake8 and isort on the project"
	@echo "  test             Run Kedro tests"
	@echo "  test-pipelines   Run pipeline comparison tests (needs services up)"
	@echo "  run              Run the Kedro pipeline"
	@echo "  clean            Remove venv, caches, and build artifacts"
	@echo ""
	@echo "Docker targets:"
	@echo "  docker-build     Build Kedro Docker image"
	@echo "  docker-up        Start all containers"
	@echo "  docker-down      Stop all containers"
	@echo "  docs-up          Start docs nginx container"
	@echo "  docs-down        Stop docs nginx container"
	@echo "  viz-up           Start kedro-viz server"
	@echo "  viz-down         Stop kedro-viz server"
	@echo ""
	@echo "Production (Airflow) targets:"
	@echo "  prod-build       Build Airflow Docker image"
	@echo "  prod-init        Initialize Airflow DB and admin user"
	@echo "  prod-up          Start Airflow stack"
	@echo "  prod-down        Stop Airflow stack"

install:
	@test -d $(VENV) || python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -e .

lint:
	$(PIP) install flake8 isort
	$(VENV)/bin/flake8 src/
	$(VENV)/bin/isort --profile black src/

test:
	$(KEDRO) test

test-pipelines:
	docker compose run --rm kedro pytest /app/tests/pipeline/ -v

run:
	$(KEDRO) run

clean:
	rm -rf $(VENV) .ipynb_checkpoints data/ logs/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t wildbook-pipeline .

docker-up:
	docker compose up -d

docker-down:
	docker compose down

docs-up:
	docker compose up -d docs

docs-down:
	docker compose down docs

viz-up:
	docker compose up -d viz

viz-down:
	docker compose down viz

prod-build:
	docker compose -f docker-compose.prod.yml build

prod-init:
	docker compose -f docker-compose.prod.yml run --rm airflow-init

prod-up:
	docker compose -f docker-compose.prod.yml up -d

prod-down:
	docker compose -f docker-compose.prod.yml down
