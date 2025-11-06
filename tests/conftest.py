"""Shared fixtures for testing."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_text_content():
    """Provide sample text content for testing."""
    return "This is a sample text document for testing purposes."


@pytest.fixture
def sample_csv_content():
    """Provide sample CSV content for testing."""
    return """Name,Age,City
John Doe,30,New York
Jane Smith,25,Los Angeles
Bob Johnson,35,Chicago"""


# ========== MOCK FIXTURES FOR UNIT TESTS ==========
# These fixtures prevent loading real embedding models in unit tests
# Real models (560MB+) should only be loaded in integration tests

from unittest.mock import Mock, AsyncMock
import numpy as np


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for unit tests (avoids loading real models).
    
    Returns a Mock object that simulates EmbeddingService behavior without
    loading the actual 560MB BGE-M3 model into memory.
    
    Usage:
        def test_something(mock_embedding_service):
            # Use mock instead of real service
            embedding = mock_embedding_service.embed_single("text")
    """
    service = Mock()
    service.model_id = "BAAI/bge-m3"
    service.device = "cpu"
    service.max_batch_size = 128
    service._model = None  # Not loaded
    service.get_embedding_dimension.return_value = 1024
    
    # Mock embed_single to return deterministic 1024-d vector
    service.embed_single.return_value = [0.1] * 1024
    
    # Mock embed_batch to return multiple vectors
    def mock_embed_batch(texts, **kwargs):
        return [[0.1 * (i + 1)] * 1024 for i in range(len(texts))]
    service.embed_batch.side_effect = mock_embed_batch
    
    # Mock async versions
    async def mock_embed_single_async(text):
        return [0.1] * 1024
    service.embed_single_async = AsyncMock(side_effect=mock_embed_single_async)
    
    async def mock_embed_batch_async(texts, **kwargs):
        return [[0.1 * (i + 1)] * 1024 for i in range(len(texts))]
    service.embed_batch_async = AsyncMock(side_effect=mock_embed_batch_async)
    
    return service


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer model for unit tests.
    
    Returns a Mock object that simulates the sentence-transformers model
    without loading actual model weights (avoids 560MB+ download/load).
    
    Usage:
        def test_something(mocker, mock_sentence_transformer):
            mocker.patch('app.services.embedding.SentenceTransformer', 
                        return_value=mock_sentence_transformer)
            service = EmbeddingService()  # Won't load real model
    """
    model = Mock()
    
    # Mock encode method for both single and batch encoding
    def mock_encode(text, convert_to_numpy=False, **kwargs):
        if isinstance(text, str):
            vec = np.random.rand(1024)
        else:  # batch
            vec = np.random.rand(len(text), 1024)
        return vec if convert_to_numpy else vec.tolist()
    
    model.encode.side_effect = mock_encode
    model.to.return_value = model  # For device switching
    model.device = Mock()
    model.device.type = "cpu"
    
    return model