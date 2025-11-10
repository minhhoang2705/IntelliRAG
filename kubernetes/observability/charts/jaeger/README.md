# IntelliRAG Jaeger Chart

Minimal production-ready Jaeger stack for IntelliRAG distributed tracing.

## Components

- **Jaeger Agent**: Trace collection (DaemonSet)
- **Jaeger Collector**: Trace processing and storage
- **Jaeger Query**: UI and API for trace visualization
- **Elasticsearch**: Trace storage backend

## Installation

```bash
# Build dependencies
helm dependency build

# Install
helm install jaeger . -n observability --create-namespace

# Upgrade
helm upgrade jaeger . -n observability
```

## Access Jaeger UI

```bash
# Port forward to Jaeger Query
kubectl port-forward -n observability svc/jaeger-query 16686:16686
```

Visit: http://localhost:16686

## Application Integration

Configure your application to send traces to Jaeger:

**OpenTelemetry (recommended)**:
```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

trace.set_tracer_provider(TracerProvider())
jaeger_exporter = JaegerExporter(
    agent_host_name="jaeger-agent.observability.svc.cluster.local",
    agent_port=6831,
)
trace.get_tracer_provider().add_span_processor(
    BatchSpanProcessor(jaeger_exporter)
)
```

**Environment variables**:
```bash
JAEGER_AGENT_HOST=jaeger-agent.observability.svc.cluster.local
JAEGER_AGENT_PORT=6831
JAEGER_SAMPLER_TYPE=probabilistic
JAEGER_SAMPLER_PARAM=0.5
```

## Configuration

Key values to customize:
- `jaeger.elasticsearch.replicas`: Number of ES nodes (3 for HA)
- `jaeger.schema.ttl.days`: Trace retention period
- `jaeger.sampling.strategies`: Sampling rates per service
- `jaeger.collector.autoscaling`: Auto-scaling settings

## Resource Usage

- CPU: ~850m request, ~2000m limit
- Memory: ~1.5Gi request, ~3Gi limit
- Storage: 20Gi (configurable)

## Production Considerations

For production:
1. Increase Elasticsearch to 3 replicas (HA)
2. Enable collector autoscaling (2-5 replicas)
3. Adjust sampling rates based on traffic
4. Increase storage and retention as needed
5. Consider using managed Elasticsearch (AWS ES, Elastic Cloud)

## Monitoring

Jaeger exports Prometheus metrics:
- Collector: `http://jaeger-collector:14269/metrics`
- Query: `http://jaeger-query:16687/metrics`

Add ServiceMonitors to scrape these endpoints.


