"""Shared fixtures for testing."""

import pytest
from pathlib import Path


@pytest.fixture
def fixtures_dir():
    """Return the path to the fixtures directory."""
    return Path(__file__).parent / "fixtures"


@pytest.fixture
def sample_text_content():
    """Provide sample text content for testing."""
    return "This is a sample text document for testing purposes."


@pytest.fixture
def sample_csv_content():
    """Provide sample CSV content for testing."""
    return """Name,Age,City
John Doe,30,New York
Jane Smith,25,Los Angeles
Bob Johnson,35,Chicago"""


# ========== MOCK FIXTURES FOR UNIT TESTS ==========
# These fixtures prevent loading real embedding models in unit tests
# Real models (560MB+) should only be loaded in integration tests

from unittest.mock import Mock, AsyncMock
import numpy as np


@pytest.fixture
def mock_embedding_service():
    """Mock embedding service for unit tests (avoids loading real models).
    
    Returns a Mock object that simulates EmbeddingService behavior without
    loading the actual 560MB BGE-M3 model into memory.
    
    Usage:
        def test_something(mock_embedding_service):
            # Use mock instead of real service
            embedding = mock_embedding_service.embed_single("text")
    """
    service = Mock()
    service.model_id = "BAAI/bge-m3"
    service.device = "cpu"
    service.max_batch_size = 128
    service._model = None  # Not loaded
    service.get_embedding_dimension.return_value = 1024
    
    # Mock embed_single to return deterministic 1024-d vector
    service.embed_single.return_value = [0.1] * 1024
    
    # Mock embed_batch to return multiple vectors
    def mock_embed_batch(texts, **kwargs):
        return [[0.1 * (i + 1)] * 1024 for i in range(len(texts))]
    service.embed_batch.side_effect = mock_embed_batch
    
    # Mock async versions
    async def mock_embed_single_async(text):
        return [0.1] * 1024
    service.embed_single_async = AsyncMock(side_effect=mock_embed_single_async)
    
    async def mock_embed_batch_async(texts, **kwargs):
        return [[0.1 * (i + 1)] * 1024 for i in range(len(texts))]
    service.embed_batch_async = AsyncMock(side_effect=mock_embed_batch_async)
    
    return service


@pytest.fixture
def mock_sentence_transformer():
    """Mock SentenceTransformer model for unit tests.
    
    Returns a Mock object that simulates the sentence-transformers model
    without loading actual model weights (avoids 560MB+ download/load).
    
    Usage:
        def test_something(mocker, mock_sentence_transformer):
            mocker.patch('app.services.embedding.SentenceTransformer', 
                        return_value=mock_sentence_transformer)
            service = EmbeddingService()  # Won't load real model
    """
    model = Mock()
    
    # Mock encode method for both single and batch encoding
    def mock_encode(text, convert_to_numpy=False, **kwargs):
        if isinstance(text, str):
            vec = np.random.rand(1024)
        else:  # batch
            vec = np.random.rand(len(text), 1024)
        return vec if convert_to_numpy else vec.tolist()
    
    model.encode.side_effect = mock_encode
    model.to.return_value = model  # For device switching
    model.device = Mock()
    model.device.type = "cpu"

    return model


