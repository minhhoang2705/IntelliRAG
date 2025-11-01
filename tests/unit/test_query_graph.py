"""Unit tests for LangGraph query routing state machine.

This module tests the state graph that orchestrates query routing
based on classification results.
"""

import pytest
from typing import Optional, List


class TestQueryGraphBuilding:
    """Test state graph construction."""

    def test_build_query_graph(self):
        """Should successfully build query routing graph."""
        from app.services.query_router.graph import build_query_graph

        # Build the graph
        graph = build_query_graph()

        # Verify graph is created
        assert graph is not None
        assert hasattr(graph, 'invoke')

    def test_graph_has_all_nodes(self):
        """Should have all required nodes."""
        from app.services.query_router.graph import build_query_graph

        graph = build_query_graph()

        # Access nodes via graph structure
        nodes = graph.nodes
        assert "classify" in nodes
        assert "retrieve" in nodes
        assert "generate" in nodes
        assert "clarify" in nodes

    @pytest.mark.asyncio
    async def test_graph_routes_rag_query_to_retrieve(self):
        """Should route RAG queries through retrieve path."""
        from app.services.query_router.graph import build_query_graph, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock, MagicMock

        # Build graph
        graph = build_query_graph()

        # Create mocked services
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.RAG,
            confidence=0.9,
            reasoning="Needs documents"
        )

        mock_vectordb = AsyncMock()
        mock_result = MagicMock()
        mock_result.payload = {"text": "Policy document context"}
        mock_vectordb.search_vectors.return_value = [mock_result]

        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Based on the policy..."

        # Create initial state
        state: QueryState = {
            "query": "What does the policy say?",
            "classification": None,
            "context": None,
            "response": None,
            "error": None
        }

        # Execute graph with all services in config
        result = await graph.ainvoke(
            state,
            config={
                "configurable": {
                    "classifier": mock_classifier,
                    "vectordb": mock_vectordb,
                    "llm": mock_llm
                }
            }
        )

        # Verify classification happened
        assert result["classification"] is not None
        assert result["classification"].query_type == QueryType.RAG

        # Verify complete RAG flow: classify → retrieve → generate → END
        assert result["classification"] is not None, "Step 1: Classification should occur"
        assert result["classification"].query_type == QueryType.RAG, "Should be classified as RAG"
        assert result["context"] is not None, "Step 2: Context should be retrieved"
        assert len(result["context"]) > 0, "Retrieved context should not be empty"
        assert result["response"] is not None, "Step 3: Response should be generated"
        assert "policy" in result["response"].lower(), "Response should use retrieved context"
        assert result["error"] is None, "No errors should occur"


