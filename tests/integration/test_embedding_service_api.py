"""Integration tests for Embedding Service API.

This module tests the standalone embedding service endpoints:
- POST /vectorize - Generate embeddings
- GET /model-info - Get model metadata
- GET /health - Health check

These tests assume the embedding service is running on localhost:8001.

Following TDD: These tests are written FIRST and should FAIL until service is implemented.

Date: 2025-11-04
"""

import pytest
import httpx
import time
from typing import List


# Test configuration
EMBEDDING_SERVICE_URL = "http://localhost:8001"
TIMEOUT = 30.0


@pytest.mark.integration
def test_embedding_service_health_endpoint():
    """Test that health endpoint returns service status.

    Expected behavior:
    - Returns 200 status code
    - Returns JSON with status, model_loaded, model_name, device, embedding_dimension
    - Model should be loaded (model_loaded=True)
    """
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(f"{EMBEDDING_SERVICE_URL}/health")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "status" in data
        assert "model_loaded" in data
        assert "model_name" in data
        assert "device" in data
        assert "embedding_dimension" in data

        # Validate model is loaded
        assert data["model_loaded"] is True
        assert data["status"] == "healthy"
        assert data["embedding_dimension"] > 0


@pytest.mark.integration
def test_embedding_service_model_info_endpoint():
    """Test that model-info endpoint returns model metadata.

    Expected behavior:
    - Returns 200 status code
    - Returns model name, dimension, device, max_batch_size
    - Dimension should match the loaded model
    """
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(f"{EMBEDDING_SERVICE_URL}/model-info")

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "model_name" in data
        assert "embedding_dimension" in data
        assert "device" in data
        assert "max_batch_size" in data
        assert "model_loaded" in data

        # Validate values
        assert data["model_loaded"] is True
        assert data["embedding_dimension"] > 0
        assert data["max_batch_size"] > 0
        assert isinstance(data["model_name"], str)
        assert len(data["model_name"]) > 0


@pytest.mark.integration
def test_embedding_service_vectorize_single_text():
    """Test vectorize endpoint with single text.

    Expected behavior:
    - Returns 200 status code
    - Returns embedding with correct dimension
    - Embedding is list of floats
    """
    test_text = "Hello world"

    with httpx.Client(timeout=TIMEOUT) as client:
        # First get model info to know expected dimension
        model_info = client.get(f"{EMBEDDING_SERVICE_URL}/model-info").json()
        expected_dim = model_info["embedding_dimension"]

        # Generate embedding
        response = client.post(
            f"{EMBEDDING_SERVICE_URL}/vectorize",
            json={"texts": [test_text], "normalize": False}
        )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "embeddings" in data
        assert "model" in data
        assert "dimension" in data
        assert "count" in data
        assert "processing_time_seconds" in data

        # Validate embeddings
        assert len(data["embeddings"]) == 1
        assert len(data["embeddings"][0]) == expected_dim
        assert data["dimension"] == expected_dim
        assert data["count"] == 1

        # Validate embedding values are floats
        assert all(isinstance(x, (int, float)) for x in data["embeddings"][0])


@pytest.mark.integration
def test_embedding_service_vectorize_batch():
    """Test vectorize endpoint with multiple texts.

    Expected behavior:
    - Returns embeddings for all input texts
    - All embeddings have same dimension
    - Processing time is recorded
    """
    test_texts = [
        "Machine learning is fascinating",
        "Natural language processing",
        "Vector embeddings are useful",
        "Semantic search applications"
    ]

    with httpx.Client(timeout=TIMEOUT) as client:
        # Get expected dimension
        model_info = client.get(f"{EMBEDDING_SERVICE_URL}/model-info").json()
        expected_dim = model_info["embedding_dimension"]

        # Generate batch embeddings
        start_time = time.time()
        response = client.post(
            f"{EMBEDDING_SERVICE_URL}/vectorize",
            json={"texts": test_texts, "normalize": False}
        )
        duration = time.time() - start_time

        assert response.status_code == 200
        data = response.json()

        # Validate batch processing
        assert len(data["embeddings"]) == len(test_texts)
        assert data["count"] == len(test_texts)

        # Validate all embeddings have correct dimension
        for embedding in data["embeddings"]:
            assert len(embedding) == expected_dim
            assert all(isinstance(x, (int, float)) for x in embedding)

        # Validate performance metrics
        assert data["processing_time_seconds"] > 0
        assert data["processing_time_seconds"] < 10.0  # Should be fast


