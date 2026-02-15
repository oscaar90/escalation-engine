.PHONY: test lint format run validate install dev

install:
	pip install -e .

dev:
	pip install -e ".[dev]"

test:
	pytest tests/ -v

lint:
	ruff check src/ && mypy src/

format:
	ruff format src/ tests/

run:
	escalation resolve-cmd payments-api

validate:
	escalation validate
