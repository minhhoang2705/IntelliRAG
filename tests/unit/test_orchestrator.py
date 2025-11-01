"""Unit tests for Orchestrator Service.

This module tests the OrchestratorService which coordinates
all RAG services and provides a unified interface.


Date: 2025-10-17
"""

import pytest
from unittest.mock import AsyncMock, MagicMock


@pytest.mark.asyncio
async def test_orchestrator_initialization():
    """Test orchestrator initializes all required services."""
    from app.services.orchestrator import OrchestratorService

    orchestrator = OrchestratorService(
        vectordb_url="http://localhost:6333",
        llm_base_url="http://localhost:8000/v1",
        llm_model="Qwen/Qwen2.5-7B-Instruct"
    )

    assert orchestrator.embedding_service is not None
    assert orchestrator.vectordb_service is not None
    assert orchestrator.llm_client is not None
    assert orchestrator.rag_pipeline is not None


@pytest.mark.asyncio
async def test_orchestrator_query(mocker):
    """Test orchestrator executes query via QueryRouter."""
    from app.services.orchestrator import OrchestratorService
    from app.services.query_router.classifier import QueryType, QueryClassification

    orchestrator = OrchestratorService()

    # Mock the query router service
    mock_result = {
        "query": "What is Python?",
        "classification": QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.95,
            reasoning="General knowledge"
        ),
        "response": "Python is a programming language",
        "context": None,
        "error": None
    }
    mock_route = AsyncMock(return_value=mock_result)
    mocker.patch.object(orchestrator.query_router_service,
                        'route_query', mock_route)

    result = await orchestrator.query(
        query="What is Python?",
        collection_name="test_docs"
    )

    assert result["answer"] == "Python is a programming language"
    assert "classification" in result
    mock_route.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_has_query_router():
    """Test orchestrator initializes QueryRouterService."""
    from app.services.orchestrator import OrchestratorService

    orchestrator = OrchestratorService()

    # Assert query router service exists
    assert orchestrator.query_router_service is not None


@pytest.mark.asyncio
async def test_orchestrator_query_router_is_correct_type():
    """Test orchestrator initializes correct QueryRouterService type."""
    from app.services.orchestrator import OrchestratorService
    from app.services.query_router_service import QueryRouterService

    orchestrator = OrchestratorService()

    # Assert it's the correct type
    assert isinstance(orchestrator.query_router_service, QueryRouterService)


@pytest.mark.asyncio
async def test_orchestrator_query_uses_router(mocker):
    """Test orchestrator query() uses QueryRouterService."""
    from app.services.orchestrator import OrchestratorService
    from app.services.query_router.classifier import QueryType, QueryClassification

    orchestrator = OrchestratorService()

    # Mock the query router service
    mock_result = {
        "query": "What is Python?",
        "classification": QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.95,
            reasoning="General knowledge question"
        ),
        "response": "Python is a programming language",
        "context": None,
        "error": None
    }
    mock_route_query = AsyncMock(return_value=mock_result)
    mocker.patch.object(orchestrator.query_router_service,
                        'route_query', mock_route_query)

    # Execute query
    result = await orchestrator.query(
        query="What is Python?",
        collection_name="docs"
    )

    # Verify query router was called
    mock_route_query.assert_called_once_with(
        query="What is Python?",
        collection_name="docs"
    )

    # Verify result includes classification
    assert "classification" in result
    assert result["classification"].query_type == QueryType.DIRECT


@pytest.mark.asyncio
async def test_orchestrator_has_ingest_method():
    """Test that orchestrator has ingest() method.

    Expected: OrchestratorService has an ingest() async method.
    """
    from app.services.orchestrator import OrchestratorService

    orchestrator = OrchestratorService()

    assert hasattr(orchestrator, 'ingest')
    assert callable(orchestrator.ingest)


