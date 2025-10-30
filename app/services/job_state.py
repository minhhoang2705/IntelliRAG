"""Job state management for async ingestion pipeline.

This module provides in-memory tracking of ingestion jobs with production-ready features:
- UUID-based job IDs
- Progress tracking (0-100%)
- Timestamps for created_at and updated_at
- TTL-based cleanup for old jobs
- Comprehensive job lifecycle management

Date: 2025-10-28
Updated: 2025-10-29 - Enhanced with production features (TDD)
"""

import uuid
import logging
from enum import Enum
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Status values for ingestion jobs."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobState:
    """Represents the state of an ingestion job with full tracking."""

    def __init__(self, job_id: str, file_path: str, collection_name: str):
        """Initialize job state.
        
        Args:
            job_id: Unique job identifier (UUID)
            file_path: Path to file being processed
            collection_name: Target collection name
        """
        self.job_id = job_id
        self.file_path = file_path
        self.collection_name = collection_name
        self.status = JobStatus.PENDING
        self.progress = 0  # 0-100%
        self.message = ""
        self.chunks_created = 0
        self.error: Optional[str] = None
        self.created_at = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class JobStateManager:
    """Production-ready job state manager with TTL and cleanup."""

    def __init__(self, ttl_seconds: int = 3600):
        """Initialize job state manager.
        
        Args:
            ttl_seconds: Time-to-live for completed/failed jobs (default: 1 hour)
        """
        self._jobs: Dict[str, JobState] = {}
        self._ttl = timedelta(seconds=ttl_seconds)
        logger.info(f"JobStateManager initialized with TTL={ttl_seconds}s")

    def create_job(self, file_path: str, collection_name: str) -> str:
        """Create a new job with UUID.
        
        Args:
            file_path: Path to file to be processed
            collection_name: Target collection name
            
        Returns:
            Job ID (UUID string)
        """
        job_id = str(uuid.uuid4())
        self._jobs[job_id] = JobState(job_id, file_path, collection_name)
        logger.info(f"Created job {job_id} for file {file_path}")
        return job_id

    def get_job(self, job_id: str) -> Optional[JobState]:
        """Get job state by ID.
        
        Args:
            job_id: Job identifier
            
        Returns:
            JobState if found, None otherwise
        """
        return self._jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus, error: str = None):
        """Update the status of a job.
        
        Args:
            job_id: Job identifier
            status: New status
            error: Optional error message (for FAILED status)
        """
        job = self._jobs.get(job_id)
        if job:
            job.status = status
            if error:
                job.error = error
            job.updated_at = datetime.now(timezone.utc)
            logger.info(f"Job {job_id} status updated to {status.value}")

    def update_job_progress(self, job_id: str, progress: int, message: str = ""):
        """Update job progress percentage.
        
        Args:
            job_id: Job identifier
            progress: Progress percentage (will be clamped to 0-100)
            message: Optional status message
        """
        job = self._jobs.get(job_id)
        if job:
            # Clamp progress to valid range
            job.progress = max(0, min(100, progress))
            job.message = message
            job.updated_at = datetime.now(timezone.utc)
            logger.debug(f"Job {job_id} progress: {job.progress}% - {message}")

    def complete_job(self, job_id: str, chunks_created: int):
        """Mark job as completed with results.
        
        Args:
            job_id: Job identifier
            chunks_created: Number of chunks created during ingestion
        """
        job = self._jobs.get(job_id)
        if job:
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.chunks_created = chunks_created
            job.message = f"Completed: {chunks_created} chunks created"
            job.updated_at = datetime.now(timezone.utc)
            logger.info(f"Job {job_id} completed: {chunks_created} chunks")

    def cleanup_old_jobs(self) -> int:
        """Remove old completed/failed jobs past TTL.
        
        Only removes jobs in COMPLETED or FAILED status that haven't been
        updated within the TTL window. PENDING and PROCESSING jobs are never
        cleaned up.
        
        Returns:
            Number of jobs cleaned up
        """
        cutoff_time = datetime.now(timezone.utc) - self._ttl
        
        jobs_to_remove = [
            job_id
            for job_id, job in self._jobs.items()
            if job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
            and job.updated_at < cutoff_time
        ]
        
        for job_id in jobs_to_remove:
            del self._jobs[job_id]
        
        if jobs_to_remove:
            logger.info(f"Cleaned up {len(jobs_to_remove)} old jobs")
        
        return len(jobs_to_remove)
