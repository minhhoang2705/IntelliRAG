"""BGE-M3 embedding service for dense and sparse embeddings.

This module provides the BGEM3EmbeddingService class for generating
1024-dimensional dense embeddings and sparse embeddings using BAAI's
BGE-M3 model via FlagEmbedding library.

Key Features:
- Dense embeddings (1024 dimensions)
- Sparse embeddings (vocabulary-based)
- Hybrid retrieval support
- Multilingual (100+ languages)
- Long context support (up to 8192 tokens)


"""

from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BGEM3EmbeddingService:
    """Service for generating BGE-M3 embeddings.

    Supports dense and sparse embeddings for hybrid retrieval.

    Attributes:
        model_id (str): HuggingFace model identifier
        device (str): Device for model execution ("cpu" or "cuda")
        use_fp16 (bool): Use FP16 precision for faster inference
        _model: Lazy-loaded model instance
    """

    DEFAULT_MODEL = "BAAI/bge-m3"
    EMBEDDING_DIM = 1024

    def __init__(
        self,
        model_id: Optional[str] = None,
        device: str = "cpu",
        use_fp16: bool = False
    ):
        """Initialize BGE-M3 embedding service.

        Args:
            model_id: HuggingFace model ID (default: BAAI/bge-m3)
            device: Device to load model on ("cpu" or "cuda", default: "cpu")
            use_fp16: Use FP16 precision (default: False)
        """
        self.model_id = model_id or self.DEFAULT_MODEL
        self.device = device
        self.use_fp16 = use_fp16
        self._model = None  # Lazy loading

    def get_embedding_dimension(self) -> int:
        """Return embedding dimension (1024 for BGE-M3).

        Returns:
            int: Embedding dimension
        """
        return self.EMBEDDING_DIM

    @property
    def model(self):
        """Get model, loading if necessary (lazy loading).

        Returns:
            BGEM3FlagModel: The loaded model instance
        """
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel
                logger.info(
                    f"Loading BGE-M3 model: {self.model_id} on device: {self.device}")
                self._model = BGEM3FlagModel(
                    self.model_id,
                    use_fp16=self.use_fp16,
                    device=self.device
                )
                logger.info("BGE-M3 model loaded successfully")
            except Exception as e:
                logger.error(f"Failed to load BGE-M3 model: {e}")
                raise RuntimeError(
                    f"Failed to initialize BGE-M3 model: {e}") from e
        return self._model

    def embed_single(self, text: str) -> List[float]:
        """Generate dense embedding for single text.

        Args:
            text: Input text to embed

        Returns:
            1024-dimensional embedding vector as list of floats
        """
        if not text:
            return [0.0] * self.EMBEDDING_DIM

        # BGE-M3 encode returns dict with 'dense_vecs' key
        result = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )

        # Extract dense embedding
        dense_embedding = result['dense_vecs'][0]

        return dense_embedding.tolist()

    def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        show_progress: bool = False
    ) -> List[List[float]]:
        """Generate dense embeddings for batch of texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (default: None uses model default)
            show_progress: Show progress bar (default: False)

        Returns:
            List of 1024-dimensional embedding vectors
        """
        if not texts:
            return []

        # BGE-M3 encode returns dict with 'dense_vecs' key
        result = self.model.encode(
            texts,
            batch_size=batch_size or 12,  # Default batch size
            return_dense=True,
            return_sparse=False,
            return_colbert_vecs=False
        )

        # Extract dense embeddings
        dense_embeddings = result['dense_vecs']

        return [emb.tolist() for emb in dense_embeddings]

    def embed_single_sparse(self, text: str) -> Dict[str, List]:
        """Generate sparse embedding for single text.

        Args:
            text: Input text to embed

        Returns:
            Dict with 'indices' and 'values' keys for sparse representation
        """
        if not text:
            return {"indices": [], "values": []}

        # BGE-M3 encode returns dict with 'lexical_weights' key for sparse
        result = self.model.encode(
            [text],
            return_dense=False,
            return_sparse=True,
            return_colbert_vecs=False
        )

        # Extract sparse embedding (vocabulary-based)
        sparse_dict = result['lexical_weights'][0]

        return {
            "indices": list(sparse_dict.keys()),
            "values": list(sparse_dict.values())
        }

    def embed_batch_sparse(self, texts: List[str]) -> List[Dict[str, List]]:
        """Generate sparse embeddings for batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of sparse embedding dicts
        """
        if not texts:
            return []

        # BGE-M3 encode returns dict with 'lexical_weights' key
        result = self.model.encode(
            texts,
            batch_size=12,
            return_dense=False,
            return_sparse=True,
            return_colbert_vecs=False
        )

        # Extract sparse embeddings
        sparse_embeddings = result['lexical_weights']

        return [
            {
                "indices": list(sparse_dict.keys()),
                "values": list(sparse_dict.values())
            }
            for sparse_dict in sparse_embeddings
        ]

    def embed_single_hybrid(self, text: str) -> Dict[str, Any]:
        """Generate both dense and sparse embeddings for single text.

        Args:
            text: Input text to embed

        Returns:
            Dict with 'dense' (list) and 'sparse' (dict) keys
        """
        if not text:
            return {
                "dense": [0.0] * self.EMBEDDING_DIM,
                "sparse": {"indices": [], "values": []}
            }

        # BGE-M3 encode returns both dense and sparse
        result = self.model.encode(
            [text],
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False
        )

        # Extract both dense and sparse embeddings
        dense_embedding = result['dense_vecs'][0]
        sparse_dict = result['lexical_weights'][0]

        return {
            "dense": dense_embedding.tolist(),
            "sparse": {
                "indices": list(sparse_dict.keys()),
                "values": list(sparse_dict.values())
            }
        }

    def embed_batch_hybrid(self, texts: List[str]) -> List[Dict[str, Any]]:
        """Generate hybrid embeddings for batch of texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of dicts with 'dense' and 'sparse' keys
        """
        if not texts:
            return []

        # BGE-M3 encode returns both dense and sparse
        result = self.model.encode(
            texts,
            batch_size=12,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False
        )

        # Extract both dense and sparse embeddings
        dense_embeddings = result['dense_vecs']
        sparse_embeddings = result['lexical_weights']

        return [
            {
                "dense": dense_emb.tolist(),
                "sparse": {
                    "indices": list(sparse_dict.keys()),
                    "values": list(sparse_dict.values())
                }
            }
            for dense_emb, sparse_dict in zip(dense_embeddings, sparse_embeddings)
        ]

    async def embed_single_async(self, text: str) -> List[float]:
        """Async version of embed_single.

        Args:
            text: Input text to embed

        Returns:
            1024-dimensional embedding vector
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_single, text)

    async def embed_batch_async(
        self,
        texts: List[str],
        batch_size: Optional[int] = None
    ) -> List[List[float]]:
        """Async version of embed_batch.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing

        Returns:
            List of 1024-dimensional embedding vectors
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.embed_batch(texts, batch_size)
        )

    async def embed_batch_hybrid_async(
        self,
        texts: List[str]
    ) -> List[Dict[str, Any]]:
        """Async version of embed_batch_hybrid.

        Args:
            texts: List of texts to embed

        Returns:
            List of dicts with 'dense' and 'sparse' keys
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_batch_hybrid, texts)
