"""Query classification service.
"""

import json
import logging
from enum import Enum
from pydantic import BaseModel, Field
from app.services.query_router.prompts import build_classification_prompt

logger = logging.getLogger(__name__)


class QueryType(Enum):
    """Query types for routing."""

    RAG = "rag"
    DIRECT = "direct"
    CLARIFICATION = "clarification"
    MULTI_HOP = "multi_hop"


class QueryClassification(BaseModel):
    """Classification result."""

    query_type: QueryType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


class QueryClassifier:
    """Service for classifying queries."""

    def __init__(self, llm_client):
        self.llm_client = llm_client
        logger.info("Initialized QueryClassifier")

    async def classify(self, query: str) -> QueryClassification:
        """Classify a query.

        Args:
            query: User query string

        Returns:
            QueryClassification with type, confidence, and reasoning
        """
        # Build prompt with few-shot examples
        prompt = build_classification_prompt(query)

        # Call LLM to classify
        response = await self.llm_client.generate(
            prompt=prompt,
            temperature=0.1,  # Low temperature for consistent classification
            max_tokens=150
        )

        # Parse JSON response
        data = json.loads(response)

        # Create classification object
        return QueryClassification(
            query_type=QueryType(data["query_type"]),
            confidence=data["confidence"],
            reasoning=data["reasoning"]
        )
