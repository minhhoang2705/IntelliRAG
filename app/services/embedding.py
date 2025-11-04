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
import httpx

logger = logging.getLogger(__name__)


class EmbeddingService(BaseEmbeddingService):
    """Service for generating multilingual text embeddings.

    Supports two modes:
    1. Remote mode (default): Calls external embedding service via HTTP
    2. Local mode: Loads SentenceTransformer model in-process

    Remote mode benefits:
    - No cold start delay (model always loaded)
    - Independent scaling
    - Consistent with LLM service architecture

    Local mode benefits:
    - No network latency
    - Backward compatibility
    - Useful for testing

    Attributes:
        use_remote (bool): If True, use remote service; if False, use local model
        remote_url (str): URL of remote embedding service
        model_id (str): HuggingFace model identifier (local mode only)
        device (str): Device for model execution (local mode only)
        max_batch_size (int): Maximum batch size to prevent OOM
        _model (SentenceTransformer): Lazy-loaded model instance (local mode only)
        _model_info_cache (dict): Cached model info from remote service

    Example (Remote mode):
        >>> service = EmbeddingService(use_remote=True)
        >>> embedding = service.embed_single("Hello world")
        >>> len(embedding)
        1024

    Example (Local mode):
        >>> service = EmbeddingService(use_remote=False)
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
        max_batch_size: int = MAX_BATCH_SIZE,
        use_remote: bool = False,
        remote_url: str = "http://localhost:8001"
    ):
        """Initialize embedding service.

        Args:
            model_id: HuggingFace model ID (default: BAAI/bge-m3) - local mode only
            device: Device to load model on ("cpu" or "cuda", default: "cpu") - local mode only
            max_batch_size: Maximum batch size to prevent OOM (default: 128)
            use_remote: If True, use remote service; if False, use local model (default: False for backward compatibility)
            remote_url: URL of remote embedding service (default: http://localhost:8001)
        """
        self.use_remote = use_remote
        self.remote_url = remote_url
        self.max_batch_size = max_batch_size
        self._model_info_cache = None  # Cache for remote model info

        if not use_remote:
            # Local mode - initialize model loading
            self.model_id = model_id or self.DEFAULT_MODEL
            self.device = device
            self._model = None  # Lazy loading
            self._model_lock = threading.Lock()  # Thread-safe model loading
        else:
            # Remote mode - model info will be fetched lazily on first use
            self.model_id = None
            self.device = None
            self._model = None
            self._model_lock = None
            logger.info(f"Using remote embedding service at {remote_url}")

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
        """Return embedding dimension.

        Returns:
            int: Embedding dimension

        Note:
            In remote mode, fetches dimension from model-info endpoint.
            In local mode, returns constant EMBEDDING_DIM.
        """
        if self.use_remote:
            model_info = self._fetch_model_info()
            return model_info["embedding_dimension"]
        else:
            return self.EMBEDDING_DIM

    def get_model_name(self) -> str:
        """Get the actual model name being used.

        Returns:
            str: Model name

        Note:
            In remote mode, fetches from model-info endpoint.
            In local mode, returns model_id.
        """
        if self.use_remote:
            model_info = self._fetch_model_info()
            return model_info["model_name"]
        else:
            return self.model_id

    def _fetch_model_info(self) -> dict:
        """Fetch model metadata from remote service.

        Returns:
            dict: Model metadata with keys: model_name, embedding_dimension, device, etc.

        Raises:
            RuntimeError: If service cannot be reached

        Note:
            Response is cached to avoid repeated HTTP calls.
        """
        if self._model_info_cache is not None:
            return self._model_info_cache

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.remote_url}/model-info")
                response.raise_for_status()
                self._model_info_cache = response.json()

                logger.info(
                    f"Connected to embedding service: "
                    f"{self._model_info_cache['model_name']} "
                    f"({self._model_info_cache['embedding_dimension']} dims)"
                )
                return self._model_info_cache

        except Exception as e:
            logger.error(
                f"Failed to fetch model info from {self.remote_url}: {e}")
            raise RuntimeError(
                f"Cannot connect to embedding service at {self.remote_url}. "
                "Is the service running?"
            ) from e

    def embed_single(self, text: str) -> List[float]:
        """Generate embedding for single text.

        Args:
            text: Input text to embed

        Returns:
            Embedding vector as list of floats (dimension depends on model)

        Example:
            >>> service = EmbeddingService(use_remote=True)
            >>> embedding = service.embed_single("Hello world")
            >>> len(embedding)
            1024

        Note:
            - Remote mode: Calls /vectorize endpoint
            - Local mode: Uses in-process model
            - Empty text returns zero vector
        """
        if self.use_remote:
            # Remote mode - call service
            return self._embed_remote([text])[0]
        else:
            # Local mode - use in-process model
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
        """Generate embeddings for batch of texts.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for processing (default: None uses max_batch_size)
            normalize: Whether to L2-normalize embeddings (default: False)
            show_progress: Show progress bar (default: False) - local mode only
            use_gpu: If True and CUDA available, temporarily use GPU for batch (default: False) - local mode only

        Returns:
            List of embedding vectors

        Example:
            >>> service = EmbeddingService(use_remote=True)
            >>> embeddings = service.embed_batch(["Hello", "World"])
            >>> len(embeddings)
            2

        Note:
            - Remote mode: Calls /vectorize endpoint
            - Local mode: GPU usage is temporary - model is moved back to original device after batch
        """
        if self.use_remote:
            # Remote mode - call service
            return self._embed_remote(texts, normalize=normalize)
        else:
            # Local mode - use in-process model
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

    def _embed_remote(self, texts: List[str], normalize: bool = False) -> List[List[float]]:
        """Call remote embedding service via HTTP.

        Args:
            texts: List of texts to embed
            normalize: Whether to L2-normalize embeddings

        Returns:
            List of embedding vectors

        Raises:
            RuntimeError: If remote service call fails
        """
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.post(
                    f"{self.remote_url}/vectorize",
                    json={"texts": texts, "normalize": normalize}
                )
                response.raise_for_status()
                result = response.json()

                # Log dimension info for debugging
                logger.debug(
                    f"Received {result['count']} embeddings of "
                    f"{result['dimension']} dimensions from {result['model']}"
                )

                return result["embeddings"]

        except Exception as e:
            logger.error(f"Remote embedding failed: {e}")
            raise RuntimeError(
                f"Failed to get embeddings from remote service: {e}") from e
