"""Embedding service for generating multilingual text embeddings.

This module provides the EmbeddingService class for converting text chunks into
1024-dimensional dense vector embeddings using the BAAI/bge-m3
model from sentence-transformers.

Key Features:
- Multilingual support (50+ languages)
- GPU/CPU hybrid operation
- Lazy model loading
- Configurable batch size to prevent OOM
- Future-proofed for multimodal embeddings

Date: 2025-10-15
"""

from typing import Optional, List
from app.services.base_embedding import BaseEmbeddingService
from sentence_transformers import SentenceTransformer
import logging
import torch
import threading

logger = logging.getLogger(__name__)


class EmbeddingService(BaseEmbeddingService):
    """Service for generating multilingual text embeddings using SentenceTransformers.

    Supports GPU/CPU hybrid operation:
    - CPU (default): For real-time single queries (~25ms per query)
    - GPU: For batch processing (enabled via use_gpu parameter)

    Future-proofed for multimodal embeddings (Phase 2).

    Attributes:
        model_id (str): HuggingFace model identifier
        device (str): Device for model execution ("cpu" or "cuda")
        max_batch_size (int): Maximum batch size to prevent OOM
        _model (SentenceTransformer): Lazy-loaded model instance

    Example:
        >>> service = EmbeddingService()
        >>> embedding = service.embed_single("Hello world")
        >>> len(embedding)
        1024
    """

    DEFAULT_MODEL = "BAAI/bge-m3"
    EMBEDDING_DIM = 1024
    MAX_BATCH_SIZE = 128

    def __init__(
        self,
        model_id: Optional[str] = None,
        device: str = "cpu",
        max_batch_size: int = MAX_BATCH_SIZE
    ):
        """Initialize embedding service.

        Args:
            model_id: HuggingFace model ID (default: BAAI/bge-m3)
            device: Device to load model on ("cpu" or "cuda", default: "cpu")
            max_batch_size: Maximum batch size to prevent OOM (default: 128)
        """
        self.model_id = model_id or self.DEFAULT_MODEL
        self.device = device
        self.max_batch_size = max_batch_size
        self._model = None  # Lazy loading
        self._model_lock = threading.Lock()  # Thread-safe model loading

    @property
    def model(self) -> SentenceTransformer:
        """Get model, loading if necessary (thread-safe lazy loading).

        Returns:
            SentenceTransformer: The loaded model instance

        Note:
            Model is loaded on first access and cached for subsequent calls.
            Loading time: ~20-30 seconds on first call, instantaneous after.
            Thread-safe: Multiple concurrent calls will wait for loading to complete.
        """
        if self._model is None:
            with self._model_lock:
                # Double-check after acquiring lock
                if self._model is None:
                    try:
                        logger.info(
                            f"Loading embedding model: {self.model_id} on device: {self.device}")
                        self._model = SentenceTransformer(self.model_id)
                        self._model.to(self.device)
                    except Exception as e:
                        logger.error(f"Failed to load embedding model: {e}")
                        raise RuntimeError(
                            f"Failed to initialize embedding model: {e}") from e
        return self._model

    def get_embedding_dimension(self) -> int:
        """Return embedding dimension (1024 for BGE-M3).

        Returns:
            int: Embedding dimension
        """
        return self.EMBEDDING_DIM

    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for single text.

        Args:
            text: Input text to embed

        Returns:
            1024-dimensional embedding vector as list of floats

        Example:
            >>> service = EmbeddingService()
            >>> embedding = service.embed_single("Hello world")
            >>> len(embedding)
            1024

        Note:
            - Empty text returns zero vector
            - Supports 50+ languages (multilingual model)
            - First call loads model (~20-30s), subsequent calls are fast
        """
        import time

        # Handle empty text
        if not text:
            return [0.0] * self.EMBEDDING_DIM

        start_time = time.time()

        # Generate embedding using the model
        embedding = self.model.encode(text, convert_to_numpy=True)

        duration = time.time() - start_time
        logger.info(
            "Generated single embedding",
            extra={'extra_data': {
                'text_length': len(text),
                'embedding_dim': len(embedding),
                'duration_seconds': round(duration, 3)
            }}
        )

        return embedding.tolist()

    def embed_batch(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        normalize: bool = False,
        show_progress: bool = False,
        use_gpu: bool = False
    ) -> List[List[float]]:
        """Generate embeddings for batch of texts with GPU/CPU hybrid support.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (default: None uses max_batch_size)
            normalize: Whether to L2-normalize embeddings (default: False)
            show_progress: Show progress bar (default: False)
            use_gpu: If True and CUDA available, temporarily use GPU for batch (default: False)

        Returns:
            List of 1024-dimensional embedding vectors

        Example:
            >>> service = EmbeddingService()
            >>> embeddings = service.embed_batch(["Hello", "World"])
            >>> len(embeddings)
            2
            >>> len(embeddings[0])
            1024

        Note:
            GPU usage is temporary - model is moved back to original device after batch.
            This allows GPU acceleration for batch ingestion while keeping CPU free for queries.
        """
        import time

        if not texts:
            return []

        start_time = time.time()
        original_device = self.device
        actual_batch_size = batch_size or self.max_batch_size

        # Determine device for this operation
        target_device = "cuda" if (
            use_gpu and torch.cuda.is_available()) else self.device

        try:
            # Temporarily move model to GPU if requested
            if target_device != original_device:
                logger.info(
                    f"Temporarily moving model to {target_device} for batch processing")
                self.model.to(target_device)

            # Process in sub-batches if needed to prevent OOM
            all_embeddings = []
            for i in range(0, len(texts), actual_batch_size):
                sub_batch = texts[i:i + actual_batch_size]

                embeddings = self.model.encode(
                    sub_batch,
                    batch_size=actual_batch_size,
                    show_progress_bar=show_progress,
                    normalize_embeddings=normalize,
                    convert_to_numpy=True,
                    device=target_device
                )

                all_embeddings.extend(embeddings)

            duration = time.time() - start_time
            logger.info(
                f"Generated batch embeddings for {len(texts)} texts",
                extra={'extra_data': {
                    'batch_size': len(texts),
                    'sub_batch_size': actual_batch_size,
                    'vectors_per_second': round(len(texts) / duration, 2),
                    'duration_seconds': round(duration, 3),
                    'normalized': normalize,
                    'device': target_device,
                    'gpu_accelerated': target_device == "cuda"
                }}
            )

            return [emb.tolist() for emb in all_embeddings]

        finally:
            # Always restore original device
            if target_device != original_device:
                logger.info(f"Restoring model to {original_device}")
                self.model.to(original_device)

    async def embed_single_async(self, text: str) -> List[float]:
        """Async version of embed_single.

        Args:
            text: Input text to embed

        Returns:
            1024-dimensional embedding vector

        Note:
            This method runs the synchronous embedding in a thread pool executor
            to avoid blocking the event loop.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.embed_single, text)

    async def embed_batch_async(
        self,
        texts: List[str],
        batch_size: Optional[int] = None,
        normalize: bool = False,
        use_gpu: bool = False
    ) -> List[List[float]]:
        """Async version of embed_batch.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing
            normalize: Whether to L2-normalize embeddings
            use_gpu: If True and CUDA available, use GPU for batch

        Returns:
            List of 1024-dimensional embedding vectors

        Note:
            This method runs the synchronous batch embedding in a thread pool executor
            to avoid blocking the event loop.
        """
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            lambda: self.embed_batch(
                texts, batch_size, normalize, False, use_gpu)
        )