@pytest.mark.asyncio
class TestQueryGraphNodes:
    """Test individual graph nodes."""

    async def test_retrieve_node(self):
        """Should retrieve context from vector database."""
        from app.services.query_router.graph import retrieve_node, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock, MagicMock

        # Create mock VectorDB service
        mock_vectordb = AsyncMock()
        mock_result = MagicMock()
        mock_result.payload = {"text": "Sample context"}
        mock_result.score = 0.95
        mock_vectordb.search_vectors.return_value = [mock_result]

        # Create state
        state: QueryState = {
            "query": "What is the revenue?",
            "classification": QueryClassification(
                query_type=QueryType.RAG,
                confidence=0.95,
                reasoning="Needs document retrieval"
            ),
            "context": None,
            "response": None,
            "error": None
        }

        # Call retrieve node with mocked service via config
        result = await retrieve_node(state, config={"configurable": {"vectordb": mock_vectordb}})

        # Verify context was added
        assert result["context"] is not None
        assert len(result["context"]) > 0
        assert "Sample context" in result["context"][0]

    async def test_generate_node_with_context(self):
        """Should generate response using LLM with context."""
        from app.services.query_router.graph import generate_node, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock

        # Create mock LLM service
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "The revenue was $10M"

        # Create state with context
        state: QueryState = {
            "query": "What is the revenue?",
            "classification": QueryClassification(
                query_type=QueryType.RAG,
                confidence=0.95,
                reasoning="Needs document retrieval"
            ),
            "context": ["Q4 revenue: $10M", "Growth: 20%"],
            "response": None,
            "error": None
        }

        # Call generate node with config
        result = await generate_node(state, config={"configurable": {"llm": mock_llm}})

        # Verify response was generated
        assert result["response"] is not None
        assert len(result["response"]) > 0
        assert "revenue" in result["response"].lower()

    async def test_classify_node_integration(self):
        """Should integrate with QueryClassifier to classify queries."""
        from app.services.query_router.graph import classify_node, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock

        # Create mock QueryClassifier
        mock_classifier = AsyncMock()
        mock_classification = QueryClassification(
            query_type=QueryType.RAG,
            confidence=0.92,
            reasoning="Query asks about document-specific information"
        )
        mock_classifier.classify.return_value = mock_classification

        # Create initial state (no classification)
        state: QueryState = {
            "query": "What does the privacy policy say about data retention?",
            "classification": None,
            "context": None,
            "response": None,
            "error": None
        }

        # Call classify node with mocked classifier via config
        result = await classify_node(state, config={"configurable": {"classifier": mock_classifier}})

        # Verify classification was added to state
        assert result["classification"] is not None
        assert result["classification"].query_type == QueryType.RAG
        assert result["classification"].confidence == 0.92
        assert result["error"] is None

        # Verify classifier was called with the query
        mock_classifier.classify.assert_called_once_with("What does the privacy policy say about data retention?")

    async def test_classify_node_error_handling(self):
        """Should handle classification errors gracefully."""
        from app.services.query_router.graph import classify_node, QueryState
        from unittest.mock import AsyncMock

        # Create mock QueryClassifier that raises an exception
        mock_classifier = AsyncMock()
        mock_classifier.classify.side_effect = Exception("LLM service unavailable")

        # Create initial state
        state: QueryState = {
            "query": "What is the revenue?",
            "classification": None,
            "context": None,
            "response": None,
            "error": None
        }

        # Call classify node with config
        result = await classify_node(state, config={"configurable": {"classifier": mock_classifier}})

        # Verify error was captured
        assert result["error"] is not None
        assert "Classification failed" in result["error"]
        assert result["classification"] is None

    async def test_clarify_node(self):
        """Should handle ambiguous queries requiring clarification."""
        from app.services.query_router.graph import clarify_node, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType

        # Create state with clarification classification
        state: QueryState = {
            "query": "Tell me more",
            "classification": QueryClassification(
                query_type=QueryType.CLARIFICATION,
                confidence=0.95,
                reasoning="Vague query needs clarification"
            ),
            "context": None,
            "response": None,
            "error": None
        }

        # Call clarify node
        result = await clarify_node(state)

        # Verify clarification response was generated
        assert result["response"] is not None
        assert "clarify" in result["response"].lower() or "more details" in result["response"].lower()
        assert result["error"] is None


class TestConditionalRouting:
    """Test conditional routing logic."""

    def test_route_query_rag(self):
        """Should route RAG queries to retrieve path."""
        from app.services.query_router.graph import route_query, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType

        state: QueryState = {
            "query": "What does the policy say?",
            "classification": QueryClassification(
                query_type=QueryType.RAG,
                confidence=0.9,
                reasoning="Needs document retrieval"
            ),
            "context": None,
            "response": None,
            "error": None
        }

        result = route_query(state)
        assert result == "retrieve"

    def test_route_query_direct(self):
        """Should route DIRECT queries to generate path."""
        from app.services.query_router.graph import route_query, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType

        state: QueryState = {
            "query": "What is Python?",
            "classification": QueryClassification(
                query_type=QueryType.DIRECT,
                confidence=0.95,
                reasoning="General knowledge"
            ),
            "context": None,
            "response": None,
            "error": None
        }

        result = route_query(state)
        assert result == "generate"

    def test_route_query_clarification(self):
        """Should route CLARIFICATION queries to clarify path."""
        from app.services.query_router.graph import route_query, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType

        state: QueryState = {
            "query": "Tell me more",
            "classification": QueryClassification(
                query_type=QueryType.CLARIFICATION,
                confidence=0.9,
                reasoning="Ambiguous"
            ),
            "context": None,
            "response": None,
            "error": None
        }

        result = route_query(state)
        assert result == "clarify"

    def test_route_query_multi_hop(self):
        """Should route MULTI_HOP queries to retrieve path."""
        from app.services.query_router.graph import route_query, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType

        state: QueryState = {
            "query": "Compare Q3 and Q4 revenue",
            "classification": QueryClassification(
                query_type=QueryType.MULTI_HOP,
                confidence=0.85,
                reasoning="Requires multiple documents"
            ),
            "context": None,
            "response": None,
            "error": None
        }

        result = route_query(state)
        assert result == "retrieve"


