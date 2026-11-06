.PHONY: help install check test lint run up down

help: ## List available commands
	@awk 'BEGIN {FS = ":.*## "; print "Usage: make <target>\n"} /^[a-zA-Z_-]+:.*## / {printf "  %-10s %s\n", $$1, $$2}' $(MAKEFILE_LIST)
install: ## Install development dependencies
	python -m pip install -e '.[dev]'
check: lint test ## Run all checks
test: ## Run tests
	python -m pytest -q
lint: ## Run Ruff
	python -m ruff check .
run: ## Run the API
	uvicorn traced.api:app --reload --port 8080
up: ## Start the container
	docker compose up --build --detach
down: ## Stop the container
	docker compose down

