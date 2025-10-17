"""Pytest configuration for integration tests.

This module provides fixtures and configuration for integration tests
that use real services (Qdrant, embedding models).

Author: IntelliRAG Team
Date: 2025-10-17
"""

import pytest
import asyncio
import requests
import time


def qdrant_available():
    """Check if Qdrant is running."""
    try:
        response = requests.get("http://localhost:6333/", timeout=2)
        return response.status_code == 200
    except:
        return False


@pytest.fixture(scope="session", autouse=True)
def check_qdrant():
    """Verify Qdrant is available before running integration tests."""
    if not qdrant_available():
        pytest.skip(
            "Qdrant not running. Start with: docker run -d --name qdrant-test -p 6333:6333 qdrant/qdrant:latest"
        )


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
