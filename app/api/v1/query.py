"""Query endpoint for RAG system.
"""

from fastapi import APIRouter, Depends, BackgroundTasks
from app.models.schemas import QueryRequest, QueryResponse, QueryClassificationSchema
from app.dependencies import get_orchestrator, get_query_logger
from app.services.orchestrator import OrchestratorService
from app.services.query_logger import QueryLoggerService
from app.api.middleware.auth import verify_api_key
import time

router = APIRouter()


@router.post("/api/v1/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    background_tasks: BackgroundTasks,
    orchestrator: OrchestratorService = Depends(get_orchestrator),
    query_logger: QueryLoggerService = Depends(get_query_logger),
    api_key: str = Depends(verify_api_key)
):
    start_time = time.time()

    result = await orchestrator.query(
        query=request.query,
        collection_name="default",
        top_k=request.top_k,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        use_rag=request.use_rag
    )

    response_time_ms = (time.time() - start_time) * 1000

    # Convert classification to schema if present
    classification_schema = None
    query_type = None
    if result.get("classification"):
        classification_schema = QueryClassificationSchema(
            query_type=result["classification"].query_type,
            confidence=result["classification"].confidence,
            reasoning=result["classification"].reasoning
        )
        query_type = result["classification"].query_type

    # Log query metadata in background for drift detection
    background_tasks.add_task(
        query_logger.log_query,
        query=request.query,
        response_time_ms=response_time_ms,
        used_rag=result["used_rag"],
        sources_count=len(result["sources"]),
        answer_length=len(result["answer"]),
        query_type=query_type
    )

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "query": request.query,
        "used_rag": result["used_rag"],
        "classification": classification_schema
    }
