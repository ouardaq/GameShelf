.DEFAULT_GOAL := help

BACKEND := backend
VENV    := $(BACKEND)/venv
BIN     := $(VENV)/bin

.PHONY: help
help: ## List available targets
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

## --- setup ---

.PHONY: install
install: ## Create the backend venv, install all dependencies, install frontend packages
	python3 -m venv $(VENV)
	$(BIN)/pip install --upgrade pip
	$(BIN)/pip install -r $(BACKEND)/requirements-dev.txt
	cd frontend && npm ci
	@test -f $(BACKEND)/.env || (cp $(BACKEND)/.env.example $(BACKEND)/.env \
		&& echo "\nCreated backend/.env from the example -- fill in DATABASE_URL, SECRET_KEY and RAWG_API_KEY.")

.PHONY: hooks
hooks: ## Install the pre-commit hooks (ruff lint + format on staged files)
	$(BIN)/pre-commit install

.PHONY: up
up: ## Start Postgres and Redis
	docker compose up -d

.PHONY: down
down: ## Stop Postgres and Redis, keeping their data
	docker compose down

## --- run ---

.PHONY: dev
dev: ## Run the API with reload on :8000
	cd $(BACKEND) && venv/bin/uvicorn app.main:app --reload

.PHONY: dev-web
dev-web: ## Run the Next.js dev server on :3000
	cd frontend && npm run dev

## --- database ---

.PHONY: migrate
migrate: ## Apply all pending migrations
	cd $(BACKEND) && venv/bin/alembic upgrade head

.PHONY: migration
migration: ## Generate a migration from model changes: make migration m="add x to y"
	@test -n "$(m)" || (echo 'Usage: make migration m="what changed"'; exit 1)
	cd $(BACKEND) && venv/bin/alembic revision --autogenerate -m "$(m)"

.PHONY: rollback
rollback: ## Undo the most recent migration
	cd $(BACKEND) && venv/bin/alembic downgrade -1

## --- quality ---

.PHONY: test
test: ## Run the backend test suite
	cd $(BACKEND) && venv/bin/pytest

.PHONY: cov
cov: ## Run the tests with a coverage report
	cd $(BACKEND) && venv/bin/pytest --cov --cov-report=term-missing

.PHONY: lint
lint: ## Report lint and formatting problems without changing anything
	cd $(BACKEND) && venv/bin/ruff check . && venv/bin/ruff format --check .
	cd frontend && npm run lint

.PHONY: fmt
fmt: ## Fix what can be fixed automatically
	cd $(BACKEND) && venv/bin/ruff check --fix . && venv/bin/ruff format .

.PHONY: check
check: lint test ## Everything CI runs, before you push
	cd $(BACKEND) && venv/bin/alembic check
