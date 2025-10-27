"""FastAPI main application for IntelliRAG.

This module provides the main FastAPI application with RAG endpoints.


Date: 2025-10-17
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.services.orchestrator import OrchestratorService
from app.models.schemas import QueryRequest, QueryResponse, QueryClassificationSchema
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize orchestrator (singleton)
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global orchestrator
    # Startup
    logger.info("Initializing IntelliRAG services...")
    orchestrator = OrchestratorService(
        vectordb_url="http://localhost:6333",
        llm_base_url="http://localhost:8000/v1",
        llm_model="Qwen/Qwen3-0.6B"
    )
    logger.info("IntelliRAG services initialized successfully")

    yield  # Application runs here

    # Shutdown (cleanup if needed)
    logger.info("Shutting down IntelliRAG services...")


# Create FastAPI app with lifespan
app = FastAPI(
    title="IntelliRAG API",
    description="Production-ready RAG system with vLLM and Qdrant",
    version="0.1.0",
    lifespan=lifespan
)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "IntelliRAG"}


@app.post("/api/v1/query", response_model=QueryResponse)
async def query_endpoint(request: QueryRequest) -> QueryResponse:
    """Query endpoint for RAG system.

    Args:
        request: Query request with user query and parameters

    Returns:
        QueryResponse with answer and sources
    """
    logger.info(f"Received query: {request.query[:50]}...")

    # Execute query via orchestrator (query router handles routing automatically)
    result = await orchestrator.query(
        query=request.query,
        collection_name="default",  # TODO: Make configurable
        top_k=request.top_k,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )

    # Convert classification to schema if present
    classification_schema = None
    if result.get("classification"):
        classification_schema = QueryClassificationSchema(
            query_type=result["classification"].query_type,
            confidence=result["classification"].confidence,
            reasoning=result["classification"].reasoning
        )

    # Format response
    response = QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        used_rag=request.use_rag,
        query=request.query,
        classification=classification_schema
    )

    logger.info(f"Query completed with {len(result['sources'])} sources")

    return response
