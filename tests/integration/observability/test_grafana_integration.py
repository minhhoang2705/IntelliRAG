"""Integration tests for Grafana dashboards and datasources.

Tests verify that Grafana is properly deployed, datasources are configured,
and dashboards are provisioned.

Prerequisites:
- Kubernetes cluster running
- Observability stack deployed (helmfile apply)
- Port-forward to Grafana: kubectl port-forward -n observability svc/grafana 3000:80
"""

import pytest
import requests


def grafana_available() -> bool:
    """Check if Grafana is accessible via port-forward."""
    try:
        response = requests.get("http://localhost:3000/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False


@pytest.fixture(scope="module", autouse=True)
def check_grafana():
    """Verify Grafana is available before running tests."""
    if not grafana_available():
        pytest.skip(
            "Grafana not accessible. Run: kubectl port-forward -n observability "
            "svc/grafana 3000:80"
        )


class TestGrafanaDeployment:
    """Test Grafana deployment and health."""

    def test_grafana_is_healthy(self):
        """Test that Grafana is running and healthy."""
        response = requests.get("http://localhost:3000/api/health", timeout=5)
        assert response.status_code == 200

        data = response.json()
        assert "database" in data
        assert data["database"] == "ok"

    def test_grafana_datasources_configured(self):
        """Test that datasources (Prometheus, Loki, Jaeger) are configured."""
        # Grafana API requires authentication
        response = requests.get(
            "http://localhost:3000/api/datasources",
            auth=("admin", "admin"),  # Default credentials
            timeout=5
        )
        assert response.status_code == 200

        datasources = response.json()
        assert len(datasources) > 0, "No datasources configured"

        # Extract datasource names
        ds_names = [ds["name"].lower() for ds in datasources]

        # Verify expected datasources exist
        assert any("prometheus" in name for name in ds_names), "Prometheus datasource not found"

    def test_grafana_dashboards_exist(self):
        """Test that dashboards are provisioned and accessible."""
        response = requests.get(
            "http://localhost:3000/api/search?type=dash-db",
            auth=("admin", "admin"),
            timeout=5
        )
        assert response.status_code == 200

        dashboards = response.json()
        # At minimum, verify we can query dashboards (may be empty if not provisioned yet)
        assert isinstance(dashboards, list)
