# CityEstate — Makefile
# =====================
# Common development and deployment commands

.PHONY: help install dev test lint serve dashboard deploy clean

# Default target
help:
	@echo "CityEstate — Egyptian Real Estate Multi-Agent System"
	@echo ""
	@echo "Commands:"
	@echo "  make install     Install dependencies"
	@echo "  make dev         Start development server"
	@echo "  make test        Run test suite"
	@echo "  make test-v      Run tests with verbose output"
	@echo "  make lint        Run linter"
	@echo "  make serve       Start API server"
	@echo "  make dashboard   Start Streamlit dashboard"
	@echo "  make all         Start API + Dashboard"
	@echo "  make seed        Seed database with sample data"
	@echo "  make backup      Create encrypted backup"
	@echo "  make docker-up   Start Docker services"
	@echo "  make docker-down Stop Docker services"
	@echo "  make clean       Clean cache and temp files"

# Install dependencies
install:
	pip install -r requirements.txt

# Development server (API + Dashboard)
dev:
	python main.py --serve & streamlit run src/dashboard/app.py

# Run tests
test:
	python -m pytest tests/ -v --tb=short

test-v:
	python -m pytest tests/ -v --tb=long -W all

# Lint (if ruff/flake8 installed)
lint:
	@ruff check src/ tests/ || flake8 src/ tests/ || echo "No linter installed"

# Start API server
serve:
	python main.py --serve

# Start dashboard
dashboard:
	streamlit run src/dashboard/app.py

# Start everything
all:
	python main.py --serve & streamlit run src/dashboard/app.py

# Seed database
seed:
	python scripts/seed_data.py

# Run all jobs once
run-all:
	python main.py --all

# Backup
backup:
	python main.py --backup

# Docker
docker-up:
	docker compose up -d

docker-down:
	docker compose down

docker-build:
	docker compose build

docker-logs:
	docker compose logs -f

# Clean
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	rm -rf .pytest_cache htmlcov .coverage
