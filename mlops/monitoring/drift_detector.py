"""
Data drift monitoring using Evidently.
Tracks input distribution shifts and model performance degradation.
"""
from evidently import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
import pandas as pd
import mlflow
from typing import Dict, Optional
import logging
from datetime import datetime, timedelta
from prometheus_client import Gauge
import os

logger = logging.getLogger(__name__)

# Prometheus metrics
DRIFT_SHARE_METRIC = Gauge(
    'evidently_drift_share',
    'Share of drifted features detected by Evidently'
)
DRIFT_DETECTION_TIMESTAMP = Gauge(
    'evidently_drift_detection_timestamp',
    'Timestamp of last drift detection run'
)

class DriftDetector:
    def __init__(
        self,
        mlflow_tracking_uri: str,
        query_logger_service: Optional['QueryLoggerService'] = None
    ):
        self.mlflow_tracking_uri = mlflow_tracking_uri
        self.query_logger = query_logger_service
        mlflow.set_tracking_uri(mlflow_tracking_uri)

    def detect_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame
    ) -> Dict:
        """
        Detect data drift between reference and current data.

        Args:
            reference_data: Historical/baseline data
            current_data: Recent data

        Returns:
            Dict with drift detection results
        """
        report = Report(metrics=[
            DataDriftPreset(),
            DataQualityPreset()
        ])

        report.run(
            reference_data=reference_data,
            current_data=current_data
        )

        results = report.as_dict()

        with mlflow.start_run(run_name=f"drift-detection-{datetime.now().isoformat()}"):
            mlflow.log_param("reference_size", len(reference_data))
            mlflow.log_param("current_size", len(current_data))

            drift_share = results["metrics"][0]["result"]["drift_share"]
            mlflow.log_metric("drift_share", drift_share)

            # Export to Prometheus
            DRIFT_SHARE_METRIC.set(drift_share)
            DRIFT_DETECTION_TIMESTAMP.set(datetime.now().timestamp())

            report_path = f"drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            report.save_html(report_path)
            mlflow.log_artifact(report_path)

            # Clean up local report file
            if os.path.exists(report_path):
                os.remove(report_path)

        logger.info(f"Drift detection complete. Drift share: {drift_share:.2%}")

        return results

    async def monitor_query_patterns(
        self,
        lookback_days: int = 7,
        use_mock_data: bool = False
    ) -> Dict:
        """
        Monitor drift in query patterns over time.
        Compares last 24 hours against previous lookback_days baseline.

        Args:
            lookback_days: Number of days for reference period
            use_mock_data: Use mock data if True, else fetch from query logs

        Returns:
            Drift detection results
        """
        logger.info(f"Monitoring query patterns (lookback: {lookback_days} days)")

        if use_mock_data or self.query_logger is None:
            logger.warning("Using mock data for drift detection")
            reference_data = self._get_mock_reference_data()
            current_data = self._get_mock_current_data()
        else:
            reference_data, current_data = await self._fetch_real_query_data(
                lookback_days
            )

        if reference_data.empty or current_data.empty:
            logger.warning("Insufficient data for drift detection")
            return {"status": "insufficient_data"}

        # Evidently v0.7.17 auto-detects column types from DataFrame
        # Ensure only numerical features are included
        numerical_features = [
            "query_length",
            "num_keywords",
            "response_time_ms",
            "sources_count"
        ]
        reference_data = reference_data[numerical_features]
        current_data = current_data[numerical_features]

        return self.detect_drift(reference_data, current_data)

    async def _fetch_real_query_data(
        self,
        lookback_days: int
    ) -> tuple[pd.DataFrame, pd.DataFrame]:
        """
        Fetch real query logs for drift detection.

        Args:
            lookback_days: Number of days for reference period

        Returns:
            Tuple of (reference_data, current_data) DataFrames
        """
        try:
            today = datetime.utcnow().date()
            yesterday = today - timedelta(days=1)

            # Reference period: lookback_days ago to 2 days ago
            reference_start = (today - timedelta(days=lookback_days + 1)).isoformat()
            reference_end = (today - timedelta(days=2)).isoformat()

            # Current period: yesterday (last 24 hours)
            current_start = yesterday.isoformat()
            current_end = yesterday.isoformat()

            # Fetch logs
            reference_logs = await self.query_logger.get_query_logs(
                start_date=reference_start,
                end_date=reference_end,
                limit=5000
            )

            current_logs = await self.query_logger.get_query_logs(
                start_date=current_start,
                end_date=current_end,
                limit=1000
            )

            logger.info(
                f"Fetched {len(reference_logs)} reference logs "
                f"and {len(current_logs)} current logs"
            )

            reference_df = pd.DataFrame(reference_logs) if reference_logs else pd.DataFrame()
            current_df = pd.DataFrame(current_logs) if current_logs else pd.DataFrame()

            # Extract relevant features
            if not reference_df.empty:
                reference_df = reference_df[[
                    "query_length",
                    "num_keywords",
                    "response_time_ms",
                    "sources_count"
                ]]

            if not current_df.empty:
                current_df = current_df[[
                    "query_length",
                    "num_keywords",
                    "response_time_ms",
                    "sources_count"
                ]]

            return reference_df, current_df

        except Exception as e:
            logger.error(f"Error fetching query data: {e}")
            return pd.DataFrame(), pd.DataFrame()

    def _get_mock_reference_data(self) -> pd.DataFrame:
        """Generate mock reference data for testing."""
        return pd.DataFrame({
            "query_length": [50, 60, 55, 70, 45, 52, 48, 65, 58, 62] * 10,
            "num_keywords": [3, 4, 3, 5, 2, 3, 2, 4, 3, 4] * 10,
            "response_time_ms": [150, 200, 180, 220, 160, 170, 190, 210, 175, 185] * 10,
            "sources_count": [3, 4, 3, 5, 2, 3, 4, 5, 3, 4] * 10
        })

    def _get_mock_current_data(self) -> pd.DataFrame:
        """Generate mock current data for testing."""
        return pd.DataFrame({
            "query_length": [80, 90, 85, 95, 75, 82, 88, 92, 78, 85] * 10,
            "num_keywords": [5, 6, 5, 7, 4, 5, 6, 6, 4, 5] * 10,
            "response_time_ms": [250, 300, 280, 320, 260, 270, 290, 310, 275, 285] * 10,
            "sources_count": [5, 6, 5, 7, 4, 5, 6, 6, 4, 5] * 10
        })
