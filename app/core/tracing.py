"""OpenTelemetry tracing setup for distributed tracing.


"""

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter


def setup_tracing(
    service_name: str,
    jaeger_host: str = "localhost",
    jaeger_port: int = 6831
):
    """Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service for tracing.
        jaeger_host: Jaeger agent hostname.
        jaeger_port: Jaeger agent port.
    """
    # Create resource with service name
    resource = Resource.create(attributes={"service.name": service_name})

    # Create tracer provider with resource
    provider = TracerProvider(resource=resource)

    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port
    )

    # Create batch span processor with exporter
    span_processor = BatchSpanProcessor(jaeger_exporter)

    # Add span processor to provider
    provider.add_span_processor(span_processor)

    # Set as global tracer provider
    trace.set_tracer_provider(provider)
