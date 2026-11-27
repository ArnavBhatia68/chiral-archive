# Common tasks. Run `make` to list them.
.DEFAULT_GOAL := help
BACKEND := cd backend &&

.PHONY: help up down migrate collect build-data lint format test

help: ## List the available commands
	@grep -E '^[a-z-]+:.*## ' $(MAKEFILE_LIST) | awk -F':.*## ' '{printf "  %-9s %s\n", $$1, $$2}'

up: ## Start Postgres (with pgvector) and Redis, and wait until they're healthy
	docker compose up -d --wait

down: ## Stop the containers (the data stays in a Docker volume)
	docker compose down

migrate: ## Apply database migrations
	$(BACKEND) uv run python -m chiral.db.migrate

collect: ## Download lore pages from the wiki into data/raw (resumable, ~1 request/s)
	$(BACKEND) uv run python -m chiral.ingest.collect

build-data: ## Turn data/raw into clean records and tables in data/processed
	$(BACKEND) uv run python -m chiral.ingest.build

lint: ## Check code style
	$(BACKEND) uv run ruff check . && uv run ruff format --check .

format: ## Fix code style
	$(BACKEND) uv run ruff check --fix . && uv run ruff format .

test: ## Run the tests (integration tests skip if Postgres isn't running)
	$(BACKEND) uv run pytest
