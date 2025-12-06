# IntelliRAG Observability Stack

Complete observability solution with **Prometheus** (metrics), **Loki** (logging), and **Jaeger** (tracing).

## 📁 Structure

```
observability/
├── charts/                    # Individual Helm charts
│   ├── prometheus/           # Metrics & alerting
│   ├── loki/                # Log aggregation
│   ├── jaeger/              # Distributed tracing
│   ├── deploy.sh            # Deployment script
│   ├── cleanup.sh           # Cleanup script
│   ├── README.md            # Comprehensive guide
│   └── QUICKSTART.md        # Quick reference
├── README.md                # This file
└── RESOURCE_ALLOCATION.md   # Resource planning guide
```

## 🚀 Quick Start

### Option 1: Deploy Everything

```bash
cd charts
./deploy.sh all
```

### Option 2: Deploy Individual Components

```bash
cd charts

# Deploy only what you need
./deploy.sh prometheus
./deploy.sh loki
./deploy.sh jaeger
```

## 📊 What's Included

### Prometheus Stack
- **Prometheus Server**: Metrics collection & storage (15 days retention)
- **Alertmanager**: Alert routing & management
- **Node Exporter**: System-level metrics
- **Kube State Metrics**: Kubernetes metrics
- **Custom IntelliRAG alerts**: API monitoring rules

### Loki Stack
- **Loki**: Log aggregation & storage (7 days retention)
- **Promtail**: Log collection agent (DaemonSet)
- **Gateway**: NGINX API gateway
- **Auto-parses JSON logs** with trace correlation

### Jaeger Stack
- **Jaeger Agent**: Trace collection (DaemonSet)
- **Jaeger Collector**: Trace processing
- **Jaeger Query**: UI & API
- **Elasticsearch**: Trace storage (7 days retention)
- **OpenTelemetry compatible**

## 🔍 Access Services

All services are accessible via port-forwarding:

```bash
# Prometheus UI
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
# Visit: http://localhost:9090

# Loki API
kubectl port-forward -n observability svc/loki-gateway 3100:80
# Query: http://localhost:3100/loki/api/v1/query_range

# Jaeger UI
kubectl port-forward -n observability svc/jaeger-query 16686:16686
# Visit: http://localhost:16686
```

## 📈 Resource Requirements (8-Core Cluster)

| Component | CPU Request | Memory Request | Storage |
|-----------|-------------|----------------|---------|
| Prometheus | ~550m | ~2Gi | 20Gi |
| Loki | ~700m | ~1.5Gi | 20Gi |
| Jaeger | ~850m | ~1.5Gi | 20Gi |
| **Total** | **~2100m** | **~5Gi** | **60Gi** |

**Available for apps**: ~5900m CPU, ~17Gi Memory

See `RESOURCE_ALLOCATION.md` for detailed breakdown.

## 🔧 Configuration

Each chart has its own `values.yaml` that can be customized:

```bash
cd charts/prometheus
# Edit values.yaml
vim values.yaml

# Apply changes
helm upgrade prometheus . -n observability
```

### Common Customizations

**Increase retention**:
- Prometheus: `prometheus.prometheusSpec.retention: 30d`
- Loki: `loki.loki.limits_config.retention_period: 336h`
- Jaeger: `jaeger.schema.ttl.days: 14`

**Increase storage**:
```yaml
storageSpec:
  volumeClaimTemplate:
    spec:
      resources:
        requests:
          storage: 100Gi  # Change from 20Gi
```

**Scale for production**:
```yaml
# Jaeger HA
elasticsearch:
  replicas: 3

# Collector autoscaling
collector:
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 5
```

## 🔄 Update Charts

```bash
cd charts/<component>
helm dependency update
helm upgrade <component> . -n observability
```

## 🧹 Cleanup

```bash
cd charts

# Remove everything
./cleanup.sh all

# Remove specific component
./cleanup.sh prometheus
```

## 🔗 Application Integration

### Metrics (Prometheus)

```python
from prometheus_client import Counter, Histogram, start_http_server

# Expose /metrics endpoint
start_http_server(8000)

requests_total = Counter('http_requests_total', 'Total requests')
request_duration = Histogram('http_request_duration_seconds', 'Request duration')
```

### Logging (Loki)

Use structured JSON logging:

```python
import structlog

structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer()
    ]
)

logger = structlog.get_logger()
logger.info("request_processed", 
    endpoint="/api/query", 
    trace_id="abc123",
    duration=0.5
)
```

### Tracing (Jaeger)

Using OpenTelemetry:

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

# Use in code
tracer = trace.get_tracer(__name__)
with tracer.start_as_current_span("process_query"):
    # Your code here
    pass
```

## 📚 Documentation

- **Quick Start**: `charts/QUICKSTART.md` - Essential commands
- **Full Guide**: `charts/README.md` - Comprehensive documentation
- **Resource Planning**: `RESOURCE_ALLOCATION.md` - Capacity planning
- **Per-component docs**: `charts/<component>/README.md`

## 🆘 Troubleshooting

### Check deployment status
```bash
kubectl get pods -n observability
kubectl get svc -n observability
kubectl top pods -n observability
```

### Check logs
```bash
kubectl logs <pod-name> -n observability
kubectl logs <pod-name> -n observability --previous
```

### Common issues

**Pods stuck in Pending**:
- Check: `kubectl describe pod <pod-name> -n observability`
- Cause: Usually insufficient CPU/memory
- Fix: Scale down replicas or increase node resources

**PVC not bound**:
- Check: `kubectl get pvc -n observability`
- Cause: StorageClass doesn't exist
- Fix: Verify `kubectl get storageclass`

**Can't access services**:
- Check: `kubectl get svc -n observability`
- Cause: Service not created or wrong port
- Fix: Verify service exists and use correct port in port-forward

## 🏭 Production Readiness

### Current Setup (Development)
✅ Single replicas for most components  
✅ Filesystem storage  
✅ Minimal retention (7-15 days)  
✅ Resource-optimized for 8-core cluster  

### Production Recommendations
- [ ] Scale Elasticsearch to 3 replicas (HA)
- [ ] Use object storage (S3/GCS) for Loki
- [ ] Enable autoscaling for collectors
- [ ] Increase retention periods (30+ days)
- [ ] Set up Alertmanager notifications
- [ ] Use managed services where possible
- [ ] Implement backup strategies
- [ ] Add resource quotas and limits

## 💡 Tips

1. **Deploy Prometheus first** - Other services expose metrics
2. **Start minimal, scale up** - Adjust based on actual usage
3. **Monitor your monitoring** - Watch resource usage
4. **Use consistent labels** - Easier correlation across tools
5. **Test alerts early** - Verify Alertmanager routing
6. **Document custom dashboards** - Save Grafana configs to Git

## 📞 Support

For issues or questions:
1. Check component-specific README files
2. Review logs: `kubectl logs <pod> -n observability`
3. Check events: `kubectl get events -n observability`
4. Refer to upstream documentation (links in component READMEs)
