# Code Style and Conventions

## General Principles
- Test-Driven Development (TDD) is MANDATORY
- Write failing test first, then implement minimal code to pass, refactor without breaking tests
- Target >80% test coverage (enforced in CI/CD)
- Clean, readable, maintainable code with proper error handling

## Python Conventions
- **Python Version**: 3.12
- **Package Manager**: uv
- **Naming**:
  - Classes: PascalCase (e.g., `OrchestratorService`)
  - Functions/Variables: snake_case (e.g., `process_document`)
  - Constants: UPPERCASE_WITH_UNDERSCORES (e.g., `MAX_FILE_SIZE`)
- **Type Hints**: Required for all functions and methods
- **Imports**: Organized with isort (stdlib → third-party → local)
- **Docstrings**: Required for all classes and public functions
- **Error Handling**: Use specific exception types, not bare except

## Async Patterns
- Use `async def` for all I/O operations
- FastAPI dependency injection with `Depends()`
- Async clients for external services (httpx, aiohttp, gcloud-aio)

## Testing
- Test files: `test_<component>.py` in tests/unit/
- Use pytest fixtures for reusable test data
- Mock external dependencies in unit tests
- Integration tests in tests/integration/ for end-to-end flows
- Test edge cases and error conditions

## File Structure
- app/ - Main application code
- tests/ - All test files
- docs/ - Documentation
- kubernetes/ - K8s manifests and Helm charts
- terraform/ - Infrastructure as Code