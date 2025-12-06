"""Integration tests for Prometheus metrics collection.

Tests verify that Prometheus is properly deployed, scraping metrics,
and that IntelliRAG application metrics are being collected.

Prerequisites:
- Kubernetes cluster running
- Observability stack deployed (helmfile apply)
- Port-forward to Prometheus: kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
"""

import pytest
import requests
from typing import Dict


def prometheus_available() -> bool:
    """Check if Prometheus is accessible via port-forward."""
    try:
        response = requests.get("http://localhost:9090/-/healthy", timeout=2)
        return response.status_code == 200
    except:
        return False


def get_prometheus_metrics(query: str) -> Dict:
    """Query Prometheus API for metrics."""
    try:
        response = requests.get(
            "http://localhost:9090/api/v1/query",
            params={"query": query},
            timeout=5
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        pytest.fail(f"Failed to query Prometheus: {e}")


@pytest.fixture(scope="module", autouse=True)
def check_prometheus():
    """Verify Prometheus is available before running tests."""
    if not prometheus_available():
        pytest.skip(
            "Prometheus not accessible. Run: kubectl port-forward -n observability "
            "svc/prometheus-kube-prometheus-prometheus 9090:9090"
        )


class TestPrometheusDeployment:
    """Test Prometheus deployment and health."""

    def test_prometheus_is_healthy(self):
        """Test that Prometheus is running and healthy."""
        response = requests.get("http://localhost:9090/-/healthy", timeout=5)
        assert response.status_code == 200
        assert response.text == "Prometheus Server is Healthy.\n"

    def test_prometheus_is_ready(self):
        """Test that Prometheus is ready to serve traffic."""
        response = requests.get("http://localhost:9090/-/ready", timeout=5)
        assert response.status_code == 200
        assert response.text == "Prometheus Server is Ready.\n"

    def test_prometheus_query_api_works(self):
        """Test that Prometheus query API is functional."""
        data = get_prometheus_metrics("up")

        assert data["status"] == "success"
        assert "data" in data
        assert "result" in data["data"]
        assert len(data["data"]["result"]) > 0, "No 'up' metrics found"

    def test_intellirag_metrics_are_available(self):
        """Test that IntelliRAG application metrics are queryable."""
        # Test for HTTP request metrics
        http_data = get_prometheus_metrics("http_requests_total")
        assert http_data["status"] == "success"

        # Test for LLM token metrics
        llm_data = get_prometheus_metrics("llm_token_count_total")
        assert llm_data["status"] == "success"

        # Note: Result may be empty if IntelliRAG app is not deployed/scraped yet
        # We're just verifying the query works without error
