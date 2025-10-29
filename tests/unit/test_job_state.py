"""Unit tests for JobStateManager.

This module tests the in-memory job state tracking system for async ingestion.

Date: 2025-10-28
"""

from app.services.job_state import JobStateManager, JobStatus


class TestJobStateManager:
    """Test suite for JobStateManager."""

    def test_create_job_returns_unique_id(self):
        """Test that creating a job returns a unique job ID.

        Expected: Job ID is a non-empty string (UUID format).
        """
        manager = JobStateManager()
        job_id = manager.create_job(
            file_path="gs://bucket/test.pdf",
            collection_name="test_collection"
        )

        assert job_id is not None
        assert isinstance(job_id, str)
        assert len(job_id) > 0

    def test_create_multiple_jobs_unique_ids(self):
        """Test that multiple jobs get unique IDs.

        Expected: Each job has a different ID.
        """
        manager = JobStateManager()
        job_id1 = manager.create_job("gs://bucket/file1.pdf", "col1")
        job_id2 = manager.create_job("gs://bucket/file2.pdf", "col2")

        assert job_id1 != job_id2

    def test_get_job_returns_correct_state(self):
        """Test retrieving job state by ID.

        Expected: Returns job state with correct file_path and collection_name.
        """
        manager = JobStateManager()
        job_id = manager.create_job(
            file_path="gs://bucket/test.pdf",
            collection_name="test_collection"
        )

        state = manager.get_job(job_id)

        assert state is not None
        assert state.file_path == "gs://bucket/test.pdf"
        assert state.collection_name == "test_collection"

    def test_get_nonexistent_job_returns_none(self):
        """Test getting a job that doesn't exist.

        Expected: Returns None for invalid job ID.
        """
        manager = JobStateManager()
        state = manager.get_job("nonexistent-job-id")

        assert state is None

    def test_new_job_starts_with_pending_status(self):
        """Test that newly created jobs have PENDING status.

        Expected: New job state has status JobStatus.PENDING.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "test_col")

        state = manager.get_job(job_id)

        assert state.status == JobStatus.PENDING

    def test_update_job_status_to_processing(self):
        """Test updating job status to PROCESSING.

        Expected: Status changes from PENDING to PROCESSING.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")

        manager.update_job_status(job_id, JobStatus.PROCESSING)
        state = manager.get_job(job_id)

        assert state.status == JobStatus.PROCESSING

    def test_update_job_status_to_completed(self):
        """Test marking a job as completed successfully.

        Expected: Status changes to COMPLETED.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")

        manager.update_job_status(job_id, JobStatus.PROCESSING)
        manager.update_job_status(job_id, JobStatus.COMPLETED)
        state = manager.get_job(job_id)

        assert state.status == JobStatus.COMPLETED

    def test_update_job_status_to_failed_with_error(self):
        """Test marking a job as failed with error message.

        Expected: Status is FAILED and error message is stored.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")

        error_msg = "File validation failed: unsupported format"
        manager.update_job_status(job_id, JobStatus.FAILED, error=error_msg)

        state = manager.get_job(job_id)

        assert state.status == JobStatus.FAILED
        assert state.error == error_msg
