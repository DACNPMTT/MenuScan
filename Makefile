ENV ?= local
ENV_FILE := env/.env.$(ENV)
ENV_EXAMPLE := env/.env.$(ENV).example
COMPOSE := docker compose --env-file $(ENV_FILE)
LOAD_ENV := set -a; . $(ENV_FILE); set +a;

-include $(ENV_FILE)
export

.DEFAULT_GOAL := help

.PHONY: help env deps deps-down deps-reset deps-logs deps-ps backend frontend migrate test-be lint-be lint-fe lint install-be install-fe

help:
	@echo "MenuScan development commands"
	@echo ""
	@echo "  make env ENV=local        Create env/.env.local from the example if missing"
	@echo "  make deps ENV=local       Start local dependency containers"
	@echo "  make backend ENV=local    Run migrations and start FastAPI locally"
	@echo "  make frontend ENV=local   Start Vite locally"
	@echo "  make migrate ENV=local    Apply backend migrations"
	@echo "  make test-be ENV=local    Run backend tests"
	@echo "  make lint                 Run backend and frontend lint"
	@echo "  make deps-down            Stop dependency containers"
	@echo "  make deps-reset           Recreate dependencies and remove volumes"

env:
	@if [ -f "$(ENV_FILE)" ]; then \
		echo "$(ENV_FILE) already exists"; \
	elif [ -f "$(ENV_EXAMPLE)" ]; then \
		cp "$(ENV_EXAMPLE)" "$(ENV_FILE)"; \
		echo "Created $(ENV_FILE)"; \
	else \
		echo "Missing $(ENV_EXAMPLE)"; \
		exit 1; \
	fi

deps: env
	$(COMPOSE) up -d db redis

deps-down: env
	$(COMPOSE) down

deps-reset: env
	$(COMPOSE) down -v
	$(COMPOSE) up -d db redis

deps-logs: env
	$(COMPOSE) logs -f db redis

deps-ps: env
	$(COMPOSE) ps

install-be:
	cd app && uv sync --locked --all-groups

install-fe:
	cd frontend && npm ci

migrate: env
	$(LOAD_ENV) cd app && uv run alembic upgrade head

backend: env migrate
	$(LOAD_ENV) cd app && uv run uvicorn main:app --reload --host 0.0.0.0 --port $${BACKEND_PORT:-8000}

frontend: env
	$(LOAD_ENV) cd frontend && npm run dev -- --host 0.0.0.0 --port $${FRONTEND_PORT:-5173}

test-be: env
	$(LOAD_ENV) cd app && uv run pytest --tb=short

lint-be:
	cd app && uv run ruff check .

lint-fe:
	cd frontend && npm run lint

lint: lint-be lint-fe
