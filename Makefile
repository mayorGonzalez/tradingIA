.PHONY: help build up down logs shell test clean restart pull-model

help:
	@echo "╔════════════════════════════════════════════╗"
	@echo "║         TradingIA Docker Commands          ║"
	@echo "╚════════════════════════════════════════════╝"
	@echo ""
	@echo "make up               - Levantar todos los servicios"
	@echo "make down             - Parar todos los servicios"
	@echo "make build            - Construir imagen Docker"
	@echo "make rebuild          - Reconstruir imagen (sin cache)"
	@echo "make logs             - Ver logs de todos los servicios"
	@echo "make logs-app         - Ver logs solo de la app"
	@echo "make logs-ollama      - Ver logs solo de Ollama"
	@echo "make shell            - Shell interactivo en trading_app"
	@echo "make shell-db         - Conectar a PostgreSQL"
	@echo "make test             - Ejecutar tests"
	@echo "make clean            - Limpiar contenedores y volumes"
	@echo "make restart          - Reiniciar servicios"
	@echo "make pull-model       - Descargar modelo Ollama"
	@echo "make health           - Ver estado de los servicios"
	@echo ""

# Docker compose
build:
	docker-compose build

rebuild:
	docker-compose build --no-cache

up:
	docker-compose up -d
	@echo "✓ Servicios levantados. Dashboard: http://localhost:8501"

down:
	docker-compose down

restart:
	docker-compose restart

# Logs
logs:
	docker-compose logs -f

logs-app:
	docker-compose logs -f trading_app

logs-ollama:
	docker-compose logs -f ollama

logs-db:
	docker-compose logs -f postgres

# Shell access
shell:
	docker-compose exec trading_app bash

shell-db:
	docker-compose exec postgres psql -U trading_user -d tradingía_db

# Health check
health:
	@echo "=== POSTGRES ==="
	docker-compose exec postgres pg_isready -U trading_user || echo "❌ Down"
	@echo ""
	@echo "=== OLLAMA ==="
	curl -s http://localhost:11434/api/tags | jq '.models[].name' || echo "❌ Down"
	@echo ""
	@echo "=== DASHBOARD ==="
	curl -s http://localhost:8501 > /dev/null && echo "✓ Up at http://localhost:8501" || echo "❌ Down"

# Modelo
pull-model:
	docker-compose exec ollama ollama pull qwen2.5-coder:3b

pull-model-mistral:
	docker-compose exec ollama ollama pull mistral

list-models:
	docker-compose exec ollama ollama list

# Testing
test:
	docker-compose exec trading_app python -m pytest tests/ -v

test-cov:
	docker-compose exec trading_app python -m pytest tests/ --cov=app

# Cleaning
clean:
	docker-compose down -v
	@echo "✓ Contenedores y volúmenes eliminados"

clean-logs:
	docker-compose exec trading_app rm -f logs/*.log dashboard_debug.log

# Development
dev-up:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml up -d

dev-down:
	docker-compose -f docker-compose.yml -f docker-compose.override.yml down

# Database
db-init:
	docker-compose exec postgres psql -U trading_user -d tradingía_db -f /docker-entrypoint-initdb.d/init.sql

db-shell:
	docker-compose exec postgres psql -U trading_user -d tradingía_db

# Monitoreo
ps:
	docker-compose ps

stats:
	docker stats --no-stream

# Environment
show-env:
	@cat .env.docker

set-env:
	@cp .env.docker .env
	@echo "✓ Variables copiadas a .env (edítalo antes de 'make up')"