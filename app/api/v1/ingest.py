"""Ingest API endpoints with async background processing.

Provides endpoints for triggering document ingestion and checking job status.
Uses FastAPI's BackgroundTasks for non-blocking async processing.
"""

import logging
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, Field
from app.models.schemas import IngestResponse, IngestStatusResponse, IngestRequest
from app.services.job_state import JobStatus
from app.api.middleware.metrics import ingestion_jobs_total, ingestion_jobs_active
from app.utils import extract_file_extension

logger = logging.getLogger(__name__)
router = APIRouter()



@router.post("/api/v1/ingest", response_model=IngestResponse, status_code=202)
async def ingest_document(
    request: IngestRequest,
    background_tasks: BackgroundTasks
) -> IngestResponse:
    """Trigger async document ingestion.
    
    Creates a job immediately and returns 202 Accepted, then processes
    the ingestion in the background. Use the status endpoint to track progress.
    
    Args:
        request: Ingestion request with file_path and collection_name
        background_tasks: FastAPI background tasks handler
        
    Returns:
        IngestResponse with job_id and initial status
        
    Raises:
        HTTPException: 500 if job creation fails
    """
    from app import main as main_module
    
    logger.info(f"Ingestion requested: {request.file_path} -> {request.collection_name}")
    
    try:
        # Create job immediately (synchronous - returns instantly)
        job_id = main_module.orchestrator.job_state_manager.create_job(
            file_path=request.file_path,
            collection_name=request.collection_name
        )

        # Record pending job metrics
        file_extension = extract_file_extension(request.file_path)
        ingestion_jobs_total.labels(status="pending", file_type=file_extension).inc()
        ingestion_jobs_active.labels(status="pending").inc()

        logger.info(f"Job created: {job_id}, scheduling background processing")
        
        # Schedule background processing (non-blocking)
        background_tasks.add_task(
            _process_ingestion_background,
            job_id=job_id,
            file_path=request.file_path,
            collection_name=request.collection_name,
            orchestrator=main_module.orchestrator
        )
        
        # Return immediately with 202 Accepted
        return IngestResponse(
            job_id=job_id,
            status="pending",
            message="Ingestion job created and scheduled for processing",
            file_path=request.file_path,
            collection_name=request.collection_name
        )
    
    except Exception as e:
        logger.error(f"Failed to create ingestion job: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Job creation failed: {str(e)}")


@router.get("/api/v1/ingest/status/{job_id}", response_model=IngestStatusResponse)
async def get_ingest_status(job_id: str) -> IngestStatusResponse:
    """Get status of ingestion job.
    
    Args:
        job_id: Job identifier from ingest endpoint
        
    Returns:
        IngestStatusResponse with current job status and progress
        
    Raises:
        HTTPException: 404 if job not found
    """
    from app import main as main_module
    
    job = main_module.orchestrator.job_state_manager.get_job(job_id)
    
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return IngestStatusResponse(
        job_id=job.job_id,
        status=job.status.value,
        progress=job.progress,
        message=job.message,
        file_path=job.file_path,
        collection_name=job.collection_name,
        chunks_created=job.chunks_created,
        error=job.error
    )


async def _process_ingestion_background(
    job_id: str,
    file_path: str,
    collection_name: str,
    orchestrator
):
    """Background task to process document ingestion.
    
    This function runs asynchronously in the background after the ingest endpoint
    returns. It updates job state throughout the processing lifecycle.
    
    Args:
        job_id: Job identifier
        file_path: GCS path to document
        collection_name: Target collection name
        orchestrator: OrchestratorService instance
    """
    logger.info(f"Background processing started for job {job_id}")
    
    try:
        # Update to PROCESSING status
        orchestrator.job_state_manager.update_job_status(job_id, JobStatus.PROCESSING)
        orchestrator.job_state_manager.update_job_progress(
            job_id, progress=10, message="Starting ingestion pipeline"
        )

        # Update active jobs gauge: decrement pending, increment processing
        ingestion_jobs_active.labels(status="pending").dec()
        ingestion_jobs_active.labels(status="processing").inc()
        
        try:
            # Run orchestrator ingestion with existing job_id
            # Pass job_id to prevent duplicate job creation
            await orchestrator.ingest(
                file_path=file_path,
                collection_name=collection_name,
                job_id=job_id
            )
            
            # Record completed job metric
            file_extension = extract_file_extension(file_path)
            ingestion_jobs_total.labels(status="completed", file_type=file_extension).inc()
            logger.info(f"Background processing completed for job {job_id}")
        
        finally:
            # ALWAYS decrement processing gauge, even if job fails
            # This prevents gauge drift from unhandled exceptions
            ingestion_jobs_active.labels(status="processing").dec()
    
    except Exception as e:
        # Handle errors gracefully - update job to FAILED status
        logger.error(f"Background processing failed for job {job_id}: {e}", exc_info=True)
        orchestrator.job_state_manager.update_job_status(
            job_id,
            JobStatus.FAILED,
            error=str(e)
        )
        orchestrator.job_state_manager.update_job_progress(
            job_id, progress=0, message=f"Ingestion failed: {str(e)}"
        )
        
        # Update metrics for failed job
        file_extension = extract_file_extension(file_path)
        ingestion_jobs_total.labels(status="failed", file_type=file_extension).inc()