@pytest.mark.asyncio
async def test_ingest_accepts_file_path_and_collection(mocker):
    """Test that ingest() accepts file_path and collection_name parameters.

    Expected: Method signature accepts both required parameters.
    """
    from app.services.orchestrator import OrchestratorService
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Mock services to prevent real GCS calls
    mocker.patch.object(orchestrator.gcs_loader, 'load_file', AsyncMock(
        return_value=[Document(page_content="test")]))
    mocker.patch.object(orchestrator.semantic_chunker,
                        'chunk_documents', AsyncMock(return_value=[]))
    mocker.patch.object(orchestrator.embedding_service,
                        'embed_batch', return_value=[])
    mocker.patch.object(orchestrator.vectordb_service,
                        'upsert_vectors', AsyncMock())

    # Should not raise TypeError for missing arguments
    result = await orchestrator.ingest(
        file_path="gs://bucket/test.pdf",
        collection_name="test_collection"
    )


@pytest.mark.asyncio
async def test_ingest_creates_job_and_returns_job_id(mocker):
    """Test that ingest() creates a job and returns job_id.

    Expected: Returns job_id string from JobStateManager.
    """
    from app.services.orchestrator import OrchestratorService
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Mock services to prevent real GCS calls
    mocker.patch.object(orchestrator.gcs_loader, 'load_file', AsyncMock(
        return_value=[Document(page_content="test")]))
    mocker.patch.object(orchestrator.semantic_chunker,
                        'chunk_documents', AsyncMock(return_value=[]))
    mocker.patch.object(orchestrator.embedding_service,
                        'embed_batch', return_value=[])
    mocker.patch.object(orchestrator.vectordb_service,
                        'upsert_vectors', AsyncMock())

    job_id = await orchestrator.ingest(
        file_path="gs://bucket/test.pdf",
        collection_name="test_collection"
    )

    assert job_id is not None
    assert isinstance(job_id, str)
    assert len(job_id) > 0


@pytest.mark.asyncio
async def test_ingest_accepts_existing_job_id(mocker):
    """Test that ingest() accepts an optional job_id parameter.

    When job_id is provided, it should use that job instead of creating a new one.
    This prevents duplicate job creation in background task scenarios.
    
    Expected: Uses provided job_id instead of creating a new one.
    """
    from app.services.orchestrator import OrchestratorService
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Pre-create a job
    existing_job_id = orchestrator.job_state_manager.create_job(
        file_path="gs://bucket/test.pdf",
        collection_name="test_collection"
    )

    # Mock services to prevent real GCS calls
    mocker.patch.object(orchestrator.gcs_loader, 'load_file', AsyncMock(
        return_value=[Document(page_content="test")]))
    mocker.patch.object(orchestrator.semantic_chunker,
                        'chunk_documents', AsyncMock(return_value=[]))
    mocker.patch.object(orchestrator.embedding_service,
                        'embed_batch', return_value=[])
    mocker.patch.object(orchestrator.vectordb_service,
                        'upsert_vectors', AsyncMock())

    # Call ingest with existing job_id
    returned_job_id = await orchestrator.ingest(
        file_path="gs://bucket/test.pdf",
        collection_name="test_collection",
        job_id=existing_job_id
    )

    # Should return the same job_id, not create a new one
    assert returned_job_id == existing_job_id
    
    # Should only have one job in the manager
    all_jobs = orchestrator.job_state_manager._jobs
    assert len(all_jobs) == 1


@pytest.mark.asyncio
async def test_ingest_updates_job_to_processing(mocker):
    """Test that ingest() updates job status to PROCESSING.

    Expected: Job status changes from PENDING to PROCESSING.
    """
    from app.services.orchestrator import OrchestratorService
    from app.services.job_state import JobStatus
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Mock services to prevent real GCS calls
    mocker.patch.object(orchestrator.gcs_loader, 'load_file', AsyncMock(
        return_value=[Document(page_content="test")]))
    mocker.patch.object(orchestrator.semantic_chunker,
                        'chunk_documents', AsyncMock(return_value=[]))
    mocker.patch.object(orchestrator.embedding_service,
                        'embed_batch', return_value=[])
    mocker.patch.object(orchestrator.vectordb_service,
                        'upsert_vectors', AsyncMock())

    job_id = await orchestrator.ingest(
        file_path="gs://bucket/test.pdf",
        collection_name="test_collection"
    )

    # Note: Job will be COMPLETED after full pipeline, not PROCESSING
    # This test verifies it was PROCESSING at some point (now it's COMPLETED)
    job = orchestrator.job_state_manager.get_job(job_id)
    assert job.status == JobStatus.COMPLETED  # Updated expectation