@pytest.mark.integration
def test_embedding_service_vectorize_with_normalization():
    """Test vectorize endpoint with L2 normalization.

    Expected behavior:
    - Returns normalized embeddings
    - Each embedding has L2 norm ≈ 1.0
    """
    import math

    test_text = "Test normalization"

    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(
            f"{EMBEDDING_SERVICE_URL}/vectorize",
            json={"texts": [test_text], "normalize": True}
        )

        assert response.status_code == 200
        data = response.json()

        # Calculate L2 norm of the embedding
        embedding = data["embeddings"][0]
        l2_norm = math.sqrt(sum(x * x for x in embedding))

        # Should be approximately 1.0 (allow small floating point errors)
        assert abs(l2_norm - 1.0) < 0.01


@pytest.mark.integration
def test_embedding_service_vectorize_empty_input():
    """Test vectorize endpoint with empty input.

    Expected behavior:
    - Returns 422 validation error (Pydantic validation)
    - Error indicates texts cannot be empty
    """
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(
            f"{EMBEDDING_SERVICE_URL}/vectorize",
            json={"texts": [], "normalize": False}
        )

        # Should return validation error
        assert response.status_code == 422


@pytest.mark.integration
def test_embedding_service_vectorize_invalid_input():
    """Test vectorize endpoint with invalid input type.

    Expected behavior:
    - Returns 422 validation error
    """
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.post(
            f"{EMBEDDING_SERVICE_URL}/vectorize",
            json={"texts": "not a list", "normalize": False}
        )

        # Should return validation error
        assert response.status_code == 422


@pytest.mark.integration
def test_embedding_service_dimension_consistency():
    """Test that dimension is consistent across endpoints.

    Expected behavior:
    - /health dimension matches /model-info dimension
    - /vectorize returns embeddings with that dimension
    """
    with httpx.Client(timeout=TIMEOUT) as client:
        # Get dimension from health endpoint
        health_data = client.get(f"{EMBEDDING_SERVICE_URL}/health").json()
        health_dim = health_data["embedding_dimension"]

        # Get dimension from model-info endpoint
        model_info = client.get(f"{EMBEDDING_SERVICE_URL}/model-info").json()
        model_dim = model_info["embedding_dimension"]

        # Generate an embedding
        vectorize_data = client.post(
            f"{EMBEDDING_SERVICE_URL}/vectorize",
            json={"texts": ["test"], "normalize": False}
        ).json()
        actual_dim = len(vectorize_data["embeddings"][0])

        # All dimensions should match
        assert health_dim == model_dim
        assert model_dim == actual_dim
        assert vectorize_data["dimension"] == actual_dim


@pytest.mark.integration
def test_embedding_service_performance_batch():
    """Test batch processing performance.

    Expected behavior:
    - Batch processing is faster than sequential
    - Service can handle reasonable batch sizes
    """
    batch_size = 10
    test_texts = [f"Test sentence number {i}" for i in range(batch_size)]

    with httpx.Client(timeout=TIMEOUT) as client:
        # Batch processing
        start_batch = time.time()
        response = client.post(
            f"{EMBEDDING_SERVICE_URL}/vectorize",
            json={"texts": test_texts, "normalize": False}
        )
        batch_duration = time.time() - start_batch

        assert response.status_code == 200
        data = response.json()
        assert len(data["embeddings"]) == batch_size

        # Batch should complete in reasonable time
        assert batch_duration < 5.0  # 5 seconds for 10 texts on CPU


@pytest.mark.integration
def test_embedding_service_root_endpoint():
    """Test root endpoint returns service information.

    Expected behavior:
    - Returns 200 status code
    - Returns service metadata and available endpoints
    """
    with httpx.Client(timeout=TIMEOUT) as client:
        response = client.get(f"{EMBEDDING_SERVICE_URL}/")

        assert response.status_code == 200
        data = response.json()

        # Should contain service info
        assert "service" in data
        assert "model" in data
        assert "dimension" in data
        assert "status" in data
        assert "endpoints" in data
