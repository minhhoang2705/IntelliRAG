"""Unit tests for HTTP MetricsMiddleware.

This module tests Prometheus HTTP metrics instrumentation.
"""

from fastapi import FastAPI
from fastapi.testclient import TestClient
from prometheus_client import REGISTRY


def get_metric_value(metric_name: str, labels: dict = None) -> float:
    """Helper to extract metric value from Prometheus registry.

    Args:
        metric_name: Name of the Prometheus metric (e.g., 'http_requests_total')
        labels: Dictionary of label key-value pairs to match

    Returns:
        Metric value or 0 if not found
    """
    for collector in REGISTRY.collect():
        for sample in collector.samples:
            # Match sample name directly (not collector name)
            if sample.name == metric_name:
                if labels is None:
                    return sample.value
                # Check if all labels match
                if all(sample.labels.get(k) == v for k, v in labels.items()):
                    return sample.value
    return 0


def test_metrics_middleware_tracks_request_count():
    """Test that http_requests_total increments on each request.

    This is the FIRST test - it will FAIL until MetricsMiddleware is implemented.
    Expected failure: ModuleNotFoundError or ImportError for metrics_middleware.
    """
    from app.api.middleware.metrics_middleware import MetricsMiddleware

    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # Get initial count
    initial_count = get_metric_value(
        'http_requests_total',
        labels={'method': 'GET', 'endpoint': '/test', 'status_code': '200'}
    )

    # Make request
    response = client.get("/test")
    assert response.status_code == 200

    # Verify metric incremented
    final_count = get_metric_value(
        'http_requests_total',
        labels={'method': 'GET', 'endpoint': '/test', 'status_code': '200'}
    )

    assert final_count == initial_count + 1, \
        f"Expected http_requests_total to increment from {initial_count} to {initial_count + 1}, got {final_count}"


def test_metrics_middleware_tracks_request_duration():
    """Test that http_request_duration_seconds records request latency.

    This test will FAIL until we add duration tracking to MetricsMiddleware.
    """
    from app.api.middleware.metrics_middleware import MetricsMiddleware

    app = FastAPI()
    app.add_middleware(MetricsMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)

    # Make request
    response = client.get("/test")
    assert response.status_code == 200

    # Verify histogram recorded the duration (_count suffix for histogram)
    duration_count = get_metric_value(
        'http_request_duration_seconds_count',
        labels={'method': 'GET', 'endpoint': '/test'}
    )

    assert duration_count > 0, \
        f"http_request_duration_seconds should record latency, got count={duration_count}"
