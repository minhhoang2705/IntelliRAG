"""Ingest API endpoints.

Provides endpoints for triggering document ingestion and checking job status.

Date: 2025-10-29
"""

from fastapi import APIRouter
from pydantic import BaseModel, Field

router = APIRouter()


class IngestRequest(BaseModel):
    """Request model for document ingestion."""
    file_path: str = Field(..., description="GCS path to document")
    collection_name: str = Field(..., description="Target collection")


@router.post("/api/v1/ingest")
async def ingest_document(request: IngestRequest):
    """Trigger document ingestion."""
    from app import main as main_module

    job_id = await main_module.orchestrator.ingest(
        file_path=request.file_path,
        collection_name=request.collection_name
    )
    return {"job_id": job_id}


@router.get("/api/v1/ingest/status/{job_id}")
async def get_ingest_status(job_id: str):
    """Get status of ingestion job."""
    from app import main as main_module

    job = main_module.orchestrator.job_state_manager.get_job(job_id)

    return {
        "status": job.status.value,
        "file_path": job.file_path,
        "collection_name": job.collection_name,
        "error": job.error
    }
