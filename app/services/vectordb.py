"""Vector database service for managing vector storage in Qdrant.

This module provides the VectorDBService class for managing vector storage
and retrieval operations in Qdrant vector database.

Key Features:
- Async operations with AsyncQdrantClient
- Collection lifecycle management
- Batch vector upsert with rich metadata
- Similarity search with filtering
- 1024-dimensional vector support (matching EmbeddingService)

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
    1024-dimensional embeddings in Qdrant vector database.

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
            vector_size: Dimension of vectors (e.g., 1024 for BGE-M3)
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
        response = await self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            limit=limit
        )
        return response.points

    async def upsert_vectors_hybrid(
        self,
        collection_name: str,
        dense_vectors: List[List[float]],
        sparse_vectors: List[Dict[str, List]],
        payloads: List[Dict[str, Any]],
        ids: List[str]
    ) -> bool:
        """Upsert hybrid embeddings (dense + sparse) with metadata.

        Args:
            collection_name: Name of the collection
            dense_vectors: List of dense vectors (1024-dimensional for BGE-M3)
            sparse_vectors: List of sparse vector dicts with 'indices' and 'values' keys
            payloads: List of metadata dictionaries for each vector
            ids: List of unique IDs for each vector

        Returns:
            True if upsert successful

        Note:
            Sparse embeddings are stored in the payload as 'sparse_embedding' field.
            This enables hybrid search by combining dense vector similarity with
            sparse matching (BM25-like) for improved retrieval accuracy.
        """
        points = [
            PointStruct(
                id=point_id,
                vector=dense_vec,
                payload={
                    **payload,
                    "sparse_embedding": sparse_vec  # Store sparse in payload
                }
            )
            for point_id, dense_vec, sparse_vec, payload 
            in zip(ids, dense_vectors, sparse_vectors, payloads)
        ]

        await self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        return True

    async def search_vectors_hybrid(
        self,
        collection_name: str,
        query_dense: List[float],
        query_sparse: Dict[str, List],
        limit: int = 10,
        alpha: float = 0.7
    ) -> List:
        """Hybrid search combining dense vector similarity and sparse matching.

        Args:
            collection_name: Name of the collection to search
            query_dense: Dense query vector (1024-dimensional for BGE-M3)
            query_sparse: Sparse query dict with 'indices' and 'values' keys
            limit: Maximum number of results to return
            alpha: Weight for dense score (0-1). sparse_weight = 1 - alpha.
                   Default 0.7 means 70% dense, 30% sparse.

        Returns:
            List of results, re-ranked by hybrid score

        Note:
            Hybrid retrieval typically improves accuracy by 10-15% over dense-only.
            The algorithm:
            1. Perform dense vector search (get top 2*limit results)
            2. Calculate sparse similarity for each result
            3. Combine scores: final = alpha * dense + (1-alpha) * sparse
            4. Re-rank and return top K
        """
        # Step 1: Dense vector search (get more results for re-ranking)
        dense_response = await self.client.query_points(
            collection_name=collection_name,
            query=query_dense,
            limit=limit * 2  # Get more candidates for re-ranking
        )
        
        # Step 2: Calculate sparse similarity and combine scores
        results_with_hybrid_score = []
        
        for point in dense_response.points:
            # Get dense score (already calculated by Qdrant)
            dense_score = point.score
            
            # Calculate sparse similarity
            if "sparse_embedding" in point.payload:
                doc_sparse = point.payload["sparse_embedding"]
                sparse_score = self._calculate_sparse_similarity(
                    query_sparse, doc_sparse
                )
            else:
                sparse_score = 0.0
            
            # Combine scores with alpha weighting
            hybrid_score = alpha * dense_score + (1 - alpha) * sparse_score
            
            # Create new result with hybrid score
            point.score = hybrid_score  # Update score
            results_with_hybrid_score.append(point)
        
        # Step 3: Re-rank by hybrid score and return top K
        results_with_hybrid_score.sort(key=lambda x: x.score, reverse=True)
        
        return results_with_hybrid_score[:limit]

    def _calculate_sparse_similarity(
        self,
        query_sparse: Dict[str, List],
        doc_sparse: Dict[str, List]
    ) -> float:
        """Calculate similarity between sparse embeddings (dot product).

        Args:
            query_sparse: Query sparse embedding with 'indices' and 'values'
            doc_sparse: Document sparse embedding with 'indices' and 'values'

        Returns:
            Sparse similarity score (0-1 range after normalization)

        Note:
            Uses dot product on overlapping indices (BM25-like scoring).
        """
        query_indices = set(query_sparse["indices"])
        doc_indices = set(doc_sparse["indices"])
        
        # Find overlapping indices
        overlap = query_indices.intersection(doc_indices)
        
        if not overlap:
            return 0.0
        
        # Calculate dot product on overlapping terms
        query_dict = {idx: val for idx, val in zip(
            query_sparse["indices"], query_sparse["values"])}
        doc_dict = {idx: val for idx, val in zip(
            doc_sparse["indices"], doc_sparse["values"])}
        
        dot_product = sum(
            query_dict[idx] * doc_dict[idx] 
            for idx in overlap
        )
        
        # Normalize (optional, helps keep scores in 0-1 range)
        # Using simple normalization by max possible overlap
        max_score = max(len(query_indices), len(doc_indices))
        normalized_score = dot_product / max_score if max_score > 0 else 0.0
        
        return normalized_score
