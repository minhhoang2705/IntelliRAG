"""Tests for ingestion error metrics classification."""

import pytest
from unittest.mock import AsyncMock


@pytest.mark.asyncio
async def test_records_error_on_gcs_load_failure(mocker):
    """Test that GCS loading errors are classified and recorded.
    
    Expected: ingestion_errors_total counter increments with
    error_type='gcs_error' and stage='loading'.
    """
    from app.services.orchestrator import OrchestratorService
    from app.api.middleware.metrics import ingestion_errors_total

    orchestrator = OrchestratorService()

    # Mock GCS loader to raise error
    mocker.patch.object(orchestrator.gcs_loader, 'load_file',
                        AsyncMock(side_effect=Exception("GCS connection timeout")))

    # Get initial count
    initial_samples = list(ingestion_errors_total.collect())[0].samples
    initial_count = sum(s.value for s in initial_samples if s.name.endswith('_total'))

    # Execute ingestion (should fail)
    try:
        await orchestrator.ingest(
            file_path="gs://bucket/test.pdf",
            collection_name="test"
        )
    except Exception:
        pass  # Expected to fail

    # Get final count
    final_samples = list(ingestion_errors_total.collect())[0].samples
    final_count = sum(s.value for s in final_samples if s.name.endswith('_total'))

    # Verify error was recorded
    assert final_count > initial_count
    
    # Find the specific error sample
    error_samples = [s for s in final_samples if s.name.endswith('_total')
                     and s.labels.get('stage') == 'loading']
    assert len(error_samples) > 0


@pytest.mark.asyncio
async def test_records_error_on_chunking_failure(mocker):
    """Test that chunking errors are classified and recorded.
    
    Expected: ingestion_errors_total counter increments with
    error_type='chunking_error' and stage='chunking'.
    """
    from app.services.orchestrator import OrchestratorService
    from app.api.middleware.metrics import ingestion_errors_total
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Mock GCS to succeed, chunker to fail
    mocker.patch.object(orchestrator.gcs_loader, 'load_file',
                        AsyncMock(return_value=[Document(page_content="test")]))
    mocker.patch.object(orchestrator.semantic_chunker, 'chunk_documents',
                        AsyncMock(side_effect=ValueError("Chunking failed")))

    # Get initial count
    initial_samples = list(ingestion_errors_total.collect())[0].samples
    initial_count = sum(s.value for s in initial_samples if s.name.endswith('_total'))

    # Execute ingestion (should fail)
    try:
        await orchestrator.ingest(
            file_path="gs://bucket/test.pdf",
            collection_name="test"
        )
    except Exception:
        pass  # Expected to fail

    # Get final count
    final_samples = list(ingestion_errors_total.collect())[0].samples
    final_count = sum(s.value for s in final_samples if s.name.endswith('_total'))

    # Verify error was recorded
    assert final_count > initial_count
    
    # Find the specific error sample
    error_samples = [s for s in final_samples if s.name.endswith('_total')
                     and s.labels.get('stage') == 'chunking']
    assert len(error_samples) > 0


@pytest.mark.asyncio
async def test_records_error_on_embedding_failure(mocker):
    """Test that embedding errors are classified and recorded.
    
    Expected: ingestion_errors_total counter increments with
    error_type='embedding_error' and stage='embedding'.
    """
    from app.services.orchestrator import OrchestratorService
    from app.api.middleware.metrics import ingestion_errors_total
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Mock GCS and chunker to succeed, embedding to fail
    mocker.patch.object(orchestrator.gcs_loader, 'load_file',
                        AsyncMock(return_value=[Document(page_content="test")]))
    mocker.patch.object(orchestrator.semantic_chunker, 'chunk_documents',
                        AsyncMock(return_value=[Document(page_content="chunk")]))
    mocker.patch.object(orchestrator.embedding_service, 'embed_batch',
                        side_effect=RuntimeError("Model inference failed"))

    # Get initial count
    initial_samples = list(ingestion_errors_total.collect())[0].samples
    initial_count = sum(s.value for s in initial_samples if s.name.endswith('_total'))

    # Execute ingestion (should fail)
    try:
        await orchestrator.ingest(
            file_path="gs://bucket/test.pdf",
            collection_name="test"
        )
    except Exception:
        pass  # Expected to fail

    # Get final count
    final_samples = list(ingestion_errors_total.collect())[0].samples
    final_count = sum(s.value for s in final_samples if s.name.endswith('_total'))

    # Verify error was recorded
    assert final_count > initial_count
    
    # Find the specific error sample
    error_samples = [s for s in final_samples if s.name.endswith('_total')
                     and s.labels.get('stage') == 'embedding']
    assert len(error_samples) > 0


@pytest.mark.asyncio
async def test_records_error_on_storage_failure(mocker):
    """Test that vector storage errors are classified and recorded.
    
    Expected: ingestion_errors_total counter increments with
    error_type='storage_error' and stage='storage'.
    """
    from app.services.orchestrator import OrchestratorService
    from app.api.middleware.metrics import ingestion_errors_total
    from langchain_core.documents import Document

    orchestrator = OrchestratorService()

    # Mock all steps to succeed except storage
    mocker.patch.object(orchestrator.gcs_loader, 'load_file',
                        AsyncMock(return_value=[Document(page_content="test")]))
    mocker.patch.object(orchestrator.semantic_chunker, 'chunk_documents',
                        AsyncMock(return_value=[Document(page_content="chunk")]))
    mocker.patch.object(orchestrator.embedding_service, 'embed_batch',
                        return_value=[[0.1, 0.2]])
    mocker.patch.object(orchestrator.vectordb_service, 'upsert_vectors',
                        AsyncMock(side_effect=ConnectionError("Qdrant timeout")))

    # Get initial count
    initial_samples = list(ingestion_errors_total.collect())[0].samples
    initial_count = sum(s.value for s in initial_samples if s.name.endswith('_total'))

    # Execute ingestion (should fail)
    try:
        await orchestrator.ingest(
            file_path="gs://bucket/test.pdf",
            collection_name="test"
        )
    except Exception:
        pass  # Expected to fail

    # Get final count
    final_samples = list(ingestion_errors_total.collect())[0].samples
    final_count = sum(s.value for s in final_samples if s.name.endswith('_total'))

    # Verify error was recorded
    assert final_count > initial_count
    
    # Find the specific error sample
    error_samples = [s for s in final_samples if s.name.endswith('_total')
                     and s.labels.get('stage') == 'storage']
    assert len(error_samples) > 0
