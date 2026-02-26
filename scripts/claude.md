# CLAUDE.md — TradingIA

## Stack
Python 3.12 · asyncio · Pydantic v2 · SQLAlchemy async · CCXT · Loguru

## Skills disponibles (en .claude/skills/)
- @quant-analyst          → lógica de scoring, métricas financieras
- @async-python-patterns  → cliente Nansen, concurrencia
- @error-handling-patterns → circuit breakers, retries
- @pydantic-models-py     → modelos en app/models/
- @architecture-patterns  → estructura de capas en app/
- @risk-metrics-calculation → app/services/risk_manager.py

## Arquitectura actual
app/models/      → Pydantic (contratos) + SQLAlchemy (DB)
app/services/    → Lógica de negocio (signal_engine, risk_manager...)
app/infraestructure/ → Adaptadores externos (exchange, database)
app/core/        → Config y utils transversales

## Convenciones
- Async everywhere: todos los servicios son async/await
- Tipado estricto: mypy con disallow_untyped_defs = true
- Logging: loguru (no print, no logging stdlib)