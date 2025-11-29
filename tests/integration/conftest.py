"""Pytest configuration for integration tests.

This module provides fixtures and configuration for integration tests
that use real services (Qdrant, embedding models).



"""

import pytest
import pytest_asyncio
import asyncio
import requests
import os
from dotenv import load_dotenv

# Load test environment variables at conftest level (before app initialization)
load_dotenv(".env.test")


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
    import logging
    from app import main

    logger = logging.getLogger(__name__)

    # Verify environment variables are loaded
    gcs_project = os.getenv("GCP_PROJECT_ID")
    gcs_bucket = os.getenv("GCS_BUCKET_NAME")
    gcs_creds = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    logger.info(f"Test environment - GCP_PROJECT_ID: {gcs_project}")
    logger.info(f"Test environment - GCS_BUCKET_NAME: {gcs_bucket}")
    logger.info(
        f"Test environment - GOOGLE_APPLICATION_CREDENTIALS: {gcs_creds}")

    # Manually trigger lifespan startup
    async with main.lifespan(main.app):
        # Verify orchestrator is initialized
        assert main.orchestrator is not None, "Orchestrator not initialized"
        assert main.orchestrator.gcs_loader is not None, "GCS loader not initialized"
        logger.info("Orchestrator initialized successfully")
        yield main.app
