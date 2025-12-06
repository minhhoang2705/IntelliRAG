"""QueryRouterService - High-level wrapper for LangGraph query router.
"""

from app.services.query_router.graph import build_query_graph
from app.services.query_router.classifier import QueryClassification, QueryType


class QueryRouterService:
    """High-level service for routing queries through LangGraph state machine."""

    def __init__(self, classifier, vectordb, llm, embedding):
        """Initialize with required services."""
        self.classifier = classifier
        self.vectordb = vectordb
        self.llm = llm
        self.embedding = embedding
        self.graph = build_query_graph()

    async def route_query(self, query: str, collection_name: str, force_rag: bool = False):
        """Route query through LangGraph state machine.

        Args:
            query: User query text
            collection_name: Vector DB collection name
            force_rag: If True, force RAG retrieval regardless of classification

        Returns:
            State dict with response, context, classification, and error
        """
        # Initialize state
        state = {
            "query": query,
            "classification": None,
            "context": None,
            "response": None,
            "error": None
        }

        # If force_rag is True, skip classification and set it to RAG
        if force_rag:
            state["classification"] = QueryClassification(
                query_type=QueryType.RAG,
                confidence=1.0,
                reasoning="User explicitly requested RAG retrieval"
            )

        # Configure with services
        config = {
            "configurable": {
                "classifier": self.classifier,
                "vectordb": self.vectordb,
                "llm": self.llm,
                "embedding": self.embedding,
                "collection_name": collection_name
            }
        }

        # Invoke graph
        result = await self.graph.ainvoke(state, config=config)

        return result
