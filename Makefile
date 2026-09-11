.PHONY: help init up down logs restart clean test test-unit test-integration

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
	@echo "  test-unit     Run unit tests (no infrastructure needed)"
	@echo "  test-int      Run integration tests (requires live DB)"
	@echo "  test          Run all tests"

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
	pytest -m "not integration" -v

test-int:
	pytest -m integration -v

test:
	pytest -v
