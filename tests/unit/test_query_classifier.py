"""Unit tests for QueryClassifier service.

This module tests the query classification functionality using LLM-based
classification for routing queries to appropriate handlers.
"""

import pytest
from app.services.query_router import QueryClassifier, QueryType


class TestQueryClassifierInit:
    """Test QueryClassifier initialization."""

    def test_init_with_llm_client(self):
        """Should successfully initialize with LLM client."""
        from unittest.mock import Mock

        mock_llm = Mock()
        classifier = QueryClassifier(llm_client=mock_llm)

        assert classifier.llm_client == mock_llm
        assert classifier is not None


@pytest.mark.asyncio
class TestQueryClassifierClassify:
    """Test QueryClassifier classify method."""

    async def test_classify_rag_query(self):
        """Should classify document-specific query as RAG type."""
        from unittest.mock import AsyncMock

        # Setup mock LLM that returns classification
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = """{"query_type": "rag", "confidence": 0.95, "reasoning": "Query asks about specific documents"}"""

        classifier = QueryClassifier(llm_client=mock_llm)

        # Classify a RAG query
        result = await classifier.classify("What does the Q4 report say about revenue?")

        assert result.query_type == QueryType.RAG
        assert result.confidence == 0.95
        assert "documents" in result.reasoning.lower()

    async def test_classify_direct_query(self):
        """Should classify general knowledge query as DIRECT type."""
        from unittest.mock import AsyncMock

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = """{"query_type": "direct", "confidence": 0.98, "reasoning": "General knowledge question"}"""

        classifier = QueryClassifier(llm_client=mock_llm)

        result = await classifier.classify("What is the capital of France?")

        assert result.query_type == QueryType.DIRECT
        assert result.confidence == 0.98
        assert "knowledge" in result.reasoning.lower()

    async def test_classify_clarification_query(self):
        """Should classify ambiguous query as CLARIFICATION type."""
        from unittest.mock import AsyncMock

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = """{"query_type": "clarification", "confidence": 0.92, "reasoning": "Vague reference needs clarification"}"""

        classifier = QueryClassifier(llm_client=mock_llm)

        result = await classifier.classify("Tell me more")

        assert result.query_type == QueryType.CLARIFICATION
        assert result.confidence == 0.92
        assert "clarification" in result.reasoning.lower()

    async def test_classify_multi_hop_query(self):
        """Should classify comparison query as MULTI_HOP type."""
        from unittest.mock import AsyncMock

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = """{"query_type": "multi_hop", "confidence": 0.90, "reasoning": "Requires comparing multiple documents"}"""

        classifier = QueryClassifier(llm_client=mock_llm)

        result = await classifier.classify("Compare contract A and contract B pricing")

        assert result.query_type == QueryType.MULTI_HOP
        assert result.confidence == 0.90
        assert "compar" in result.reasoning.lower()
