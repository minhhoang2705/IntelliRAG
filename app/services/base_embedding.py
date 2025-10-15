"""Abstract base class for embedding services.

This module provides the BaseEmbeddingService abstract class that defines
the common interface for all embedding services (text, image, video, audio).

This design enables future multimodal support (Phase 2) while maintaining
a consistent interface across all embedding types.

Architecture:
- Phase 1 (Current): TextEmbeddingService (sentence-transformers)
- Phase 2 (Future): ImageEmbeddingService (CLIP), VideoEmbeddingService, etc.

Author: IntelliRAG Team
Date: 2025-10-15
"""

from abc import ABC, abstractmethod
from typing import List, Any, Optional


class BaseEmbeddingService(ABC):
    """Abstract base class for all embedding services.

    This class defines the common interface that all embedding services
    must implement, regardless of modality (text, image, video, audio).

    Future implementations:
    - TextEmbeddingService (current: EmbeddingService)
    - ImageEmbeddingService (Phase 2: CLIP, Jina)
    - VideoEmbeddingService (Phase 2)
    - AudioEmbeddingService (Phase 2)

    Design principles:
    - Generic interface for different modalities
    - Consistent API across all services
    - Extensible for future multimodal support
    """

    @abstractmethod
    def embed_single(self, data: Any) -> List[float]:
        """Generate embedding for single data item.

        Args:
            data: Input data to embed (text, image, video, audio)

        Returns:
            Embedding vector as list of floats

        Note:
            Concrete implementations should specify the exact type
            and dimension of the returned vector.
        """
        pass

    @abstractmethod
    def embed_batch(
        self,
        data_items: List[Any],
        batch_size: Optional[int] = None,
        **kwargs
    ) -> List[List[float]]:
        """Generate embeddings for batch of data items.

        Args:
            data_items: List of data items to embed
            batch_size: Batch size for processing
            **kwargs: Additional modality-specific parameters

        Returns:
            List of embedding vectors

        Note:
            Concrete implementations should handle modality-specific
            parameters like normalize, use_gpu, etc.
        """
        pass

    @abstractmethod
    def get_embedding_dimension(self) -> int:
        """Return embedding dimension.

        Returns:
            int: Dimension of embedding vectors

        Note:
            Dimension varies by model:
            - mpnet-base-v2: 768
            - CLIP ViT-B/32: 512
            - Jina v2: 768
        """
        pass
