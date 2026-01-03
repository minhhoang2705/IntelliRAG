"""Shared fixtures for testing."""

import pytest
from pathlib import Path
import os


@pytest.fixture(scope="session", autouse=True)
def setup_plotly_config():
    """Create Plotly config directory for Evidently tests.

    Evidently uses Plotly for visualizations, which requires a .plotly
    directory with a .config file. This fixture ensures the directory
    exists before any tests run.
    """
    plotly_dir = Path.home() / ".plotly"
    config_file = plotly_dir / ".config"

    # Create directory if it doesn't exist
    if not plotly_dir.exists():
        plotly_dir.mkdir(parents=True, exist_ok=True)

    # Create config file with default settings if it doesn't exist
    if not config_file.exists():
        config_file.write_text('{"plotly_domain": "https://plot.ly"}')

    yield

    # Cleanup is optional - leaving .plotly directory doesn't hurt


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
def mock_orchestrator():
    """Mock orchestrator with all dependencies for unit tests.

    Returns a fully mocked OrchestratorService with all services mocked,
    preventing actual network/database connections in tests.

    Usage:
        def test_something(mock_orchestrator):
            result = await mock_orchestrator.query("test query")
    """
    from app.services.orchestrator import OrchestratorService
    from app.services.query_router.classifier import QueryType, QueryClassification
    from unittest.mock import Mock, AsyncMock

    # Create mocked services
    mock_embedding = Mock()
    mock_embedding.embed_single.return_value = [0.1] * 1024
    mock_embedding.embed_batch.return_value = [[0.1] * 1024]
    mock_embedding.get_embedding_dimension.return_value = 1024
    mock_embedding.is_healthy.return_value = True

    mock_vectordb = Mock()
    mock_vectordb.search_vectors = AsyncMock(return_value=[])
    mock_vectordb.upsert_vectors = AsyncMock()
    mock_vectordb.get_collection = AsyncMock()
    mock_vectordb.ensure_collection_with_dimension = AsyncMock()

    mock_llm = Mock()
    mock_llm.generate = AsyncMock(return_value={
        "text": "Mock answer",
        "usage": {"total_tokens": 100}
    })
    mock_llm.is_healthy = AsyncMock(return_value=True)

    # Cloud-agnostic storage loader (supports both GCS and S3)
    mock_storage_loader = Mock()
    mock_storage_loader.load_file = AsyncMock(return_value=[])
    mock_storage_loader.bucket = "test-bucket"  # Required for path extraction

    mock_chunker = Mock()
    mock_chunker.chunk_documents = AsyncMock(return_value=[])

    mock_job_mgr = Mock()
    mock_job_mgr.create_job.return_value = "test-job-123"
    mock_job_mgr.update_job_status = Mock()
    mock_job_mgr.update_job_progress = Mock()
    mock_job_mgr.get_job = Mock(return_value=Mock(status="completed"))

    mock_router = Mock()
    mock_router.route_query = AsyncMock(return_value={
        "answer": "Mock answer",
        "sources": [],
        "classification": QueryClassification(
            query_type=QueryType.DIRECT,
            confidence=0.95,
            reasoning="Test"
        )
    })

    # Create orchestrator with mocked services
    orchestrator = OrchestratorService(
        embedding_service=mock_embedding,
        vectordb_service=mock_vectordb,
        llm_client=mock_llm,
        storage_loader=mock_storage_loader,
        semantic_chunker=mock_chunker,
        job_state_manager=mock_job_mgr,
        query_router_service=mock_router
    )

    return orchestrator


def create_mock_llm_response(
    text: str = "Mock response",
    total_tokens: int = 100,
    prompt_tokens: int = 50,
    completion_tokens: int = 50,
    model: str = "Qwen/Qwen3-0.6B"
):
    """Create properly structured mock LLM response with actual int tokens."""
    from unittest.mock import Mock
    import time

    mock_response = Mock()
    mock_message = Mock()
    mock_message.content = text
    mock_choice = Mock()
    mock_choice.message = mock_message
    mock_response.choices = [mock_choice]

    # CRITICAL: Actual integers, not Mocks
    mock_usage = Mock()
    mock_usage.total_tokens = total_tokens
    mock_usage.prompt_tokens = prompt_tokens
    mock_usage.completion_tokens = completion_tokens
    mock_response.usage = mock_usage

    mock_response.model = model
    mock_response.created = int(time.time())
    mock_response.id = f"chatcmpl-{int(time.time())}"

    return mock_response


def create_mock_classification(
    query_type: str = "rag",
    confidence: float = 0.95,
    reasoning: str = "Test reasoning"
):
    """Create QueryClassification mock."""
    from unittest.mock import Mock
    from app.services.query_router.classifier import QueryType

    mock_classification = Mock()
    if query_type.lower() == "rag":
        mock_classification.query_type = QueryType.RAG
    elif query_type.lower() == "direct":
        mock_classification.query_type = QueryType.DIRECT
    else:
        mock_classification.query_type = QueryType.MULTI_HOP

    mock_classification.confidence = confidence
    mock_classification.reasoning = reasoning
    return mock_classification


def create_mock_context_manager(return_value=None):
    """Create mock supporting context manager protocol (for GCS, file operations)."""
    from unittest.mock import Mock

    mock_obj = Mock()
    mock_obj.__enter__ = Mock(return_value=return_value or mock_obj)
    mock_obj.__exit__ = Mock(return_value=False)
    return mock_obj


def create_mock_orchestrator_result(
    answer: str = "Test answer",
    sources: list = None,
    classification=None,
    used_rag: bool = False
):
    """Create orchestrator query result dict."""
    return {
        "answer": answer,
        "sources": sources or [],
        "classification": classification,
        "used_rag": used_rag
    }


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


# ========== AUTH TESTING FIXTURES ==========
# These fixtures disable authentication for endpoint testing

from app.api.middleware.auth import verify_api_key


@pytest.fixture
def mock_api_key():
    """Mock API key verification to always succeed.

    Returns a fake API key that passes validation.
    Use with app.dependency_overrides[verify_api_key].

    Usage:
        def test_endpoint(mock_api_key):
            app.dependency_overrides[verify_api_key] = lambda: mock_api_key
    """
    return "test-api-key-mock"


@pytest.fixture
def auth_override():
    """Dependency override function that bypasses API key verification.

    Returns a callable that can be used to override verify_api_key dependency.

    Usage:
        def test_endpoint(auth_override):
            app.dependency_overrides[verify_api_key] = auth_override
            client = TestClient(app)
            # Requests will bypass auth
    """
    def override_verify_api_key():
        return "test-api-key"
    return override_verify_api_key