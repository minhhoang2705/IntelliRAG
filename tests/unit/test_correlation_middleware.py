"""Unit tests for correlation ID middleware."""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
import uuid


def test_correlation_middleware_generates_request_id():
    """Test that middleware generates a request ID if none provided."""
    from app.api.middleware.correlation import CorrelationIDMiddleware

    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)

    @app.get("/test")
    async def test_endpoint():
        return {"status": "ok"}

    client = TestClient(app)
    response = client.get("/test")

    # Verify response has X-Request-ID header
    assert "X-Request-ID" in response.headers
    # Verify it's a valid UUID
    request_id = response.headers["X-Request-ID"]
    uuid.UUID(request_id)  # Will raise ValueError if invalid
