"""Unit tests for orchestrator metrics recording.

Tests verify that orchestrator.ingest() records metrics for each processing stage.

Date: 2025-10-30
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch


class TestOrchestratorMetrics:
    """Test orchestrator metrics instrumentation (TDD)."""

    @pytest.mark.asyncio
    async def test_loading_stage_records_duration_metric(self):
        """Loading stage should record duration metric.

        Expected: document_processing_stage_duration_seconds recorded with stage='loading'
        RED: This should FAIL as metrics not instrumented yet.
        """
        from app.services.orchestrator import OrchestratorService
        from app.services.job_state import JobStateManager

        orchestrator = OrchestratorService()

        with patch("app.services.orchestrator.document_processing_stage_duration_seconds") as mock_duration:
            with patch.object(orchestrator.gcs_loader, "load_file", new=AsyncMock(return_value=[])):
                with patch.object(orchestrator.semantic_chunker, "chunk_documents", new=AsyncMock(return_value=[])):
                    with patch.object(orchestrator.embedding_service, "embed_batch", return_value=[]):
                        with patch.object(orchestrator.vectordb_service, "upsert_vectors", new=AsyncMock()):
                            try:
                                await orchestrator.ingest(
                                    file_path="gs://bucket/test.pdf",
                                    collection_name="test"
                                )
                            except:
                                pass  # Ignore errors, we're testing metrics

                            # Verify loading stage duration was recorded
                            calls = mock_duration.labels.call_args_list
                            loading_calls = [c for c in calls if c[1].get('stage') == 'loading']
                            assert len(loading_calls) > 0, "Should record loading stage duration"
                            assert loading_calls[0][1]['file_type'] == 'pdf'
                            mock_duration.labels.return_value.observe.assert_called()

    @pytest.mark.asyncio
    async def test_chunking_stage_records_duration_and_count(self):
        """Chunking stage should record duration and chunks created.

        Expected: document_processing_stage_duration_seconds + ingestion_chunks_created
        RED: This should FAIL as metrics not instrumented yet.
        """
        from app.services.orchestrator import OrchestratorService
        from langchain.schema import Document

        orchestrator = OrchestratorService()

        # Mock chunks
        mock_chunks = [
            Document(page_content="chunk1", metadata={}),
            Document(page_content="chunk2", metadata={}),
            Document(page_content="chunk3", metadata={})
        ]

        with patch("app.services.orchestrator.document_processing_stage_duration_seconds") as mock_duration:
            with patch("app.services.orchestrator.ingestion_chunks_created") as mock_chunks_metric:
                with patch.object(orchestrator.gcs_loader, "load_file", new=AsyncMock(return_value=[])):
                    with patch.object(orchestrator.semantic_chunker, "chunk_documents", new=AsyncMock(return_value=mock_chunks)):
                        with patch.object(orchestrator.embedding_service, "embed_batch", return_value=[[], [], []]):
                            with patch.object(orchestrator.vectordb_service, "upsert_vectors", new=AsyncMock()):
                                try:
                                    await orchestrator.ingest(
                                        file_path="gs://bucket/test.pdf",
                                        collection_name="test"
                                    )
                                except:
                                    pass

                                # Verify chunking stage duration
                                duration_calls = mock_duration.labels.call_args_list
                                chunking_calls = [c for c in duration_calls if c[1].get('stage') == 'chunking']
                                assert len(chunking_calls) > 0, "Should record chunking stage duration"

                                # Verify chunks created metric
                                mock_chunks_metric.labels.assert_called_with(file_type='pdf')
                                mock_chunks_metric.labels.return_value.observe.assert_called_with(3)

    @pytest.mark.asyncio
    async def test_embedding_stage_records_duration_metric(self):
        """Embedding stage should record duration metric.

        Expected: document_processing_stage_duration_seconds recorded with stage='embedding'
        RED: This should FAIL as metrics not instrumented yet.
        """
        from app.services.orchestrator import OrchestratorService

        orchestrator = OrchestratorService()

        with patch("app.services.orchestrator.document_processing_stage_duration_seconds") as mock_duration:
            with patch.object(orchestrator.gcs_loader, "load_file", new=AsyncMock(return_value=[])):
                with patch.object(orchestrator.semantic_chunker, "chunk_documents", new=AsyncMock(return_value=[])):
                    with patch.object(orchestrator.embedding_service, "embed_batch", return_value=[]):
                        with patch.object(orchestrator.vectordb_service, "upsert_vectors", new=AsyncMock()):
                            try:
                                await orchestrator.ingest(
                                    file_path="gs://bucket/test.pdf",
                                    collection_name="test"
                                )
                            except:
                                pass

                            # Verify embedding stage duration
                            calls = mock_duration.labels.call_args_list
                            embedding_calls = [c for c in calls if c[1].get('stage') == 'embedding']
                            assert len(embedding_calls) > 0, "Should record embedding stage duration"

    @pytest.mark.asyncio
    async def test_storage_stage_records_duration_metric(self):
        """Storage stage should record duration metric.

        Expected: document_processing_stage_duration_seconds recorded with stage='storage'
        RED: This should FAIL as metrics not instrumented yet.
        """
        from app.services.orchestrator import OrchestratorService

        orchestrator = OrchestratorService()

        with patch("app.services.orchestrator.document_processing_stage_duration_seconds") as mock_duration:
            with patch.object(orchestrator.gcs_loader, "load_file", new=AsyncMock(return_value=[])):
                with patch.object(orchestrator.semantic_chunker, "chunk_documents", new=AsyncMock(return_value=[])):
                    with patch.object(orchestrator.embedding_service, "embed_batch", return_value=[]):
                        with patch.object(orchestrator.vectordb_service, "upsert_vectors", new=AsyncMock()):
                            try:
                                await orchestrator.ingest(
                                    file_path="gs://bucket/test.pdf",
                                    collection_name="test"
                                )
                            except:
                                pass

                            # Verify storage stage duration
                            calls = mock_duration.labels.call_args_list
                            storage_calls = [c for c in calls if c[1].get('stage') == 'storage']
                            assert len(storage_calls) > 0, "Should record storage stage duration"


class TestIngestionJobDurationMetric:
    """Tests for end-to-end ingestion job duration tracking."""

    @pytest.mark.asyncio
    async def test_records_total_job_duration_on_success(self, mocker):
        """Test that successful ingestion records total job duration.
        
        Expected: ingestion_job_duration_seconds histogram records duration
        with status='completed' and correct file_type label.
        """
        from app.services.orchestrator import OrchestratorService
        from app.api.middleware.metrics import ingestion_job_duration_seconds
        from langchain_core.documents import Document

        orchestrator = OrchestratorService()

        # Mock services
        mocker.patch.object(orchestrator.gcs_loader, 'load_file', AsyncMock(
            return_value=[Document(page_content="test")]))
        mocker.patch.object(orchestrator.semantic_chunker,
                            'chunk_documents', AsyncMock(return_value=[Document(page_content="chunk")]))
        mocker.patch.object(orchestrator.embedding_service,
                            'embed_batch', return_value=[[0.1, 0.2]])
        mocker.patch.object(orchestrator.vectordb_service,
                            'upsert_vectors', AsyncMock())

        # Get initial sample count
        initial_samples = list(ingestion_job_duration_seconds.collect())[0].samples
        initial_count = sum(1 for s in initial_samples if s.name.endswith('_count'))

        # Execute ingestion
        await orchestrator.ingest(
            file_path="gs://bucket/test.pdf",
            collection_name="test"
        )

        # Get final samples
        final_samples = list(ingestion_job_duration_seconds.collect())[0].samples
        final_count = sum(1 for s in final_samples if s.name.endswith('_count'))

        # Verify metric was recorded
        assert final_count > initial_count
        
        # Find the specific sample with our labels
        count_samples = [s for s in final_samples if s.name.endswith('_count') 
                         and s.labels.get('status') == 'completed' 
                         and s.labels.get('file_type') == 'pdf']
        assert len(count_samples) > 0

    @pytest.mark.asyncio
    async def test_records_job_duration_on_failure(self, mocker):
        """Test that failed ingestion records total job duration.
        
        Expected: ingestion_job_duration_seconds histogram records duration
        with status='failed' and correct file_type label.
        """
        from app.services.orchestrator import OrchestratorService
        from app.api.middleware.metrics import ingestion_job_duration_seconds

        orchestrator = OrchestratorService()

        # Mock GCS loader to raise an error
        mocker.patch.object(orchestrator.gcs_loader, 'load_file',
                            AsyncMock(side_effect=Exception("GCS failure")))

        # Get initial sample count
        initial_samples = list(ingestion_job_duration_seconds.collect())[0].samples
        initial_count = sum(1 for s in initial_samples if s.name.endswith('_count'))

        # Execute ingestion (should fail)
        try:
            await orchestrator.ingest(
                file_path="gs://bucket/test.pdf",
                collection_name="test"
            )
        except Exception:
            pass  # Expected to fail

        # Get final samples
        final_samples = list(ingestion_job_duration_seconds.collect())[0].samples
        final_count = sum(1 for s in final_samples if s.name.endswith('_count'))

        # Verify metric was recorded
        assert final_count > initial_count
        
        # Find the specific sample with our labels
        count_samples = [s for s in final_samples if s.name.endswith('_count') 
                         and s.labels.get('status') == 'failed' 
                         and s.labels.get('file_type') == 'pdf']
        assert len(count_samples) > 0
