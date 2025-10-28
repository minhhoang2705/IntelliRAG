"""Unit tests for BGE-M3 embedding service.

Tests for the BGE-M3 embedding service that provides dense and sparse
embeddings using BAAI's FlagEmbedding library.

Date: 2025-10-24
"""

import pytest
import numpy as np
from app.services.bge_m3_embedding import BGEM3EmbeddingService


class TestBGEM3EmbeddingServiceInit:
    """Test BGE-M3 embedding service initialization."""

    @pytest.mark.unit
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        service = BGEM3EmbeddingService()
        assert service.model_id == "BAAI/bge-m3"
        assert service.device == "cpu"
        assert service.use_fp16 is False
        assert service._model is None  # Lazy loading

    @pytest.mark.unit
    def test_get_embedding_dimension(self):
        """Test that embedding dimension is 1024 for BGE-M3."""
        service = BGEM3EmbeddingService()
        assert service.get_embedding_dimension() == 1024

    @pytest.mark.unit
    def test_embed_single_dense(self, mocker):
        """Test single text dense embedding."""
        # Mock the model property to avoid loading real BGE-M3
        service = BGEM3EmbeddingService()
        
        # Mock the _load_model method's return value
        mock_model = mocker.Mock()
        mock_model.encode.return_value = {
            'dense_vecs': np.array([np.random.rand(1024)])  # Needs to be numpy array for .tolist()
        }
        service._model = mock_model  # Directly set the mocked model
        
        text = "This is a test sentence."

        embedding = service.embed_single(text)

        assert isinstance(embedding, list)
        assert len(embedding) == 1024
        assert all(isinstance(x, float) for x in embedding)
        # Mock returns non-zero embeddings
        assert any(x != 0.0 for x in embedding)
        mock_model.encode.assert_called_once()

    @pytest.mark.unit
    def test_embed_batch_dense(self, mocker):
        """Test batch dense embedding generation."""
        # Mock the model to avoid loading real BGE-M3
        service = BGEM3EmbeddingService()
        
        mock_model = mocker.Mock()
        mock_model.encode.return_value = {
            'dense_vecs': np.random.rand(3, 1024)  # Needs to be numpy array
        }
        service._model = mock_model
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
        mock_model.encode.assert_called_once()

    @pytest.mark.unit
    def test_embed_single_sparse(self, mocker):
        """Test single text sparse embedding."""
        # Mock the model to avoid loading real BGE-M3
        service = BGEM3EmbeddingService()
        
        mock_model = mocker.Mock()
        mock_model.encode.return_value = {
            'lexical_weights': [{1: 0.5, 5: 0.3, 10: 0.2}]  # Dict mapping token_id -> weight
        }
        service._model = mock_model
        text = "This is a test sentence."

        sparse_emb = service.embed_single_sparse(text)

        assert isinstance(sparse_emb, dict)
        assert "indices" in sparse_emb
        assert "values" in sparse_emb
        assert isinstance(sparse_emb["indices"], list)
        assert isinstance(sparse_emb["values"], list)
        assert len(sparse_emb["indices"]) == len(sparse_emb["values"])
        # Mock returns positive values
        assert all(v > 0.0 for v in sparse_emb["values"])
        mock_model.encode.assert_called_once()

    @pytest.mark.unit
    def test_embed_single_hybrid(self, mocker):
        """Test single text hybrid embedding (dense + sparse)."""
        # Mock the model to avoid loading real BGE-M3
        service = BGEM3EmbeddingService()
        
        mock_model = mocker.Mock()
        mock_model.encode.return_value = {
            'dense_vecs': np.array([np.random.rand(1024)]),  # Needs to be numpy array
            'lexical_weights': [{1: 0.5, 5: 0.3, 10: 0.2}]  # Dict mapping token_id -> weight
        }
        service._model = mock_model
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
        mock_model.encode.assert_called_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_embed_single_async(self, mocker):
        """Test async single embedding."""
        # Mock the model to avoid loading real BGE-M3
        service = BGEM3EmbeddingService()
        
        mock_model = mocker.Mock()
        mock_model.encode.return_value = {
            'dense_vecs': np.array([np.random.rand(1024)])  # Needs to be numpy array
        }
        service._model = mock_model
        text = "Test async embedding."

        embedding = await service.embed_single_async(text)

        assert len(embedding) == 1024
        assert isinstance(embedding, list)
        assert all(isinstance(x, float) for x in embedding)
        mock_model.encode.assert_called_once()
