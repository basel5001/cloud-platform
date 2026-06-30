.PHONY: install install-dev test lint format dev docker-build docker-run clean

install:
	pip install -r requirements.txt

install-dev:
	pip install -r requirements-dev.txt

test:
	python -m pytest tests/ -v

lint:
	ruff check src/ tests/
	ruff format --check src/ tests/

format:
	ruff check --fix src/ tests/
	ruff format src/ tests/

dev:
	uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

docker-build:
	docker build -t cloud-platform:latest .

docker-run:
	docker compose up -d

docker-down:
	docker compose down

clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache .ruff_cache .mypy_cache
	rm -f platform.db
