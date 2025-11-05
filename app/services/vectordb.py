"""Vector database service for managing vector storage in Qdrant.

This module provides the VectorDBService class for managing vector storage
and retrieval operations in Qdrant vector database.

Key Features:
- Async operations with AsyncQdrantClient
- Collection lifecycle management with dynamic dimensions
- Batch vector upsert with rich metadata
- Similarity search with filtering
- Auto-detection of embedding dimensions from EmbeddingService
- Auto-migration when embedding dimensions change

Date: 2025-11-05 (Updated with auto-migration)
"""

from typing import Optional, List, Dict, Any
from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
import logging
import uuid
import re

logger = logging.getLogger(__name__)


# Helper functions for collection naming
def format_collection_name_with_dimension(base_name: str, dimension: int) -> str:
    """Format collection name with dimension suffix.

    Args:
        base_name: Base collection name
        dimension: Vector dimension

    Returns:
        Collection name with dimension suffix (e.g., "docs_1024")
    """
    return f"{base_name}_{dimension}"


def parse_collection_dimension(collection_name: str) -> Optional[int]:
    """Parse dimension from collection name.

    Args:
        collection_name: Collection name (e.g., "docs_1024")

    Returns:
        Dimension if found in name, None otherwise
    """
    # Match pattern: _<number> at the end
    match = re.search(r'_(\d+)$', collection_name)
    if match:
        return int(match.group(1))
    return None


def get_collection_name_for_model(
    base_name: str,
    model_name: str,
    dimension: int
) -> str:
    """Generate collection name including model info and dimension.

    Args:
        base_name: Base collection name
        model_name: Model name (e.g., "BAAI/bge-m3")
        dimension: Vector dimension

    Returns:
        Collection name with model and dimension (e.g., "docs_bge_m3_1024")
    """
    # Extract model short name and sanitize
    model_short = model_name.split('/')[-1]
    model_short = re.sub(r'[^a-z0-9]+', '_', model_short.lower())
    model_short = model_short.strip('_')

    return f"{base_name}_{model_short}_{dimension}"


