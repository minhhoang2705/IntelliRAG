"""Unit tests for query endpoint router.

This module tests the query API endpoint with dependency injection.

Date: 2025-11-05
"""

import pytest
from unittest.mock import patch, Mock


class TestQueryEndpointRouter:
    """Test suite for /api/v1/query endpoint."""

    def test_query_router_exists(self):
        """Test that query router module can be imported."""
        from app.api.v1 import query
        assert hasattr(query, 'router')

    def test_dependency_injection_returns_orchestrator_when_initialized(self):
        """Test get_orchestrator returns orchestrator when available."""
        from app.dependencies import get_orchestrator, get_query_logger

        # Mock orchestrator
        mock_orchestrator = Mock()

        with patch('app.main.orchestrator', mock_orchestrator):
            result = get_orchestrator()
            assert result == mock_orchestrator

    def test_dependency_injection_raises_503_when_orchestrator_is_none(self):
        """Test get_orchestrator raises HTTPException 503 when orchestrator is None."""
        from app.dependencies import get_orchestrator, get_query_logger
        from fastapi import HTTPException

        with patch('app.main.orchestrator', None):
            with pytest.raises(HTTPException) as exc_info:
                get_orchestrator()

            assert exc_info.value.status_code == 503

    def test_query_endpoint_exists_at_correct_path(self):
        """Test query endpoint is registered at /api/v1/query."""
        from app.api.v1.query import router

        routes = [route.path for route in router.routes]
        assert "/api/v1/query" in routes

    @pytest.mark.asyncio
    async def test_query_endpoint_calls_orchestrator_with_request_data(self, auth_override):
        """Test query endpoint calls orchestrator.query() with request data."""
        # RED: Will fail because endpoint doesn't call orchestrator
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        # Create mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test answer",
            "sources": [],
            "classification": None,
            "used_rag": False
        })

        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        # Setup app with dependency override
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)

            # Make request
            payload = {
                "query": "What is RAG?",
                "top_k": 5,
                "temperature": 0.7,
                "max_tokens": 512,
                "use_rag": True
            }

            response = client.post("/api/v1/query", json=payload)

            # Verify orchestrator was called
            mock_orchestrator.query.assert_called_once()

            # Verify it was called with query text
            call_args = mock_orchestrator.query.call_args
            assert call_args.kwargs["query"] == "What is RAG?"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_endpoint_returns_query_response(self, auth_override):
        """Test query endpoint returns QueryResponse with answer."""
        # RED: Will fail because endpoint doesn't return anything
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        # Create mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "RAG is Retrieval-Augmented Generation",
            "sources": [],
            "classification": None,
            "used_rag": False
        })

        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        # Setup app
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)

            # Make request
            payload = {
                "query": "What is RAG?",
                "top_k": 5,
                "temperature": 0.7,
                "max_tokens": 512,
                "use_rag": True
            }

            response = client.post("/api/v1/query", json=payload)

            # Verify response
            assert response.status_code == 200
            data = response.json()
            assert "answer" in data
            assert data["answer"] == "RAG is Retrieval-Augmented Generation"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_endpoint_passes_all_parameters_to_orchestrator(self, auth_override):
        """Test query endpoint passes top_k, temperature, max_tokens to orchestrator."""
        # RED: Will fail because endpoint doesn't pass these parameters
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        # Create mock orchestrator
        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test",
            "sources": [],
            "classification": None,
            "used_rag": False
        })

        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        # Setup app
        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)

            # Make request with specific parameters
            payload = {
                "query": "Test query",
                "top_k": 10,
                "temperature": 0.9,
                "max_tokens": 1024,
                "use_rag": True
            }

            response = client.post("/api/v1/query", json=payload)

            # Verify orchestrator was called with all parameters
            call_args = mock_orchestrator.query.call_args
            assert call_args.kwargs["top_k"] == 10
            assert call_args.kwargs["temperature"] == 0.9
            assert call_args.kwargs["max_tokens"] == 1024
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_endpoint_includes_sources_in_response(self, auth_override):
        """Test query endpoint includes sources from orchestrator result."""
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test",
            "sources": [{"text": "Source 1", "score": 0.95, "id": "doc1"}],
            "classification": None,
            "used_rag": False
        })


        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)
            response = client.post("/api/v1/query", json={
                "query": "Test", "top_k": 5, "temperature": 0.7,
                "max_tokens": 512, "use_rag": True
            })

            data = response.json()
            assert "sources" in data
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_endpoint_includes_query_in_response(self, auth_override):
        """Test query endpoint echoes back the query in response."""
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test",
            "sources": [],
            "classification": None,
            "used_rag": False
        })


        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)
            response = client.post("/api/v1/query", json={
                "query": "What is TDD?",
                "top_k": 5,
                "temperature": 0.7,
                "max_tokens": 512,
                "use_rag": True
            })

            data = response.json()
            assert "query" in data
            assert data["query"] == "What is TDD?"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_endpoint_includes_used_rag_in_response(self, auth_override):
        """Test query endpoint includes used_rag field from request."""
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test",
            "sources": [],
            "classification": None,
            "used_rag": True
        })


        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)
            response = client.post("/api/v1/query", json={
                "query": "Test query",
                "top_k": 5,
                "temperature": 0.7,
                "max_tokens": 512,
                "use_rag": True
            })

            data = response.json()
            assert "used_rag" in data
            assert data["used_rag"] is True
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_endpoint_includes_classification_when_present(self, auth_override):
        """Test query endpoint includes classification from orchestrator result."""
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        # Create mock classification object
        mock_classification = Mock()
        mock_classification.query_type = "rag"
        mock_classification.confidence = 0.95
        mock_classification.reasoning = "Query requires document context"

        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test answer",
            "sources": [],
            "classification": mock_classification,
            "used_rag": False
        })


        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)
            response = client.post("/api/v1/query", json={
                "query": "Test query",
                "top_k": 5,
                "temperature": 0.7,
                "max_tokens": 512,
                "use_rag": True
            })

            data = response.json()
            assert "classification" in data
            assert data["classification"] is not None
            assert data["classification"]["query_type"] == "rag"
            assert data["classification"]["confidence"] == 0.95
            assert data["classification"]["reasoning"] == "Query requires document context"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_endpoint_passes_collection_name_to_orchestrator(self, auth_override):
        """Test query endpoint passes collection_name='default' to orchestrator."""
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test",
            "sources": [],
            "classification": None,
            "used_rag": False
        })


        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)
            response = client.post("/api/v1/query", json={
                "query": "Test query",
                "top_k": 5,
                "temperature": 0.7,
                "max_tokens": 512,
                "use_rag": True
            })

            # Verify orchestrator was called with collection_name
            call_args = mock_orchestrator.query.call_args
            assert "collection_name" in call_args.kwargs
            assert call_args.kwargs["collection_name"] == "default"
        finally:
            app.dependency_overrides.clear()

    @pytest.mark.asyncio
    async def test_query_endpoint_response_validates_as_query_response_schema(self, auth_override):
        """Test that endpoint response can be validated as QueryResponse."""
        from app.api.v1.query import router
        from app.dependencies import get_orchestrator, get_query_logger
        from app.api.middleware.auth import verify_api_key
        from app.models.schemas import QueryResponse
        from fastapi.testclient import TestClient
        from fastapi import FastAPI
        from unittest.mock import AsyncMock

        mock_orchestrator = Mock()
        mock_orchestrator.query = AsyncMock(return_value={
            "answer": "Test answer",
            "sources": [{"text": "Source 1", "score": 0.95, "id": "doc1"}],
            "classification": None,
            "used_rag": False
        })


        # Create mock query logger
        mock_query_logger = Mock()
        mock_query_logger.log_query = AsyncMock()

        app = FastAPI()
        app.include_router(router)
        app.dependency_overrides[get_orchestrator] = lambda: mock_orchestrator
        app.dependency_overrides[get_query_logger] = lambda: mock_query_logger
        app.dependency_overrides[verify_api_key] = auth_override

        try:
            client = TestClient(app)
            response = client.post("/api/v1/query", json={
                "query": "Test query",
                "top_k": 5,
                "temperature": 0.7,
                "max_tokens": 512,
                "use_rag": True
            })

            # Verify response can be parsed as QueryResponse
            assert response.status_code == 200
            data = response.json()

            # Validate response matches QueryResponse schema
            query_response = QueryResponse(**data)
            assert query_response.answer == "Test answer"
            assert query_response.query == "Test query"
            assert query_response.used_rag is False
        finally:
            app.dependency_overrides.clear()

    def test_query_endpoint_has_response_model_declaration(self):
        """Test that query endpoint declares QueryResponse as response_model."""
        from app.api.v1.query import router
        from app.models.schemas import QueryResponse

        # Find the query endpoint route
        query_route = None
        for route in router.routes:
            if route.path == "/api/v1/query":
                query_route = route
                break

        assert query_route is not None, "Query route not found"
        assert query_route.response_model == QueryResponse
