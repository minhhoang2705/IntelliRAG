"""End-to-end integration tests for the complete observability stack.

Tests verify that all observability components (Prometheus, Grafana, Jaeger, Loki)
are deployed, healthy, and properly integrated with each other.

Prerequisites:
- Kubernetes cluster running
- Observability stack deployed (helmfile apply)
- Port-forwards active for all services:
  * kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
  * kubectl port-forward -n observability svc/grafana 3000:80
  * kubectl port-forward -n observability svc/jaeger-query 16686:16686
  * kubectl port-forward -n observability svc/loki 3100:3100
"""

import pytest
import requests


def all_services_available() -> bool:
    """Check if all observability services are accessible."""
    services = [
        ("http://localhost:9090/-/healthy", "Prometheus"),
        ("http://localhost:3000/api/health", "Grafana"),
        ("http://localhost:16686/", "Jaeger"),
        ("http://localhost:3100/ready", "Loki")
    ]

    for url, name in services:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code != 200:
                return False
        except:
            return False
    return True


@pytest.fixture(scope="module", autouse=True)
def check_all_services():
    """Verify all observability services are available."""
    if not all_services_available():
        pytest.skip(
            "Not all observability services are accessible. Ensure port-forwards are active."
        )


class TestObservabilityStackE2E:
    """End-to-end tests for the complete observability stack."""

    def test_all_services_are_healthy(self):
        """Test that all observability services are healthy."""
        # Prometheus
        prom = requests.get("http://localhost:9090/-/healthy", timeout=5)
        assert prom.status_code == 200

        # Grafana
        grafana = requests.get("http://localhost:3000/api/health", timeout=5)
        assert grafana.status_code == 200

        # Jaeger
        jaeger = requests.get("http://localhost:16686/", timeout=5)
        assert jaeger.status_code == 200

        # Loki
        loki = requests.get("http://localhost:3100/ready", timeout=5)
        assert loki.status_code == 200
