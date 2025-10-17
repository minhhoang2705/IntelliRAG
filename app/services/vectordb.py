"""Vector database service for managing vector storage in Qdrant.

This module provides the VectorDBService class for managing vector storage
and retrieval operations in Qdrant vector database.

Key Features:
- Async operations with AsyncQdrantClient
- Collection lifecycle management
- Batch vector upsert with rich metadata
- Similarity search with filtering
- 768-dimensional vector support (matching EmbeddingService)

Date: 2025-10-16
"""

from typing import Optional, List, Dict, Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import logging

logger = logging.getLogger(__name__)


class VectorDBService:
    """Service for managing vector storage in Qdrant.

    This service provides async operations for storing and retrieving
    768-dimensional embeddings in Qdrant vector database.

    Attributes:
        url (str): Qdrant server URL
        api_key (Optional[str]): API key for authentication
        client (AsyncQdrantClient): Async Qdrant client instance

    Example:
        >>> service = VectorDBService(url="http://localhost:6333")
        >>> # Use async methods for operations
    """

    def __init__(self, url: str, api_key: Optional[str] = None):
        """Initialize vector DB service.

        Args:
            url: Qdrant server URL (e.g., http://localhost:6333)
            api_key: Optional API key for authentication (for Qdrant Cloud)

        Note:
            Client is initialized immediately. For production use with API key,
            ensure URL uses HTTPS to avoid insecure connection warnings.
        """
        self.url = url
        self.api_key = api_key
        self.client = AsyncQdrantClient(url=url, api_key=api_key)
        logger.info(f"Initialized VectorDBService with URL: {url}")

    async def create_collection(
        self,
        collection_name: str,
        vector_size: int,
        distance: str
    ) -> bool:
        """Create a new collection in Qdrant.

        Args:
            collection_name: Name of the collection to create
            vector_size: Dimension of vectors (e.g., 768 for mpnet-base-v2)
            distance: Distance metric ("cosine", "dot", or "euclidean")

        Returns:
            True if collection created successfully
        """
        distance_map = {
            "cosine": Distance.COSINE,
            "dot": Distance.DOT,
            "euclidean": Distance.EUCLID
        }

        if distance not in distance_map:
            raise ValueError(f"Unsupported distance metric: {distance}")

        await self.client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(
                size=vector_size,
                distance=distance_map[distance]
            )
        )
        return True

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if a collection exists."""
        return await self.client.collection_exists(collection_name)

    async def delete_collection(self, collection_name: str) -> bool:
        """Delete a collection."""
        await self.client.delete_collection(collection_name)
        return True

    async def get_collection_info(self, collection_name: str):
        """Get collection information."""
        return await self.client.get_collection(collection_name)

    async def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """Upsert vectors with metadata.

        Args:
            collection_name: Name of the collection
            vectors: List of vectors (each vector is a list of floats)
            payloads: List of metadata dictionaries for each vector
            ids: List of unique IDs for each vector

        Returns:
            True if upsert successful
        """
        points = [
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload
            )
            for point_id, vector, payload in zip(ids, vectors, payloads)
        ]

        await self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        return True

    async def search_vectors(
        self,
        collection_name: str,
        query_vector: List[float],
        limit: int = 10
    ):
        """Search for similar vectors."""
        return await self.client.search(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=limit
        )
