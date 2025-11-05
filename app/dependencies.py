"""Dependency injection for FastAPI endpoints.

Date: 2025-11-05
"""

from fastapi import HTTPException


def get_orchestrator():
    """Get OrchestratorService instance for dependency injection."""
    # Lazy import to avoid circular dependency
    from app import main as main_module
    
    if main_module.orchestrator is None:
        raise HTTPException(status_code=503)
    return main_module.orchestrator
