.PHONY: help install-be install-fe up down logs ps migrate seed pull-models \
        fmt lint test test-be test-fe shell-api shell-worker clean

help:
	@echo "CortexFlow — common commands"
	@echo "  make up              build & start full stack"
	@echo "  make down            stop stack"
	@echo "  make logs            tail logs (all services)"
	@echo "  make migrate         apply DB migrations + init vector collection"
	@echo "  make seed            seed admin user + demo workspace"
	@echo "  make pull-models     ollama pull qwen2.5:3b + nomic-embed-text"
	@echo "  make test            run backend + frontend tests"
	@echo "  make lint            ruff + mypy + eslint"
	@echo "  make clean           remove containers + volumes"

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f --tail=100

ps:
	docker compose ps

migrate:
	docker compose exec api alembic upgrade head
	docker compose exec api python -m app.scripts.init_vector_store

seed:
	docker compose exec api python -m app.scripts.seed

pull-models:
	ollama pull qwen2.5:3b || docker compose exec ollama ollama pull qwen2.5:3b
	ollama pull nomic-embed-text || docker compose exec ollama ollama pull nomic-embed-text

install-be:
	python -m venv .venv && . .venv/bin/activate && pip install -U pip && pip install -r requirements.txt
	pip install -r requirements-dev.txt

install-fe:
	cd frontend && pnpm install

lint:
	ruff check . && mypy app || true
	cd frontend && pnpm lint || true

test: test-be test-fe

test-be:
	pytest -q

test-fe:
	cd frontend && pnpm test --run || true

shell-api:
	docker compose exec api bash

shell-worker:
	docker compose exec worker bash

clean:
	docker compose down -v
