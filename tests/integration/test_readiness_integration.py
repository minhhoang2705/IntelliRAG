"""Integration tests for /ready endpoint with real TestClient.

Tests verify the readiness endpoint behavior in a more realistic scenario
using FastAPI's TestClient which properly handles the lifespan context.

Date: 2025-11-19
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, AsyncMock, Mock


@pytest.mark.integration
def test_readiness_endpoint_with_initialized_app():
    """Test readiness endpoint with fully initialized app.
    
    This integration test uses TestClient which triggers the lifespan
    context and initializes the orchestrator properly.
    """
    from app.main import app
    
    # Mock all external HTTP calls to avoid real dependencies
    with patch('httpx.AsyncClient') as mock_client_class:
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        
        # Mock all health checks to return success
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.elapsed = Mock()
        mock_response.elapsed.total_seconds.return_value = 0.05
        mock_client.get.return_value = mock_response
        
        mock_client_class.return_value = mock_client
        
        # Create test client (triggers lifespan and initializes orchestrator)
        with TestClient(app) as client:
            response = client.get("/ready")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verify response structure
            assert data["status"] == "ready"
            assert data["service"] == "intellirag-api"
            assert "timestamp" in data
            assert "check" in data
            
            # Verify all components checked
            required_components = ["qdrant", "llm", "embedding", "gcs"]
            for component in required_components:
                assert component in data["check"]
                assert data["check"][component]["status"] == "healthy"


@pytest.mark.integration
def test_readiness_endpoint_health_check():
    """Simple integration test to verify endpoint is accessible."""
    from app.main import app
    
    client = TestClient(app)
    
    # At minimum, endpoint should be accessible (even if services are down)
    response = client.get("/ready")
    
    # Should return either 200 or 503 (both are valid)
    assert response.status_code in [200, 503]
    
    # Should have proper JSON structure
    data = response.json()
    if response.status_code == 200:
        assert data["status"] == "ready"
    else:
        # 503 returns detail
        assert "detail" in data
        detail = data["detail"]
        assert detail["status"] == "not ready"