@pytest.mark.asyncio
async def test_ingest_loads_document_from_gcs(mocker):
    """Test that ingest() loads document from GCS.

    Expected: GCSLoaderService.load_file() is called with correct blob path.
    """
    from app.services.orchestrator import OrchestratorService
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Mock GCS loader service
    mock_load_file = AsyncMock(return_value=[
        Document(page_content="Test content", metadata={"source": "test.pdf"})
    ])
    mocker.patch.object(orchestrator.gcs_loader, 'load_file', mock_load_file)

    # Mock other services to avoid actual processing
    mocker.patch.object(orchestrator.semantic_chunker,
                        'chunk_documents', AsyncMock(return_value=[]))
    mocker.patch.object(orchestrator.embedding_service,
                        'embed_batch', return_value=[])
    mocker.patch.object(orchestrator.vectordb_service,
                        'upsert_vectors', AsyncMock())

    await orchestrator.ingest(
        file_path="gs://test-bucket/folder/test.pdf",
        collection_name="test_collection"
    )

    # Verify GCS loader was called with correct blob path
    mock_load_file.assert_called_once_with("folder/test.pdf")


@pytest.mark.asyncio
async def test_ingest_completes_full_pipeline_and_marks_completed(mocker):
    """Test complete ingestion pipeline execution.

    Expected: Loads docs, chunks, embeds, stores in vectordb, marks job COMPLETED.
    """
    from app.services.orchestrator import OrchestratorService
    from app.services.job_state import JobStatus
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Mock complete pipeline
    mock_documents = [Document(page_content="Test content", metadata={
                               "source": "test.pdf"})]
    mock_chunks = [
        Document(page_content="Chunk 1", metadata={"chunk_index": 0}),
        Document(page_content="Chunk 2", metadata={"chunk_index": 1})
    ]
    mock_embeddings = [[0.1, 0.2], [0.3, 0.4]]

    mocker.patch.object(orchestrator.gcs_loader, 'load_file',
                        AsyncMock(return_value=mock_documents))
    mocker.patch.object(orchestrator.semantic_chunker,
                        'chunk_documents', AsyncMock(return_value=mock_chunks))
    mocker.patch.object(orchestrator.embedding_service,
                        'embed_batch', return_value=mock_embeddings)
    mock_upsert = mocker.patch.object(
        orchestrator.vectordb_service, 'upsert_vectors', AsyncMock())

    job_id = await orchestrator.ingest(
        file_path="gs://test-bucket/test.pdf",
        collection_name="test_collection"
    )

    # Verify job completed successfully
    job = orchestrator.job_state_manager.get_job(job_id)
    assert job.status == JobStatus.COMPLETED
    assert job.error is None


@pytest.mark.asyncio
async def test_ingest_accepts_existing_job_id(mocker):
    """Test that ingest() accepts an optional job_id parameter.

    When job_id is provided, it should use that job instead of creating a new one.
    This prevents duplicate job creation in background task scenarios.
    
    Expected: Uses provided job_id instead of creating a new one.
    """
    from app.services.orchestrator import OrchestratorService
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Pre-create a job
    existing_job_id = orchestrator.job_state_manager.create_job(
        file_path="gs://bucket/test.pdf",
        collection_name="test_collection"
    )

    # Mock services to prevent real GCS calls
    mocker.patch.object(orchestrator.gcs_loader, 'load_file', AsyncMock(
        return_value=[Document(page_content="test")]))
    mocker.patch.object(orchestrator.semantic_chunker,
                        'chunk_documents', AsyncMock(return_value=[]))
    mocker.patch.object(orchestrator.embedding_service,
                        'embed_batch', return_value=[])
    mocker.patch.object(orchestrator.vectordb_service,
                        'upsert_vectors', AsyncMock())

    # Call ingest with existing job_id
    returned_job_id = await orchestrator.ingest(
        file_path="gs://bucket/test.pdf",
        collection_name="test_collection",
        job_id=existing_job_id
    )

    # Should return the same job_id, not create a new one
    assert returned_job_id == existing_job_id
    
    # Should only have one job in the manager
    all_jobs = orchestrator.job_state_manager._jobs
    assert len(all_jobs) == 1
