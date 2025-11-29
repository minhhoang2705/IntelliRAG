"""
Query logging service for drift detection.
Captures query metadata for monitoring input distribution shifts.
"""
from datetime import datetime
from typing import Dict, List, Optional
import logging
from app.services.vectordb import VectorDBService
from qdrant_client.models import Distance
import re
import uuid

logger = logging.getLogger(__name__)


class QueryLoggerService:
    """
    Logs query metadata to Qdrant for drift monitoring.
    Stores as separate collection: 'query_logs'
    """

    def __init__(self, vectordb_service: VectorDBService):
        self.vectordb_service = vectordb_service
        self.collection_name = "query_logs"

    async def initialize_collection(self):
        """Initialize query logs collection in Qdrant."""
        try:
            collections = await self.vectordb_service.list_collections()
            if self.collection_name not in collections:
                await self.vectordb_service.create_collection(
                    collection_name=self.collection_name,
                    vector_size=1,  # Dummy vector, we only care about payload
                    distance=Distance.COSINE
                )
                logger.info(f"Created collection: {self.collection_name}")
        except Exception as e:
            logger.error(f"Error initializing query logs collection: {e}")

    async def log_query(
        self,
        query: str,
        response_time_ms: float,
        used_rag: bool,
        sources_count: int = 0,
        answer_length: int = 0,
        query_type: Optional[str] = None
    ):
        """
        Log query metadata for drift detection.

        Args:
            query: User query text
            response_time_ms: Response time in milliseconds
            used_rag: Whether RAG was used
            sources_count: Number of sources retrieved
            answer_length: Length of generated answer
            query_type: Classified query type (factual/conversational/etc.)
        """
        try:
            metadata = {
                "query": query,
                "query_length": len(query),
                "num_words": len(query.split()),
                "num_keywords": self._count_keywords(query),
                "response_time_ms": response_time_ms,
                "used_rag": used_rag,
                "sources_count": sources_count,
                "answer_length": answer_length,
                "query_type": query_type or "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "date": datetime.utcnow().date().isoformat()
            }

            # Store in Qdrant with dummy vector
            point_id = str(uuid.uuid4())
            await self.vectordb_service.upsert_vectors(
                collection_name=self.collection_name,
                vectors=[[0.0]],  # Dummy vector
                payloads=[metadata],
                ids=[point_id]
            )

            logger.debug(f"Logged query metadata: {metadata['query_length']} chars")

        except Exception as e:
            logger.error(f"Error logging query: {e}")

    def _count_keywords(self, query: str) -> int:
        """
        Count meaningful keywords in query (simple heuristic).
        Excludes common stop words.
        """
        stop_words = {
            "a", "an", "the", "is", "are", "was", "were", "be", "been",
            "what", "when", "where", "who", "why", "how", "can", "could",
            "would", "should", "do", "does", "did", "will", "shall",
            "may", "might", "must", "to", "of", "in", "on", "at", "by"
        }

        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        return len(keywords)

    async def get_query_logs(
        self,
        start_date: str,
        end_date: str,
        limit: int = 10000
    ) -> List[Dict]:
        """
        Fetch query logs within date range.

        Args:
            start_date: ISO format date string (YYYY-MM-DD)
            end_date: ISO format date string (YYYY-MM-DD)
            limit: Maximum number of logs to fetch

        Returns:
            List of query log dictionaries
        """
        try:
            # Use client directly for scroll with filter
            
            # For simple date string matching, we can't use Range (numeric only)
            # Instead, fetch all and filter in Python
            filter_condition = None
            
            # Access the underlying client
            results, _ = await self.vectordb_service.client.scroll(
                collection_name=self.collection_name,
                scroll_filter=filter_condition,
                limit=limit,
                with_payload=True,
                with_vectors=False
            )

            logs = []
            for point in results:
                if point.payload:
                    payload_dict = dict(point.payload)
                    # Filter by date range in Python
                    if "date" in payload_dict:
                        point_date = payload_dict["date"]
                        if start_date <= point_date <= end_date:
                            logs.append(payload_dict)

            logger.info(f"Fetched {len(logs)} query logs from {start_date} to {end_date}")
            return logs

        except Exception as e:
            logger.error(f"Error fetching query logs: {e}")
            return []
