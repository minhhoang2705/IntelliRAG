# Grafana Dashboards and Alerts Guide

**Date**: 2025-11-09
**Status**: ✅ Production Ready
**Grafana Version**: 9.x+
**Prometheus Version**: 2.x+

---

## 📊 Overview

IntelliRAG includes **8 comprehensive Grafana dashboards** and **16 alert rules** for monitoring system health, performance, and costs.

### New Dashboards Created (3)
1. **System Health Overview** - Main dashboard showing overall system status
2. **HTTP API Performance** - Detailed HTTP metrics and API performance
3. **LLM Metrics** - Updated with correct metric names for token tracking

### Existing Dashboards (5)
4. Infrastructure
5. Ingestion Pipeline
6. IntelliRAG Overview
7. Query Performance

---

## 🎯 Dashboard Guide

### 1. System Health Overview (`system-health-overview`)

**Purpose**: Single-pane view of system health for quick status checks

**Key Panels**:
- **Service Status** - UP/DOWN indicator
- **Request Rate** - Current RPS
- **P95 Response Time** - 95th percentile latency
- **Error Rate** - Percentage of 5xx errors
- **Active Jobs** - Ingestion queue depth
- **HTTP Traffic** - Request breakdown by status code
- **LLM Token Usage** - Input vs output tokens/sec
- **Estimated Cost** - Hourly cost projection ($0.15/1M input, $0.60/1M output)
- **Success Rate** - Percentage of 2xx responses
- **Avg Tokens/Request** - Token efficiency

**Best For**:
- Daily health checks
- Incident response
- Executive summaries

**Refresh Rate**: 30 seconds

---

### 2. HTTP API Performance (`http-api-performance`)

**Purpose**: Deep dive into HTTP request metrics and API performance

**Key Panels**:
- **Request Rate (RPS)** - Total, 2xx, 4xx, 5xx breakdown
- **Response Time (P50, P95, P99)** - Latency percentiles
- **Error Rate %** - Server error percentage
- **Avg Response Time** - Mean latency
- **Total Requests (5min)** - Request volume
- **Status Code Distribution** - Pie chart of status codes
- **Per-Endpoint Response Time (P95)** - Endpoint-specific latency
- **Requests by Method** - GET vs POST breakdown
- **Top Slowest Endpoints** - Table of slowest endpoints
- **Error Details** - Table of recent errors

**Best For**:
- Performance optimization
- Identifying slow endpoints
- API debugging
- Capacity planning

**Refresh Rate**: 30 seconds

**Key Queries**:
```promql
# Request rate
sum(rate(http_requests_total{job="intellirag"}[5m]))

# P95 latency
histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket{job="intellirag"}[5m])) by (le))

# Error rate
sum(rate(http_requests_total{job="intellirag",status_code=~"5.."}[5m])) / sum(rate(http_requests_total{job="intellirag"}[5m])) * 100
```

---

### 3. LLM Metrics (`llm-metrics`)

**Purpose**: Monitor LLM token usage and costs

**Key Panels**:
- **Token Usage (Input vs Output)** - Tokens/sec by type
- **GPU Utilization** - GPU usage percentage (gauge)
- **Total Tokens (24h)** - Daily token consumption
- *Plus other existing panels*

**Best For**:
- Cost monitoring
- Token usage optimization
- Model performance tracking

**Refresh Rate**: 30 seconds

**Key Queries**:
```promql
# Input tokens per second
rate(llm_token_count_total{job="intellirag",type="input"}[5m])

# Output tokens per second
rate(llm_token_count_total{job="intellirag",type="output"}[5m])

# Daily token total
sum(increase(llm_token_count_total{job="intellirag"}[24h]))

# Hourly cost estimate
(sum(rate(llm_token_count_total{type="input"}[1h])) * 0.00015 / 1000 +
 sum(rate(llm_token_count_total{type="output"}[1h])) * 0.0006 / 1000) * 3600
```

---

## 🚨 Alert Rules

### Alert Severity Levels

| Severity | Description | Response Time |
|----------|-------------|---------------|
| **Critical** | System down or severely degraded | Immediate (15 min) |
| **Warning** | Performance degradation or approaching limits | 1-4 hours |
| **Info** | Informational, no action required | Review daily |

---

### Critical Alerts (5)

