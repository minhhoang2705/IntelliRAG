"""FastAPI main application for IntelliRAG.

This module provides the main FastAPI application with RAG endpoints.

2025-10-17
"""

from app.api.middleware.metrics_middleware import MetricsMiddleware
from contextlib import asynccontextmanager
import os
from fastapi import FastAPI, Response
from app.services.orchestrator import OrchestratorService
from prometheus_client import generate_latest
from app.core.logging import setup_logging, get_logger
from app.core.tracing import setup_tracing
from app.api.v1.upload import router as upload_router
from app.api.v1.ingest import router as ingest_router
from app.api.v1.query import router as query_router
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

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

    # Initialize OpenTelemetry tracing
    setup_tracing(
        service_name="IntelliRAG",
        jaeger_host=os.getenv("JAEGER_HOST", "localhost"),
        jaeger_port=int(os.getenv("JAEGER_PORT", "6831"))
    )
    logger.info("OpenTelemetry tracing initialized")

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

# Instrument FastAPI app for automatic tracing
FastAPIInstrumentor.instrument_app(app)

# Add HTTP metrics middleware
app.add_middleware(MetricsMiddleware)

# Include routers
app.include_router(upload_router)
app.include_router(query_router)
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
