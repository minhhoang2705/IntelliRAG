# IntelliRAG Observability Best Practices

**Version**: 1.0
**Last Updated**: 2025-11-06

## Table of Contents

- [Debugging with Traces](#debugging-with-traces)
- [Log Analysis with Loki](#log-analysis-with-loki)
- [Metrics Monitoring](#metrics-monitoring)
- [Alerting Strategy](#alerting-strategy)
- [Performance Optimization](#performance-optimization)
- [Cost Optimization](#cost-optimization)

---

## Debugging with Traces

### Finding Slow Requests

**1. Identify slow endpoints in Grafana**

Navigate to: **Query Performance Dashboard** → **P95/P99 Latency** panel

Look for endpoints with P99 > 2s.

**2. Get trace ID from logs**

```bash
# Using kubectl
kubectl logs -n default deployment/intellirag-api | \
  jq '. | select(.duration_seconds > 2) | .trace_id'

# Using Loki (in Grafana Explore)
{app="intellirag"} | json | duration_seconds > 2 | line_format "{{.trace_id}}"
```

**3. Analyze trace in Jaeger**

- Navigate to: `http://jaeger.intellirag.local`
- Search by `trace_id`
- Look for:
  - **Long-running spans**: Identify bottlenecks
  - **Sequential operations**: Could be parallelized?
  - **Failed spans**: Red markers indicate errors
  - **High span count**: Indicates N+1 query problems

**Example Analysis**:
```
Total Duration: 3.2s
├─ query_classification: 0.1s ✓
├─ embedding_generation: 1.8s ⚠️ SLOW
├─ vector_search: 0.2s ✓
└─ llm_generation: 1.1s ✓
```
**Action**: Optimize embedding generation (enable batch processing or GPU acceleration).

### Trace Correlation Across Services

All IntelliRAG services propagate trace context. Use `trace_id` to correlate:
- API requests → Background jobs
- Vector DB operations → RAG pipeline
- LLM calls → Response generation

**Add Custom Spans for Debugging**:
```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("document_count", len(documents))
    span.set_attribute("chunk_size", chunk_size)
    # Your code here
```

---

## Log Analysis with Loki

### Essential LogQL Queries

**Find all logs for a specific trace**:
```logql
{app="intellirag"} |= "trace_id" |~ "YOUR_TRACE_ID"
```

**Find errors in ingestion pipeline**:
```logql
{app="intellirag"} |= "ingestion" |= "ERROR"
```

**Track specific user requests**:
```logql
{app="intellirag"}
  |= "user_id"
  |= "USER_123"
  | json
  | line_format "{{.timestamp}} {{.message}}"
```

**Performance analysis** (requests > 2s):
```logql
{app="intellirag"}
  | json
  | duration_seconds > 2
  | line_format "{{.timestamp}} {{.endpoint}} {{.duration_seconds}}s"
```

**Aggregate error counts by type**:
```logql
sum by (error_type) (
  rate({app="intellirag"} |= "ERROR" | json | __error__="" [5m])
)
```

**Top 10 slowest endpoints**:
```logql
topk(10,
  avg by(endpoint) (
    rate({app="intellirag"} | json | duration_seconds > 0 [5m])
  )
)
```

**Failed authentication attempts**:
```logql
{app="intellirag"} |= "authentication" |= "failed"
  | json
  | line_format "{{.timestamp}} IP: {{.ip}} User: {{.username}}"
```

---

## Metrics Monitoring

### Key Metrics to Watch

#### 🚨 Critical Metrics (Alert Immediately)

| Metric | Threshold | Action |
|--------|-----------|--------|
| `up{job="intellirag"}` | == 0 for 1m | Service down - immediate investigation |
| `rate(http_requests_total{status_code=~"5.."}[5m])` | > 5% | High error rate - check logs |
| `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m]))` | > 5s | High latency - trace analysis |
| `gpu_utilization_percent` | > 95% for 10m | GPU overload - scale or optimize |

#### ⚠️ Warning Metrics (Monitor Closely)

| Metric | Threshold | Action |
|--------|-----------|--------|
| `ingestion_jobs_active` | > 100 | Queue backlog - scale workers |
| `embedding_cache_hits_total{hit="false"} / embedding_cache_hits_total` | > 50% | Low cache hit - increase cache size |
| `rate(ingestion_errors_total[5m])` | > 1% | Ingestion issues - check file validation |
| Container memory usage | > 85% | Memory pressure - increase limits |

### Dashboard Usage Patterns

**Daily Standup**: Use **IntelliRAG Overview**
- Quick health check
- Error rate trends
- GPU utilization

**Performance Tuning**: Use **Query Performance**
- Stage-by-stage latency
- Cache effectiveness
- Router decision distribution

**Capacity Planning**: Use **Infrastructure**
- Resource usage trends
- Growth patterns
- Pod restart frequency

**Cost Management**: Use **LLM Metrics**
- Token usage trends
- Cost projections
- High-cost query patterns

---

## Alerting Strategy

### Three-Tier Severity Model

**🔴 Critical (Page Immediately)**

```yaml
ServiceDown:
  condition: up{job="intellirag"} == 0
  for: 1m
  action: Page on-call engineer

HighErrorRate:
  condition: error_rate > 5%
  for: 5m
  action: Page on-call engineer

HighLatency:
  condition: P99 > 5s
  for: 5m
  action: Page on-call engineer
```

**🟡 Warning (Notify Team)**

```yaml
QueueBacklog:
  condition: ingestion_jobs_active > 100
  for: 5m
  action: Slack notification

LowCacheHitRate:
  condition: cache_hit_rate < 50%
  for: 10m
  action: Slack notification

HighMemory:
  condition: memory_usage > 85%
  for: 5m
  action: Slack notification
```

**🔵 Info (Awareness)**

```yaml
NewDeployment:
  condition: deployment_updated
  action: Slack notification

QueryPatternShift:
  condition: distribution_change > 30%
  for: 30m
  action: Email notification
```

### Alert Runbooks

Each alert should have a runbook link:

```yaml
annotations:
  summary: "High error rate detected"
  description: "Error rate is {{ $value | humanizePercentage }}"
  runbook_url: "https://docs.intellirag.com/runbooks/high-error-rate"
```

**Runbook Template**:
1. **Symptom**: What's happening?
2. **Impact**: How does it affect users?
3. **Diagnosis**: How to investigate?
4. **Mitigation**: Quick fixes
5. **Resolution**: Long-term solution

---

## Performance Optimization

### Using Metrics for Optimization

**1. Identify Bottlenecks**

```promql
# Find slowest pipeline stage
topk(1,
  histogram_quantile(0.95,
    rate(rag_query_duration_seconds_bucket{job="intellirag"}[5m])
  )
)
```

**2. Cache Analysis**

```promql
# Calculate cache hit rate
rate(embedding_cache_hits_total{hit="true"}[5m])
  /
rate(embedding_cache_hits_total[5m])
```

**Action**: If < 70%, increase cache size or adjust TTL.

**3. Batch Processing Efficiency**

```promql
# Average chunks per document
rate(ingestion_chunks_created_sum[5m])
  /
rate(ingestion_chunks_created_count[5m])
```

**Action**: Optimize chunk size for better embedding performance.

### Using Traces for Optimization

**1. Parallelization Opportunities**

Look for sequential spans that could run concurrently:

```
❌ Sequential (3.0s total):
├─ embed_chunk_1: 1.0s
├─ embed_chunk_2: 1.0s
└─ embed_chunk_3: 1.0s

✅ Parallel (1.0s total):
├─ embed_chunk_1: 1.0s
├─ embed_chunk_2: 1.0s  } concurrent
└─ embed_chunk_3: 1.0s
```

**2. Resource Contention**

If span durations spike during high load, check for:
- Thread pool saturation
- Database connection limits
- GPU memory contention

### Using Logs for Optimization

**Find most common errors**:
```logql
topk(10,
  count_over_time({app="intellirag"} |= "ERROR" [24h])
)
```

**Action**: Fix most frequent errors first for maximum impact.

---

## Cost Optimization

### Reduce Storage Costs

**1. Metrics Retention**

```yaml
# prometheus/values.yaml
retention: 30d  # Keep last 30 days
retentionSize: 45GB  # Or 45GB, whichever comes first
```

**Downsample older data**:
- Keep 1-minute resolution for 7 days
- Downsample to 5-minute resolution for 8-30 days

**2. Log Filtering**

```yaml
# loki/values.yaml - Filter out verbose logs
snippets:
  pipelineStages:
    # Drop health check logs
    - match:
        selector: '{endpoint="/health"}'
        action: drop

    # Drop debug logs in production
    - match:
        selector: '{level="DEBUG"}'
        action: drop
```

**3. Trace Sampling**

```yaml
# jaeger/values.yaml
sampling:
  strategies: |
    {
      "default_strategy": {
        "type": "probabilistic",
        "param": 0.1  # Sample 10% of traces
      },
      "service_strategies": [
        {
          "service": "intellirag-api",
          "type": "probabilistic",
          "param": 0.5  # Sample 50% from main API
        }
      ]
    }
```

### Resource Optimization

**Right-size Components**:

```bash
# Monitor actual usage
kubectl top pods -n observability

# Adjust resources based on usage
kubectl edit deployment/<component> -n observability
```

**Use Autoscaling**:

```yaml
# For Prometheus
autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 5
  targetCPUUtilizationPercentage: 80
```

### Query Optimization

**Avoid expensive queries**:

```promql
# ❌ Expensive (high cardinality)
rate(http_requests_total[5m])

# ✅ Better (aggregated)
sum by(endpoint) (rate(http_requests_total[5m]))
```

**Use recording rules** for complex queries:

```yaml
groups:
  - name: intellirag_recordings
    interval: 30s
    rules:
      - record: job:http_request_rate:5m
        expr: sum(rate(http_requests_total{job="intellirag"}[5m]))
```

---

## Maintenance Tasks

### Daily
- ✅ Check alert status in Grafana
- ✅ Review error logs in Loki
- ✅ Monitor resource usage

### Weekly
- ✅ Review dashboard performance
- ✅ Update alert thresholds based on patterns
- ✅ Clean up old traces/logs

### Monthly
- ✅ Review retention policies
- ✅ Optimize slow queries
- ✅ Update documentation
- ✅ Capacity planning review

### Quarterly
- ✅ Security audit
- ✅ Cost optimization review
- ✅ Tool version updates
- ✅ Disaster recovery testing

---

## Additional Resources

- **Prometheus Best Practices**: https://prometheus.io/docs/practices/
- **Grafana Dashboarding**: https://grafana.com/docs/grafana/latest/dashboards/
- **Jaeger Sampling**: https://www.jaegertracing.io/docs/latest/sampling/
- **Loki LogQL**: https://grafana.com/docs/loki/latest/logql/

---

*For deployment instructions, see [observability-deployment-guide.md](observability-deployment-guide.md)*
*For troubleshooting, see [troubleshooting-observability.md](troubleshooting-observability.md)*