@pytest.fixture
def mock_metrics_response():
    """Mock Prometheus metrics response for testing.

    Returns a sample metrics response in Prometheus text format
    containing all IntelliRAG metrics without requiring actual HTTP calls.
    """
    return """# HELP query_classification_total Total number of query classifications
# TYPE query_classification_total counter
query_classification_total{query_type="factual"} 100
query_classification_total{query_type="conversational"} 50

# HELP query_classification_confidence Query classification confidence score
# TYPE query_classification_confidence histogram
query_classification_confidence_bucket{le="0.5"} 10
query_classification_confidence_bucket{le="0.7"} 30
query_classification_confidence_bucket{le="0.9"} 80
query_classification_confidence_bucket{le="+Inf"} 150
query_classification_confidence_sum 120.5
query_classification_confidence_count 150

# HELP query_classification_duration_seconds Time taken to classify queries
# TYPE query_classification_duration_seconds histogram
query_classification_duration_seconds_bucket{le="0.1"} 50
query_classification_duration_seconds_bucket{le="0.5"} 120
query_classification_duration_seconds_bucket{le="+Inf"} 150
query_classification_duration_seconds_sum 45.5
query_classification_duration_seconds_count 150

# HELP query_router_decisions_total Total routing decisions made
# TYPE query_router_decisions_total counter
query_router_decisions_total{decision="rag",route="retrieval"} 80
query_router_decisions_total{decision="direct",route="llm"} 70

# HELP rag_query_duration_seconds RAG pipeline stage durations
# TYPE rag_query_duration_seconds histogram
rag_query_duration_seconds_bucket{stage="embedding",le="0.1"} 40
rag_query_duration_seconds_bucket{stage="embedding",le="+Inf"} 80
rag_query_duration_seconds_bucket{stage="retrieval",le="0.1"} 60
rag_query_duration_seconds_bucket{stage="retrieval",le="+Inf"} 80

# HELP rag_retrieval_results Number of documents retrieved
# TYPE rag_retrieval_results histogram
rag_retrieval_results_bucket{le="5"} 50
rag_retrieval_results_bucket{le="10"} 100
rag_retrieval_results_bucket{le="+Inf"} 150

# HELP llm_token_count Token usage by type
# TYPE llm_token_count counter
llm_token_count{type="input"} 50000
llm_token_count{type="output"} 30000

# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/api/v1/query",status="200"} 150
http_requests_total{method="POST",endpoint="/api/v1/upload",status="200"} 50

# HELP http_request_duration_seconds HTTP request duration
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{le="0.5"} 100
http_request_duration_seconds_bucket{le="1.0"} 180
http_request_duration_seconds_bucket{le="+Inf"} 200

# HELP vector_db_operations_total Vector database operations
# TYPE vector_db_operations_total counter
vector_db_operations_total{operation="search",status="success"} 150
vector_db_operations_total{operation="insert",status="success"} 50

# HELP embedding_cache_hits_total Embedding cache hits
# TYPE embedding_cache_hits_total counter
embedding_cache_hits_total{hit="true"} 120
embedding_cache_hits_total{hit="false"} 30

# HELP gpu_utilization_percent GPU utilization percentage
# TYPE gpu_utilization_percent gauge
gpu_utilization_percent 75.5

# HELP ingestion_jobs_total Total ingestion jobs
# TYPE ingestion_jobs_total counter
ingestion_jobs_total{status="completed"} 45
ingestion_jobs_total{status="failed"} 5

# HELP ingestion_jobs_active Currently active ingestion jobs
# TYPE ingestion_jobs_active gauge
ingestion_jobs_active 3

# HELP file_upload_duration_seconds File upload duration
# TYPE file_upload_duration_seconds histogram
file_upload_duration_seconds_bucket{le="1.0"} 30
file_upload_duration_seconds_bucket{le="5.0"} 48
file_upload_duration_seconds_bucket{le="+Inf"} 50

# HELP file_upload_size_bytes File upload size
# TYPE file_upload_size_bytes histogram
file_upload_size_bytes_bucket{le="1000000"} 20
file_upload_size_bytes_bucket{le="10000000"} 45
file_upload_size_bytes_bucket{le="+Inf"} 50

# HELP document_processing_stage_duration_seconds Document processing stage duration
# TYPE document_processing_stage_duration_seconds histogram
document_processing_stage_duration_seconds_bucket{stage="parsing",le="1.0"} 40
document_processing_stage_duration_seconds_bucket{stage="parsing",le="+Inf"} 50

# HELP ingestion_chunks_created Chunks created during ingestion
# TYPE ingestion_chunks_created histogram
ingestion_chunks_created_bucket{le="50"} 20
ingestion_chunks_created_bucket{le="100"} 45
ingestion_chunks_created_bucket{le="+Inf"} 50
ingestion_chunks_created_sum 2500
ingestion_chunks_created_count 50

# HELP ingestion_job_duration_seconds Total ingestion job duration
# TYPE ingestion_job_duration_seconds histogram
ingestion_job_duration_seconds_bucket{le="10"} 30
ingestion_job_duration_seconds_bucket{le="30"} 48
ingestion_job_duration_seconds_bucket{le="+Inf"} 50

# HELP ingestion_errors_total Ingestion errors
# TYPE ingestion_errors_total counter
ingestion_errors_total{error_type="parse_error"} 3
ingestion_errors_total{error_type="timeout"} 2
"""