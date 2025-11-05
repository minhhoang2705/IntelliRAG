"""Unit tests for OpenTelemetry integration in main app.

This module tests that tracing is properly configured on app startup.

Date: 2025-11-05
"""

import pytest


class TestMainAppTracing:
    """Test suite for tracing integration in main application."""

    @pytest.mark.asyncio
    async def test_setup_tracing_called_on_startup(self):
        """Test that setup_tracing is called during app lifespan startup."""
        # RED: Will fail because setup_tracing not called in lifespan
        from app.main import lifespan, app
        from unittest.mock import patch, AsyncMock

        with patch('app.main.setup_tracing') as mock_setup_tracing:
            # Trigger lifespan startup
            async with lifespan(app):
                pass

            # Verify setup_tracing was called
            mock_setup_tracing.assert_called_once()
            call_kwargs = mock_setup_tracing.call_args.kwargs
            assert "service_name" in call_kwargs
            assert call_kwargs["service_name"] == "IntelliRAG"

    def test_fastapi_instrumentor_import_exists(self):
        """Test that FastAPIInstrumentor can be imported from main."""
        # RED: Will fail if FastAPIInstrumentor not imported
        from app import main
        assert hasattr(main, "FastAPIInstrumentor")

    def test_fastapi_app_instrumented(self):
        """Test that FastAPI app has been instrumented with OpenTelemetry."""
        from app.main import app
        
        # Check that the app has the OTEL middleware added by instrumentation
        middleware_names = [m.__class__.__name__ for m in app.user_middleware]
        assert any("OpenTelemetry" in name or "Telemetry" in name for name in middleware_names), \
            f"OpenTelemetry middleware not found. Middleware: {middleware_names}"
