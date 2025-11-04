"""Unit tests for EmbeddingService remote mode.

This module tests the remote embedding service client functionality:
- Remote mode configuration
- Model info fetching and caching
- Remote embedding generation
- Dimension discovery
- Error handling

Following TDD: These tests are written FIRST and should FAIL until implementation.

Date: 2025-11-04
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import httpx


@pytest.mark.unit
def test_embedding_service_remote_mode_initialization():
    """Test EmbeddingService can be initialized in remote mode.

    Expected behavior:
    - use_remote=True sets remote mode
    - remote_url is configurable
    - Does not load local model
    """
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    assert service.use_remote is True
    assert service.remote_url == "http://localhost:8001"
    # Should not have loaded local model
    assert service._model is None


@pytest.mark.unit
def test_embedding_service_local_mode_still_works():
    """Test backward compatibility - local mode still functions.

    Expected behavior:
    - use_remote=False uses local model
    - All existing local behavior preserved
    """
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(
        use_remote=False,
        device="cpu"
    )

    assert service.use_remote is False
    assert service.device == "cpu"
    assert service.model_id == "BAAI/bge-m3"


@pytest.mark.unit
@patch('httpx.Client')
def test_embedding_service_fetch_model_info(mock_client_class):
    """Test fetching model info from remote service.

    Expected behavior:
    - Calls GET /model-info endpoint
    - Caches the response
    - Returns model metadata
    """
    from app.services.embedding import EmbeddingService

    # Mock response
    mock_response = Mock()
    mock_response.json.return_value = {
        "model_name": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "device": "cpu",
        "max_batch_size": 128,
        "model_loaded": True
    }
    mock_response.raise_for_status = Mock()

    # Mock client
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    # Initialize service
    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    # Fetch model info
    model_info = service._fetch_model_info()

    # Verify
    assert model_info["model_name"] == "BAAI/bge-m3"
    assert model_info["embedding_dimension"] == 1024
    mock_client.get.assert_called_once_with("http://localhost:8001/model-info")


@pytest.mark.unit
@patch('httpx.Client')
def test_embedding_service_model_info_caching(mock_client_class):
    """Test that model info is cached after first fetch.

    Expected behavior:
    - First call fetches from remote
    - Subsequent calls use cache
    - HTTP request only made once
    """
    from app.services.embedding import EmbeddingService

    # Mock response
    mock_response = Mock()
    mock_response.json.return_value = {
        "model_name": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "device": "cpu",
        "max_batch_size": 128,
        "model_loaded": True
    }
    mock_response.raise_for_status = Mock()

    # Mock client
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    # Initialize service
    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    # Fetch model info twice
    info1 = service._fetch_model_info()
    info2 = service._fetch_model_info()

    # Should be the same cached object
    assert info1 is info2
    # HTTP request should only be made once
    assert mock_client.get.call_count == 1


@pytest.mark.unit
@patch('httpx.Client')
def test_embedding_service_get_embedding_dimension_remote(mock_client_class):
    """Test get_embedding_dimension in remote mode.

    Expected behavior:
    - Fetches dimension from /model-info
    - Returns correct dimension
    """
    from app.services.embedding import EmbeddingService

    # Mock response
    mock_response = Mock()
    mock_response.json.return_value = {
        "model_name": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "device": "cpu",
        "max_batch_size": 128,
        "model_loaded": True
    }
    mock_response.raise_for_status = Mock()

    # Mock client
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    # Initialize service
    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    # Get dimension
    dimension = service.get_embedding_dimension()

    # Verify
    assert dimension == 1024


@pytest.mark.unit
@patch('httpx.Client')
def test_embedding_service_get_model_name_remote(mock_client_class):
    """Test get_model_name in remote mode.

    Expected behavior:
    - Fetches model name from /model-info
    - Returns correct model name
    """
    from app.services.embedding import EmbeddingService

    # Mock response
    mock_response = Mock()
    mock_response.json.return_value = {
        "model_name": "sentence-transformers/all-MiniLM-L6-v2",
        "embedding_dimension": 384,
        "device": "cpu",
        "max_batch_size": 128,
        "model_loaded": True
    }
    mock_response.raise_for_status = Mock()

    # Mock client
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_response
    mock_client_class.return_value = mock_client

    # Initialize service
    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    # Get model name
    model_name = service.get_model_name()

    # Verify
    assert model_name == "sentence-transformers/all-MiniLM-L6-v2"


@pytest.mark.unit
@patch('httpx.Client')
def test_embedding_service_embed_single_remote(mock_client_class):
    """Test embed_single in remote mode.

    Expected behavior:
    - Calls POST /vectorize endpoint
    - Returns single embedding vector
    """
    from app.services.embedding import EmbeddingService

    # Mock model info response
    mock_model_info = Mock()
    mock_model_info.json.return_value = {
        "model_name": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "device": "cpu",
        "max_batch_size": 128,
        "model_loaded": True
    }
    mock_model_info.raise_for_status = Mock()

    # Mock vectorize response
    mock_vectorize = Mock()
    mock_vectorize.json.return_value = {
        "embeddings": [[0.1] * 1024],
        "model": "BAAI/bge-m3",
        "dimension": 1024,
        "count": 1,
        "processing_time_seconds": 0.025
    }
    mock_vectorize.raise_for_status = Mock()

    # Mock client
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_model_info
    mock_client.post.return_value = mock_vectorize
    mock_client_class.return_value = mock_client

    # Initialize service and embed
    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    embedding = service.embed_single("Hello world")

    # Verify
    assert len(embedding) == 1024
    assert all(x == 0.1 for x in embedding)
    mock_client.post.assert_called_once()


@pytest.mark.unit
@patch('httpx.Client')
def test_embedding_service_embed_batch_remote(mock_client_class):
    """Test embed_batch in remote mode.

    Expected behavior:
    - Calls POST /vectorize with batch
    - Returns list of embedding vectors
    """
    from app.services.embedding import EmbeddingService

    # Mock model info response
    mock_model_info = Mock()
    mock_model_info.json.return_value = {
        "model_name": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "device": "cpu",
        "max_batch_size": 128,
        "model_loaded": True
    }
    mock_model_info.raise_for_status = Mock()

    # Mock vectorize response
    mock_vectorize = Mock()
    mock_vectorize.json.return_value = {
        "embeddings": [[0.1] * 1024, [0.2] * 1024, [0.3] * 1024],
        "model": "BAAI/bge-m3",
        "dimension": 1024,
        "count": 3,
        "processing_time_seconds": 0.075
    }
    mock_vectorize.raise_for_status = Mock()

    # Mock client
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_model_info
    mock_client.post.return_value = mock_vectorize
    mock_client_class.return_value = mock_client

    # Initialize service and embed batch
    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    texts = ["First text", "Second text", "Third text"]
    embeddings = service.embed_batch(texts)

    # Verify
    assert len(embeddings) == 3
    assert len(embeddings[0]) == 1024
    assert all(x == 0.1 for x in embeddings[0])
    assert all(x == 0.2 for x in embeddings[1])
    assert all(x == 0.3 for x in embeddings[2])


@pytest.mark.unit
@patch('httpx.Client')
def test_embedding_service_remote_connection_error(mock_client_class):
    """Test error handling when remote service is unavailable.

    Expected behavior:
    - Raises RuntimeError when service cannot be reached
    - Error message is informative
    """
    from app.services.embedding import EmbeddingService

    # Mock client that raises connection error
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.side_effect = httpx.ConnectError("Connection refused")
    mock_client_class.return_value = mock_client

    # Initialize service (should succeed - lazy loading)
    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    # Try to use service - should raise error during first use
    with pytest.raises(RuntimeError) as exc_info:
        service.get_embedding_dimension()

    assert "Cannot connect to embedding service" in str(exc_info.value)


@pytest.mark.unit
@patch('httpx.Client')
def test_embedding_service_remote_http_error(mock_client_class):
    """Test error handling when remote service returns HTTP error.

    Expected behavior:
    - Raises RuntimeError when embedding request fails
    - Error message includes details
    """
    from app.services.embedding import EmbeddingService

    # Mock model info response (success)
    mock_model_info = Mock()
    mock_model_info.json.return_value = {
        "model_name": "BAAI/bge-m3",
        "embedding_dimension": 1024,
        "device": "cpu",
        "max_batch_size": 128,
        "model_loaded": True
    }
    mock_model_info.raise_for_status = Mock()

    # Mock vectorize response (error)
    mock_vectorize = Mock()
    mock_vectorize.raise_for_status.side_effect = httpx.HTTPStatusError(
        "500 Internal Server Error",
        request=Mock(),
        response=Mock(status_code=500)
    )

    # Mock client
    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_model_info
    mock_client.post.return_value = mock_vectorize
    mock_client_class.return_value = mock_client

    # Initialize service
    service = EmbeddingService(
        use_remote=True,
        remote_url="http://localhost:8001"
    )

    # Try to embed - should raise error
    with pytest.raises(RuntimeError) as exc_info:
        service.embed_single("Test text")

    assert "Failed to get embeddings from remote service" in str(
        exc_info.value)
