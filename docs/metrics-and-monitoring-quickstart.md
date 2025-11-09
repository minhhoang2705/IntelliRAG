# Metrics & Monitoring Quick Start Guide

**Date**: 2025-11-09
**Status**: ✅ Production Ready
**Time to Setup**: 10 minutes

---

## 🎯 What You Just Got

### ✅ Metrics Instrumentation (Phase 1 & 2 Complete)
- **HTTP Request Metrics**: Track requests/sec, response times, error rates
- **LLM Token Metrics**: Monitor token usage, costs, input vs output

### ✅ Grafana Dashboards (3 New + 1 Updated)
1. **System Health Overview** - Main monitoring dashboard
2. **HTTP API Performance** - Deep dive into API metrics
3. **LLM Metrics** (Updated) - Token usage and costs

### ✅ Alert Rules (16 total, 4 new)
- Critical: ServiceDown, HighErrorRate, HighLatency, GPUOverload
- Warning: LowSuccessRate, HighClientErrorRate, HighTokenUsageRate, SlowP95ResponseTime
- Info: NewDeployment, QueryTypeDistributionShift

---

## 🚀 Quick Start (3 Steps)

### Step 1: Start Your Services

```bash
# Start IntelliRAG API
uvicorn app.main:app --reload

# Your metrics are now exposed at:
# http://localhost:8000/metrics
```

**Verify Metrics**:
```bash
curl http://localhost:8000/metrics | grep -E "(http_requests_total|llm_token_count_total)"
```

Expected output:
```prometheus
http_requests_total{method="GET",endpoint="/health",status_code="200"} 1.0
llm_token_count_total{model="Qwen/Qwen2.5-7B-Instruct",type="input"} 0.0
llm_token_count_total{model="Qwen/Qwen2.5-7B-Instruct",type="output"} 0.0
```

---

### Step 2: Deploy Observability Stack

```bash
# Navigate to observability directory
cd kubernetes/observability

# Deploy Prometheus, Grafana, Jaeger, Loki
helmfile apply

# Wait for pods to be ready
kubectl get pods -n observability

# Port forward to Grafana
kubectl port-forward -n observability svc/grafana 3000:80
```

**Access Grafana**:
- URL: http://localhost:3000
- Username: `admin`
- Password: `admin` (change on first login)

---

### Step 3: View Dashboards

Navigate to:
1. **Dashboards** → **IntelliRAG** folder
2. Open **"System Health Overview"**
3. You should see:
   - Service Status: UP (green)
   - Request Rate: 0-X RPS
   - P95 Response Time: <1s
   - Error Rate: 0%

**Generate Some Traffic**:
```bash
# Make a few requests
for i in {1..10}; do
  curl http://localhost:8000/health
  curl -X POST http://localhost:8000/api/v1/query \
    -H "Content-Type: application/json" \
    -d '{"query": "What is Python?"}'
done
```

**Refresh Dashboard** - You should now see:
- Request rate increasing
- Response times populated
- Token counts incrementing

---

## 📊 Dashboard Tour

### System Health Overview
**What It Shows**:
- Overall system status at a glance
- Key performance indicators (KPIs)
- Cost estimates

**When to Use**:
- Daily health checks
- Incident response
- Executive reports

**Key Panels**:
1. Service Status - Is the system up?
2. Request Rate - How much traffic?
3. P95 Response Time - How fast?
4. Error Rate - How reliable?
5. Estimated Cost - How much $?

---

### HTTP API Performance
**What It Shows**:
- Detailed HTTP request metrics
- Per-endpoint performance
- Error analysis

**When to Use**:
- Performance optimization
- Debugging slow endpoints
- Capacity planning

**Key Insights**:
- Which endpoints are slowest?
- What's the error distribution?
- How does traffic vary by method (GET/POST)?

**Pro Tip**: Use the "Top Slowest Endpoints" table to identify optimization targets

---

### LLM Metrics
**What It Shows**:
- Token usage rates (input vs output)
- GPU utilization
- Cost projections

**When to Use**:
- Cost optimization
- Token efficiency analysis
- Model performance tracking

**Key Insights**:
- Input/output token ratio
- Daily token consumption
- Hourly cost estimates

**Pro Tip**: Monitor input vs output ratio - higher output means more generation, higher costs

---

## 🚨 Understanding Alerts

### Alert Workflow

1. **Alert Fires** → Prometheus evaluates rule
2. **Notification Sent** → To configured channels (Slack/Email)
3. **Investigate** → Use dashboards to diagnose
4. **Resolve** → Fix issue
5. **Alert Resolves** → Auto-closes when condition clears

### Critical Alerts (Immediate Action Required)

#### ServiceDown
**What**: API is unreachable
**Action**:
```bash
# Check if service is running
kubectl get pods -n default | grep intellirag

# View logs
kubectl logs -n default <pod-name>

# Restart if needed
kubectl rollout restart deployment/intellirag
```

#### HighErrorRate
**What**: > 5% of requests returning 5xx errors
**Action**:
1. Open **HTTP API Performance** dashboard
2. Check **Error Details** table
3. View application logs for stack traces
4. Review recent deployments

#### HighLatency
**What**: P99 latency > 5 seconds
**Action**:
1. Check **Per-Endpoint Response Time** in HTTP dashboard
2. Review **LLM Metrics** for slow generation
3. Check database query performance
4. Consider scaling resources

---

### Warning Alerts (Monitor & Plan)

#### LowSuccessRate (NEW)
**What**: < 95% of requests successful
**Action**:
- Review error distribution
- Check for client-side issues
- Investigate infrastructure problems

