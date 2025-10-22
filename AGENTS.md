# AGENTS.md - IntelliRAG Development Guide

## Build/Test Commands
- **Run all tests**: `pytest`
- **Run single test**: `pytest tests/unit/test_database.py::TestDatabaseService::test_database_service_connect -v`
- **Run with coverage**: `pytest --cov=app --cov-report=term-missing`
- **Run specific markers**: `pytest -m unit` or `pytest -m integration`
- **Install dependencies**: `uv sync` (using uv package manager)
- **Start services**: `docker-compose up -d` (PostgreSQL, Qdrant, MinIO)
- **Run FastAPI**: `uvicorn app.main:app --reload`

## Architecture & Structure
- **PostgreSQL**: Primary database (asyncpg connection pool, min_size=10, max_size=20)
- **Qdrant**: Vector database at localhost:6333 (collections, embeddings)
- **MinIO/S3**: Object storage for raw documents (bucket: raw-documents)
- **Key Services**: DatabaseService (app/services/database.py), EmbeddingService, VectorDB, RAG Pipeline
- **API**: FastAPI with async endpoints, Pydantic validation, dependency injection
- **Tech Stack**: Python 3.12, FastAPI, asyncpg, LangChain/LangGraph, Sentence Transformers, vLLM

## Code Style & Conventions
- **TDD MANDATORY**: Write failing test first → implement → refactor (>80% coverage enforced)
- **Imports**: Standard library → Third-party → Local (use isort)
- **Naming**: PascalCase (classes), snake_case (functions/vars), UPPERCASE (constants)
- **Type hints**: Required for all functions/methods (use `str | None`, not `Optional[str]`)
- **Error handling**: Use specific exceptions (asyncpg.UniqueViolationError, etc.), log with context
- **Async**: Use `async def` for I/O operations, AsyncMock for tests
- **Logging**: `logging` module with levels (INFO, ERROR, WARNING)
- **Commits**: `<type>(<scope>): <description>` format, NO AI attributions, NO secrets in git

## Critical Rules (from CLAUDE.md & .cursor/rules)
- NEVER skip tests or commit failing tests
- NEVER commit .env files or credentials
- ALWAYS run tests before committing (`pytest --cov`)
- ALWAYS use connection pools with proper sizing (environment-aware)
- ALWAYS handle database exceptions (UniqueViolation, ForeignKeyViolation, TimeoutError)
- Transaction isolation: Use `pool.acquire()` then `connection.transaction()` for SERIALIZABLE
- Prioritize functionality and readability over strict linting
