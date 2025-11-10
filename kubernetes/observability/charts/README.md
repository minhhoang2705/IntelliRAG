# IntelliRAG Observability Charts

Minimal production-ready Helm charts for complete observability stack.

## 📦 Charts

1. **Prometheus** - Metrics monitoring and alerting
2. **Loki** - Log aggregation and querying
3. **Jaeger** - Distributed tracing

Each chart is independent and can be deployed separately.

## 🚀 Quick Start

### Prerequisites

```bash
# Create namespace
kubectl create namespace observability

# Add Helm repositories (done automatically during deployment)
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update
```

### Deploy All Components

```bash
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG/kubernetes/observability/charts

# 1. Deploy Prometheus
cd prometheus
helm dependency build
helm install prometheus . -n observability
cd ..

# 2. Deploy Loki
cd loki
helm dependency build
helm install loki . -n observability
cd ..

# 3. Deploy Jaeger
cd jaeger
helm dependency build
helm install jaeger . -n observability
cd ..
```

### Verify Deployment

```bash
# Check all pods
kubectl get pods -n observability

# Check services
kubectl get svc -n observability
```

## 🔍 Access UIs

### Prometheus

```bash
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
```
Visit: http://localhost:9090

### Loki (via Grafana)

```bash
kubectl port-forward -n observability svc/loki-gateway 3100:80
```
Query: http://localhost:3100

### Jaeger UI

```bash
kubectl port-forward -n observability svc/jaeger-query 16686:16686
```
Visit: http://localhost:16686

## 📊 Resource Requirements

### For 8-Core Minikube Cluster

| Component | CPU Request | CPU Limit | Memory Request | Memory Limit | Storage |
|-----------|-------------|-----------|----------------|--------------|---------|
| **Prometheus** | ~550m | ~2000m | ~2Gi | ~3.5Gi | 20Gi |
| **Loki** | ~700m | ~1500m | ~1.5Gi | ~2Gi | 20Gi |
| **Jaeger** | ~850m | ~2000m | ~1.5Gi | ~3Gi | 20Gi |
| **Total** | **~2100m** | **~5500m** | **~5Gi** | **~8.5Gi** | **60Gi** |

**Remaining for applications**: ~5900m CPU, ~17Gi Memory

## 🔧 Configuration

### Prometheus

Key configurations in `prometheus/values.yaml`:
- `retention`: Data retention period (default: 15d)
- `storageSpec`: Storage configuration
- `additionalScrapeConfigs`: Custom scrape targets
- `additionalPrometheusRulesMap`: Custom alerts

### Loki

Key configurations in `loki/values.yaml`:
- `limits_config.retention_period`: Log retention (default: 7d)
- `singleBinary.persistence.size`: Storage size
- `promtail.config.scrapeConfigs`: Log collection rules

### Jaeger

Key configurations in `jaeger/values.yaml`:
- `elasticsearch.replicas`: ES replicas (1 for dev, 3 for prod)
- `schema.ttl.days`: Trace retention (default: 7d)
- `sampling.strategies`: Per-service sampling rates

## 🔄 Updates

### Upgrade Individual Chart

```bash
cd <chart-name>
helm dependency update
helm upgrade <chart-name> . -n observability
```

### Uninstall

```bash
helm uninstall prometheus -n observability
helm uninstall loki -n observability
helm uninstall jaeger -n observability
```

## 🏭 Production Recommendations

When moving to production (GKE):

### Prometheus
- Increase retention to 30d
- Add persistent volume snapshots
- Configure remote write to long-term storage
- Set up Alertmanager notification channels

### Loki
- Switch to `SimpleScalable` deployment mode
- Use object storage (GCS/S3) instead of filesystem
- Increase retention to 30d
- Enable index caching

### Jaeger
- Scale Elasticsearch to 3 replicas (HA)
- Enable collector autoscaling (2-5 replicas)
- Consider managed Elasticsearch
- Adjust sampling rates based on traffic

## 🔗 Integration

### Application Instrumentation

**Metrics (Prometheus)**:
```python
from prometheus_client import Counter, Histogram, start_http_server

# Expose metrics endpoint
start_http_server(8000)

# Define metrics
requests_total = Counter('http_requests_total', 'Total requests')
request_duration = Histogram('http_request_duration_seconds', 'Request duration')
```

**Logging (Loki)**:
```python
import structlog

# Configure structured logging
structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
logger.info("request_processed", endpoint="/api/query", trace_id="abc123")
```

**Tracing (Jaeger)**:
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

## 📚 Additional Resources

- [Prometheus Documentation](https://prometheus.io/docs/)
- [Loki Documentation](https://grafana.com/docs/loki/latest/)
- [Jaeger Documentation](https://www.jaegertracing.io/docs/)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)

## 🆘 Troubleshooting

### Pods not starting

```bash
# Check pod status
kubectl describe pod <pod-name> -n observability

# Check logs
kubectl logs <pod-name> -n observability

# Check events
kubectl get events -n observability --sort-by='.lastTimestamp'
```

### Insufficient resources

```bash
# Check node resources
kubectl describe nodes

# Check resource usage
kubectl top nodes
kubectl top pods -n observability
```

### Storage issues

```bash
# Check PVCs
kubectl get pvc -n observability

# Check PVs
kubectl get pv
```

## 📝 Notes

- All charts use `storageClassName: standard` (Minikube default)
- For GKE, change to `pd-standard` or `pd-ssd`
- Ingress is disabled by default - enable in values if needed
- Grafana is disabled in Prometheus chart - deploy separately if needed