@pytest.mark.asyncio
class TestEndToEndGraphFlows:
    """Test complete end-to-end graph execution for all query types."""

    async def test_complete_rag_flow(self):
        """Test complete RAG flow: classify → retrieve → generate → END."""
        from app.services.query_router.graph import build_query_graph, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock, MagicMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier for RAG query
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.RAG,
            confidence=0.92,
            reasoning="Query requires document retrieval"
        )

        # Mock VectorDB service
        mock_vectordb = AsyncMock()
        mock_result = MagicMock()
        mock_result.payload = {"text": "Q4 revenue was $10 million with 20% growth"}
        mock_vectordb.search_vectors.return_value = [mock_result]

        # Mock LLM service
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Based on the Q4 report, revenue was $10 million with 20% growth."

        # Execute complete RAG flow
        result = await graph.ainvoke(
            {
                "query": "What was our Q4 revenue?",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier,
                    "vectordb": mock_vectordb,
                    "llm": mock_llm
                }
            }
        )

        # Verify complete flow
        assert result["classification"].query_type == QueryType.RAG
        assert result["context"] is not None and len(result["context"]) > 0
        assert result["response"] is not None
        assert "revenue" in result["response"].lower()
        assert result["error"] is None

    async def test_complete_direct_flow(self):
        """Test complete DIRECT flow: classify → generate → END."""
        from app.services.query_router.graph import build_query_graph, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier for DIRECT query
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.98,
            reasoning="General knowledge question"
        )

        # Mock LLM service
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Python is a high-level programming language."

        # Execute complete DIRECT flow
        result = await graph.ainvoke(
            {
                "query": "What is Python?",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier,
                    "llm": mock_llm
                }
            }
        )

        # Verify complete flow (no retrieval for DIRECT)
        assert result["classification"].query_type == QueryType.DIRECT
        assert result["context"] is None  # No retrieval step
        assert result["response"] is not None
        assert "Python" in result["response"]
        assert result["error"] is None

    async def test_complete_clarification_flow(self):
        """Test complete CLARIFICATION flow: classify → clarify → END."""
        from app.services.query_router.graph import build_query_graph, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier for CLARIFICATION query
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.CLARIFICATION,
            confidence=0.95,
            reasoning="Query is ambiguous and needs clarification"
        )

        # Execute complete CLARIFICATION flow
        result = await graph.ainvoke(
            {
                "query": "Tell me more",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier
                }
            }
        )

        # Verify complete flow
        assert result["classification"].query_type == QueryType.CLARIFICATION
        assert result["context"] is None  # No retrieval
        assert result["response"] is not None
        assert "more details" in result["response"].lower() or "clarify" in result["response"].lower()
        assert result["error"] is None

    async def test_complete_multi_hop_flow(self):
        """Test complete MULTI_HOP flow: classify → retrieve → generate → END."""
        from app.services.query_router.graph import build_query_graph, QueryState
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock, MagicMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier for MULTI_HOP query
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.MULTI_HOP,
            confidence=0.88,
            reasoning="Requires comparing multiple documents"
        )

        # Mock VectorDB service with multiple documents
        mock_vectordb = AsyncMock()
        mock_result1 = MagicMock()
        mock_result1.payload = {"text": "Q3 revenue: $8M"}
        mock_result2 = MagicMock()
        mock_result2.payload = {"text": "Q4 revenue: $10M"}
        mock_vectordb.search_vectors.return_value = [mock_result1, mock_result2]

        # Mock LLM service
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "Q4 revenue ($10M) was 25% higher than Q3 revenue ($8M)."

        # Execute complete MULTI_HOP flow
        result = await graph.ainvoke(
            {
                "query": "Compare Q3 and Q4 revenue",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier,
                    "vectordb": mock_vectordb,
                    "llm": mock_llm
                }
            }
        )

        # Verify complete flow (same as RAG but with multiple docs)
        assert result["classification"].query_type == QueryType.MULTI_HOP
        assert result["context"] is not None
        assert len(result["context"]) >= 2  # Multiple documents retrieved
        assert result["response"] is not None
        assert "revenue" in result["response"].lower()
        assert result["error"] is None

    async def test_error_handling_classification_failure(self):
        """Test E2E flow when classification step fails."""
        from app.services.query_router.graph import build_query_graph
        from unittest.mock import AsyncMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier that raises exception
        mock_classifier = AsyncMock()
        mock_classifier.classify.side_effect = Exception("LLM service timeout")

        # Execute flow with classification error
        result = await graph.ainvoke(
            {
                "query": "What is the revenue?",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier
                }
            }
        )

        # Verify error was captured and flow terminated
        assert result["error"] is not None
        assert "Classification failed" in result["error"]
        assert result["classification"] is None
        assert result["response"] is None

    async def test_error_handling_retrieval_failure(self):
        """Test E2E flow when retrieval step fails."""
        from app.services.query_router.graph import build_query_graph
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier for RAG query
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.RAG,
            confidence=0.9,
            reasoning="Needs retrieval"
        )

        # Mock VectorDB that raises exception
        mock_vectordb = AsyncMock()
        mock_vectordb.search_vectors.side_effect = Exception("Database connection failed")

        # Execute flow with retrieval error
        result = await graph.ainvoke(
            {
                "query": "What is the policy?",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier,
                    "vectordb": mock_vectordb
                }
            }
        )

        # Verify error was captured
        assert result["error"] is not None
        assert "Retrieval failed" in result["error"]
        assert result["classification"].query_type == QueryType.RAG
        assert result["context"] is None
        assert result["response"] is None

    async def test_error_handling_generation_failure(self):
        """Test E2E flow when generation step fails."""
        from app.services.query_router.graph import build_query_graph
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock, MagicMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier for RAG query
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.RAG,
            confidence=0.9,
            reasoning="Needs retrieval"
        )

        # Mock VectorDB with valid results
        mock_vectordb = AsyncMock()
        mock_result = MagicMock()
        mock_result.payload = {"text": "Sample context"}
        mock_vectordb.search_vectors.return_value = [mock_result]

        # Mock LLM that raises exception
        mock_llm = AsyncMock()
        mock_llm.generate.side_effect = Exception("LLM generation timeout")

        # Execute flow with generation error
        result = await graph.ainvoke(
            {
                "query": "What is the policy?",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier,
                    "vectordb": mock_vectordb,
                    "llm": mock_llm
                }
            }
        )

        # Verify error was captured but retrieval succeeded
        assert result["error"] is not None
        assert "Generation failed" in result["error"]
        assert result["classification"].query_type == QueryType.RAG
        assert result["context"] is not None  # Retrieval succeeded
        assert result["response"] is None  # Generation failed

    async def test_edge_case_empty_retrieval_results(self):
        """Test E2E flow when vector search returns no results."""
        from app.services.query_router.graph import build_query_graph
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier for RAG query
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.RAG,
            confidence=0.85,
            reasoning="Needs retrieval"
        )

        # Mock VectorDB returning empty results
        mock_vectordb = AsyncMock()
        mock_vectordb.search_vectors.return_value = []

        # Mock LLM
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "I don't have information about that in the documents."

        # Execute flow with no retrieval results
        result = await graph.ainvoke(
            {
                "query": "What is the policy on Mars colonization?",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier,
                    "vectordb": mock_vectordb,
                    "llm": mock_llm
                }
            }
        )

        # Verify flow completes with empty context
        assert result["classification"].query_type == QueryType.RAG
        assert result["context"] is not None
        assert len(result["context"]) == 0  # Empty results
        assert result["response"] is not None
        assert result["error"] is None

    async def test_edge_case_low_confidence_classification(self):
        """Test E2E flow with low confidence classification."""
        from app.services.query_router.graph import build_query_graph
        from app.services.query_router.classifier import QueryClassification, QueryType
        from unittest.mock import AsyncMock

        # Build graph
        graph = build_query_graph()

        # Mock classifier with low confidence
        mock_classifier = AsyncMock()
        mock_classifier.classify.return_value = QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.55,  # Low confidence
            reasoning="Uncertain classification"
        )

        # Mock LLM
        mock_llm = AsyncMock()
        mock_llm.generate.return_value = "General answer with uncertainty."

        # Execute flow with low confidence
        result = await graph.ainvoke(
            {
                "query": "Explain things",
                "classification": None,
                "context": None,
                "response": None,
                "error": None
            },
            config={
                "configurable": {
                    "classifier": mock_classifier,
                    "llm": mock_llm
                }
            }
        )

        # Verify flow completes despite low confidence
        assert result["classification"].query_type == QueryType.DIRECT
        assert result["classification"].confidence == 0.55
        assert result["response"] is not None
        assert result["error"] is None
