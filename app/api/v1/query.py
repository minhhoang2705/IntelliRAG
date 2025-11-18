"""Query endpoint for RAG system.
"""

from fastapi import APIRouter, Depends
from app.models.schemas import QueryRequest, QueryResponse, QueryClassificationSchema
from app.dependencies import get_orchestrator
from app.services.orchestrator import OrchestratorService

router = APIRouter()


@router.post("/api/v1/query", response_model=QueryResponse)
async def query_endpoint(
    request: QueryRequest,
    orchestrator: OrchestratorService = Depends(get_orchestrator)
):
    result = await orchestrator.query(
        query=request.query,
        collection_name="default",
        top_k=request.top_k,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        use_rag=request.use_rag
    )

    # Convert classification to schema if present
    classification_schema = None
    if result.get("classification"):
        classification_schema = QueryClassificationSchema(
            query_type=result["classification"].query_type,
            confidence=result["classification"].confidence,
            reasoning=result["classification"].reasoning
        )

    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "query": request.query,
        # CHANGE: Use actual value from orchestrator
        "used_rag": result["used_rag"],
        "classification": classification_schema
    }
