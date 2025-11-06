# Troubleshooting IntelliRAG Observability Stack

**Version**: 1.0
**Last Updated**: 2025-11-06

## Table of Contents

- [Deployment Issues](#deployment-issues)
- [Metrics Collection Issues](#metrics-collection-issues)
- [Tracing Issues](#tracing-issues)
- [Logging Issues](#logging-issues)
- [Dashboard Issues](#dashboard-issues)
- [Performance Issues](#performance-issues)

---

## Deployment Issues

### Pods Not Starting

**Symptoms**: Pods stuck in `Pending`, `CrashLoopBackOff`, or `ImagePullBackOff`

**Diagnosis**:
```bash
kubectl get pods -n observability
kubectl describe pod <pod-name> -n observability
kubectl logs <pod-name> -n observability
```

**Common Causes & Solutions**:

| Issue | Symptom | Solution |
|-------|---------|----------|
| Insufficient resources | `0/3 nodes available: Insufficient cpu/memory` | Scale up cluster or reduce resource requests |
| PVC not bound | `waiting for PVC to be bound` | Check storage provisioner: `kubectl get storageclass` |
| ImagePullBackOff | `Failed to pull image` | Check network access to registry, verify image exists |
| CrashLoopBackOff | Pod restarts repeatedly | Check logs for error messages |

**Example Fix**:
```bash
# Scale up GKE cluster
gcloud container clusters resize intellirag-cluster --num-nodes=5

# Or reduce resource requests
kubectl edit deployment/<component> -n observability
# Adjust spec.template.spec.containers[].resources.requests
```

### Helm Release Failures

**Symptoms**: `helmfile sync` fails with error

**Check Helm status**:
```bash
helm list -n observability
helm status <release-name> -n observability
```

**Common Fixes**:
```bash
# Rollback failed release
helm rollback <release-name> -n observability

# Delete and reinstall
helm uninstall <release-name> -n observability
helmfile sync

# Force delete stuck resources
kubectl delete pod <pod-name> -n observability --grace-period=0 --force
```

---

## Metrics Collection Issues

### Metrics Not Appearing in Prometheus

**Symptoms**: No data in Grafana, queries return empty results

**Diagnosis Steps**:

**1. Check if Prometheus is scraping targets**

```bash
# Port-forward Prometheus
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090

# Open browser: http://localhost:9090/targets
# Look for "intellirag-metrics" target
# Should be State: UP
```

**2. Verify application exposes /metrics**

```bash
# Port-forward IntelliRAG service
kubectl port-forward -n default svc/intellirag-service 8000:8000

# Check metrics endpoint
curl http://localhost:8000/metrics

# Should return Prometheus-format metrics
```

**3. Check Prometheus scrape configuration**

```bash
kubectl get prometheuses.monitoring.coreos.com -n observability -o yaml | grep -A 20 additionalScrapeConfigs
```

**4. Check Prometheus logs for scrape errors**

```bash
kubectl logs -n observability prometheus-kube-prometheus-prometheus-0 -c prometheus | grep error
```

**Common Solutions**:

| Issue | Fix |
|-------|-----|
| Wrong service name | Update `additionalScrapeConfigs` in `prometheus/values.yaml` |
| Network policy blocking | Add NetworkPolicy to allow Prometheus → IntelliRAG |
| Wrong port | Verify IntelliRAG service port matches scrape config |
| Service not found | Check service exists: `kubectl get svc -n default` |

**Example Fix**:
```yaml
# prometheus/values.yaml
additionalScrapeConfigs:
  - job_name: 'intellirag-metrics'
    static_configs:
      - targets:
          - 'intellirag-service.default.svc.cluster.local:8000'  # ← Verify this
```

### Metrics Delayed or Missing Data Points

**Symptoms**: Data appears with 1-2 minute delay, gaps in graphs

**Check scrape interval**:
```bash
kubectl get prometheuses.monitoring.coreos.com -n observability -o yaml | grep scrapeInterval
```

**Solutions**:
- **Increase scrape frequency**: Reduce `scrapeInterval` from 30s to 15s
- **Check disk space**: `kubectl exec -it -n observability prometheus-xxx -- df -h`
- **Increase retention**: May be dropping old data too quickly

---

## Tracing Issues

### No Traces Appearing in Jaeger

**Symptoms**: Jaeger UI shows no traces for "intellirag-api" service

**Diagnosis Steps**:

**1. Verify Jaeger agent is running**

```bash
kubectl get pods -n observability | grep jaeger-agent
# Should see daemonset pods on each node
```

**2. Check application tracing configuration**

```bash
kubectl get deployment intellirag-api -o yaml | grep -A 5 JAEGER
# Should see:
# - name: JAEGER_AGENT_HOST
#   value: "jaeger-agent.observability.svc.cluster.local"
```

**3. Test trace export**

```bash
# Check application logs for trace export errors
kubectl logs -n default deployment/intellirag-api | grep -i jaeger

# Common errors:
# - "failed to send spans to jaeger"
# - "connection refused"
# - "timeout"
```

**4. Verify network connectivity**

```bash
# Test from application pod
kubectl exec -it -n default deployment/intellirag-api -- \
  nc -zv jaeger-agent.observability.svc.cluster.local 6831
```

**Common Solutions**:

| Issue | Fix |
|-------|-----|
| Agent not reachable | Check NetworkPolicy, verify DNS resolution |
| UDP port blocked | Jaeger uses UDP 6831, check firewall rules |
| Sampling rate too low | Increase sampling in jaeger/values.yaml |
| Traces expired | Check retention: traces kept for 7 days by default |

**Example Fix**:
```yaml
# jaeger/values.yaml - Increase sampling
sampling:
  strategies: |
    {
      "default_strategy": {
        "type": "probabilistic",
        "param": 0.5  # ← Increase from 0.1 to 0.5 (50%)
      }
    }
```

### Trace Context Not Propagating

**Symptoms**: Traces show only single span, missing downstream services

**Check trace headers**:
```bash
# In your code, verify trace headers are propagated
from opentelemetry.propagate import inject

headers = {}
inject(headers)  # Adds traceparent header
# Pass headers to downstream requests
```

**Verify instrumentation**:
```python
# Ensure OpenTelemetry auto-instrumentation is enabled
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

FastAPIInstrumentor().instrument_app(app)
```

---

## Logging Issues

### Logs Not Appearing in Loki

**Symptoms**: Loki queries return no results

**Diagnosis Steps**:

**1. Check Promtail is running**

```bash
kubectl get pods -n observability | grep promtail
# Should see daemonset pods on each node
```

**2. Test Loki API**

```bash
kubectl port-forward -n observability svc/loki-gateway 3100:80

curl -G -s "http://localhost:3100/loki/api/v1/labels"
# Should return: {"status":"success","data":["app","pod",...]}
```

**3. Check Promtail logs**

```bash
kubectl logs -n observability daemonset/promtail | grep -i error
```

**Common Solutions**:

| Issue | Fix |
|-------|-----|
| Promtail can't reach Loki | Check service name in `promtail.config.clients` |
| Labels missing | Verify pod labels match Promtail selectors |
| Logs filtered out | Check pipeline stages in loki/values.yaml |
| Storage full | Increase PVC size or reduce retention |

**Example Fix**:
```yaml
# loki/values.yaml - Check client URL
promtail:
  config:
    clients:
      - url: http://loki-gateway/loki/api/v1/push  # ← Verify this
```

### Log Format Issues

**Symptoms**: JSON logs not parsed correctly, missing fields

**Check log format**:
```bash
kubectl logs -n default deployment/intellirag-api --tail=10
# Logs should be valid JSON
```

**Fix pipeline configuration**:
```yaml
# loki/values.yaml
snippets:
  pipelineStages:
    - json:
        expressions:
          level: level
          trace_id: trace_id  # ← Ensure field names match your logs
          message: message
    - labels:
        level:
        trace_id:
```

---

## Dashboard Issues

### Dashboards Not Loading in Grafana

**Symptoms**: Dashboard list empty or shows "Dashboard not found"

**Diagnosis Steps**:

**1. Check ConfigMap exists**

```bash
kubectl get configmap grafana-dashboards-intellirag -n observability

# If missing, recreate:
kubectl create configmap grafana-dashboards-intellirag \
  --from-file=observability/grafana/provisioning/dashboards/json/ \
  --namespace=observability
```

**2. Check Grafana dashboard provider**

```bash
kubectl exec -it -n observability deployment/grafana -- \
  cat /etc/grafana/provisioning/dashboards/dashboards.yaml
```

**3. Restart Grafana**

```bash
kubectl rollout restart deployment/grafana -n observability
```

**4. Check Grafana logs**

```bash
kubectl logs -n observability deployment/grafana | grep -i error
```

### Dashboard Queries Returning No Data

**Symptoms**: Panels show "No data" despite metrics existing

**Check data source connection**:
1. Login to Grafana
2. Go to: Configuration → Data Sources → Prometheus
3. Click "Test" button
4. Should show: "Data source is working"

**Verify query syntax**:
```promql
# Test in Prometheus first
http_requests_total{job="intellirag"}

# If works in Prometheus but not Grafana:
# - Check time range in Grafana
# - Verify datasource selected correctly
# - Check for query template variables
```

**Common Issues**:

| Issue | Fix |
|-------|-----|
| Wrong datasource | Select correct datasource in panel settings |
| Time range too narrow | Expand time range (e.g., Last 6 hours) |
| Label mismatch | Verify `job="intellirag"` label exists on metrics |
| Query timeout | Increase timeout in datasource settings |

---

## Performance Issues

### High Memory Usage in Prometheus

**Symptoms**: Prometheus pod OOMKilled, high memory usage

**Check current usage**:
```bash
kubectl top pod -n observability | grep prometheus
```

**Solutions**:

**1. Reduce cardinality**

```bash
# Check metric cardinality
kubectl port-forward -n observability prometheus-xxx 9090:9090
curl -s http://localhost:9090/api/v1/status/tsdb | jq '.data.seriesCountByMetricName'

# Look for metrics with >10,000 series
# Remove high-cardinality labels
```

**2. Decrease retention**

```yaml
# prometheus/values.yaml
retention: 15d  # ← Reduce from 30d
```

**3. Enable compression**

```yaml
# prometheus/values.yaml
storageSpec:
  volumeClaimTemplate:
    spec:
      resources:
        requests:
          storage: 50Gi
```

**4. Increase resources**

```yaml
# prometheus/values.yaml
resources:
  limits:
    memory: 8Gi  # ← Increase from 4Gi
```

### Slow Dashboard Queries

**Symptoms**: Dashboards take >10s to load

**Use recording rules**:

```yaml
# prometheus/values.yaml
additionalPrometheusRulesMap:
  intellirag-recordings:
    groups:
      - name: intellirag_recordings
        interval: 30s
        rules:
          - record: job:http_request_rate:5m
            expr: sum(rate(http_requests_total{job="intellirag"}[5m]))
```

**Optimize queries**:
```promql
# ❌ Expensive
rate(http_requests_total[5m])

# ✅ Better (aggregated)
sum by(endpoint) (rate(http_requests_total[5m]))

# ✅ Best (use recording rule)
job:http_request_rate:5m
```

---

## Common Error Messages

### "context deadline exceeded"

**Cause**: Query timeout

**Fix**: Increase `query_timeout` in datasource settings or optimize query

### "too many open files"

**Cause**: File descriptor limit reached

**Fix**:
```bash
kubectl edit deployment/<component> -n observability

# Add:
spec:
  template:
    spec:
      containers:
        - name: prometheus
          securityContext:
            ulimits:
              nofile:
                soft: 65536
                hard: 65536
```

### "out of memory"

**Cause**: Insufficient memory allocation

**Fix**: Increase memory limits in values.yaml

---

## Getting Help

### Collect Diagnostic Information

```bash
#!/bin/bash
# diagnose-observability.sh

echo "=== Pod Status ==="
kubectl get pods -n observability

echo "=== Resource Usage ==="
kubectl top pods -n observability

echo "=== Recent Events ==="
kubectl get events -n observability --sort-by='.lastTimestamp' | tail -20

echo "=== Prometheus Targets ==="
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090 &
sleep 5
curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | {job: .labels.job, health: .health}'
kill %1

echo "=== Persistent Volume Status ==="
kubectl get pvc -n observability
```

### Support Channels

- **Documentation**: `docs/deployment/observability/`
- **GitHub Issues**: Include diagnostic output
- **Slack**: `#observability` channel with diagnostic info

---

*For deployment guide, see [observability-deployment-guide.md](observability-deployment-guide.md)*
*For best practices, see [observability-best-practices.md](observability-best-practices.md)*
