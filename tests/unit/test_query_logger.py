"""
Unit tests for QueryLoggerService.
"""
import pytest
from unittest.mock import AsyncMock
from app.services.query_logger import QueryLoggerService


@pytest.fixture
def mock_vectordb_service():
    """Mock VectorDBService for testing."""
    service = AsyncMock()
    service.list_collections = AsyncMock(return_value=["default"])
    service.create_collection = AsyncMock()
    service.upsert_vectors = AsyncMock()
    service.client = AsyncMock()
    service.client.scroll = AsyncMock(return_value=([], None))
    return service


@pytest.fixture
def query_logger(mock_vectordb_service):
    """QueryLoggerService instance with mocked VectorDB."""
    return QueryLoggerService(vectordb_service=mock_vectordb_service)


@pytest.mark.asyncio
class TestQueryLoggerService:
    """Test suite for QueryLoggerService."""

    async def test_initialize_collection_creates_new(self, query_logger, mock_vectordb_service):
        """Test that initialize_collection creates collection if not exists."""
        # Arrange
        mock_vectordb_service.list_collections = AsyncMock(return_value=[])
        
        # Act
        await query_logger.initialize_collection()
        
        # Assert
        mock_vectordb_service.create_collection.assert_called_once()
        call_args = mock_vectordb_service.create_collection.call_args
        assert call_args.kwargs["collection_name"] == "query_logs"
        assert call_args.kwargs["vector_size"] == 1

    async def test_initialize_collection_skips_if_exists(self, query_logger, mock_vectordb_service):
        """Test that initialize_collection skips if collection exists."""
        # Arrange
        mock_vectordb_service.list_collections = AsyncMock(return_value=["query_logs"])
        
        # Act
        await query_logger.initialize_collection()
        
        # Assert
        mock_vectordb_service.create_collection.assert_not_called()

    async def test_log_query_success(self, query_logger, mock_vectordb_service):
        """Test successful query logging."""
        # Act
        await query_logger.log_query(
            query="What is RAG?",
            response_time_ms=287.5,
            used_rag=True,
            sources_count=5,
            answer_length=450,
            query_type="factual"
        )
        
        # Assert
        mock_vectordb_service.upsert_vectors.assert_called_once()
        call_args = mock_vectordb_service.upsert_points.call_args
        
        assert call_args.kwargs["collection_name"] == "query_logs"
        points = call_args.kwargs["points"]
        assert len(points) == 1
        
        payload = points[0]["payload"]
        assert payload["query"] == "What is RAG?"
        assert payload["query_length"] == 13
        assert payload["response_time_ms"] == 287.5
        assert payload["used_rag"] is True
        assert payload["sources_count"] == 5
        assert payload["answer_length"] == 450
        assert payload["query_type"] == "factual"
        assert "timestamp" in payload
        assert "date" in payload

    async def test_log_query_handles_error(self, query_logger, mock_vectordb_service):
        """Test that log_query handles errors gracefully."""
        # Arrange
        mock_vectordb_service.upsert_points = AsyncMock(
            side_effect=Exception("Qdrant error")
        )
        
        # Act - should not raise exception
        await query_logger.log_query(
            query="test query",
            response_time_ms=100.0,
            used_rag=False,
            sources_count=0,
            answer_length=0
        )
        
        # Assert - verify error was logged but execution continued
        mock_vectordb_service.upsert_vectors.assert_called_once()

    def test_count_keywords_basic(self, query_logger):
        """Test keyword counting with basic query."""
        # Act
        count = query_logger._count_keywords("What is machine learning?")
        
        # Assert
        assert count == 2  # "machine" and "learning" (excluding stop words)

    def test_count_keywords_filters_stop_words(self, query_logger):
        """Test that stop words are filtered."""
        # Act
        count = query_logger._count_keywords("The quick brown fox")
        
        # Assert
        assert count == 3  # "quick", "brown", "fox" (excluding "the")

    def test_count_keywords_empty_query(self, query_logger):
        """Test keyword counting with empty query."""
        # Act
        count = query_logger._count_keywords("")
        
        # Assert
        assert count == 0

    async def test_get_query_logs_success(self, query_logger, mock_vectordb_service):
        """Test fetching query logs."""
        # Arrange
        from qdrant_client.models import Record
        
        mock_logs = [
            Record(
                id="1",
                vector=[0.0],
                payload={
                    "query": "test query 1",
                    "query_length": 12,
                    "date": "2025-11-27"
                }
            ),
            Record(
                id="2",
                vector=[0.0],
                payload={
                    "query": "test query 2",
                    "query_length": 13,
                    "date": "2025-11-28"
                }
            )
        ]
        mock_vectordb_service.client.scroll = AsyncMock(return_value=(mock_logs, None))
        
        # Act
        logs = await query_logger.get_query_logs(
            start_date="2025-11-27",
            end_date="2025-11-28",
            limit=100
        )
        
        # Assert
        assert len(logs) == 2
        assert logs[0]["query"] == "test query 1"
        assert logs[1]["query"] == "test query 2"
        
        mock_vectordb_service.client.scroll.assert_called_once()
        call_args = mock_vectordb_service.scroll_points.call_args
        assert call_args.kwargs["collection_name"] == "query_logs"
        assert call_args.kwargs["limit"] == 100

    async def test_get_query_logs_empty_result(self, query_logger, mock_vectordb_service):
        """Test fetching query logs with no results."""
        # Arrange
        mock_vectordb_service.scroll_points = AsyncMock(return_value=[])
        
        # Act
        logs = await query_logger.get_query_logs(
            start_date="2025-11-27",
            end_date="2025-11-28"
        )
        
        # Assert
        assert logs == []

    async def test_get_query_logs_handles_error(self, query_logger, mock_vectordb_service):
        """Test that get_query_logs handles errors gracefully."""
        # Arrange
        mock_vectordb_service.scroll_points = AsyncMock(
            side_effect=Exception("Qdrant error")
        )
        
        # Act
        logs = await query_logger.get_query_logs(
            start_date="2025-11-27",
            end_date="2025-11-28"
        )
        
        # Assert
        assert logs == []

    async def test_log_query_metadata_structure(self, query_logger, mock_vectordb_service):
        """Test that logged metadata has correct structure."""
        # Act
        await query_logger.log_query(
            query="How does attention mechanism work in transformers?",
            response_time_ms=350.2,
            used_rag=True,
            sources_count=8,
            answer_length=1200,
            query_type="technical"
        )
        
        # Assert
        call_args = mock_vectordb_service.upsert_points.call_args
        payload = call_args.kwargs["payloads"][0]
        
        # Verify all required fields
        required_fields = [
            "query", "query_length", "num_words", "num_keywords",
            "response_time_ms", "used_rag", "sources_count",
            "answer_length", "query_type", "timestamp", "date"
        ]
        for field in required_fields:
            assert field in payload, f"Missing field: {field}"
        
        # Verify data types
        assert isinstance(payload["query_length"], int)
        assert isinstance(payload["num_words"], int)
        assert isinstance(payload["num_keywords"], int)
        assert isinstance(payload["response_time_ms"], float)
        assert isinstance(payload["used_rag"], bool)
        assert isinstance(payload["sources_count"], int)
        assert isinstance(payload["answer_length"], int)

    async def test_log_query_with_none_query_type(self, query_logger, mock_vectordb_service):
        """Test logging with None query_type defaults to 'unknown'."""
        # Act
        await query_logger.log_query(
            query="test query",
            response_time_ms=100.0,
            used_rag=False,
            sources_count=0,
            answer_length=100,
            query_type=None
        )
        
        # Assert
        call_args = mock_vectordb_service.upsert_points.call_args
        payload = call_args.kwargs["payloads"][0]
        assert payload["query_type"] == "unknown"
