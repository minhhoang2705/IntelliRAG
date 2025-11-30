"""Unit tests for ingest API endpoints.

This module tests the POST /api/v1/ingest and GET /api/v1/ingest/status endpoints.
"""

from fastapi.testclient import TestClient
import pytest
import asyncio
import time
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_ingest_endpoint_exists():
    """Test that POST /api/v1/ingest endpoint exists.

    Expected: Endpoint responds (not 404).
    """
    from app.main import app

    client = TestClient(app)
    response = client.post("/api/v1/ingest")

    assert response.status_code != 404


def test_ingest_returns_job_id(mocker, auth_override):
    """Test that ingest endpoint returns a job_id.

    Expected: Response contains job_id field.
    """
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService
    from langchain_core.documents import Document
    from app.api.middleware.auth import verify_api_key

    # Initialize and mock orchestrator
    main_module.orchestrator = OrchestratorService()
    mocker.patch.object(main_module.orchestrator.gcs_loader, 'load_file', AsyncMock(return_value=[Document(page_content="test")]))
    mocker.patch.object(main_module.orchestrator.semantic_chunker, 'chunk_documents', AsyncMock(return_value=[]))
    mocker.patch.object(main_module.orchestrator.embedding_service, 'embed_batch', return_value=[])
    mocker.patch.object(main_module.orchestrator.vectordb_service, 'upsert_vectors', AsyncMock())

    # Override auth for testing
    app.dependency_overrides[verify_api_key] = auth_override
    try:
        client = TestClient(app)

        response = client.post("/api/v1/ingest", json={
            "file_path": "gs://bucket/test.pdf",
            "collection_name": "test"
        })

        data = response.json()
        assert "job_id" in data
    finally:
        app.dependency_overrides.clear()


def test_ingest_calls_orchestrator(mocker, auth_override):
    """Test that ingest endpoint calls orchestrator.ingest().

    Expected: Orchestrator.ingest() is called with correct parameters.
    """
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService
    from app.api.middleware.auth import verify_api_key

    # Initialize orchestrator for testing
    main_module.orchestrator = OrchestratorService()

    # Mock the ingest method
    mock_ingest = AsyncMock(return_value="test-job-123")
    mocker.patch.object(main_module.orchestrator, 'ingest', mock_ingest)

    # Override auth for testing
    app.dependency_overrides[verify_api_key] = auth_override
    try:
        client = TestClient(app)

        payload = {
            "file_path": "gs://test-bucket/test.pdf",
            "collection_name": "test_collection"
        }

        response = client.post("/api/v1/ingest", json=payload)
    finally:
        app.dependency_overrides.clear()

    # Verify orchestrator was called with job_id parameter
    assert mock_ingest.called
    call_args = mock_ingest.call_args
    assert call_args.kwargs["file_path"] == "gs://test-bucket/test.pdf"
    assert call_args.kwargs["collection_name"] == "test_collection"
    assert "job_id" in call_args.kwargs  # job_id should be passed

    # Verify response contains job_id
    data = response.json()
    assert "job_id" in data


def test_status_endpoint_exists():
    """Test that status endpoint exists."""
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService

    # Initialize orchestrator with a test job
    main_module.orchestrator = OrchestratorService()
    job_id = main_module.orchestrator.job_state_manager.create_job("gs://test.pdf", "test")

    client = TestClient(app)
    response = client.get(f"/api/v1/ingest/status/{job_id}")

    assert response.status_code != 404


def test_status_returns_job_info(mocker, auth_override):
    """Test that status endpoint returns job information."""
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService
    from app.services.job_state import JobStatus
    from app.api.middleware.auth import verify_api_key

    # Setup orchestrator with a completed job
    main_module.orchestrator = OrchestratorService()
    job_id = main_module.orchestrator.job_state_manager.create_job(
        "gs://bucket/test.pdf",
        "test_collection"
    )
    main_module.orchestrator.job_state_manager.update_job_status(job_id, JobStatus.COMPLETED)

    # Override auth for testing
    app.dependency_overrides[verify_api_key] = auth_override
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/ingest/status/{job_id}")

        data = response.json()
        assert "status" in data
    finally:
        app.dependency_overrides.clear()


