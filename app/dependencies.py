"""Dependency injection for FastAPI endpoints.
"""

from fastapi import HTTPException
from app.services.query_logger import QueryLoggerService

_query_logger = None


def get_orchestrator():
    """Get OrchestratorService instance for dependency injection."""
    # Lazy import to avoid circular dependency
    from app import main as main_module
    
    if main_module.orchestrator is None:
        raise HTTPException(status_code=503)
    return main_module.orchestrator


async def get_query_logger() -> QueryLoggerService:
    """Get QueryLoggerService instance for dependency injection."""
    global _query_logger
    
    if _query_logger is None:
        orchestrator = get_orchestrator()
        _query_logger = QueryLoggerService(
            vectordb_service=orchestrator.vectordb_service
        )
        await _query_logger.initialize_collection()
    
    return _query_logger
