.PHONY: help init up down logs restart clean test test-unit test-int test-db-up test-db-down

help:
	@echo "Usage: make <target>"
	@echo ""
	@echo "  init          First-time setup: init DB schema + Kafka topics"
	@echo "  up            Start all backend services (no frontend)"
	@echo "  up-full       Start all services including frontend"
	@echo "  down          Stop and remove containers"
	@echo "  logs          Tail logs from all backend services"
	@echo "  restart       down + up"
	@echo "  clean         down + remove volumes (destructive!)"
	@echo ""
	@echo "  train         Run training job (profile=task)"
	@echo "  infer         Run inference job (profile=task)"
	@echo ""
	@echo "  test-unit     Run backend unit tests (no DB, Kafka, network or .env)"
	@echo "  test-int      Start the disposable test DB and run integration tests"
	@echo "  test          Start the disposable test DB and run the whole backend suite"
	@echo "  test-db-up    Start the disposable test DB on port 55432"
	@echo "  test-db-down  Remove the disposable test DB"

# ---------------------------------------------------------------------------
# Infrastructure
# ---------------------------------------------------------------------------

init:
	docker compose --profile init up db-init

up:
	docker compose up timescaledb zookeeper kafka mlflow backend consumer adminer

up-full:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f timescaledb kafka backend consumer mlflow

restart: down up

clean:
	docker compose down -v

# ---------------------------------------------------------------------------
# ML tasks
# ---------------------------------------------------------------------------

train:
	docker compose --profile task up training

infer:
	docker compose --profile task up inference

# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

test-unit:
	pytest -m "not integration"

test-db-up:
	docker compose -f docker-compose.test.yaml up -d --wait

test-db-down:
	docker compose -f docker-compose.test.yaml down -v

test-int: test-db-up
	pytest -m integration

test: test-db-up
	pytest