def test_status_returns_complete_job_data(mocker, auth_override):
    """Test that status endpoint returns complete job information."""
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService
    from app.services.job_state import JobStatus
    from app.api.middleware.auth import verify_api_key

    # Setup with completed job
    main_module.orchestrator = OrchestratorService()
    job_id = main_module.orchestrator.job_state_manager.create_job(
        "gs://bucket/doc.pdf",
        "docs_collection"
    )
    main_module.orchestrator.job_state_manager.update_job_status(job_id, JobStatus.COMPLETED)

    # Override auth for testing
    app.dependency_overrides[verify_api_key] = auth_override
    try:
        client = TestClient(app)
        response = client.get(f"/api/v1/ingest/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["file_path"] == "gs://bucket/doc.pdf"
        assert data["collection_name"] == "docs_collection"
        assert data["error"] is None
    finally:
        app.dependency_overrides.clear()


class TestAsyncBackgroundProcessing:
    """Test suite for async background processing of ingestion jobs.

    These tests verify that ingestion happens asynchronously using FastAPI's
    BackgroundTasks, allowing for non-blocking responses and progress tracking.
    """

    @pytest.fixture(autouse=True)
    def setup_orchestrator(self, mocker):
        """Initialize orchestrator and mock expensive operations for all tests in this class."""
        from app import main as main_module
        from app.services.orchestrator import OrchestratorService
        from app.services.job_state import JobStatus

        # Initialize orchestrator if not already done
        if main_module.orchestrator is None:
            main_module.orchestrator = OrchestratorService(
                vectordb_url="http://localhost:6333",
                llm_base_url="http://localhost:8000/v1",
                llm_model="Qwen/Qwen3-0.6B"
            )

        # Mock the expensive ingest() method to prevent actual GCS/processing
        # This allows tests to verify async behavior without waiting for real processing
        async def mock_ingest(file_path, collection_name, job_id=None):
            """Mock ingest that updates job status without actual processing."""
            # Add minimal delay to yield control to event loop
            # This simulates async behavior without blocking tests
            await asyncio.sleep(0.01)
            
            # Simulate successful ingestion by updating job state
            if job_id:
                main_module.orchestrator.job_state_manager.update_job_status(
                    job_id, JobStatus.COMPLETED
                )
                main_module.orchestrator.job_state_manager.update_job_progress(
                    job_id, progress=100, message="Processing completed"
                )
                # Update chunks_created directly on job object (matching orchestrator.py pattern)
                job = main_module.orchestrator.job_state_manager.get_job(job_id)
                if job:
                    job.chunks_created = 5
            return job_id

        mocker.patch.object(
            main_module.orchestrator,
            'ingest',
            side_effect=mock_ingest
        )

        yield

        # Cleanup (optional)
        # main_module.orchestrator = None

    @pytest.mark.asyncio
    async def test_ingest_returns_202_accepted_immediately(self, auth_override):
        """Ingest endpoint should return 202 Accepted immediately without waiting.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        request_data = {
            "file_path": "gs://bucket/test.pdf",
            "collection_name": "documents"
        }

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                start_time = time.time()
                response = await client.post("/api/v1/ingest", json=request_data)
                duration = time.time() - start_time

            # Should return immediately
            assert duration < 0.5, f"Request took {duration}s, should be <0.5s for async"

            # Should return 202 Accepted (not 200 OK)
            assert response.status_code == 202, f"Expected 202 Accepted, got {response.status_code}"

            data = response.json()
            assert "job_id" in data, "Response must include job_id"
            assert "status" in data, "Response must include status"
            assert data["status"] in ["pending", "processing"], f"Status should be pending/processing, got {data['status']}"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ingest_creates_job_before_processing(self, auth_override):
        """Ingest should create job immediately before starting background task.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        request_data = {
            "file_path": "gs://bucket/test.pdf",
            "collection_name": "documents"
        }

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                ingest_response = await client.post("/api/v1/ingest", json=request_data)
                job_id = ingest_response.json()["job_id"]

                # Check job exists immediately (fixture mock completes instantly)
                status_response = await client.get(f"/api/v1/ingest/status/{job_id}")

                assert status_response.status_code == 200
                status_data = status_response.json()
                # Job may be pending, processing, or already completed (depending on timing)
                assert status_data["status"] in ["pending", "processing", "completed"]
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_background_task_processes_asynchronously(self, auth_override):
        """Background task should process ingestion without blocking endpoint.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    # Start 3 ingestion jobs rapidly
                    start_time = time.time()
                    jobs = []
                    for i in range(3):
                        response = await client.post("/api/v1/ingest", json={
                            "file_path": f"gs://bucket/test{i}.pdf",
                            "collection_name": "docs"
                        })
                        jobs.append(response.json()["job_id"])

                    total_time = time.time() - start_time

                    # All 3 requests should complete quickly (not 6 seconds if blocking)
                    assert total_time < 2.0, f"3 requests took {total_time}s, should be <2s if async"
                    assert len(jobs) == 3, "Should have created 3 jobs"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_status_endpoint_tracks_progress(self, auth_override):
        """Status endpoint should show progress updates during processing.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                # Start ingestion
                ingest_response = await client.post("/api/v1/ingest", json={
                    "file_path": "gs://bucket/test.pdf",
                    "collection_name": "docs"
                })
                job_id = ingest_response.json()["job_id"]

                # Poll status multiple times
                progress_values = []
                for _ in range(5):
                    await asyncio.sleep(0.2)
                    status_response = await client.get(f"/api/v1/ingest/status/{job_id}")
                    data = status_response.json()

                    assert "progress" in data, "Status must include progress field"
                    progress_values.append(data["progress"])

                # Progress should increase or stay completed
                assert all(0 <= p <= 100 for p in progress_values), "Progress must be 0-100%"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_background_task_updates_job_state(self, auth_override):
        """Background task should update job state through its lifecycle.

        Expected: Job transitions PENDING → PROCESSING → COMPLETED
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    # Start ingestion
                    ingest_response = await client.post("/api/v1/ingest", json={
                        "file_path": "gs://bucket/test.pdf",
                        "collection_name": "docs"
                    })
                    job_id = ingest_response.json()["job_id"]

                    # Check initial state (may be processing or already completed with BackgroundTasks)
                    status_response = await client.get(f"/api/v1/ingest/status/{job_id}")
                    initial_status = status_response.json()["status"]
                    assert initial_status in ["pending", "processing", "completed"], \
                        f"Unexpected status: {initial_status}"

                    # Wait for completion if still processing
                    if initial_status != "completed":
                        await asyncio.sleep(0.6)

                    # Final state should be completed
                    status_response = await client.get(f"/api/v1/ingest/status/{job_id}")
                    final_status = status_response.json()["status"]
                    assert final_status == "completed", f"Expected 'completed', got '{final_status}'"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_background_task_handles_errors_gracefully(self, auth_override):
        """Background task should catch errors and update job to FAILED status.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.main.orchestrator.ingest") as mock_ingest:
                    # Mock ingestion failure
                    mock_ingest.side_effect = Exception("GCS connection timeout")

                    # Start ingestion
                    ingest_response = await client.post("/api/v1/ingest", json={
                        "file_path": "gs://bucket/test.pdf",
                        "collection_name": "docs"
                    })
                    job_id = ingest_response.json()["job_id"]

                    # Wait for background task to fail
                    await asyncio.sleep(0.3)

                    # Check status
                    status_response = await client.get(f"/api/v1/ingest/status/{job_id}")
                    data = status_response.json()

                    assert data["status"] == "failed", f"Expected 'failed', got '{data['status']}'"
                    assert "error" in data, "Failed job must include error field"
                    assert data["error"] is not None, "Error field must not be None"
                    assert "GCS connection" in data["error"], "Error message should mention the issue"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_chunks_created(self, auth_override):
        """Status endpoint should include chunks_created for completed jobs.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                    # Start and wait for completion
                    ingest_response = await client.post("/api/v1/ingest", json={
                        "file_path": "gs://bucket/test.pdf",
                        "collection_name": "docs"
                    })
                    job_id = ingest_response.json()["job_id"]

                    await asyncio.sleep(0.3)

                    # Check status
                    status_response = await client.get(f"/api/v1/ingest/status/{job_id}")
                    data = status_response.json()

                    assert data["status"] == "completed"
                    assert "chunks_created" in data, "Completed job must include chunks_created"
                    assert data["chunks_created"] == 5, f"Expected 5 chunks (from mock), got {data['chunks_created']}"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_status_endpoint_returns_404_for_invalid_job(self, auth_override):
        """Status endpoint should return 404 for non-existent job IDs.
        """
        from app.main import app
        from app.api.middleware.auth import verify_api_key

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                response = await client.get("/api/v1/ingest/status/invalid-job-id-12345")

                assert response.status_code == 404, f"Expected 404, got {response.status_code}"
                error_data = response.json()
                assert "detail" in error_data, "404 response should include detail"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ingest_records_pending_job_metric(self, auth_override):
        """Ingest endpoint should record ingestion_jobs_total metric for pending jobs.
        """
        from app.main import app
        from app import main as main_module
        from app.services.orchestrator import OrchestratorService
        from app.api.middleware.auth import verify_api_key

        main_module.orchestrator = OrchestratorService()

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.ingest.ingestion_jobs_total") as mock_total:
                    with patch("app.main.orchestrator.ingest") as mock_ingest:
                        mock_ingest.return_value = None

                        response = await client.post("/api/v1/ingest", json={
                            "file_path": "gs://bucket/test.pdf",
                            "collection_name": "test"
                        })

                        assert response.status_code == 202

                        # Verify pending was recorded (check all calls, not just last)
                        calls = mock_total.labels.call_args_list
                        pending_calls = [c for c in calls if c[1].get('status') == 'pending']
                        assert len(pending_calls) == 1, "Should record one pending job"
                        assert pending_calls[0][1]['file_type'] == 'pdf'

                        # Wait for background task to complete
                        await asyncio.sleep(0.2)
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_ingest_increments_active_jobs_gauge(self, auth_override):
        """Ingest endpoint should increment active jobs gauge for pending jobs.
        """
        from app.main import app
        from app import main as main_module
        from app.services.orchestrator import OrchestratorService
        from app.api.middleware.auth import verify_api_key

        main_module.orchestrator = OrchestratorService()

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.ingest.ingestion_jobs_active") as mock_active:
                    with patch("app.main.orchestrator.ingest") as mock_ingest:
                        mock_ingest.return_value = None

                        response = await client.post("/api/v1/ingest", json={
                            "file_path": "gs://bucket/test.pdf",
                            "collection_name": "test"
                        })

                        assert response.status_code == 202

                        # Verify pending gauge was incremented (check immediately, before background task)
                        calls = mock_active.labels.call_args_list
                        pending_calls = [c for c in calls if c[1].get('status') == 'pending']
                        assert len(pending_calls) >= 1, "Should increment pending gauge"
                        mock_active.labels.return_value.inc.assert_called()
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_background_processing_updates_active_jobs_gauge(self, auth_override):
        """Background processing should decrement pending and increment processing gauge.
        """
        from app.main import app
        from app import main as main_module
        from app.services.orchestrator import OrchestratorService
        from app.api.middleware.auth import verify_api_key

        main_module.orchestrator = OrchestratorService()

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.ingest.ingestion_jobs_active") as mock_active:
                    with patch("app.main.orchestrator.ingest") as mock_ingest:
                        # Mock ingest to complete successfully
                        mock_ingest.return_value = None

                        response = await client.post("/api/v1/ingest", json={
                            "file_path": "gs://bucket/test.pdf",
                            "collection_name": "test"
                        })

                        assert response.status_code == 202

                        # Wait for background task to start
                        await asyncio.sleep(0.2)

                        # Verify pending gauge was decremented
                        assert mock_active.labels.call_count >= 2
                        calls = mock_active.labels.call_args_list

                        # First call: increment pending (in main endpoint)
                        assert calls[0] == ((), {"status": "pending"})

                        # Second call: decrement pending (in background task)
                        assert calls[1] == ((), {"status": "pending"})

                        # Third call: increment processing (in background task)
                        assert calls[2] == ((), {"status": "processing"})

                        # Verify dec() called on pending gauge
                        assert mock_active.labels.return_value.dec.called
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_successful_completion_decrements_processing_gauge(self, auth_override):
        """Successful job should decrement processing gauge when done.
        """
        from app.main import app
        from app import main as main_module
        from app.services.orchestrator import OrchestratorService
        from app.api.middleware.auth import verify_api_key

        main_module.orchestrator = OrchestratorService()

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.ingest.ingestion_jobs_active") as mock_active:
                    with patch("app.main.orchestrator.ingest") as mock_ingest:
                        mock_ingest.return_value = None

                        response = await client.post("/api/v1/ingest", json={
                            "file_path": "gs://bucket/test.pdf",
                            "collection_name": "test"
                        })

                        assert response.status_code == 202
                        await asyncio.sleep(0.3)

                        # Verify processing gauge was decremented (should be called twice: pending dec, processing dec)
                        assert mock_active.labels.return_value.dec.call_count >= 2
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_successful_completion_records_completed_total(self, auth_override):
        """Successful job should increment completed counter.
        """
        from app.main import app
        from app import main as main_module
        from app.services.orchestrator import OrchestratorService
        from app.api.middleware.auth import verify_api_key

        main_module.orchestrator = OrchestratorService()

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.ingest.ingestion_jobs_total") as mock_total:
                    with patch("app.main.orchestrator.ingest") as mock_ingest:
                        mock_ingest.return_value = None

                        response = await client.post("/api/v1/ingest", json={
                            "file_path": "gs://bucket/test.pdf",
                            "collection_name": "test"
                        })

                        assert response.status_code == 202
                        await asyncio.sleep(0.3)

                        # Verify completed counter was incremented
                        calls = mock_total.labels.call_args_list
                        completed_calls = [c for c in calls if c[1].get('status') == 'completed']
                        assert len(completed_calls) == 1, "Should record one completed job"
                        assert completed_calls[0][1]['file_type'] == 'pdf'
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_failed_job_records_failure_metrics(self, auth_override):
        """Failed job should decrement processing gauge and record failure counter.
        """
        from app.main import app
        from app import main as main_module
        from app.services.orchestrator import OrchestratorService
        from app.api.middleware.auth import verify_api_key

        main_module.orchestrator = OrchestratorService()

        app.dependency_overrides[verify_api_key] = auth_override
        try:
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
                with patch("app.api.v1.ingest.ingestion_jobs_active") as mock_active:
                    with patch("app.api.v1.ingest.ingestion_jobs_total") as mock_total:
                        with patch("app.main.orchestrator.ingest") as mock_ingest:
                            # Mock failure
                            mock_ingest.side_effect = Exception("Processing error")

                            response = await client.post("/api/v1/ingest", json={
                                "file_path": "gs://bucket/test.pdf",
                                "collection_name": "test"
                            })

                            assert response.status_code == 202
                            await asyncio.sleep(0.3)

                            # Verify processing gauge was decremented (pending dec + processing dec)
                            assert mock_active.labels.return_value.dec.call_count >= 2

                            # Verify failed counter was incremented
                            calls = mock_total.labels.call_args_list
                            failed_calls = [c for c in calls if c[1].get('status') == 'failed']
                            assert len(failed_calls) == 1, "Should record one failed job"
                            assert failed_calls[0][1]['file_type'] == 'pdf'
        finally:
            app.dependency_overrides.clear()