#### 1. ServiceDown
**Trigger**: Service unreachable for 1 minute
**Expression**: `up{job="intellirag"} == 0`
**Action**:
- Check if service is running
- Review logs for crash reasons
- Restart service if needed

#### 2. HighErrorRate
**Trigger**: 5xx error rate > 5% for 5 minutes
**Expression**: `rate(http_requests_total{status_code=~"5.."}[5m]) > 0.05`
**Action**:
- Check application logs for errors
- Review recent deployments
- Investigate database/external service connectivity

#### 3. HighLatency
**Trigger**: P99 latency > 5 seconds for 5 minutes
**Expression**: `histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 5`
**Action**:
- Check endpoint-specific latency in HTTP API dashboard
- Review database query performance
- Investigate LLM response times

#### 4. GPUOverload
**Trigger**: GPU utilization > 95% for 10 minutes
**Expression**: `gpu_utilization_percent{job="intellirag"} > 95`
**Action**:
- Consider reducing max_tokens or temperature
- Scale horizontally if possible
- Review vLLM batch size settings

---

### Warning Alerts (10)

#### 5. QueueBacklog
**Trigger**: > 100 active ingestion jobs for 5 minutes
**Expression**: `ingestion_jobs_active{job="intellirag"} > 100`
**Action**:
- Scale ingestion workers
- Check for stuck jobs
- Review ingestion pipeline performance

#### 6. LowCacheHitRate
**Trigger**: Cache miss rate > 50% for 10 minutes
**Expression**: Complex rate calculation
**Action**:
- Review cache configuration
- Increase cache size if memory available
- Analyze query patterns

#### 7. SlowVectorSearch
**Trigger**: P95 vector search > 1 second for 10 minutes
**Expression**: `histogram_quantile(0.95, rate(vector_db_operations_total{operation="search"}[5m])) > 1`
**Action**:
- Check Qdrant performance metrics
- Review index configuration
- Consider increasing resources

#### 8. IngestionErrors
**Trigger**: Ingestion error rate > 0.01/s for 5 minutes
**Expression**: `rate(ingestion_errors_total[5m]) > 0.01`
**Action**:
- Check ingestion logs by error type
- Review file validation logic
- Investigate storage connectivity

#### 9. HighMemoryUsage
**Trigger**: Container memory > 85% for 5 minutes
**Expression**: Memory usage ratio > 0.85
**Action**:
- Increase memory limits
- Check for memory leaks
- Review resource requests

#### 10. PodRestarting
**Trigger**: > 3 restarts in 1 hour
**Expression**: `increase(kube_pod_container_status_restarts_total[1h]) > 3`
**Action**:
- Check pod logs
- Review OOM errors
- Investigate crash loops

#### 11. HighCost (UPDATED)
**Trigger**: Token cost > $0.01/5min for 10 minutes
**Expression**: `(rate(llm_token_count_total{type="input"}[5m]) * 0.00015 / 1000) + (rate(llm_token_count_total{type="output"}[5m]) * 0.0006 / 1000) > 0.01`
**Action**:
- Review token usage by endpoint
- Optimize prompt templates
- Consider caching common responses
- Adjust temperature/max_tokens

#### 12. LowSuccessRate (NEW)
**Trigger**: Success rate < 95% for 5 minutes
**Expression**: `sum(rate(http_requests_total{status_code=~"2.."}[5m])) / sum(rate(http_requests_total[5m])) < 0.95`
**Action**:
- Check error details in HTTP API dashboard
- Review recent code changes
- Investigate client request patterns

#### 13. HighClientErrorRate (NEW)
**Trigger**: 4xx error rate > 10% for 5 minutes
**Expression**: `sum(rate(http_requests_total{status_code=~"4.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.1`
**Action**:
- Review API documentation
- Check client SDK versions
- Investigate malformed requests

#### 14. HighTokenUsageRate (NEW)
**Trigger**: Token usage > 10,000 tokens/sec for 10 minutes
**Expression**: `sum(rate(llm_token_count_total[5m])) > 10000`
**Action**:
- Review query patterns
- Check for abnormal traffic
- Consider rate limiting

#### 15. SlowP95ResponseTime (NEW)
**Trigger**: P95 latency > 2 seconds for 5 minutes
**Expression**: `histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (endpoint, le)) > 2`
**Action**:
- Check slow endpoints in dashboard
- Review database indexes
- Optimize query performance

---

