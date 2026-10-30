.PHONY: install format lint test run clean help db-init

quickstart: docker-up

# === Setup ===
install:
	uv sync --directory apps/server --dev
	@if git rev-parse --git-dir > /dev/null 2>&1; then \
		uv run --directory apps/server pre-commit install; \
	else \
		echo "⚠️  Not a git repository - skipping pre-commit install"; \
		echo "   Run 'git init && make install' to set up pre-commit hooks"; \
	fi
	@echo ""
	@echo "✅ Installation complete!"
	@echo ""
	@echo "Next steps:"
	@echo "  • make docker-up        # Start the development stack"
	@echo ""
	@echo "Note: apps/server/.env is pre-configured for development"

# === Code Quality ===
format:
	uv run --directory apps/server ruff format app tests cli
	uv run --directory apps/server ruff check app tests cli --fix

lint:
	uv run --directory apps/server ruff check app tests cli
	uv run --directory apps/server ruff format app tests cli --check
	uv run --directory apps/server ty check

# === Testing ===
test:
	uv run --directory apps/server pytest tests/ -v

test-cov:
	uv run --directory apps/server pytest tests/ -v --cov=app --cov-report=html --cov-report=term-missing

# === Agent/Chatbot Tests (Fase 0-8 do plano) ===
test-agents:
	uv run --directory apps/server pytest tests/agents/ -v --tb=short

test-agent-integration:
	uv run --directory apps/server pytest tests/integration/ -v --tb=short -m integration

test-chatbot: test-agents test-agent-integration

test-chatbot-docker:
	docker compose up -d db redis app
	docker compose exec -T app uv run alembic upgrade head
	docker compose exec -T app uv run pytest tests/agents/ tests/integration/ -v --tb=short

# === Frontend Tests ===
test-frontend:
	cd apps/web && npm run test

# === E2E Tests (Playwright) ===
test-e2e:
	cd apps/web && npx playwright test

# === Run All Tests ===
test-all: test-backend test-frontend test-e2e

# === Alias for backend tests ===
test-backend:
	uv run --directory apps/server pytest tests/api/ -v

# === Database ===
db-init: docker-up

db-migrate:
	@read -p "Migration message: " msg; \
	docker compose exec app bagcoin_api db migrate -m "$$msg"

db-upgrade:
	docker compose exec app bagcoin_api db upgrade

db-downgrade:
	docker compose exec app bagcoin_api db downgrade

db-current:
	docker compose exec app bagcoin_api db current

db-history:
	docker compose exec app bagcoin_api db history

# === Server ===
run:
	uv run --directory apps/server bagcoin_api server run --reload

run-prod:
	uv run --directory apps/server bagcoin_api server run --host 0.0.0.0 --port 8000

routes:
	uv run --directory apps/server bagcoin_api server routes

# === Users ===
create-admin:
	@echo "Creating admin user..."
	docker compose exec app bagcoin_api user create-admin

user-create:
	docker compose exec app bagcoin_api user create

user-list:
	docker compose exec app bagcoin_api user list

# === Docker: Backend (Development) ===
docker-up:
	docker compose up -d --build
	@echo ""
	@echo "✅ Backend services started!"
	@echo "   API: http://localhost:8000"
	@echo "   Docs: http://localhost:8000/docs"
	@echo "   Web: http://localhost:3000"
	@echo "   Evolution: http://localhost:8080"

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f

docker-build:
	docker compose build

docker-shell:
	docker compose exec app /bin/bash

# === Docker: Individual Services ===
docker-db:
	docker compose up -d db
	@echo ""
	@echo "✅ PostgreSQL started on the Docker network"

docker-db-stop:
	docker compose stop db

docker-redis:
	docker compose up -d redis
	@echo ""
	@echo "✅ Redis started on the Docker network"

docker-redis-stop:
	docker compose stop redis

# === Cleanup ===
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ty_cache -exec rm -rf {} + 2>/dev/null || true
	rm -rf htmlcov/ .coverage coverage.xml

# === Help ===
help:
	@echo ""
	@echo "bagcoin_api - Available Commands"
	@echo "======================================"
	@echo ""
	@echo "Quick Start:"
	@echo "  make quickstart    Build and start development services"
	@echo ""
	@echo "Setup:"
	@echo "  make install       Install dependencies + pre-commit hooks"
	@echo ""
	@echo "Development:"
	@echo "  make run           Start dev server (with hot reload)"
	@echo "  make test          Run backend tests"
	@echo "  make test-cov      Run backend tests with coverage"
	@echo "  make test-backend       Run backend API tests (pytest tests/api/)"
	@echo "  make test-frontend      Run frontend Vitest tests"
	@echo "  make test-e2e           Run Playwright end-to-end tests"
	@echo "  make test-all           Run all tests (backend + frontend + e2e)"
	@echo "  make lint          Check code quality"
	@echo "  make format        Auto-format code"
	@echo ""
	@echo "Database:"
	@echo "  make db-init       Initialize database (start + migrate)"
	@echo "  make db-migrate    Create new migration"
	@echo "  make db-upgrade    Apply migrations"
	@echo "  make db-downgrade  Rollback last migration"
	@echo "  make db-current    Show current migration"
	@echo ""
	@echo "Users:"
	@echo "  make create-admin  Create admin user (for SQLAdmin access)"
	@echo "  make user-create   Create new user (interactive)"
	@echo "  make user-list     List all users"
	@echo ""
	@echo ""
	@echo "Docker (Development):"
	@echo "  make docker-up            Start backend services"
	@echo "  make docker-down          Stop all services"
	@echo "  make docker-logs          View backend logs"
	@echo "  make docker-build         Build backend images"
	@echo "  make docker-db            Start only PostgreSQL"
	@echo "  make docker-redis         Start only Redis"
	@echo ""
	@echo ""
	@echo "Other:"
	@echo "  make routes        Show all API routes"
	@echo "  make clean         Clean cache files"
	@echo ""
