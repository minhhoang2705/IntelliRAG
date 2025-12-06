"""Integration tests for Jaeger tracing.

Tests verify that Jaeger is properly deployed and can receive/query traces.

Prerequisites:
- Kubernetes cluster running
- Observability stack deployed (helmfile apply)
- Port-forward to Jaeger: kubectl port-forward -n observability svc/jaeger-query 16686:16686
"""

import pytest
import requests


def jaeger_available() -> bool:
    """Check if Jaeger is accessible via port-forward."""
    try:
        response = requests.get("http://localhost:16686/", timeout=2)
        return response.status_code == 200
    except:
        return False


@pytest.fixture(scope="module", autouse=True)
def check_jaeger():
    """Verify Jaeger is available before running tests."""
    if not jaeger_available():
        pytest.skip(
            "Jaeger not accessible. Run: kubectl port-forward -n observability "
            "svc/jaeger-query 16686:16686"
        )


class TestJaegerDeployment:
    """Test Jaeger deployment and functionality."""

    def test_jaeger_ui_accessible(self):
        """Test that Jaeger UI is accessible."""
        response = requests.get("http://localhost:16686/", timeout=5)
        assert response.status_code == 200
        assert b"Jaeger" in response.content or b"jaeger" in response.content

    def test_jaeger_api_services_endpoint(self):
        """Test that Jaeger API services endpoint is functional."""
        response = requests.get("http://localhost:16686/api/services", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert "data" in data
        # data can be None (no services traced yet) or a list
        assert data["data"] is None or isinstance(data["data"], list)
