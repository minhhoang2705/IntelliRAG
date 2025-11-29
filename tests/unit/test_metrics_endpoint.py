"""Unit tests for Prometheus metrics endpoint."""

from fastapi.testclient import TestClient


def test_metrics_endpoint_exists():
    """Test that /metrics endpoint is defined."""
    from app.main import app

    # Check if /metrics route exists
    routes = [route.path for route in app.routes]
    assert "/metrics" in routes


def test_metrics_endpoint_returns_prometheus_format():
    """Test metrics endpoint returns Prometheus format."""
    from app.main import app

    client = TestClient(app)
    response = client.get("/metrics")

    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
