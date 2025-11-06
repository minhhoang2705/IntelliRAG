"""Mocked unit tests for metrics collection (CI-friendly).

These tests verify that all defined metrics are properly exported
without requiring a running Prometheus instance.
"""

import pytest
from prometheus_client.parser import text_string_to_metric_families


class TestMetricsCollectionMocked:
    """Test suite for metrics collection with mocks."""

    @pytest.mark.asyncio
    async def test_all_metrics_exported(self, mock_metrics_response):
        """Test that all defined metrics are exported in /metrics endpoint."""
        # Parse the mocked metrics response
        metric_names = set()
        for family in text_string_to_metric_families(mock_metrics_response):
            metric_names.add(family.name)

        # Expected metrics from app/api/middleware/metrics.py
        # Note: Prometheus parser strips _total suffix from counters
        expected_metrics = [
            "query_classification",  # counter (parsed without _total)
            "query_classification_confidence",
            "query_classification_duration_seconds",
            "query_router_decisions",  # counter (parsed without _total)
            "rag_query_duration_seconds",
            "rag_retrieval_results",
            "llm_token_count",  # counter (but without _total in original name)
            "http_requests",  # counter (parsed without _total)
            "http_request_duration_seconds",
            "vector_db_operations",  # counter (parsed without _total)
            "embedding_cache_hits",  # counter (parsed without _total)
            "gpu_utilization_percent",
            "ingestion_jobs",  # counter (parsed without _total)
            "ingestion_jobs_active",
            "file_upload_duration_seconds",
            "file_upload_size_bytes",
            "document_processing_stage_duration_seconds",
            "ingestion_chunks_created",
            "ingestion_job_duration_seconds",
            "ingestion_errors",  # counter (parsed without _total)
        ]

        for metric in expected_metrics:
            assert metric in metric_names, f"Metric {metric} not exported"
