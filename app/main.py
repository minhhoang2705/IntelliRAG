"""FastAPI main application for IntelliRAG.

This module provides the main FastAPI application with RAG endpoints.

Date: 2025-10-17
"""

from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Response
from app.services.orchestrator import OrchestratorService
from app.models.schemas import QueryRequest, QueryResponse, QueryClassificationSchema
from prometheus_client import generate_latest
from app.core.logging import setup_logging, get_logger
from app.api.v1.upload import router as upload_router
from app.api.v1.ingest import router as ingest_router

# Configure structured logging
setup_logging(level="INFO")
logger = get_logger(__name__)

# Initialize orchestrator (singleton)
orchestrator = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application lifespan - startup and shutdown."""
    global orchestrator
    # Startup
    if orchestrator is None:
        logger.info("Initializing IntelliRAG services...")
        orchestrator = OrchestratorService(
            vectordb_url=os.getenv("QDRANT_URL", "http://localhost:6333"),
            llm_base_url=os.getenv(
                "VLLM_BASE_URL", "http://localhost:8000/v1"),
            llm_model=os.getenv("VLLM_MODEL", "Qwen/Qwen3-0.6B"),
            gcs_project=os.getenv("GCP_PROJECT_ID", "test-project"),
            gcs_bucket=os.getenv("GCS_BUCKET_NAME", "test-bucket"),
            embedding_service_url=os.getenv(
                "EMBEDDING_SERVICE_URL", "http://localhost:8001"),
            use_remote_embedding=os.getenv(
                "EMBEDDING_USE_REMOTE", "true").lower() == "true"
        )
        logger.info("IntelliRAG services initialized successfully")
    else:
        logger.info("IntelliRAG services already initialized")

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

# Include routers
app.include_router(upload_router)
app.include_router(ingest_router)


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "IntelliRAG"}


@app.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type='text/plain; version=0.0.4; charset=utf-8'
    )


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

    # Format response - handle None answer gracefully
    answer = result.get("answer") or result.get(
        "response") or "Unable to generate response"
    sources = result.get("sources", [])

    response = QueryResponse(
        answer=answer,
        sources=sources,
        used_rag=request.use_rag,
        query=request.query,
        classification=classification_schema
    )

    logger.info(f"Query completed with {len(sources)} sources")

    return response
