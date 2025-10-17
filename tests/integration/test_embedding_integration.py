"""Integration tests for EmbeddingService with real model.

This module tests EmbeddingService with actual SentenceTransformer model,
not mocked. Tests include model loading, real inference, batch processing,
and multilingual support.

Author: IntelliRAG Team
Date: 2025-10-17
"""

import pytest


@pytest.mark.integration
def test_embedding_service_loads_real_model():
    """Test EmbeddingService loads actual model from HuggingFace.

    RED Phase: This test will verify real model loading (not mocked).
    Expected: Model loads successfully and has 768 dimensions.
    """
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()

    # Verify model loads (may take ~20-30s on first run)
    assert service.model is not None
    assert service.get_embedding_dimension() == 768


@pytest.mark.integration
def test_embedding_service_generates_real_embeddings():
    """Test real embedding generation (not mocked).
    
    Integration Test: Verifies actual embedding generation with real model.
    Expected: 768-d non-zero embeddings with reasonable L2 norm.
    """
    from app.services.embedding import EmbeddingService
    import numpy as np

    service = EmbeddingService()

    text = "This is a test sentence for embedding."
    embedding = service.embed_single(text)

    # Verify embedding properties
    assert isinstance(embedding, list)
    assert len(embedding) == 768
    assert all(isinstance(x, float) for x in embedding)

    # Verify embeddings are not zero vectors
    assert not all(x == 0.0 for x in embedding)

    # Verify embeddings are normalized (L2 norm should be reasonable)
    norm = np.linalg.norm(embedding)
    assert 0.1 < norm < 10.0  # Reasonable range


@pytest.mark.integration
def test_embedding_service_batch_real_inference():
    """Test batch embedding with real model.
    
    Integration Test: Verifies batch processing with real model.
    Expected: All texts get 768-d embeddings, different texts produce different embeddings.
    """
    from app.services.embedding import EmbeddingService
    from tests.fixtures.integration_data import SAMPLE_TEXTS
    import numpy as np

    service = EmbeddingService()

    embeddings = service.embed_batch(SAMPLE_TEXTS)

    # Verify batch results
    assert len(embeddings) == len(SAMPLE_TEXTS)
    assert all(len(emb) == 768 for emb in embeddings)

    # Verify embeddings are different for different texts
    emb1 = np.array(embeddings[0])
    emb2 = np.array(embeddings[1])
    cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    # Similar texts should have high similarity, but not identical
    assert 0.0 < cosine_sim < 1.0


@pytest.mark.integration
def test_embedding_service_multilingual():
    """Test multilingual embedding support.
    
    Integration Test: Verifies model handles multiple languages correctly.
    Expected: Similar meanings across languages have high cosine similarity (>0.5).
    """
    from app.services.embedding import EmbeddingService
    from tests.fixtures.integration_data import MULTILINGUAL_SAMPLES
    import numpy as np

    service = EmbeddingService()

    embeddings = {}
    for lang, text in MULTILINGUAL_SAMPLES.items():
        embeddings[lang] = service.embed_single(text)

    # All embeddings should be valid 768-d vectors
    assert all(len(emb) == 768 for emb in embeddings.values())

    # Similar meanings should have high similarity
    # "Hello world" variants should be similar to each other
    en_emb = np.array(embeddings['en'])
    fr_emb = np.array(embeddings['fr'])

    similarity = np.dot(en_emb, fr_emb) / (np.linalg.norm(en_emb) * np.linalg.norm(fr_emb))

    # Multilingual model should recognize semantic similarity
    assert similarity > 0.5  # Reasonable threshold for similar meanings
