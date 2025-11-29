"""
Unit tests for DriftDetector with real data integration.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import pandas as pd
from datetime import datetime, timedelta
from mlops.monitoring.drift_detector import DriftDetector


@pytest.fixture
def mock_query_logger():
    """Mock QueryLoggerService for testing."""
    logger = AsyncMock()
    logger.get_query_logs = AsyncMock(return_value=[])
    return logger


@pytest.fixture
def drift_detector(mock_query_logger):
    """DriftDetector instance with mocked dependencies."""
    with patch('mlflow.set_tracking_uri'):
        detector = DriftDetector(
            mlflow_tracking_uri="http://test-mlflow:5000",
            query_logger_service=mock_query_logger
        )
    return detector


@pytest.fixture
def sample_reference_logs():
    """Sample reference query logs."""
    return [
        {
            "query_length": 50,
            "num_keywords": 3,
            "response_time_ms": 150.0,
            "sources_count": 3,
            "date": "2025-11-20"
        },
        {
            "query_length": 60,
            "num_keywords": 4,
            "response_time_ms": 200.0,
            "sources_count": 4,
            "date": "2025-11-21"
        },
        {
            "query_length": 55,
            "num_keywords": 3,
            "response_time_ms": 180.0,
            "sources_count": 3,
            "date": "2025-11-22"
        }
    ]


@pytest.fixture
def sample_current_logs():
    """Sample current query logs."""
    return [
        {
            "query_length": 80,
            "num_keywords": 5,
            "response_time_ms": 250.0,
            "sources_count": 5,
            "date": "2025-11-27"
        },
        {
            "query_length": 90,
            "num_keywords": 6,
            "response_time_ms": 300.0,
            "sources_count": 6,
            "date": "2025-11-27"
        }
    ]


@pytest.mark.asyncio
class TestDriftDetector:
    """Test suite for DriftDetector."""

    async def test_monitor_query_patterns_with_mock_data(self, drift_detector):
        """Test drift detection with mock data."""
        # Mock MLFlow context
        with patch('mlflow.start_run') as mock_run:
            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock()
            
            with patch('mlops.monitoring.drift_detector.DRIFT_SHARE_METRIC'):
                with patch('mlops.monitoring.drift_detector.DRIFT_DETECTION_TIMESTAMP'):
                    # Act
                    result = await drift_detector.monitor_query_patterns(
                        lookback_days=7,
                        use_mock_data=True
                    )
                    
                    # Assert
                    assert result is not None
                    assert "metrics" in result

    async def test_fetch_real_query_data_success(
        self,
        drift_detector,
        mock_query_logger,
        sample_reference_logs,
        sample_current_logs
    ):
        """Test fetching real query data from logs."""
        # Arrange
        mock_query_logger.get_query_logs = AsyncMock(
            side_effect=[sample_reference_logs, sample_current_logs]
        )
        drift_detector.query_logger = mock_query_logger
        
        # Act
        reference_df, current_df = await drift_detector._fetch_real_query_data(
            lookback_days=7
        )
        
        # Assert
        assert not reference_df.empty
        assert not current_df.empty
        assert len(reference_df) == 3
        assert len(current_df) == 2
        
        # Verify columns
        expected_columns = ["query_length", "num_keywords", "response_time_ms", "sources_count"]
        assert list(reference_df.columns) == expected_columns
        assert list(current_df.columns) == expected_columns
        
        # Verify get_query_logs was called twice
        assert mock_query_logger.get_query_logs.call_count == 2

    async def test_fetch_real_query_data_empty_logs(self, drift_detector, mock_query_logger):
        """Test fetching data when no logs available."""
        # Arrange
        mock_query_logger.get_query_logs = AsyncMock(return_value=[])
        drift_detector.query_logger = mock_query_logger
        
        # Act
        reference_df, current_df = await drift_detector._fetch_real_query_data(
            lookback_days=7
        )
        
        # Assert
        assert reference_df.empty
        assert current_df.empty

    async def test_fetch_real_query_data_handles_error(self, drift_detector, mock_query_logger):
        """Test error handling when fetching logs fails."""
        # Arrange
        mock_query_logger.get_query_logs = AsyncMock(
            side_effect=Exception("Database error")
        )
        drift_detector.query_logger = mock_query_logger
        
        # Act
        reference_df, current_df = await drift_detector._fetch_real_query_data(
            lookback_days=7
        )
        
        # Assert
        assert reference_df.empty
        assert current_df.empty

    async def test_monitor_query_patterns_insufficient_data(
        self,
        drift_detector,
        mock_query_logger
    ):
        """Test drift detection with insufficient data."""
        # Arrange
        mock_query_logger.get_query_logs = AsyncMock(return_value=[])
        drift_detector.query_logger = mock_query_logger
        
        # Act
        result = await drift_detector.monitor_query_patterns(
            lookback_days=7,
            use_mock_data=False
        )
        
        # Assert
        assert result == {"status": "insufficient_data"}

    async def test_monitor_query_patterns_real_data(
        self,
        drift_detector,
        mock_query_logger,
        sample_reference_logs,
        sample_current_logs
    ):
        """Test drift detection with real data."""
        # Arrange
        mock_query_logger.get_query_logs = AsyncMock(
            side_effect=[sample_reference_logs, sample_current_logs]
        )
        drift_detector.query_logger = mock_query_logger
        
        # Mock MLFlow and Prometheus
        with patch('mlflow.start_run') as mock_run:
            mock_run.return_value.__enter__ = MagicMock(
                return_value=MagicMock(info=MagicMock(run_id="test123"))
            )
            mock_run.return_value.__exit__ = MagicMock()
            
            with patch('mlflow.log_param'):
                with patch('mlflow.log_metric'):
                    with patch('mlflow.log_artifact'):
                        with patch('mlops.monitoring.drift_detector.DRIFT_SHARE_METRIC'):
                            with patch('mlops.monitoring.drift_detector.DRIFT_DETECTION_TIMESTAMP'):
                                # Act
                                result = await drift_detector.monitor_query_patterns(
                                    lookback_days=7,
                                    use_mock_data=False
                                )
                                
                                # Assert
                                assert result is not None
                                assert "metrics" in result

    def test_get_mock_reference_data(self, drift_detector):
        """Test mock reference data generation."""
        # Act
        df = drift_detector._get_mock_reference_data()
        
        # Assert
        assert not df.empty
        assert len(df) == 100  # 10 * 10
        assert list(df.columns) == [
            "query_length",
            "num_keywords",
            "response_time_ms",
            "sources_count"
        ]
        
        # Check data ranges
        assert df["query_length"].min() >= 45
        assert df["query_length"].max() <= 70
        assert df["num_keywords"].min() >= 2
        assert df["num_keywords"].max() <= 5

    def test_get_mock_current_data(self, drift_detector):
        """Test mock current data generation."""
        # Act
        df = drift_detector._get_mock_current_data()
        
        # Assert
        assert not df.empty
        assert len(df) == 100  # 10 * 10
        assert list(df.columns) == [
            "query_length",
            "num_keywords",
            "response_time_ms",
            "sources_count"
        ]
        
        # Check data ranges (should be higher than reference)
        assert df["query_length"].min() >= 75
        assert df["query_length"].max() <= 95

    def test_detect_drift_basic(self, drift_detector):
        """Test basic drift detection."""
        # Arrange
        from evidently import ColumnMapping
        
        reference_data = pd.DataFrame({
            "query_length": [50, 60, 55] * 10,
            "num_keywords": [3, 4, 3] * 10
        })
        
        current_data = pd.DataFrame({
            "query_length": [80, 90, 85] * 10,
            "num_keywords": [5, 6, 5] * 10
        })
        
        column_mapping = ColumnMapping()
        column_mapping.numerical_features = ["query_length", "num_keywords"]
        
        # Mock MLFlow and Prometheus
        with patch('mlflow.start_run') as mock_run:
            mock_run.return_value.__enter__ = MagicMock()
            mock_run.return_value.__exit__ = MagicMock()
            
            with patch('mlflow.log_param'):
                with patch('mlflow.log_metric'):
                    with patch('mlflow.log_artifact'):
                        with patch('mlops.monitoring.drift_detector.DRIFT_SHARE_METRIC'):
                            with patch('mlops.monitoring.drift_detector.DRIFT_DETECTION_TIMESTAMP'):
                                with patch('os.path.exists', return_value=True):
                                    with patch('os.remove'):
                                        # Act
                                        result = drift_detector.detect_drift(
                                            reference_data,
                                            current_data,
                                            column_mapping
                                        )
                                        
                                        # Assert
                                        assert result is not None
                                        assert "metrics" in result
                                        assert len(result["metrics"]) > 0

    async def test_monitor_query_patterns_uses_mock_when_no_logger(self):
        """Test that mock data is used when query_logger is None."""
        # Arrange
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
                        with patch('mlops.monitoring.drift_detector.DRIFT_SHARE_METRIC'):
                            with patch('mlops.monitoring.drift_detector.DRIFT_DETECTION_TIMESTAMP'):
                                # Act
                                result = await detector.monitor_query_patterns(
                                    lookback_days=7,
                                    use_mock_data=False  # Should fall back to mock
                                )
                                
                                # Assert
                                assert result is not None
                                assert "metrics" in result

    async def test_fetch_real_query_data_date_calculation(
        self,
        drift_detector,
        mock_query_logger
    ):
        """Test that date ranges are calculated correctly."""
        # Arrange
        mock_query_logger.get_query_logs = AsyncMock(return_value=[])
        drift_detector.query_logger = mock_query_logger
        
        # Act
        await drift_detector._fetch_real_query_data(lookback_days=7)
        
        # Assert
        assert mock_query_logger.get_query_logs.call_count == 2
        
        # Check reference period call
        ref_call = mock_query_logger.get_query_logs.call_args_list[0]
        ref_start = ref_call.kwargs["start_date"]
        ref_end = ref_call.kwargs["end_date"]
        
        # Check current period call
        curr_call = mock_query_logger.get_query_logs.call_args_list[1]
        curr_start = curr_call.kwargs["start_date"]
        curr_end = curr_call.kwargs["end_date"]
        
        # Verify dates are in correct format
        assert len(ref_start) == 10  # YYYY-MM-DD
        assert len(ref_end) == 10
        assert len(curr_start) == 10
        assert len(curr_end) == 10
        
        # Verify current period is yesterday
        today = datetime.utcnow().date()
        yesterday = (today - timedelta(days=1)).isoformat()
        assert curr_start == yesterday
        assert curr_end == yesterday
