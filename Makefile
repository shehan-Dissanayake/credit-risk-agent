.PHONY: install lint format typecheck test check run hello-trace up down

install:
	pip install -e ".[dev]"
	pre-commit install

lint:
	ruff check .
	ruff format --check .

format:
	ruff check --fix .
	ruff format .

typecheck:
	mypy

test:
	pytest

# Everything CI runs, in one command. Run this before every push.
check: lint typecheck test

run:
	uvicorn credit_risk_agent.api.main:app --reload

hello-trace:
	cra hello-trace

up:
	docker compose up -d

down:
	docker compose down
