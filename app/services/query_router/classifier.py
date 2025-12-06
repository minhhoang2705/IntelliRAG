"""Query classification service.
"""

import json
import logging
import re
import time
from enum import Enum
from pydantic import BaseModel, Field
from opentelemetry import trace
from app.services.query_router.prompts import build_classification_prompt
from app.api.middleware.metrics import (
    query_classification_total,
    query_classification_confidence,
    query_classification_duration_seconds
)

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
        # Get tracer for instrumentation
        tracer = trace.get_tracer(__name__)

        with tracer.start_as_current_span("query.classify"):
            # Start timing for metrics
            start_time = time.time()

            # Build prompt with few-shot examples
            prompt = build_classification_prompt(query)

            # Call LLM to classify
            response = await self.llm_client.generate(
                prompt=prompt,
                temperature=0.1,  # Low temperature for consistent classification
                max_tokens=250  # Increased to allow for complete JSON response
            )

            # Parse JSON response with error handling
            # First, clean up response: remove thinking tags
            cleaned_response = response.strip()
            cleaned_response = re.sub(
                r'<think>.*?</think>', '', cleaned_response, flags=re.DOTALL)
            cleaned_response = cleaned_response.strip()

            try:
                # First try: direct JSON parse
                data = json.loads(cleaned_response)
            except json.JSONDecodeError:
                # Second try: extract JSON from markdown code blocks
                json_match = re.search(
                    r'```(?:json)?\s*(\{.*?\})\s*```', cleaned_response, re.DOTALL)
                if json_match:
                    try:
                        data = json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        # Third try: find any JSON-like structure
                        json_match = re.search(
                            r'\{[^{}]*"query_type"[^{}]*\}', cleaned_response)
                        if json_match:
                            data = json.loads(json_match.group(0))
                        else:
                            raise ValueError(
                                f"Could not extract valid JSON from response: {response[:200]}")
                else:
                    # Third try: find any JSON-like structure
                    json_match = re.search(
                        r'\{[^{}]*"query_type"[^{}]*\}', cleaned_response)
                    if json_match:
                        data = json.loads(json_match.group(0))
                    else:
                        raise ValueError(
                            f"Could not extract valid JSON from response: {response[:200]}")

            # Create classification object
            classification = QueryClassification(
                query_type=QueryType(data["query_type"]),
                confidence=data["confidence"],
                reasoning=data["reasoning"]
            )

            # Record metrics
            duration = time.time() - start_time
            query_classification_duration_seconds.observe(duration)
            query_classification_confidence.observe(classification.confidence)
            query_classification_total.labels(
                query_type=classification.query_type.value
            ).inc()

            return classification
