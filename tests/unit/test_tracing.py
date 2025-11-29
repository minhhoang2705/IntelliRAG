"""Unit tests for OpenTelemetry tracing setup.

This module tests the tracing configuration for distributed tracing.

Date: 2025-11-05
"""



class TestTracingSetup:
    """Test suite for OpenTelemetry tracing initialization."""

    def test_tracing_module_exists(self):
        """Test that tracing module can be imported."""
        from app.core import tracing
        assert hasattr(tracing, 'setup_tracing')

    def test_setup_tracing_initializes_tracer_provider(self):
        """Test that setup_tracing creates a TracerProvider."""
        from app.core.tracing import setup_tracing
        from unittest.mock import patch, Mock

        with patch('app.core.tracing.TracerProvider') as mock_provider_class:
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider

            setup_tracing(service_name="test-service")

            # Verify TracerProvider was created
            mock_provider_class.assert_called_once()

    def test_setup_tracing_configures_jaeger_exporter(self):
        """Test that setup_tracing configures Jaeger exporter."""
        from app.core.tracing import setup_tracing
        from unittest.mock import patch, Mock

        with patch('app.core.tracing.JaegerExporter') as mock_exporter_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter

            setup_tracing(
                service_name="test-service",
                jaeger_host="localhost",
                jaeger_port=6831
            )

            # Verify Jaeger exporter was created with correct params
            mock_exporter_class.assert_called_once()
            call_kwargs = mock_exporter_class.call_args.kwargs
            assert call_kwargs.get("agent_host_name") == "localhost"
            assert call_kwargs.get("agent_port") == 6831

    def test_setup_tracing_creates_batch_span_processor(self):
        """Test that setup_tracing creates BatchSpanProcessor with exporter."""
        # RED: Will fail because BatchSpanProcessor not imported/used
        from app.core.tracing import setup_tracing
        from unittest.mock import patch, Mock

        with patch('app.core.tracing.JaegerExporter') as mock_exporter_class, \
             patch('app.core.tracing.BatchSpanProcessor') as mock_processor_class:
            mock_exporter = Mock()
            mock_exporter_class.return_value = mock_exporter
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor

            setup_tracing(service_name="test-service")

            # Verify BatchSpanProcessor was created with exporter
            mock_processor_class.assert_called_once_with(mock_exporter)

    def test_setup_tracing_adds_processor_to_provider(self):
        """Test that setup_tracing adds span processor to tracer provider."""
        from app.core.tracing import setup_tracing
        from unittest.mock import patch, Mock

        with patch('app.core.tracing.TracerProvider') as mock_provider_class, \
             patch('app.core.tracing.BatchSpanProcessor') as mock_processor_class, \
             patch('app.core.tracing.JaegerExporter'):
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider
            mock_processor = Mock()
            mock_processor_class.return_value = mock_processor

            setup_tracing(service_name="test-service")

            # Verify add_span_processor was called with processor
            mock_provider.add_span_processor.assert_called_once_with(mock_processor)

    def test_setup_tracing_sets_global_tracer_provider(self):
        """Test that setup_tracing sets the global tracer provider."""
        from app.core.tracing import setup_tracing
        from unittest.mock import patch, Mock

        with patch('app.core.tracing.TracerProvider') as mock_provider_class, \
             patch('app.core.tracing.trace') as mock_trace, \
             patch('app.core.tracing.JaegerExporter'):
            mock_provider = Mock()
            mock_provider_class.return_value = mock_provider

            setup_tracing(service_name="test-service")

            # Verify set_tracer_provider was called with provider
            mock_trace.set_tracer_provider.assert_called_once_with(mock_provider)

    def test_setup_tracing_configures_resource_with_service_name(self):
        """Test that setup_tracing creates Resource with service name."""
        from app.core.tracing import setup_tracing
        from unittest.mock import patch, Mock

        with patch('app.core.tracing.Resource') as mock_resource_class, \
             patch('app.core.tracing.TracerProvider'), \
             patch('app.core.tracing.JaegerExporter'):
            mock_resource = Mock()
            mock_resource_class.create.return_value = mock_resource

            setup_tracing(service_name="intellirag-api")

            # Verify Resource.create was called with service.name
            mock_resource_class.create.assert_called_once()
            call_kwargs = mock_resource_class.create.call_args.kwargs
            assert "attributes" in call_kwargs
            assert call_kwargs["attributes"]["service.name"] == "intellirag-api"
