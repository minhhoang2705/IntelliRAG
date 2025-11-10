"""Integration tests for Loki logging.

Tests verify that Loki is properly deployed and can receive/query logs.

Prerequisites:
- Kubernetes cluster running
- Observability stack deployed (helmfile apply)
- Port-forward to Loki: kubectl port-forward -n observability svc/loki 3100:3100
"""

import pytest
import requests


def loki_available() -> bool:
    """Check if Loki is accessible via port-forward."""
    try:
        response = requests.get("http://localhost:3100/ready", timeout=2)
        return response.status_code == 200
    except:
        return False


@pytest.fixture(scope="module", autouse=True)
def check_loki():
    """Verify Loki is available before running tests."""
    if not loki_available():
        pytest.skip(
            "Loki not accessible. Run: kubectl port-forward -n observability "
            "svc/loki 3100:3100"
        )


class TestLokiDeployment:
    """Test Loki deployment and functionality."""

    def test_loki_is_ready(self):
        """Test that Loki is ready to receive logs."""
        response = requests.get("http://localhost:3100/ready", timeout=5)
        assert response.status_code == 200
        assert response.text.strip() == "ready"
