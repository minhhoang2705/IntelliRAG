"""LangGraph state machine for query routing.
"""

from typing import TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from app.services.query_router.classifier import QueryType, QueryClassification
import logging

logger = logging.getLogger(__name__)


class QueryState(TypedDict):
    """State for query routing graph."""
    query: str
    classification: Optional[QueryClassification]
    context: Optional[List[str]]
    response: Optional[str]
    error: Optional[str]


async def classify_node(state: QueryState, config=None) -> QueryState:
    """Classify the query using QueryClassifier.

    Args:
        state: Current state
        config: RunnableConfig with classifier

    Returns:
        Updated state with classification
    """
    try:
        # Extract classifier from config
        classifier = config.get("configurable", {}).get("classifier") if config else None
        if not classifier:
            raise ValueError("Classifier not provided in config")

        # Perform classification
        classification = await classifier.classify(state["query"])

        logger.info(
            f"Classified query: type={classification.query_type.value}, "
            f"confidence={classification.confidence}"
        )

        # Update state with classification
        return {
            **state,
            "classification": classification,
            "error": None
        }
    except Exception as e:
        logger.error(f"Classification failed: {e}")
        return {
            **state,
            "error": f"Classification failed: {str(e)}"
        }


async def clarify_node(state: QueryState) -> QueryState:
    return {
        **state,
        "response": "Could you please provide more details about your question?"
    }


def route_query(state: QueryState) -> str:
    """Route query based on classification.

    If classification failed (None) or there's an error, terminate.
    Otherwise route based on query type.
    """
    classification = state["classification"]
    error = state.get("error")

    # If classification failed or error exists, terminate
    if classification is None or error:
        return END

    if classification.query_type == QueryType.DIRECT:
        return "generate"
    elif classification.query_type == QueryType.CLARIFICATION:
        return "clarify"

    return "retrieve"


async def generate_node(state: QueryState, config=None) -> QueryState:
    """Generate response using LLM.

    Args:
        state: Current state with query and optional context
        config: RunnableConfig with LLM service

    Returns:
        Updated state with response
    """
    query = state["query"]
    context = state.get("context")

    # Extract LLM service from config
    llm_service = config.get("configurable", {}).get("llm") if config else None
    if not llm_service:
        return {
            **state,
            "error": "LLM service not provided in config"
        }

    try:
        # Format prompt with or without context
        if context and len(context) > 0:
            context_text = "\n\n".join(
                [f"[{i+1}] {ctx}" for i, ctx in enumerate(context)])
            prompt = f"""Answer based on context:

{context_text}

Question: {query}"""
        else:
            prompt = query

        # Generate response
        response = await llm_service.generate(prompt=prompt)

        logger.info(f"Generated response for query: {query[:50]}...")

        return {
            **state,
            "response": response
        }
    except Exception as e:
        logger.error(f"Generation failed: {e}")
        return {
            **state,
            "error": f"Generation failed: {str(e)}"
        }


async def retrieve_node(state: QueryState, config=None) -> QueryState:
    """Retrieve relevant context from vector database.

    Args:
        state: Current state with query
        config: RunnableConfig with vectordb service

    Returns:
        Updated state with context
    """
    query = state["query"]

    # Extract vectordb from config
    vectordb_service = config.get("configurable", {}).get("vectordb") if config else None
    if not vectordb_service:
        return {
            **state,
            "error": "VectorDB service not provided in config"
        }

    try:
        # Search for relevant documents
        results = await vectordb_service.search_vectors(
            collection_name="default",
            query_vector=[],  # Placeholder - will be replaced with actual embedding
            limit=5
        )

        # Extract context from results
        context = []
        for result in results:
            text = result.payload.get("text", "")
            context.append(text)

        logger.info(f"Retrieved {len(context)} context chunks")

        return {
            **state,
            "context": context
        }
    except Exception as e:
        logger.error(f"Retrieval failed: {e}")
        return {
            **state,
            "error": f"Retrieval failed: {str(e)}"
        }


def build_query_graph():
    """Build LangGraph state machine for query routing.

    Returns:
        Compiled state graph
    """
    # Create state graph
    graph = StateGraph(QueryState)

    # Add classify node
    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    graph.add_node("clarify", clarify_node)

    # Set entry point
    graph.set_entry_point("classify")

    # Add conditional routing from classify
    graph.add_conditional_edges(
        "classify",
        route_query,
        {
            "retrieve": "retrieve",  # RAG & MULTI_HOP queries
            "generate": "generate",   # DIRECT queries
            "clarify": "clarify",     # CLARIFICATION queries
            END: END                   # Error cases
        }
    )
    
    # Add conditional routing from retrieve (to handle errors)
    def route_after_retrieve(state: QueryState) -> str:
        """Route after retrieval - check for errors."""
        if state.get("error"):
            return END
        return "generate"

    graph.add_conditional_edges(
        "retrieve",
        route_after_retrieve,
        {
            "generate": "generate",
            END: END
        }
    )
    graph.add_edge("generate", END)
    graph.add_edge("clarify", END)

    return graph.compile()
