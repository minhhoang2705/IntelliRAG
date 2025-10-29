"""Unit tests for ingest API endpoints.

This module tests the POST /api/v1/ingest and GET /api/v1/ingest/status endpoints.

Date: 2025-10-29
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_ingest_endpoint_exists():
    """Test that POST /api/v1/ingest endpoint exists.

    Expected: Endpoint responds (not 404).
    """
    from app.main import app

    client = TestClient(app)
    response = client.post("/api/v1/ingest")

    assert response.status_code != 404


def test_ingest_returns_job_id(mocker):
    """Test that ingest endpoint returns a job_id.

    Expected: Response contains job_id field.
    """
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService
    from langchain_core.documents import Document

    # Initialize and mock orchestrator
    main_module.orchestrator = OrchestratorService()
    mocker.patch.object(main_module.orchestrator.gcs_loader, 'load_file', AsyncMock(return_value=[Document(page_content="test")]))
    mocker.patch.object(main_module.orchestrator.semantic_chunker, 'chunk_documents', AsyncMock(return_value=[]))
    mocker.patch.object(main_module.orchestrator.embedding_service, 'embed_batch', return_value=[])
    mocker.patch.object(main_module.orchestrator.vectordb_service, 'upsert_vectors', AsyncMock())

    client = TestClient(app)

    response = client.post("/api/v1/ingest", json={
        "file_path": "gs://bucket/test.pdf",
        "collection_name": "test"
    })

    data = response.json()
    assert "job_id" in data


def test_ingest_calls_orchestrator(mocker):
    """Test that ingest endpoint calls orchestrator.ingest().

    Expected: Orchestrator.ingest() is called with correct parameters.
    """
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService

    # Initialize orchestrator for testing
    main_module.orchestrator = OrchestratorService()

    # Mock the ingest method
    mock_ingest = AsyncMock(return_value="test-job-123")
    mocker.patch.object(main_module.orchestrator, 'ingest', mock_ingest)

    client = TestClient(app)

    payload = {
        "file_path": "gs://test-bucket/test.pdf",
        "collection_name": "test_collection"
    }

    response = client.post("/api/v1/ingest", json=payload)

    # Verify orchestrator was called
    mock_ingest.assert_called_once_with(
        file_path="gs://test-bucket/test.pdf",
        collection_name="test_collection"
    )

    # Verify response contains real job_id from orchestrator
    data = response.json()
    assert data["job_id"] == "test-job-123"


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


def test_status_returns_job_info(mocker):
    """Test that status endpoint returns job information."""
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService
    from app.services.job_state import JobStatus

    # Setup orchestrator with a completed job
    main_module.orchestrator = OrchestratorService()
    job_id = main_module.orchestrator.job_state_manager.create_job(
        "gs://bucket/test.pdf",
        "test_collection"
    )
    main_module.orchestrator.job_state_manager.update_job_status(job_id, JobStatus.COMPLETED)

    client = TestClient(app)
    response = client.get(f"/api/v1/ingest/status/{job_id}")

    data = response.json()
    assert "status" in data


def test_status_returns_complete_job_data(mocker):
    """Test that status endpoint returns complete job information."""
    from app.main import app
    from app import main as main_module
    from app.services.orchestrator import OrchestratorService
    from app.services.job_state import JobStatus

    # Setup with completed job
    main_module.orchestrator = OrchestratorService()
    job_id = main_module.orchestrator.job_state_manager.create_job(
        "gs://bucket/doc.pdf",
        "docs_collection"
    )
    main_module.orchestrator.job_state_manager.update_job_status(job_id, JobStatus.COMPLETED)

    client = TestClient(app)
    response = client.get(f"/api/v1/ingest/status/{job_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["file_path"] == "gs://bucket/doc.pdf"
    assert data["collection_name"] == "docs_collection"
    assert data["error"] is None
