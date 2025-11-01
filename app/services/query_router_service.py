"""QueryRouterService - High-level wrapper for LangGraph query router.
"""

from app.services.query_router.graph import build_query_graph
from app.services.query_router.classifier import QueryClassification, QueryType


class QueryRouterService:
    """High-level service for routing queries through LangGraph state machine."""

    def __init__(self, classifier, vectordb, llm):
        """Initialize with required services."""
        self.classifier = classifier
        self.vectordb = vectordb
        self.llm = llm
        self.graph = build_query_graph()

    async def route_query(self, query: str, collection_name: str):
        """Route query through LangGraph state machine."""
        # Initialize state
        state = {
            "query": query,
            "classification": None,
            "context": None,
            "response": None,
            "error": None
        }

        # Configure with services
        config = {
            "configurable": {
                "classifier": self.classifier,
                "vectordb": self.vectordb,
                "llm": self.llm,
                "collection_name": collection_name
            }
        }

        # Invoke graph
        result = await self.graph.ainvoke(state, config=config)

        return result
