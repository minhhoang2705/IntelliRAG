"""FastAPI main application for IntelliRAG.

This module provides the main FastAPI application with RAG endpoints.

2025-10-17
"""

from email.policy import HTTP
from inspect import CO_ASYNC_GENERATOR
from app.api.middleware.metrics_middleware import MetricsMiddleware
from contextlib import asynccontextmanager
import os
import httpx
import time
import asyncio
from prometheus_client import Counter
from fastapi import FastAPI, HTTPException, Response, status
from app.services import embedding
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

readiness_check_counter = Counter(
    'readiness_check_total',
    'Total number of readiness checks'
)

readiness_check_failures = Counter(
    'readiness_check_failures_total',
    'Total number of readiness check failures',
    ['component']
)

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


@app.get("/")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "IntelliRAG"}

@app.get("/ready", status_code = status.HTTP_200_OK, tags=["Health"])
async def readiness_check():
    """Readiness probe endpoint with concurrent dependency checks"""
    readiness_check_counter.inc()
    
    health_status = {
        "status": "ready",
        "timestamp": time.time(),
        "service": "intellirag-api",
        "check": {}
    }
    
    # Check if orchestrator is initialized
    if orchestrator is None:
        health_status["status"] = "not ready"
        health_status["check"]["orchestrator"] = {
            "status": "unhealthy",
            "error": "Service is still initializing"
        }
        readiness_check_failures.labels(component="orchestrator").inc()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=health_status
        )
    
    # Define concurrent health check functions
    async def check_qdrant():
        """Check Qdrant connectivity"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                qdrant_url = f"{orchestrator.vectordb_service.url}/"
                response = await client.get(qdrant_url)
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds() * 1000,
                    "critical": True
                }
        except Exception as e:
            readiness_check_failures.labels(component="qdrant").inc()
            return {
                "status": "unhealthy",
                "error": str(e),
                "critical": True
            }
    
    async def check_llm():
        """Check LLM endpoint"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                llm_url = f"{orchestrator.llm_client.base_url}/models"
                response = await client.get(llm_url)
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds() * 1000,
                    "critical": True
                }
        except Exception as e:
            readiness_check_failures.labels(component="llm").inc()
            return {
                "status": "unhealthy",
                "error": str(e),
                "critical": True
            }
    
    async def check_embedding():
        """Check embedding endpoint (non-critical)"""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                embedding_url = f"{orchestrator.embedding_service.remote_url}/health"
                response = await client.get(embedding_url)
                return {
                    "status": "healthy" if response.status_code == 200 else "unhealthy",
                    "response_time": response.elapsed.total_seconds() * 1000,
                    "critical": False
                }
        except Exception as e:
            readiness_check_failures.labels(component="embedding").inc()
            logger.warning(f"Embedding service check failed (non-critical): {e}")
            return {
                "status": "degraded",
                "error": str(e),
                "critical": False
            }
    
    # Run all HTTP checks concurrently
    qdrant_result, llm_result, embedding_result = await asyncio.gather(
        check_qdrant(),
        check_llm(),
        check_embedding(),
        return_exceptions=True
    )
    
    # Process results
    health_status["check"]["qdrant"] = qdrant_result if not isinstance(qdrant_result, Exception) else {
        "status": "unhealthy",
        "error": str(qdrant_result),
        "critical": True
    }
    health_status["check"]["llm"] = llm_result if not isinstance(llm_result, Exception) else {
        "status": "unhealthy",
        "error": str(llm_result),
        "critical": True
    }
    health_status["check"]["embedding"] = embedding_result if not isinstance(embedding_result, Exception) else {
        "status": "degraded",
        "error": str(embedding_result),
        "critical": False
    }
    
    # Check GCS access (synchronous check)
    try:
        if orchestrator.gcs_loader.bucket is not None:
            health_status["check"]["gcs"] = {"status": "healthy", "critical": True}
        else:
            health_status["check"]["gcs"] = {
                "status": "unhealthy",
                "error": "GCS bucket not configured",
                "critical": True
            }
            readiness_check_failures.labels(component="gcs").inc()
    except Exception as e:
        health_status["check"]["gcs"] = {
            "status": "unhealthy",
            "error": str(e),
            "critical": True
        }
        readiness_check_failures.labels(component="gcs").inc()
    
    # Determine overall health based on critical services only
    critical_checks = [
        health_status["check"].get("qdrant", {}),
        health_status["check"].get("llm", {}),
        health_status["check"].get("gcs", {})
    ]
    
    all_critical_healthy = all(
        check.get("status") == "healthy" 
        for check in critical_checks 
        if check.get("critical", False)
    )
    
    if not all_critical_healthy:
        health_status["status"] = "not ready"
        raise HTTPException(
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE,
            detail= health_status
        )
    
    return health_status


@app.get("/metrics")
async def metrics_endpoint():
    """Expose Prometheus metrics."""
    return Response(
        content=generate_latest(),
        media_type='text/plain; version=0.0.4; charset=utf-8'
    )
