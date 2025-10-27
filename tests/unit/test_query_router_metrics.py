"""Unit tests for Query Router metrics collection."""

import pytest
from unittest.mock import MagicMock, patch


def test_query_classification_metrics_exist():
    """Test that query classification metrics are defined."""
    from app.api.middleware.metrics import (
        query_classification_total,
        query_classification_confidence,
        query_classification_duration_seconds
    )
    
    assert query_classification_total is not None
    assert query_classification_confidence is not None
    assert query_classification_duration_seconds is not None


def test_query_classification_counter_has_labels():
    """Test classification counter has proper labels."""
    from app.api.middleware.metrics import query_classification_total
    
    # Counter should support query_type label
    # This will fail until we implement the metric
    assert hasattr(query_classification_total, 'labels')


def test_query_classification_confidence_is_histogram():
    """Test confidence metric is a histogram."""
    from app.api.middleware.metrics import query_classification_confidence
    from prometheus_client import Histogram
    
    assert isinstance(query_classification_confidence, Histogram)


def test_classification_duration_is_histogram():
    """Test duration metric is a histogram."""
    from app.api.middleware.metrics import query_classification_duration_seconds
    from prometheus_client import Histogram
    
    assert isinstance(query_classification_duration_seconds, Histogram)
