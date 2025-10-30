"""Unit tests for JobStateManager.

This module tests the in-memory job state tracking system for async ingestion.

Date: 2025-10-28
Updated: 2025-10-29 - Added production-ready features (TDD)
"""

import re
import time
from datetime import datetime
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

    def test_job_uses_uuid_format(self):
        """Job IDs should be UUID format, not simple integers.
        
        Expected: Job ID matches UUID pattern (8-4-4-4-12 hex digits).
        RED: This should FAIL with current integer-based IDs.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        
        # UUID format: 8-4-4-4-12 hex digits
        uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
        assert re.match(uuid_pattern, job_id), f"Job ID {job_id} is not in UUID format"

    def test_job_tracks_progress_percentage(self):
        """Jobs should track progress from 0-100%.
        
        Expected: Can update progress with percentage and message.
        RED: This should FAIL as update_job_progress() doesn't exist.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        
        job = manager.get_job(job_id)
        assert job.progress == 0, "New job should have 0% progress"
        
        manager.update_job_progress(job_id, progress=50, message="Chunking...")
        job = manager.get_job(job_id)
        assert job.progress == 50
        assert job.message == "Chunking..."
        
        manager.update_job_progress(job_id, progress=100, message="Complete")
        job = manager.get_job(job_id)
        assert job.progress == 100

    def test_job_stores_timestamps(self):
        """Jobs should have created_at and updated_at timestamps.
        
        Expected: JobState has timestamp fields.
        RED: This should FAIL as JobState doesn't have timestamp fields.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        
        job = manager.get_job(job_id)
        assert hasattr(job, 'created_at'), "Job should have created_at timestamp"
        assert hasattr(job, 'updated_at'), "Job should have updated_at timestamp"
        assert isinstance(job.created_at, datetime)
        assert isinstance(job.updated_at, datetime)
        assert job.created_at <= job.updated_at

    def test_timestamps_update_on_status_change(self):
        """updated_at should change when job is updated.
        
        Expected: updated_at increases after status change.
        RED: This should FAIL as timestamps don't exist.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        
        job = manager.get_job(job_id)
        initial_updated_at = job.updated_at
        
        time.sleep(0.01)  # Small delay
        manager.update_job_status(job_id, JobStatus.PROCESSING)
        
        job = manager.get_job(job_id)
        assert job.updated_at > initial_updated_at, "updated_at should increase on update"

    def test_cleanup_removes_old_completed_jobs(self):
        """Old jobs past TTL should be automatically cleaned up.
        
        Expected: cleanup_old_jobs() removes completed jobs past TTL.
        RED: This should FAIL as cleanup_old_jobs() doesn't exist.
        """
        manager = JobStateManager(ttl_seconds=1)  # 1 second TTL
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        manager.update_job_status(job_id, JobStatus.COMPLETED)
        
        time.sleep(1.5)  # Wait past TTL
        
        cleaned = manager.cleanup_old_jobs()
        assert cleaned == 1, "Should clean up 1 old job"
        assert manager.get_job(job_id) is None, "Old job should be removed"

    def test_cleanup_keeps_recent_jobs(self):
        """Recent jobs should not be cleaned up even if completed.
        
        Expected: Jobs within TTL are kept.
        RED: This should FAIL as cleanup_old_jobs() doesn't exist.
        """
        manager = JobStateManager(ttl_seconds=10)  # 10 second TTL
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        manager.update_job_status(job_id, JobStatus.COMPLETED)
        
        cleaned = manager.cleanup_old_jobs()
        assert cleaned == 0, "Should not clean recent jobs"
        assert manager.get_job(job_id) is not None, "Recent job should be kept"

    def test_cleanup_keeps_processing_jobs(self):
        """Processing jobs should never be cleaned up.
        
        Expected: Only completed/failed jobs are cleaned.
        RED: This should FAIL as cleanup_old_jobs() doesn't exist.
        """
        manager = JobStateManager(ttl_seconds=1)
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        manager.update_job_status(job_id, JobStatus.PROCESSING)
        
        time.sleep(1.5)
        
        cleaned = manager.cleanup_old_jobs()
        assert cleaned == 0, "Should not clean processing jobs"
        assert manager.get_job(job_id) is not None, "Processing job should be kept"

    def test_complete_job_sets_chunks_created(self):
        """Completing job should record chunks_created count.
        
        Expected: complete_job() sets chunks_created and status.
        RED: This should FAIL as complete_job() doesn't exist.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        
        manager.complete_job(job_id, chunks_created=42)
        job = manager.get_job(job_id)
        
        assert job.chunks_created == 42
        assert job.status == JobStatus.COMPLETED
        assert job.progress == 100
        assert "42 chunks" in job.message.lower() or "complete" in job.message.lower()

    def test_progress_is_clamped_to_valid_range(self):
        """Progress should be clamped between 0 and 100.
        
        Expected: Values <0 become 0, values >100 become 100.
        RED: This should FAIL as update_job_progress() doesn't exist.
        """
        manager = JobStateManager()
        job_id = manager.create_job("gs://bucket/test.pdf", "col1")
        
        # Test negative value
        manager.update_job_progress(job_id, progress=-10)
        job = manager.get_job(job_id)
        assert job.progress == 0, "Negative progress should be clamped to 0"
        
        # Test over 100
        manager.update_job_progress(job_id, progress=150)
        job = manager.get_job(job_id)
        assert job.progress == 100, "Progress >100 should be clamped to 100"
