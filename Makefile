.PHONY: dev dev-down dev-logs test-memory test-transform test lint deploy-memory deploy-transform deploy help

dev:
	docker-compose up --build

dev-down:
	docker-compose down -v

dev-logs:
	docker-compose logs -f

test-memory:
	cd memory-store && pip install -e '.[dev]' -q && pytest tests/ -v

test-transform:
	cd transform-agent && pip install -e '.[dev]' -q && pytest tests/ -v

test: test-memory test-transform

lint:
	ruff check memory-store/src transform-agent/src shared

deploy-memory:
	cd memory-store && fly deploy

deploy-transform:
	cd transform-agent && fly deploy

deploy: deploy-memory deploy-transform

help:
	@echo "Available targets:"
	@echo "  dev            - Start all services with docker-compose"
	@echo "  dev-down       - Stop and remove containers + volumes"
	@echo "  dev-logs       - Tail logs from all services"
	@echo "  test-memory    - Run memory-store tests"
	@echo "  test-transform - Run transform-agent tests"
	@echo "  test           - Run all tests"
	@echo "  lint           - Run ruff linter on all services"
	@echo "  deploy-memory  - Deploy memory-store to Fly.io"
	@echo "  deploy-transform - Deploy transform-agent to Fly.io"
	@echo "  deploy         - Deploy all services to Fly.io"
