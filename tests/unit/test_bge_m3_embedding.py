"""Unit tests for BGE-M3 embedding service.

Tests for the BGE-M3 embedding service that provides dense and sparse
embeddings using BAAI's FlagEmbedding library.

Date: 2025-10-24
"""

import pytest
from app.services.bge_m3_embedding import BGEM3EmbeddingService


class TestBGEM3EmbeddingServiceInit:
    """Test BGE-M3 embedding service initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        service = BGEM3EmbeddingService()
        assert service.model_id == "BAAI/bge-m3"
        assert service.device == "cpu"
        assert service.use_fp16 is False
        assert service._model is None  # Lazy loading

    def test_get_embedding_dimension(self):
        """Test that embedding dimension is 1024 for BGE-M3."""
        service = BGEM3EmbeddingService()
        assert service.get_embedding_dimension() == 1024

    def test_embed_single_dense(self):
        """Test single text dense embedding."""
        service = BGEM3EmbeddingService()
        text = "This is a test sentence."

        embedding = service.embed_single(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        assert all(isinstance(x, float) for x in embedding)
        # Verify non-zero embeddings
        assert any(x != 0.0 for x in embedding)

    def test_embed_batch_dense(self):
        """Test batch dense embedding generation."""
        service = BGEM3EmbeddingService()
        texts = [
            "First sentence.",
            "Second sentence.",
            "Third sentence."
        ]

        embeddings = service.embed_batch(texts)

        assert isinstance(embeddings, list)
        assert len(embeddings) == 3
        for emb in embeddings:
            assert len(emb) == 1024
            assert all(isinstance(x, float) for x in emb)

    def test_embed_single_sparse(self):
        """Test single text sparse embedding."""
        service = BGEM3EmbeddingService()
        text = "This is a test sentence."

        sparse_emb = service.embed_single_sparse(text)

        assert isinstance(sparse_emb, dict)
        assert "indices" in sparse_emb
        assert "values" in sparse_emb
        assert isinstance(sparse_emb["indices"], list)
        assert isinstance(sparse_emb["values"], list)
        assert len(sparse_emb["indices"]) == len(sparse_emb["values"])
        # Sparse embeddings should have non-zero values
        assert all(v > 0.0 for v in sparse_emb["values"])

    def test_embed_single_hybrid(self):
        """Test single text hybrid embedding (dense + sparse)."""
        service = BGEM3EmbeddingService()
        text = "This is a test sentence."

        result = service.embed_single_hybrid(text)

        assert isinstance(result, dict)
        assert "dense" in result
        assert "sparse" in result
        assert len(result["dense"]) == 1024
        assert "indices" in result["sparse"]
        assert "values" in result["sparse"]
        assert len(result["sparse"]["indices"]) > 0
        assert len(result["sparse"]["values"]) > 0

    @pytest.mark.asyncio
    async def test_embed_single_async(self):
        """Test async single embedding."""
        service = BGEM3EmbeddingService()
        text = "Test async embedding."

        embedding = await service.embed_single_async(text)

        assert len(embedding) == 1024
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)
