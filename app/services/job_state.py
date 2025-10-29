"""Job state management for async ingestion pipeline.

This module provides in-memory tracking of ingestion jobs.

Date: 2025-10-28
"""

from enum import Enum


class JobStatus(Enum):
    """Status values for ingestion jobs."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class JobState:
    """Represents the state of an ingestion job."""

    def __init__(self, job_id: str, file_path: str, collection_name: str):
        self.job_id = job_id
        self.file_path = file_path
        self.collection_name = collection_name
        self.status = JobStatus.PENDING
        self.error = None


class JobStateManager:
    """Manages in-memory state for ingestion jobs."""

    def __init__(self):
        self._counter = 0
        self._jobs = {}

    def create_job(self, file_path: str, collection_name: str) -> str:
        """Create a new job and return its ID."""
        self._counter += 1
        job_id = str(self._counter)
        self._jobs[job_id] = JobState(job_id, file_path, collection_name)
        return job_id

    def get_job(self, job_id: str):
        """Get job state by ID."""
        return self._jobs.get(job_id)

    def update_job_status(self, job_id: str, status: JobStatus, error: str = None):
        """Update the status of a job."""
        job = self._jobs.get(job_id)
        if job:
            job.status = status
            if error:
                job.error = error