### Info Alerts (2)

#### 16. NewDeployment
**Trigger**: Deployment updated
**Action**: Monitor for anomalies

#### 17. QueryTypeDistributionShift
**Trigger**: Query pattern shift > 30% vs 24h ago
**Action**: Review for expected changes

---

## 🛠️ Setup Instructions

### 1. Access Grafana

```bash
# Port forward to Grafana (if running in Kubernetes)
kubectl port-forward -n observability svc/grafana 3000:80

# Access at: http://localhost:3000
# Default credentials: admin/admin (change on first login)
```

### 2. Verify Dashboards

Dashboards are automatically provisioned from:
```
observability/grafana/provisioning/dashboards/json/
├── http-api-performance.json (NEW)
├── system-health.json (NEW)
├── llm-metrics.json (UPDATED)
├── infrastructure.json
├── ingestion-pipeline.json
├── intellirag-overview.json
└── query-performance.json
```

### 3. Configure Alerts

Alerts are provisioned from:
```
observability/grafana/alerts/alerting-rules.yaml
```

**To enable alerting**:
1. Configure notification channels (Slack, Email, PagerDuty)
2. Set up contact points in Grafana UI
3. Test alert notifications

### 4. Customize Thresholds

Edit `alerting-rules.yaml` to adjust thresholds:

```yaml
# Example: Change high latency threshold from 5s to 3s
- alert: HighLatency
  expr: histogram_quantile(0.99, rate(http_request_duration_seconds_bucket[5m])) > 3  # Changed from 5
  for: 5m
```

---

## 📈 Best Practices

### Dashboard Usage

1. **Start with System Health**
   - Check overall status first
   - Identify any critical issues

2. **Drill Down**
   - Use HTTP API dashboard for request issues
   - Use LLM dashboard for cost/token issues

3. **Set Time Range**
   - Default: Last 6 hours
   - Incidents: Last 1-2 hours
   - Trends: Last 7 days

### Alert Management

1. **Reduce Alert Fatigue**
   - Adjust thresholds based on baseline
   - Group related alerts
   - Use appropriate severity levels

2. **Alert Response**
   - Document runbooks for each alert
   - Track MTTR (Mean Time To Resolution)
   - Post-incident reviews

3. **Cost Optimization**
   - Set budget alerts
   - Monitor token efficiency
   - Review usage patterns weekly

---

## 🔍 Troubleshooting

### No Data in Dashboards

**Check**:
1. Prometheus is scraping IntelliRAG: `up{job="intellirag"} == 1`
2. Metrics endpoint is accessible: `curl http://localhost:8000/metrics`
3. Correct job label in prometheus config

### Alert Not Firing

**Check**:
1. Alert rule syntax is correct
2. Metric names match implementation (`llm_token_count_total` not `llm_token_count`)
3. Evaluation interval in Prometheus config

### High Dashboard Load Times

**Solutions**:
1. Reduce time range
2. Increase refresh interval (30s → 1min)
3. Optimize query complexity

---

## 📊 Metric Reference

### HTTP Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `http_requests_total` | Counter | method, endpoint, status_code | Total HTTP requests |
| `http_request_duration_seconds` | Histogram | method, endpoint | Request latency |

### LLM Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `llm_token_count_total` | Counter | model, type | Token usage (input/output) |

### Ingestion Metrics
| Metric | Type | Labels | Description |
|--------|------|--------|-------------|
| `ingestion_jobs_total` | Counter | status, file_type | Total ingestion jobs |
| `ingestion_jobs_active` | Gauge | status | Active ingestion jobs |
| `ingestion_errors_total` | Counter | error_type, stage | Ingestion errors |

---

## 🎯 SLO Targets

| Metric | Target | Current Alert Threshold |
|--------|--------|------------------------|
| **Availability** | 99.9% | Alert if down > 1min |
| **Success Rate** | > 99% | Alert if < 95% |
| **P95 Latency** | < 500ms | Alert if > 2s |
| **P99 Latency** | < 2s | Alert if > 5s |
| **Error Rate** | < 1% | Alert if > 5% |

---

## 📚 Additional Resources

- [Prometheus Query Basics](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [Alert Notification Channels](https://grafana.com/docs/grafana/latest/alerting/notifications/)

---

**Last Updated**: 2025-11-09
**Maintained By**: IntelliRAG Team
**Version**: 1.0
