.PHONY: venv install install-dev local-dev local-test local-lint dev test

PYTHON := python3.12
VENV := venv
BIN := $(VENV)/bin

venv:
	$(PYTHON) -m venv $(VENV)

install: venv
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install .

install-dev: venv
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install ".[dev]"

local-dev:
	$(BIN)/uvicorn app:app --reload --host 0.0.0.0 --port 8000

local-test:
	$(BIN)/python -m pytest tests/ -v --tb=short

local-lint:
	$(BIN)/ruff check .
	$(BIN)/ruff format --check .

dev:
	docker compose up --build

test:
	docker compose run --rm app python -m pytest tests/ -v --tb=short
