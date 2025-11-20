"""Unit tests for /ready readiness endpoint.

Tests verify that the readiness probe correctly checks all dependencies
and returns appropriate status codes.

Date: 2025-11-19
"""

import pytest
from unittest.mock import AsyncMock, patch, Mock
from fastapi.testclient import TestClient
from httpx import Response
import time


class TestReadinessEndpoint:
    """Test suite for /ready endpoint."""

    @pytest.fixture
    def mock_orchestrator(self):
        """Create mock orchestrator with all required attributes."""
        mock_orch = Mock()
        mock_orch.vectordb_url = "http://localhost:6333"
        mock_orch.llm_base_url = "http://localhost:8000/v1"
        mock_orch.embedding_service_url = "http://localhost:8001"
        mock_orch.gcs_bucket = "test-bucket"
        return mock_orch

    @pytest.fixture
    def mock_healthy_response(self):
        """Create mock HTTP response for healthy service."""
        response = Mock(spec=Response)
        response.status_code = 200
        response.elapsed = Mock()
        response.elapsed.total_seconds.return_value = 0.05
        return response

    @pytest.fixture
    def mock_unhealthy_response(self):
        """Create mock HTTP response for unhealthy service."""
        response = Mock(spec=Response)
        response.status_code = 503
        response.elapsed = Mock()
        response.elapsed.total_seconds.return_value = 0.1
        return response

    @pytest.mark.asyncio
    async def test_all_services_healthy(self, mock_orchestrator, mock_healthy_response):
        """Test readiness when all services are healthy.
        
        RED: This test should FAIL initially because:
        - Implementation doesn't handle orchestrator properly
        - Need to verify all components return healthy status
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                mock_async_client.get.return_value = mock_healthy_response
                mock_client.return_value = mock_async_client

                client = TestClient(main.app)
                response = client.get("/ready")

                assert response.status_code == 200
                data = response.json()
                
                assert data["status"] == "ready"
                assert data["service"] == "intellirag-api"
                assert "timestamp" in data
                assert "check" in data
                
                # Verify all components are healthy
                assert data["check"]["qdrant"]["status"] == "healthy"
                assert data["check"]["llm"]["status"] == "healthy"
                assert data["check"]["embedding"]["status"] == "healthy"
                assert data["check"]["gcs"]["status"] == "healthy"
                
                # Verify response times are present
                assert "response_time" in data["check"]["qdrant"]
                assert "response_time" in data["check"]["llm"]
                assert "response_time" in data["check"]["embedding"]

    @pytest.mark.asyncio
    async def test_qdrant_unhealthy(self, mock_orchestrator, mock_healthy_response, mock_unhealthy_response):
        """Test readiness when Qdrant is unhealthy.
        
        RED: Should FAIL - need to verify proper 503 response
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                
                async def mock_get(url, *args, **kwargs):
                    if "qdrant" in url or "6333" in url:
                        return mock_unhealthy_response
                    return mock_healthy_response
                
                mock_async_client.get.side_effect = mock_get
                mock_client.return_value = mock_async_client

                client = TestClient(main.app)
                response = client.get("/ready")

                assert response.status_code == 503
                data = response.json()
                
                assert "detail" in data
                detail = data["detail"]
                assert detail["status"] == "not ready"
                assert detail["check"]["qdrant"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_llm_unhealthy(self, mock_orchestrator, mock_healthy_response, mock_unhealthy_response):
        """Test readiness when LLM endpoint is unhealthy.
        
        RED: Should FAIL - verify LLM failure handling
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                
                async def mock_get(url, *args, **kwargs):
                    if "8000" in url:
                        return mock_unhealthy_response
                    return mock_healthy_response
                
                mock_async_client.get.side_effect = mock_get
                mock_client.return_value = mock_async_client

                client = TestClient(main.app)
                response = client.get("/ready")

                assert response.status_code == 503
                data = response.json()
                
                assert "detail" in data
                detail = data["detail"]
                assert detail["status"] == "not ready"
                assert detail["check"]["llm"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_embedding_unhealthy(self, mock_orchestrator, mock_healthy_response, mock_unhealthy_response):
        """Test readiness when embedding service is unhealthy.
        
        RED: Should FAIL - verify embedding service failure handling
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                
                async def mock_get(url, *args, **kwargs):
                    if "8001" in url:
                        return mock_unhealthy_response
                    return mock_healthy_response
                
                mock_async_client.get.side_effect = mock_get
                mock_client.return_value = mock_async_client

                client = TestClient(main.app)
                response = client.get("/ready")

                assert response.status_code == 503
                data = response.json()
                
                assert "detail" in data
                detail = data["detail"]
                assert detail["status"] == "not ready"
                assert detail["check"]["embedding"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_gcs_bucket_not_configured(self, mock_orchestrator, mock_healthy_response):
        """Test readiness when GCS bucket is not configured.
        
        RED: Should FAIL - verify GCS check failure handling
        """
        from app import main
        
        mock_orchestrator.gcs_bucket = None
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                mock_async_client.get.return_value = mock_healthy_response
                mock_client.return_value = mock_async_client

                client = TestClient(main.app)
                response = client.get("/ready")

                assert response.status_code == 503
                data = response.json()
                
                assert "detail" in data
                detail = data["detail"]
                assert detail["status"] == "not ready"
                assert detail["check"]["gcs"]["status"] == "unhealthy"
                assert "not configured" in detail["check"]["gcs"]["error"].lower()

    @pytest.mark.asyncio
    async def test_multiple_services_unhealthy(self, mock_orchestrator, mock_unhealthy_response):
        """Test readiness when multiple services are unhealthy.
        
        RED: Should FAIL - verify handling of multiple failures
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                mock_async_client.get.return_value = mock_unhealthy_response
                mock_client.return_value = mock_async_client

                client = TestClient(main.app)
                response = client.get("/ready")

                assert response.status_code == 503
                data = response.json()
                
                assert "detail" in data
                detail = data["detail"]
                assert detail["status"] == "not ready"
                assert detail["check"]["qdrant"]["status"] == "unhealthy"
                assert detail["check"]["llm"]["status"] == "unhealthy"
                assert detail["check"]["embedding"]["status"] == "unhealthy"

    @pytest.mark.asyncio
    async def test_service_timeout(self, mock_orchestrator):
        """Test readiness when a service times out.
        
        RED: Should FAIL - verify timeout exception handling
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                
                async def mock_get(url, *args, **kwargs):
                    if "qdrant" in url or "6333" in url:
                        raise Exception("Connection timeout")
                    response = Mock(spec=Response)
                    response.status_code = 200
                    response.elapsed = Mock()
                    response.elapsed.total_seconds.return_value = 0.05
                    return response
                
                mock_async_client.get.side_effect = mock_get
                mock_client.return_value = mock_async_client

                client = TestClient(main.app)
                response = client.get("/ready")

                assert response.status_code == 503
                data = response.json()
                
                assert "detail" in data
                detail = data["detail"]
                assert detail["status"] == "not ready"
                assert detail["check"]["qdrant"]["status"] == "unhealthy"
                assert "error" in detail["check"]["qdrant"]

    @pytest.mark.asyncio
    async def test_orchestrator_not_initialized(self):
        """Test readiness when orchestrator is not initialized.
        
        Verifies clean error message when service is still starting up.
        """
        from app import main
        
        with patch.object(main, 'orchestrator', None):
            client = TestClient(main.app)
            response = client.get("/ready")

            # Should return 503 when orchestrator is not ready
            assert response.status_code == 503
            data = response.json()
            assert "detail" in data
            
            detail = data["detail"]
            assert detail["status"] == "not ready"
            assert "orchestrator" in detail["check"]
            assert detail["check"]["orchestrator"]["status"] == "unhealthy"
            assert "initializing" in detail["check"]["orchestrator"]["error"].lower()

    @pytest.mark.asyncio
    async def test_prometheus_metrics_incremented(self, mock_orchestrator, mock_healthy_response):
        """Test that Prometheus metrics are properly incremented.
        
        RED: Should FAIL - verify metrics tracking
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                mock_async_client.get.return_value = mock_healthy_response
                mock_client.return_value = mock_async_client

                # Get initial counter value
                initial_count = main.readiness_check_counter._value.get()

                client = TestClient(main.app)
                response = client.get("/ready")

                # Verify counter incremented
                final_count = main.readiness_check_counter._value.get()
                assert final_count > initial_count

    @pytest.mark.asyncio
    async def test_failure_metrics_incremented(self, mock_orchestrator, mock_unhealthy_response):
        """Test that failure metrics are properly tracked.
        
        RED: Should FAIL - verify failure metrics per component
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                
                async def mock_get(url, *args, **kwargs):
                    if "qdrant" in url or "6333" in url:
                        return mock_unhealthy_response
                    response = Mock(spec=Response)
                    response.status_code = 200
                    response.elapsed = Mock()
                    response.elapsed.total_seconds.return_value = 0.05
                    return response
                
                mock_async_client.get.side_effect = mock_get
                mock_client.return_value = mock_async_client

                # Get initial failure count for qdrant
                try:
                    initial_failures = main.readiness_check_failures.labels(component="qdrant")._value.get()
                except:
                    initial_failures = 0

                client = TestClient(main.app)
                response = client.get("/ready")

                # Verify failure metric incremented for qdrant
                final_failures = main.readiness_check_failures.labels(component="qdrant")._value.get()
                assert final_failures > initial_failures

    @pytest.mark.asyncio
    async def test_response_structure(self, mock_orchestrator, mock_healthy_response):
        """Test that response structure is correct for healthy state.
        
        RED: Should FAIL - verify response schema
        """
        from app import main
        
        with patch.object(main, 'orchestrator', mock_orchestrator):
            with patch('httpx.AsyncClient') as mock_client:
                mock_async_client = AsyncMock()
                mock_async_client.__aenter__.return_value = mock_async_client
                mock_async_client.__aexit__.return_value = None
                mock_async_client.get.return_value = mock_healthy_response
                mock_client.return_value = mock_async_client

                client = TestClient(main.app)
                response = client.get("/ready")

                assert response.status_code == 200
                data = response.json()
                
                # Verify top-level structure
                required_keys = ["status", "timestamp", "service", "check"]
                for key in required_keys:
                    assert key in data, f"Missing key: {key}"
                
                # Verify timestamp is recent (within last 5 seconds)
                assert abs(time.time() - data["timestamp"]) < 5
                
                # Verify check structure
                required_checks = ["qdrant", "llm", "embedding", "gcs"]
                for check_name in required_checks:
                    assert check_name in data["check"], f"Missing check: {check_name}"
                    assert "status" in data["check"][check_name]
