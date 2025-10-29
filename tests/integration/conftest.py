"""Pytest configuration for integration tests.

This module provides fixtures and configuration for integration tests
that use real services (Qdrant, embedding models).


Date: 2025-10-17
"""

import pytest
import pytest_asyncio
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


def vllm_available():
    """Check if vLLM is running with OpenAI-compatible API."""
    try:
        response = requests.get("http://localhost:8000/v1/models", timeout=2)
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


def vllm_available():
    """Check if vLLM is running with OpenAI-compatible API."""
    try:
        response = requests.get("http://localhost:8000/v1/models", timeout=2)
        return response.status_code == 200
    except:
        return False


@pytest.fixture(scope="session")
def check_vllm():
    """Verify vLLM is available before running RAG integration tests."""
    if not vllm_available():
        pytest.skip(
            "vLLM not running. Start with: docker run -d --gpus all -p 8000:8000 vllm/vllm-openai --model Qwen/Qwen3-0.6B"
        )


@pytest_asyncio.fixture(scope="function")
async def initialized_app():
    """Fixture that provides FastAPI app with initialized orchestrator.
    
    This fixture properly initializes the app using the lifespan context manager
    to ensure the orchestrator is available for tests.
    """
    from app import main
    
    # Manually trigger lifespan startup
    async with main.lifespan(main.app):
        yield main.app