#### HighTokenUsageRate (NEW)
**What**: > 10,000 tokens/sec
**Action**:
- Check for traffic spikes
- Review query patterns
- Consider rate limiting

#### HighCost
**What**: Token costs exceeding budget
**Action**:
1. Open **LLM Metrics** dashboard
2. Review token usage patterns
3. Optimize:
   - Reduce `max_tokens` parameter
   - Lower `temperature` for deterministic outputs
   - Cache common responses
   - Optimize prompt templates

---

## 💰 Cost Monitoring

### Current Pricing (Example)
- Input tokens: $0.15 / 1M tokens
- Output tokens: $0.60 / 1M tokens

### Calculate Daily Cost

**Dashboard**: LLM Metrics → "Estimated Cost (Hourly)"

**Manual Calculation**:
```promql
# Hourly cost
(sum(rate(llm_token_count_total{type="input"}[1h])) * 0.00015 / 1000 +
 sum(rate(llm_token_count_total{type="output"}[1h])) * 0.0006 / 1000) * 3600

# Daily cost (multiply by 24)
# Monthly cost (multiply by 730)
```

### Cost Optimization Tips

1. **Reduce Max Tokens**
   ```python
   # Before
   llm_client.generate(prompt, max_tokens=512)

   # After
   llm_client.generate(prompt, max_tokens=256)  # 50% cost reduction
   ```

2. **Lower Temperature**
   ```python
   # Before
   llm_client.generate(prompt, temperature=0.7)

   # After
   llm_client.generate(prompt, temperature=0.3)  # More deterministic, less sampling
   ```

3. **Cache Responses**
   - Implement response caching for common queries
   - Use Redis or in-memory cache
   - Cache TTL: 1 hour for dynamic, 24h for static

---

## 🔍 Troubleshooting

### "No Data" in Dashboards

**Possible Causes**:
1. Prometheus not scraping IntelliRAG
2. Metrics endpoint not accessible
3. Incorrect job label

**Fix**:
```bash
# 1. Check Prometheus targets
kubectl port-forward -n observability svc/prometheus 9090:9090
# Open: http://localhost:9090/targets
# Look for "intellirag" job - should be "UP"

# 2. Test metrics endpoint
curl http://localhost:8000/metrics

# 3. Check Prometheus config
kubectl get configmap -n observability prometheus-server -o yaml | grep intellirag
```

---

### Metrics Not Incrementing

**Check**:
1. **Is traffic flowing?**
   ```bash
   # Generate test traffic
   for i in {1..100}; do
     curl http://localhost:8000/health
   done

   # Check metrics
   curl http://localhost:8000/metrics | grep http_requests_total
   ```

2. **Are metrics instrumented?**
   ```bash
   # Search for metric usage in code
   grep -r "http_requests_total" app/
   grep -r "llm_token_count" app/
   ```

3. **Check logs for errors**
   ```bash
   # Look for metric-related errors
   kubectl logs -n default <pod-name> | grep -i metric
   ```

---

### Alert Not Firing

**Debug Steps**:
1. **Check alert rule syntax**
   ```bash
   # Validate Prometheus rules
   promtool check rules observability/grafana/alerts/alerting-rules.yaml
   ```

2. **Test alert expression manually**
   ```bash
   # In Prometheus UI (localhost:9090)
   # Paste alert expression, should return > 0 when condition met
   ```

3. **Check evaluation interval**
   - Alerts evaluate every 30s-5min
   - Wait for `for` duration to pass
   - Check alert state in Prometheus UI

---

## 📈 Performance Baselines

Use these as reference for "normal" performance:

| Metric | Good | Warning | Critical |
|--------|------|---------|----------|
| **P95 Latency** | < 500ms | 500ms - 2s | > 2s |
| **P99 Latency** | < 1s | 1s - 5s | > 5s |
| **Error Rate** | < 0.1% | 0.1% - 1% | > 1% |
| **Success Rate** | > 99.9% | 95% - 99.9% | < 95% |
| **Request Rate** | Varies | - | - |
| **Token/Request** | 50-200 | 200-500 | > 500 |
| **GPU Utilization** | 60-80% | 80-95% | > 95% |

---

## 🎯 Next Steps

### Week 1: Observe
- Monitor dashboards daily
- Note baseline metrics
- Adjust alert thresholds if needed

### Week 2: Optimize
- Identify slowest endpoints
- Reduce token usage
- Set cost budgets

### Week 3: Scale
- Review capacity metrics
- Plan for growth
- Add auto-scaling rules

### Week 4: Automate
- Set up notification channels
- Create runbooks for alerts
- Implement auto-remediation

---

## 📚 Learn More

- **Full Documentation**: `docs/grafana-dashboards-and-alerts.md`
- **Metrics Implementation**: `docs/metrics-implementation-summary.md`
- **Gap Analysis**: `docs/metrics-gap-analysis.md`

---

## ✅ Success Checklist

- [ ] Metrics endpoint accessible at `/metrics`
- [ ] Prometheus scraping IntelliRAG successfully
- [ ] Grafana dashboards loading with data
- [ ] System Health dashboard shows "UP" status
- [ ] HTTP metrics incrementing with traffic
- [ ] LLM token counts updating after queries
- [ ] Alert rules deployed to Prometheus
- [ ] Notification channels configured
- [ ] Baseline metrics documented
- [ ] Team trained on dashboard usage

---

**Congratulations!** Your IntelliRAG system now has production-grade monitoring 🎉

**Need Help?**
- Check documentation in `docs/`
- Review alert runbooks
- Test traffic: `curl http://localhost:8000/health`

---

**Last Updated**: 2025-11-09
**Status**: ✅ Ready for Production
