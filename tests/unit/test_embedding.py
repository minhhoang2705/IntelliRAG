"""Unit tests for EmbeddingService.

This module tests the embedding service for generating multilingual text embeddings
using the BAAI/bge-m3 model (1024-dimensional vectors).

Test Coverage:
- Service instantiation and configuration
- Model lazy loading
- Device management (CPU/GPU)
- Single text embedding
- Batch text embedding
- Async operations
- Multimodal interface compliance

Following TDD methodology: Write tests first, implement after.
"""

import pytest
import numpy as np


import torch


def test_embedding_service_can_be_instantiated():
    """Test EmbeddingService can be created."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    assert service is not None


def test_embedding_service_has_model_id_parameter():
    """Test EmbeddingService accepts model_id parameter."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(model_id="custom-model")
    assert service.model_id == "custom-model"


def test_embedding_service_defaults_to_mpnet():
    """Test default model is BAAI/bge-m3."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    assert service.model_id == "BAAI/bge-m3"


def test_embedding_service_accepts_device_parameter():
    """Test EmbeddingService accepts device parameter."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(device="cpu")
    assert service.device == "cpu"


def test_embedding_service_defaults_to_cpu():
    """Test default device is CPU."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    assert service.device == "cpu"


def test_embedding_service_accepts_max_batch_size():
    """Test EmbeddingService accepts max_batch_size parameter."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(max_batch_size=32)
    assert service.max_batch_size == 32


def test_embedding_service_defaults_max_batch_size():
    """Test default max_batch_size is 128."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    assert service.max_batch_size == 128


def test_embedding_service_lazy_loads_model():
    """Test model is not loaded until first use."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    assert service._model is None  # Not loaded yet


def test_embedding_service_has_get_embedding_dimension():
    """Test service has get_embedding_dimension method."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    dimension = service.get_embedding_dimension()
    assert dimension == 1024  # bge-m3 dimension


def test_embedding_service_embed_single_returns_vector():
    """Test embed_single returns correct shape vector."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    vector = service.embed_single("Test sentence")

    assert vector is not None
    assert len(vector) == 1024  # mpnet-base-v2 dimension
    assert isinstance(vector, list)
    assert all(isinstance(v, float) for v in vector)


def test_embedding_service_embed_single_handles_empty_text():
    """Test embed_single handles empty text gracefully."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    vector = service.embed_single("")

    # Should still return 1024-d zero vector
    assert len(vector) == 1024
    assert all(v == 0.0 for v in vector)


def test_embedding_service_embed_single_multilingual():
    """Test embed_single handles multilingual text."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()

    # Test various languages
    texts = [
        "Hello world",  # English
        "Bonjour le monde",  # French
        "Hola mundo",  # Spanish
        "Xin chào thế giới",  # Vietnamese
    ]

    for text in texts:
        vector = service.embed_single(text)
        assert len(vector) == 1024
        # Check vector is not all zeros (actual embedding computed)
        assert any(v != 0.0 for v in vector)


def test_embedding_service_embed_single_logs_operation():
    """Test embedding operation is logged."""
    from app.services.embedding import EmbeddingService
    from unittest.mock import patch

    service = EmbeddingService()

    with patch('app.services.embedding.logger') as mock_logger:
        service.embed_single("Test")
        # Should log the embedding operation
        assert mock_logger.info.called


def test_embedding_service_embed_single_consistent_output():
    """Test embed_single produces consistent embeddings for same input."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    text = "Consistency test"

    vector1 = service.embed_single(text)
    vector2 = service.embed_single(text)

    # Same text should produce same embedding
    assert len(vector1) == len(vector2)
    # Check vectors are very similar (allowing for floating point precision)
    for v1, v2 in zip(vector1, vector2):
        assert abs(v1 - v2) < 1e-6


def test_embedding_service_embed_single_different_inputs():
    """Test embed_single produces different embeddings for different inputs."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()

    vector1 = service.embed_single("Hello world")
    vector2 = service.embed_single("Goodbye world")

    # Different texts should produce different embeddings
    assert vector1 != vector2
    # Check they're actually different (not just memory references)
    differences = sum(1 for v1, v2 in zip(vector1, vector2) if abs(v1 - v2) > 0.01)
    assert differences > 100  # Expect significant differences


def test_embedding_service_embed_batch_returns_vectors():
    """Test embed_batch returns correct shape."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    texts = ["First sentence", "Second sentence", "Third sentence"]
    vectors = service.embed_batch(texts)

    assert len(vectors) == 3
    assert all(len(v) == 1024 for v in vectors)
    assert isinstance(vectors, list)
    assert all(isinstance(v, list) for v in vectors)


@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_embedding_service_embed_batch_with_gpu():
    """Test batch embedding with GPU acceleration."""
    from app.services.embedding import EmbeddingService
    import torch

    service = EmbeddingService(device="cpu")  # Start on CPU

    texts = [f"Test sentence {i}" for i in range(50)]
    vectors = service.embed_batch(texts, use_gpu=True)  # Use GPU for batch

    assert len(vectors) == 50
    assert all(len(v) == 1024 for v in vectors)
    # Verify model returned to CPU after batch
    assert service.model.device.type == "cpu"


def test_embedding_service_embed_batch_respects_max_batch_size():
    """Test batch embedding respects max_batch_size to prevent OOM."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(max_batch_size=32)

    # Create batch larger than max_batch_size
    texts = [f"Sentence {i}" for i in range(100)]
    vectors = service.embed_batch(texts)

    # Should process in sub-batches but return all vectors
    assert len(vectors) == 100
    assert all(len(v) == 1024 for v in vectors)


