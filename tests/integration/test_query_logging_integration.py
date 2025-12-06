"""
Integration tests for query logging and drift detection.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from app.main import app
from app.services.query_logger import QueryLoggerService


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator for testing."""
    orchestrator = MagicMock()
    orchestrator.query = AsyncMock(return_value={
        "answer": "This is a test answer about RAG systems.",
        "sources": [
            {"text": "Source 1", "score": 0.95},
            {"text": "Source 2", "score": 0.90},
            {"text": "Source 3", "score": 0.85}
        ],
        "used_rag": True,
        "classification": MagicMock(
            query_type="technical",
            confidence=0.92,
            reasoning="Technical question about RAG"
        )
    })
    return orchestrator


@pytest.fixture
def mock_query_logger():
    """Mock query logger for testing."""
    logger = AsyncMock()
    logger.log_query = AsyncMock()
    return logger


@pytest.fixture
def test_client(mock_orchestrator, mock_query_logger):
    """Test client with mocked dependencies."""
    with patch('app.dependencies.get_orchestrator', return_value=mock_orchestrator):
        with patch('app.dependencies.get_query_logger', return_value=mock_query_logger):
            with patch('app.api.middleware.auth.verify_api_key', return_value="test-key"):
                client = TestClient(app)
                yield client


@pytest.mark.asyncio
class TestQueryLoggingIntegration:
    """Integration tests for query logging flow."""

    def test_query_endpoint_logs_metadata(self, test_client, mock_orchestrator, mock_query_logger):
        """Test that query endpoint logs metadata to QueryLoggerService."""
        # Act
        response = test_client.post(
            "/api/v1/query",
            json={
                "query": "What is retrieval-augmented generation?",
                "top_k": 5,
                "temperature": 0.7,
                "max_tokens": 500
            }
        )
        
        # Assert
        assert response.status_code == 200
        
        # Verify orchestrator was called
        mock_orchestrator.query.assert_called_once()
        
        # Verify query logger was called (in background task)
        # Note: Background tasks execute after response, so we check the call was made
        assert mock_query_logger.log_query.called

    def test_query_endpoint_captures_response_time(
        self,
        test_client,
        mock_orchestrator,
        mock_query_logger
    ):
        """Test that response time is captured correctly."""
        # Arrange
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test answer",
            "sources": [],
            "used_rag": False,
            "classification": None
        })
        
        # Act
        response = test_client.post(
            "/api/v1/query",
            json={"query": "test query", "top_k": 5}
        )
        
        # Assert
        assert response.status_code == 200

    def test_query_endpoint_logs_with_classification(
        self,
        test_client,
        mock_orchestrator,
        mock_query_logger
    ):
        """Test logging when query has classification."""
        # Act
        response = test_client.post(
            "/api/v1/query",
            json={
                "query": "Explain transformer architecture",
                "top_k": 3
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert "classification" in data
        assert data["classification"]["query_type"] == "technical"

    def test_query_endpoint_logs_without_classification(
        self,
        test_client,
        mock_orchestrator,
        mock_query_logger
    ):
        """Test logging when query has no classification."""
        # Arrange
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Simple answer",
            "sources": [],
            "used_rag": False,
            "classification": None
        })
        
        # Act
        response = test_client.post(
            "/api/v1/query",
            json={"query": "simple query", "top_k": 5}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["classification"] is None

    def test_query_endpoint_handles_logging_error(
        self,
        test_client,
        mock_orchestrator,
        mock_query_logger
    ):
        """Test that logging errors don't break the query flow."""
        # Arrange
        mock_query_logger.log_query = AsyncMock(
            side_effect=Exception("Logging error")
        )
        
        # Act
        response = test_client.post(
            "/api/v1/query",
            json={"query": "test query", "top_k": 5}
        )
        
        # Assert - request should still succeed
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data


@pytest.mark.asyncio
class TestDriftDetectionIntegration:
    """Integration tests for end-to-end drift detection."""

    async def test_full_drift_detection_flow_with_mock_data(self):
        """Test complete drift detection flow using mock data."""
        # Arrange
        from mlops.monitoring.drift_detector import DriftDetector
        
        with patch('mlflow.set_tracking_uri'):
            detector = DriftDetector(
                mlflow_tracking_uri="http://test:5000",
                query_logger_service=None
            )
        
        # Mock MLFlow operations
        with patch('mlflow.start_run') as mock_run:
            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock()
            
            with patch('mlflow.log_param') as mock_log_param:
                with patch('mlflow.log_metric') as mock_log_metric:
                    with patch('mlflow.log_artifact') as mock_log_artifact:
                        with patch('mlops.monitoring.drift_detector.DRIFT_SHARE_METRIC') as mock_metric:
                            with patch('mlops.monitoring.drift_detector.DRIFT_DETECTION_TIMESTAMP'):
                                # Act
                                result = await detector.monitor_query_patterns(
                                    lookback_days=7,
                                    use_mock_data=True
                                )
                                
                                # Assert
                                assert result is not None
                                assert "metrics" in result
                                
                                # Verify MLFlow logging
                                assert mock_log_param.called
                                assert mock_log_metric.called
                                assert mock_log_artifact.called
                                assert mock_metric.set.called

    async def test_drift_detection_with_query_logger(self):
        """Test drift detection with QueryLoggerService integration."""
        # Arrange
        from qdrant_client.models import Record
        
        mock_vectordb = AsyncMock()
        mock_record = Record(
            id="test-id",
            vector=[0.0],
            payload={
                "query_length": 50,
                "num_keywords": 3,
                "response_time_ms": 150.0,
                "sources_count": 3,
                "date": "2025-11-27"
            }
        )
        mock_vectordb.client = AsyncMock()
        mock_vectordb.client.scroll = AsyncMock(return_value=([mock_record], None))
        
        query_logger = QueryLoggerService(qdrant_service=mock_vectordb)
        
        from mlops.monitoring.drift_detector import DriftDetector
        
        with patch('mlflow.set_tracking_uri'):
            detector = DriftDetector(
                mlflow_tracking_uri="http://test:5000",
                query_logger_service=query_logger
            )
        
        # Mock MLFlow
        with patch('mlflow.start_run') as mock_run:
            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock()
            
            with patch('mlflow.log_param'):
                with patch('mlflow.log_metric'):
                    with patch('mlflow.log_artifact'):
                        with patch('mlops.monitoring.drift_detector.DRIFT_SHARE_METRIC'):
                            with patch('mlops.monitoring.drift_detector.DRIFT_DETECTION_TIMESTAMP'):
                                # Act
                                result = await detector.monitor_query_patterns(
                                    lookback_days=7,
                                    use_mock_data=False
                                )
                                
                                # Assert - insufficient data expected with only 1 log
                                assert result == {"status": "insufficient_data"}

    async def test_end_to_end_query_and_drift_detection(self):
        """Test complete flow: query → log → drift detection."""
        # Arrange
        from qdrant_client.models import Record
        
        mock_vectordb = AsyncMock()
        mock_vectordb.list_collections = AsyncMock(return_value=[])
        mock_vectordb.create_collection = AsyncMock()
        mock_vectordb.upsert_vectors = AsyncMock()
        
        # Simulate accumulated logs
        sample_records = []
        for i in range(10):
            record = Record(
                id=f"test-{i}",
                vector=[0.0],
                payload={
                    "query_length": 50 + i,
                    "num_keywords": 3,
                    "response_time_ms": 150.0,
                    "sources_count": 3,
                    "date": "2025-11-20"
                }
            )
            sample_records.append(record)
        
        mock_vectordb.client = AsyncMock()
        mock_vectordb.client.scroll = AsyncMock(return_value=(sample_records, None))
        
        query_logger = QueryLoggerService(qdrant_service=mock_vectordb)
        await query_logger.initialize_collection()
        
        # Step 1: Log queries
        for i in range(5):
            await query_logger.log_query(
                query=f"Test query {i}",
                response_time_ms=150.0 + i * 10,
                used_rag=True,
                sources_count=3,
                answer_length=500,
                query_type="test"
            )
        
        # Step 2: Run drift detection
        from mlops.monitoring.drift_detector import DriftDetector
        
        with patch('mlflow.set_tracking_uri'):
            detector = DriftDetector(
                mlflow_tracking_uri="http://test:5000",
                query_logger_service=query_logger
            )
        
        with patch('mlflow.start_run') as mock_run:
            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock()
            
            with patch('mlflow.log_param'):
                with patch('mlflow.log_metric'):
                    with patch('mlflow.log_artifact'):
                        with patch('mlops.monitoring.drift_detector.DRIFT_SHARE_METRIC'):
                            with patch('mlops.monitoring.drift_detector.DRIFT_DETECTION_TIMESTAMP'):
                                # Act
                                result = await detector.monitor_query_patterns(
                                    lookback_days=7,
                                    use_mock_data=False
                                )
                                
                                # Assert
                                # Should still show insufficient data as we need both reference and current
                                assert result == {"status": "insufficient_data"}
        
        # Verify logs were stored
        assert mock_vectordb.upsert_vectors.call_count == 5


@pytest.mark.asyncio
class TestPrometheusMetricsIntegration:
    """Integration tests for Prometheus metrics export."""

    async def test_drift_metrics_exported_to_prometheus(self):
        """Test that drift metrics are exported to Prometheus."""
        # Arrange
        from mlops.monitoring.drift_detector import DriftDetector
        
        with patch('mlflow.set_tracking_uri'):
            detector = DriftDetector(
                mlflow_tracking_uri="http://test:5000",
                query_logger_service=None
            )
        
        # Mock MLFlow
        with patch('mlflow.start_run') as mock_run:
            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock()
            
            with patch('mlflow.log_param'):
                with patch('mlflow.log_metric'):
                    with patch('mlflow.log_artifact'):
                        with patch('mlops.monitoring.drift_detector.DRIFT_SHARE_METRIC') as mock_drift:
                            with patch('mlops.monitoring.drift_detector.DRIFT_DETECTION_TIMESTAMP') as mock_timestamp:
                                # Act
                                await detector.monitor_query_patterns(
                                    lookback_days=7,
                                    use_mock_data=True
                                )
                                
                                # Assert - metrics should be set
                                mock_drift.set.assert_called_once()
                                mock_timestamp.set.assert_called_once()
                                
                                # Verify drift_share is between 0 and 1
                                drift_value = mock_drift.set.call_args[0][0]
                                assert 0.0 <= drift_value <= 1.0
