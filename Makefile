# ==============================================================================
# InsurTech AI Assistant - Test Environment Automation
# ==============================================================================

SHELL := /usr/bin/env bash
PYTHON ?= .venv/bin/python3
PYTEST ?= .venv/bin/pytest
COMPOSE_FILE := docker-compose.test.yml
USER ?= customerA
VARIANT ?= valid
TARGET_HOST ?= http://127.0.0.1:5000

.PHONY: help up down reset seed test test-security smoke token logs clean

help: ## Show available commands
	@echo "InsurTech AI Assistant Test Suite"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-16s\033[0m %s\n", $$1, $$2}'

up: ## Spin up isolated test environment containers (Postgres, Redis, Fake Claims, AI)
	docker compose -f $(COMPOSE_FILE) up -d --build

down: ## Stop and remove test containers
	docker compose -f $(COMPOSE_FILE) down

reset: ## Reset test environment volumes and re-seed database
	docker compose -f $(COMPOSE_FILE) down -v
	docker compose -f $(COMPOSE_FILE) up -d
	@echo "Waiting for services to become healthy..."
	@sleep 4
	$(MAKE) seed

seed: ## Seed Ethiopian policy PDF, Golden QA pairs, and regulatory registry
	APP_ENV=test $(PYTHON) scripts/seed_test_data.py

test: ## Run unit and integration tests (excluding security and live markers)
	APP_ENV=test $(PYTEST) -m "not security and not live" -v

test-security: ## Run security tests (targeting AUDIT_REPORT.md findings, xfails noted)
	APP_ENV=test $(PYTEST) -m "security" -v

smoke: ## Execute end-to-end automated smoke test script
	./scripts/smoke_test.sh $(TARGET_HOST)

token: ## Mint a signed JWT token (make token USER=customerA [VARIANT=valid|expired|wrong_signature|alg_none])
	@APP_ENV=test $(PYTHON) scripts/dev_token_issuer.py $(USER) $(VARIANT)

logs: ## Tail logs from the AI microservice test container
	docker compose -f $(COMPOSE_FILE) logs -f ai-service-test

clean: ## Clean pytest caches and temporary test files
	rm -rf .pytest_cache tests/__pycache__ app/**/__pycache__