class VectorDBService:
    """Service for managing vector storage in Qdrant.

    This service provides async operations for storing and retrieving
    embeddings in Qdrant vector database with dynamic dimension support.

    Attributes:
        url (str): Qdrant server URL
        api_key (Optional[str]): API key for authentication
        client (AsyncQdrantClient): Async Qdrant client instance

    Example:
        >>> service = VectorDBService(url="http://localhost:6333")
        >>> await service.ensure_collection_with_embeddings(
        ...     "my_collection", embedding_service
        ... )
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

    async def ensure_collection_with_dimension(
        self,
        collection_name: str,
        vector_size: int,
        distance: str = "cosine",
        recreate_if_mismatch: bool = False,
        auto_migrate: bool = False
    ) -> Dict[str, Any]:
        """Ensure collection exists with correct dimension.

        This method intelligently handles dimension mismatches:
        1. If collection doesn't exist: create it
        2. If collection exists with same dimension: accept it
        3. If dimension mismatch and auto_migrate=True: create new collection with dimension suffix
        4. If dimension mismatch and recreate_if_mismatch=True: delete and recreate (loses data!)
        5. Otherwise: raise ValueError

        Args:
            collection_name: Name of the collection
            vector_size: Expected vector dimension
            distance: Distance metric ("cosine", "dot", or "euclidean")
            recreate_if_mismatch: If True, recreate collection on dimension mismatch (DELETES DATA!)
            auto_migrate: If True, create new collection with dimension suffix on mismatch

        Returns:
            Dictionary with status information:
            {
                "action": "created" | "exists" | "recreated" | "created_new",
                "dimension": int,
                "points_deleted": int (only if recreated),
                "new_collection_name": str (only if created_new),
                "old_collection_name": str (only if created_new)
            }

        Raises:
            ValueError: If collection exists with wrong dimension and no migration flag set
        """
        exists = await self.collection_exists(collection_name)

        if not exists:
            # Create new collection
            await self.create_collection(collection_name, vector_size, distance)
            logger.info(
                f"Created collection '{collection_name}' with dimension {vector_size}")
            return {"action": "created", "dimension": vector_size}

        # Collection exists - check dimension
        collection_info = await self.get_collection_info(collection_name)
        current_dimension = collection_info.config.params.vectors.size

        if current_dimension == vector_size:
            # Dimension matches - all good!
            logger.info(
                f"Collection '{collection_name}' exists with correct dimension {vector_size}")
            return {"action": "exists", "dimension": vector_size}

        # Dimension mismatch!
        logger.warning(
            f"Dimension mismatch in collection '{collection_name}': "
            f"existing={current_dimension}, requested={vector_size}"
        )

        # Option 1: Auto-migrate (create new collection with dimension suffix)
        if auto_migrate:
            new_collection_name = format_collection_name_with_dimension(
                collection_name, vector_size)

            # Check if new collection already exists
            new_exists = await self.collection_exists(new_collection_name)
            if not new_exists:
                await self.create_collection(new_collection_name, vector_size, distance)
                logger.info(
                    f"Created new collection '{new_collection_name}' with dimension {vector_size} "
                    f"(old collection '{collection_name}' with dimension {current_dimension} preserved)"
                )

            return {
                "action": "created_new",
                "dimension": vector_size,
                "new_collection_name": new_collection_name,
                "old_collection_name": collection_name
            }

        # Option 2: Recreate collection (DELETES DATA!)
        if recreate_if_mismatch:
            points_count = collection_info.points_count
            logger.warning(
                f"Recreating collection '{collection_name}': "
                f"dimension mismatch ({current_dimension} → {vector_size}). "
                f"Deleting {points_count} existing points!"
            )

            await self.delete_collection(collection_name)
            await self.create_collection(collection_name, vector_size, distance)

            return {
                "action": "recreated",
                "dimension": vector_size,
                "points_deleted": points_count
            }

        # No migration option set - raise error with helpful message
        raise ValueError(
            f"Collection '{collection_name}' exists with dimension {current_dimension}, "
            f"but current embedding model uses dimension {vector_size}. "
            f"Options:\n"
            f"1. Use a different collection name\n"
            f"2. Switch back to the original embedding model\n"
            f"3. Delete the collection manually: await vectordb_service.delete_collection('{collection_name}')\n"
            f"4. Set auto_migrate=True to create new collection '{collection_name}_{vector_size}'\n"
            f"5. Set recreate_if_mismatch=True (WARNING: deletes all {collection_info.points_count} points)"
        )

    async def migrate_collection(
        self,
        old_collection_name: str,
        new_collection_name: str,
        embedding_service,
        batch_size: int = 100
    ) -> Dict[str, Any]:
        """Migrate points from old collection to new collection with re-embedding.

        This method:
        1. Retrieves all points from old collection
        2. Re-embeds texts using new embedding model
        3. Inserts points into new collection
        4. Preserves all metadata

        Args:
            old_collection_name: Source collection name
            new_collection_name: Destination collection name (must already exist)
            embedding_service: Embedding service for re-embedding
            batch_size: Number of points to process per batch

        Returns:
            Dictionary with migration statistics:
            {
                "points_migrated": int,
                "old_collection": str,
                "new_collection": str
            }
        """
        logger.info(
            f"Starting migration from '{old_collection_name}' to '{new_collection_name}'")

        total_migrated = 0
        offset = None

        while True:
            # Retrieve batch of points from old collection
            points, next_offset = await self.client.scroll(
                collection_name=old_collection_name,
                limit=batch_size,
                offset=offset,
                with_payload=True,
                with_vectors=True
            )

            if not points:
                break

            # Extract texts for re-embedding
            texts = [point.payload.get("text", "") for point in points]

            # Re-embed with new model
            new_embeddings = embedding_service.embed_batch(texts)

            # Prepare points for new collection
            new_points = [
                PointStruct(
                    id=str(point.id),
                    vector=new_embedding,
                    payload=point.payload
                )
                for point, new_embedding in zip(points, new_embeddings)
            ]

            # Insert into new collection
            await self.client.upsert(
                collection_name=new_collection_name,
                points=new_points
            )

            total_migrated += len(points)
            logger.info(f"Migrated {total_migrated} points...")

            # Check if there are more points
            if next_offset is None:
                break

            offset = next_offset

        logger.info(
            f"Migration complete: {total_migrated} points migrated from "
            f"'{old_collection_name}' to '{new_collection_name}'"
        )

        return {
            "points_migrated": total_migrated,
            "old_collection": old_collection_name,
            "new_collection": new_collection_name
        }

    async def upsert_vectors(
        self,
        collection_name: str,
        vectors: List[List[float]],
        payloads: List[Dict[str, Any]],
        ids: Optional[List[str]] = None
    ) -> bool:
        """Upsert vectors with metadata.

        Args:
            collection_name: Name of the collection
            vectors: List of vectors (each vector is a list of floats)
            payloads: List of metadata dictionaries for each vector
            ids: List of unique IDs for each vector. If None, UUIDs will be generated.

        Returns:
            True if upsert successful
        """
        # Generate UUIDs if ids not provided
        if ids is None:
            ids = [str(uuid.uuid4()) for _ in range(len(vectors))]

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
