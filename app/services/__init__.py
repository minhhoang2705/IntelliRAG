"""Services package for IntelliRAG."""
# Base abstract class
from app.services.base_embedding import BaseEmbeddingService
# Embedding service
from app.services.embedding import EmbeddingService

__all__ = ["BaseEmbeddingService", "EmbeddingService"]
