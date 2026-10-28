.PHONY: install format lint test run clean help db-init

# === Quick Start (one command to rule them all) ===
quickstart: install docker-up
	@echo "Waiting for database to be ready..."
	@sleep 8
	@echo "Creating initial migration..."
	cd apps/server && uv run bagcoin_api db migrate -m "initial" || true
	@echo "Applying migrations..."
	cd apps/server && uv run bagcoin_api db upgrade
	@echo "Creating admin user (admin@example.com / admin123)..."
	cd apps/server && uv run bagcoin_api user create --email admin@example.com --password admin123 --superuser 2>/dev/null || true
	@echo ""
	@echo "🚀 Ready! All services running:"
	@echo "   API:      http://localhost:8000"
	@echo "   Docs:     http://localhost:8000/docs"
	@echo "   Admin:    http://localhost:8000/admin (admin@example.com / admin123)"

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
	@echo "  • make docker-db        # Start PostgreSQL"
	@echo "  • make db-upgrade       # Apply migrations"
	@echo "  • make run              # Start development server"
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

# === WhatsApp Bridge Tests ===
test-whatsapp-bridge:
	cd apps/whatsapp-bridge && npx vitest run

# === Run All Tests ===
test-all: test-backend test-frontend test-e2e test-whatsapp-bridge

# === Alias for backend tests ===
test-backend:
	uv run --directory apps/server pytest tests/api/ -v

# === Database ===
db-init: docker-db
	@echo "Waiting for PostgreSQL to be ready..."
	@sleep 8
	cd apps/server && uv run bagcoin_api db migrate -m "initial" || true
	cd apps/server && uv run bagcoin_api db upgrade
	@echo ""
	@echo "✅ Database initialized!"

db-migrate:
	@read -p "Migration message: " msg; \
	uv run --directory apps/server bagcoin_api db migrate -m "$$msg"

db-upgrade:
	uv run --directory apps/server bagcoin_api db upgrade

db-downgrade:
	uv run --directory apps/server bagcoin_api db downgrade

db-current:
	uv run --directory apps/server bagcoin_api db current

db-history:
	uv run --directory apps/server bagcoin_api db history

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
	uv run --directory apps/server bagcoin_api user create-admin

user-create:
	uv run --directory apps/server bagcoin_api user create

user-list:
	uv run --directory apps/server bagcoin_api user list

# === Celery ===
celery-worker:
	uv run --directory apps/server bagcoin_api celery worker

celery-beat:
	uv run --directory apps/server bagcoin_api celery beat

celery-flower:
	uv run --directory apps/server bagcoin_api celery flower
	@echo ""
	@echo "✅ Flower started at http://localhost:5555"

# === Docker: Backend (Development) ===
docker-up:
	docker-compose build app
	docker-compose up -d
	@echo ""
	@echo "✅ Backend services started!"
	@echo "   API: http://localhost:8000"
	@echo "   Docs: http://localhost:8000/docs"
	@echo "   Flower: http://localhost:5555"
	@echo "   PostgreSQL: localhost:5432"
	@echo "   Redis: localhost:6379"

docker-down:
	docker-compose down

docker-logs:
	docker-compose logs -f

docker-build:
	docker-compose build

docker-shell:
	docker-compose exec app /bin/bash

# === Docker: Production (with Traefik) ===
docker-prod:
	docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
	@echo ""
	@echo "✅ Production services started with Traefik!"
	@echo ""
	@echo "Endpoints (replace DOMAIN with your domain):"
	@echo "   API: https://api.$$DOMAIN"
	@echo "   Flower: https://flower.$$DOMAIN"
	@echo "   Traefik: https://traefik.$$DOMAIN"

docker-prod-down:
	docker compose --env-file .env.prod -f docker-compose.prod.yml down

docker-prod-logs:
	docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f

docker-prod-build:
	docker compose --env-file .env.prod -f docker-compose.prod.yml build

# === Docker: Individual Services ===
docker-db:
	docker-compose up -d db
	@echo ""
	@echo "✅ PostgreSQL started on port 5432"
	@echo "   Connection: postgresql://postgres:postgres@localhost:5432/bagcoin_api"

docker-db-stop:
	docker-compose stop db

docker-redis:
	docker-compose up -d redis
	@echo ""
	@echo "✅ Redis started on port 6379"

docker-redis-stop:
	docker-compose stop redis

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
	@echo "  make quickstart    Install + start all services + setup DB"
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
	@echo "  make test-whatsapp-bridge Run WhatsApp Bridge vitest tests"
	@echo "  make test-all           Run all tests (backend + frontend + e2e + whatsapp)"
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
	@echo "Celery:"
	@echo "  make celery-worker  Start Celery worker"
	@echo "  make celery-beat    Start Celery beat scheduler"
	@echo "  make celery-flower  Start Flower monitoring UI"
	@echo ""
	@echo "Docker (Development):"
	@echo "  make docker-up            Start backend services"
	@echo "  make docker-down          Stop all services"
	@echo "  make docker-logs          View backend logs"
	@echo "  make docker-build         Build backend images"
	@echo "  make docker-db            Start only PostgreSQL"
	@echo "  make docker-redis         Start only Redis"
	@echo ""
	@echo "Docker (Production with Traefik):"
	@echo "  make docker-prod          Start production stack"
	@echo "  make docker-prod-down     Stop production stack"
	@echo "  make docker-prod-logs     View production logs"
	@echo ""
	@echo "Other:"
	@echo "  make routes        Show all API routes"
	@echo "  make clean         Clean cache files"
	@echo ""
