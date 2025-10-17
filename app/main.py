"""FastAPI main application for IntelliRAG.

This module provides the main FastAPI application with RAG endpoints.

Author: IntelliRAG Team
Date: 2025-10-17
"""

from fastapi import FastAPI
from app.services.orchestrator import OrchestratorService
from app.models.schemas import QueryRequest, QueryResponse
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="IntelliRAG API",
    description="Production-ready RAG system with vLLM and Qdrant",
    version="0.1.0"
)

# Initialize orchestrator (singleton)
orchestrator = None


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global orchestrator
    logger.info("Initializing IntelliRAG services...")
    orchestrator = OrchestratorService(
        vectordb_url="http://localhost:6333",
        llm_base_url="http://localhost:8000/v1",
        llm_model="Qwen/Qwen2.5-7B-Instruct"
    )
    logger.info("IntelliRAG services initialized successfully")


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

    # Execute query via orchestrator
    result = await orchestrator.query(
        query=request.query,
        collection_name="default",  # TODO: Make configurable
        use_rag=request.use_rag,
        top_k=request.top_k,
        temperature=request.temperature,
        max_tokens=request.max_tokens
    )

    # Format response
    response = QueryResponse(
        answer=result["answer"],
        sources=result["sources"],
        used_rag=request.use_rag,
        query=request.query
    )

    logger.info(f"Query completed with {len(result['sources'])} sources")

    return response