def test_embedding_service_embed_batch_normalizes():
    """Test batch embedding can normalize vectors."""
    from app.services.embedding import EmbeddingService
    import numpy as np

    service = EmbeddingService()
    texts = ["Test sentence"]

    vectors = service.embed_batch(texts, normalize=True)

    # Check L2 norm is approximately 1.0
    norm = np.linalg.norm(vectors[0])
    assert abs(norm - 1.0) < 0.001


def test_embedding_service_embed_batch_handles_empty_list():
    """Test embed_batch handles empty input."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    vectors = service.embed_batch([])

    assert vectors == []


def test_embedding_service_embed_batch_handles_single_item():
    """Test embed_batch handles single item list."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    vectors = service.embed_batch(["Single text"])

    assert len(vectors) == 1
    assert len(vectors[0]) == 1024


def test_embedding_service_embed_batch_logs_metrics():
    """Test batch embedding logs performance metrics."""
    from app.services.embedding import EmbeddingService
    from unittest.mock import patch

    service = EmbeddingService()
    texts = ["Text 1", "Text 2", "Text 3"]

    with patch('app.services.embedding.logger') as mock_logger:
        service.embed_batch(texts)
        # Should log batch metrics (size, duration, device)
        assert mock_logger.info.called


def test_embedding_service_embed_batch_processes_large_batch():
    """Test embed_batch can process large batches."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    texts = [f"This is test sentence number {i}" for i in range(200)]

    vectors = service.embed_batch(texts)

    assert len(vectors) == 200
    assert all(len(v) == 1024 for v in vectors)
    # Verify all vectors have content (not zeros)
    assert all(any(abs(val) > 0.01 for val in vec) for vec in vectors)


def test_embedding_service_embed_batch_falls_back_to_cpu():
    """Test embed_batch falls back to CPU when GPU requested but unavailable."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService(device="cpu")
    texts = ["Test 1", "Test 2"]

    # Request GPU (may or may not be available)
    vectors = service.embed_batch(texts, use_gpu=True)

    # Should still work (fallback to CPU if needed)
    assert len(vectors) == 2
    assert all(len(v) == 1024 for v in vectors)


@pytest.mark.asyncio
async def test_embedding_service_embed_single_async():
    """Test async single embedding."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    vector = await service.embed_single_async("Test sentence")

    assert len(vector) == 1024
    assert isinstance(vector, list)


@pytest.mark.asyncio
async def test_embedding_service_embed_batch_async():
    """Test async batch embedding."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    texts = ["First", "Second", "Third"]
    vectors = await service.embed_batch_async(texts)

    assert len(vectors) == 3
    assert all(len(v) == 1024 for v in vectors)


@pytest.mark.asyncio
async def test_embedding_service_async_concurrent_calls():
    """Test multiple async calls can run concurrently."""
    from app.services.embedding import EmbeddingService
    import asyncio

    service = EmbeddingService()
    
    # Run multiple async operations concurrently
    tasks = [
        service.embed_single_async("Text 1"),
        service.embed_single_async("Text 2"),
        service.embed_single_async("Text 3")
    ]
    
    vectors = await asyncio.gather(*tasks)
    
    assert len(vectors) == 3
    assert all(len(v) == 1024 for v in vectors)


@pytest.mark.asyncio
async def test_embedding_service_async_error_handling():
    """Test async methods handle errors gracefully."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    
    # Empty text should still work
    vector = await service.embed_single_async("")
    assert len(vector) == 1024
    assert all(v == 0.0 for v in vector)
    
    # Empty batch should work
    vectors = await service.embed_batch_async([])
    assert vectors == []


def test_base_embedding_service_is_abstract():
    """Test BaseEmbeddingService cannot be instantiated."""
    from app.services.base_embedding import BaseEmbeddingService
    import pytest

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        BaseEmbeddingService()


def test_base_embedding_service_has_abstract_embed_single():
    """Test BaseEmbeddingService has abstract embed_single method."""
    from app.services.base_embedding import BaseEmbeddingService
    import inspect

    # Check method exists and is abstract
    assert hasattr(BaseEmbeddingService, 'embed_single')
    assert inspect.isabstract(BaseEmbeddingService)


def test_base_embedding_service_has_abstract_embed_batch():
    """Test BaseEmbeddingService has abstract embed_batch method."""
    from app.services.base_embedding import BaseEmbeddingService

    assert hasattr(BaseEmbeddingService, 'embed_batch')


def test_base_embedding_service_has_abstract_get_embedding_dimension():
    """Test BaseEmbeddingService has abstract get_embedding_dimension method."""
    from app.services.base_embedding import BaseEmbeddingService

    assert hasattr(BaseEmbeddingService, 'get_embedding_dimension')


def test_embedding_service_inherits_from_base():
    """Test EmbeddingService inherits from BaseEmbeddingService."""
    from app.services.embedding import EmbeddingService
    from app.services.base_embedding import BaseEmbeddingService

    assert issubclass(EmbeddingService, BaseEmbeddingService)


def test_concrete_implementation_can_be_instantiated():
    """Test that concrete EmbeddingService can still be instantiated."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()
    assert service is not None
    assert hasattr(service, 'embed_single')
    assert hasattr(service, 'embed_batch')
    assert hasattr(service, 'get_embedding_dimension')


def test_base_service_enforces_interface():
    """Test that subclasses must implement all abstract methods."""
    from app.services.base_embedding import BaseEmbeddingService
    import pytest

    # Try to create incomplete subclass
    class IncompleteService(BaseEmbeddingService):
        def embed_single(self, data):
            pass
        # Missing embed_batch and get_embedding_dimension

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteService()
