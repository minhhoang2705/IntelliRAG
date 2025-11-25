# Day 3: Observability Integration & Optimization

**Duration**: 5-6 hours
**Prerequisites**: Prometheus/Grafana running, Day 1-2 complete
**Output**: Grafana dashboards, alerting rules, optimized configurations

---

## 🎯 Objectives

1. Configure Prometheus to scrape vLLM and embedding metrics
2. Create comprehensive Grafana dashboard (10+ panels)
3. Set up alerting rules for critical conditions
4. Optimize vLLM and embedding configurations based on Day 1-2 data
5. Validate 20%+ performance improvement

---

## 📋 Tasks Overview

| Task | Duration | Output |
|------|----------|--------|
| 3.1 Verify Prometheus Metrics | 1 hour | Metrics endpoints validated |
| 3.2 Configure ServiceMonitors | 30 min | Prometheus scraping configured |
| 3.3 Create Grafana Dashboard | 2 hours | 10-panel dashboard |
| 3.4 Configure Alerting Rules | 1 hour | 6+ alert rules |
| 3.5 Optimize Configurations | 1.5 hours | Optimized vLLM/embedding configs |

---

## Task 3.1: Verify Prometheus Metrics (1 hour)

### Check vLLM Metrics Endpoint

```bash
# On local GPU server (minikube context)
kubectl config use-context minikube

# Get vLLM pod
VLLM_POD=$(kubectl get pods -n kserve -l serving.kserve.io/inferenceservice=vllm-qwen -o jsonpath='{.items[0].metadata.name}')

echo "vLLM Pod: $VLLM_POD"

# Port-forward to vLLM metrics
kubectl port-forward -n kserve $VLLM_POD 8000:8000 &

# Check metrics endpoint
curl http://localhost:8000/metrics | head -100

# Look for key metrics:
# - vllm:num_requests_running
# - vllm:num_requests_waiting
# - vllm:gpu_cache_usage_perc
# - vllm:time_to_first_token_seconds
# - http_requests_total
# - request_duration_seconds_bucket
```

**Save sample metrics**:
```bash
curl http://localhost:8000/metrics > /tmp/vllm-metrics-sample.txt

# Grep for vLLM-specific metrics
grep "vllm:" /tmp/vllm-metrics-sample.txt
```

### Check Embedding Metrics Endpoint

```bash
# Get embedding pod
EMBED_POD=$(kubectl get pods -n kserve -l serving.kserve.io/inferenceservice=embedding-service -o jsonpath='{.items[0].metadata.name}')

# Port-forward (use different local port)
kubectl port-forward -n kserve $EMBED_POD 8080:8080 &

# Check metrics
curl http://localhost:8080/metrics | head -100

# Look for:
# - http_requests_total
# - http_request_duration_seconds
# - process_cpu_seconds_total
# - process_resident_memory_bytes
```

### Success Criteria
- ✅ vLLM metrics endpoint accessible
- ✅ Embedding metrics endpoint accessible
- ✅ At least 10 useful metrics found per service

---

## Task 3.2: Configure Prometheus ServiceMonitors (30 minutes)

### Create vLLM ServiceMonitor

Create `kubernetes/kserve/servicemonitor-vllm.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-metrics
  namespace: kserve
  labels:
    app: vllm-qwen
    release: prometheus  # Match your Prometheus operator label
spec:
  selector:
    matchLabels:
      serving.kserve.io/inferenceservice: vllm-qwen
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
      scrapeTimeout: 10s
```

### Create Embedding ServiceMonitor

Create `kubernetes/kserve/servicemonitor-embedding.yaml`:

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: embedding-metrics
  namespace: kserve
  labels:
    app: embedding-service
    release: prometheus
spec:
  selector:
    matchLabels:
      serving.kserve.io/inferenceservice: embedding-service
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
      scrapeTimeout: 10s
```

### Apply ServiceMonitors

```bash
# Apply to GKE cluster (if Prometheus Operator installed)
kubectl config use-context <gke-context>

kubectl apply -f kubernetes/kserve/servicemonitor-vllm.yaml
kubectl apply -f kubernetes/kserve/servicemonitor-embedding.yaml

# Verify ServiceMonitors created
kubectl get servicemonitor -n kserve

# Wait 30 seconds for Prometheus to discover targets
sleep 30

# Check Prometheus targets
kubectl port-forward -n observability svc/prometheus-server 9090:80 &

# Open http://localhost:9090/targets
# Look for vllm-metrics and embedding-metrics targets (should be UP)
```

**If targets show as DOWN**: Check labels match between ServiceMonitor and Service

---

## Task 3.3: Create Grafana Dashboard (2 hours)

### Access Grafana

```bash
# Port-forward to Grafana
kubectl port-forward -n observability svc/grafana 3000:80

# Get admin password
kubectl get secret -n observability grafana -o jsonpath="{.data.admin-password}" | base64 --decode

# Open http://localhost:3000
# Login: admin / <password-from-above>
```

### Create Dashboard JSON

Create `observability/grafana/provisioning/dashboards/json/model-serving.json`:

**Panel 1: vLLM Request Rate**
```json
{
  "title": "vLLM Request Rate",
  "targets": [{
    "expr": "rate(http_requests_total{job=\"vllm-qwen\"}[5m])",
    "legendFormat": "{{method}} {{status}}"
  }],
  "type": "graph"
}
```

**Complete dashboard structure** (simplified):
```json
{
  "dashboard": {
    "title": "Model Serving - IntelliRAG",
    "panels": [
      {
        "id": 1,
        "title": "vLLM Request Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(http_requests_total{service=\"vllm-qwen\"}[5m])",
          "legendFormat": "Requests/sec"
        }]
      },
      {
        "id": 2,
        "title": "vLLM P95 Latency",
        "type": "timeseries",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(request_duration_seconds_bucket{service=\"vllm-qwen\"}[5m]))",
          "legendFormat": "P95"
        }],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 0.5, "color": "yellow"},
                {"value": 1, "color": "red"}
              ]
            }
          }
        }
      },
      {
        "id": 3,
        "title": "vLLM Queue Depth",
        "type": "timeseries",
        "targets": [{
          "expr": "vllm_num_requests_waiting",
          "legendFormat": "Waiting Requests"
        }]
      },
      {
        "id": 4,
        "title": "GPU Utilization",
        "type": "gauge",
        "targets": [{
          "expr": "nvidia_gpu_utilization{gpu=\"0\"}",
          "legendFormat": "GPU {{gpu}}"
        }],
        "fieldConfig": {
          "defaults": {
            "min": 0,
            "max": 100,
            "thresholds": {
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 70, "color": "yellow"},
                {"value": 90, "color": "green"}
              ]
            }
          }
        }
      },
      {
        "id": 5,
        "title": "GPU Memory Usage",
        "type": "gauge",
        "targets": [{
          "expr": "nvidia_gpu_memory_used_bytes{gpu=\"0\"} / nvidia_gpu_memory_total_bytes{gpu=\"0\"} * 100",
          "legendFormat": "GPU Memory %"
        }],
        "fieldConfig": {
          "defaults": {
            "max": 100,
            "thresholds": {
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 85, "color": "yellow"},
                {"value": 95, "color": "red"}
              ]
            }
          }
        }
      },
      {
        "id": 6,
        "title": "Embedding Request Rate",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(http_requests_total{service=\"embedding-service\"}[5m])"
        }]
      },
      {
        "id": 7,
        "title": "Embedding P95 Latency",
        "type": "timeseries",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(request_duration_seconds_bucket{service=\"embedding-service\"}[5m]))"
        }],
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 0.3, "color": "yellow"},
                {"value": 0.5, "color": "red"}
              ]
            }
          }
        }
      },
      {
        "id": 8,
        "title": "Embedding CPU Usage",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(container_cpu_usage_seconds_total{pod=~\"embedding-service.*\"}[5m])"
        }]
      },
      {
        "id": 9,
        "title": "Error Rate (5xx)",
        "type": "timeseries",
        "targets": [{
          "expr": "rate(http_requests_total{status=~\"5..\"}[5m])"
        }],
        "alert": {
          "name": "High Error Rate",
          "conditions": [{
            "evaluator": {
              "params": [0.01],
              "type": "gt"
            }
          }]
        }
      },
      {
        "id": 10,
        "title": "CloudFlare Tunnel Health",
        "type": "stat",
        "targets": [{
          "expr": "probe_success{target=\"https://llm.blockchainradar.xyz\"}"
        }],
        "fieldConfig": {
          "defaults": {
            "mappings": [
              {"value": 1, "text": "UP", "color": "green"},
              {"value": 0, "text": "DOWN", "color": "red"}
            ]
          }
        }
      }
    ]
  }
}
```

### Import Dashboard

1. Open Grafana: http://localhost:3000
2. Click "+" → "Import"
3. Upload `model-serving.json`
4. Select Prometheus datasource
5. Click "Import"

### Verify Dashboard

- All panels showing data (not "No data")
- Metrics updating in real-time
- Thresholds configured correctly

**Take screenshots** for documentation

---

## Task 3.4: Configure Alerting Rules (1 hour)

Create `observability/grafana/alerts/model-serving-alerts.yaml`:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-model-serving-alerts
  namespace: observability
data:
  model-serving-alerts.yml: |
    groups:
      - name: model_serving
        interval: 30s
        rules:
          - alert: HighVLLMLatency
            expr: histogram_quantile(0.95, rate(request_duration_seconds_bucket{service="vllm-qwen"}[5m])) > 1
            for: 5m
            labels:
              severity: warning
              component: vllm
            annotations:
              summary: "vLLM P95 latency >1s for 5 minutes"
              description: "Current P95 latency: {{ $value }}s. Check GPU utilization and queue depth."
              runbook_url: "https://docs.intellirag.example.com/runbooks/high-latency"

          - alert: VLLMServiceDown
            expr: up{job="vllm-qwen"} == 0
            for: 2m
            labels:
              severity: critical
              component: vllm
            annotations:
              summary: "vLLM service is down"
              description: "vLLM InferenceService unavailable for 2 minutes."

          - alert: GPUMemoryHigh
            expr: nvidia_gpu_memory_used_bytes{gpu="0"} / nvidia_gpu_memory_total_bytes{gpu="0"} > 0.95
            for: 10m
            labels:
              severity: warning
              component: gpu
            annotations:
              summary: "GPU memory >95% for 10 minutes"
              description: "GPU {{ $labels.gpu }} memory usage at {{ $value | humanizePercentage }}. Consider reducing batch size."

          - alert: EmbeddingHighLatency
            expr: histogram_quantile(0.95, rate(request_duration_seconds_bucket{service="embedding-service"}[5m])) > 0.5
            for: 5m
            labels:
              severity: warning
              component: embedding
            annotations:
              summary: "Embedding P95 latency >500ms"
              description: "Current latency: {{ $value }}s. Check CPU utilization."

          - alert: HighErrorRate
            expr: rate(http_requests_total{status=~"5.."}[5m]) > 0.01
            for: 3m
            labels:
              severity: critical
              component: api
            annotations:
              summary: "Error rate >1% for 3 minutes"
              description: "5xx errors at {{ $value | humanizePercentage }}. Check application logs."

          - alert: CloudFlareTunnelDown
            expr: probe_success{target="https://llm.blockchainradar.xyz"} == 0
            for: 2m
            labels:
              severity: critical
              component: networking
            annotations:
              summary: "CloudFlare Tunnel is down"
              description: "Cannot reach local GPU server via CloudFlare Tunnel."
```

Apply alerts:
```bash
kubectl apply -f observability/grafana/alerts/model-serving-alerts.yaml

# Verify alerts loaded in Prometheus
# Open http://localhost:9090/alerts
```

---

## Task 3.5: Optimize Configurations (1.5 hours)

### Based on Day 1-2 Data, Choose Optimization Path

#### Scenario A: GPU Utilization <90%

Edit `kubernetes/kserve/vllm-qwen-inference.yaml`:

```yaml
spec:
  predictor:
    containers:
      - name: kserve-container
        image: vllm/vllm-openai:latest
        args:
          - --model=Qwen/Qwen3-0.6B
          - --gpu-memory-utilization=0.95  # INCREASE from 0.5
          - --max-model-len=8192           # INCREASE from 4096
          - --max-num-seqs=512             # INCREASE batch size
          - --enable-prefix-caching
          - --enable-chunked-prefill
```

#### Scenario B: High Latency but GPU Not Saturated

```yaml
args:
  - --model=Qwen/Qwen3-0.6B
  - --gpu-memory-utilization=0.95
  - --kv-cache-dtype=fp8     # ADD: Use FP8 for KV cache
  - --enforce-eager          # ADD: Disable CUDA graphs if overhead high
  - --enable-prefix-caching
```

#### Scenario C: GPU Memory Constrained

```yaml
args:
  - --model=Qwen/Qwen3-0.6B
  - --gpu-memory-utilization=0.90  # REDUCE slightly
  - --max-model-len=4096            # REDUCE
  - --quantization=fp8              # ADD: Quantize model
```

### Optimize Embedding Service

Edit `kubernetes/kserve/embedding-inference.yaml`:

```yaml
env:
  - name: MAX_BATCH_SIZE
    value: "128"  # INCREASE from 32 (based on Day 1 findings)
  - name: MAX_WORKERS
    value: "4"    # INCREASE parallelism
```

### Optimize CloudFlare Tunnel

Edit `~/.cloudflared/config.yml` on local server:

```yaml
ingress:
  - hostname: llm.blockchainradar.xyz
    service: http://localhost:8000
    originRequest:
      connectTimeout: 60s
      keepAliveConnections: 100   # ADD
      keepAliveTimeout: 90s        # ADD
      tcpKeepAlive: 30s            # ADD
```

### Apply Optimizations

```bash
# Apply vLLM changes
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml

# Apply embedding changes
kubectl apply -f kubernetes/kserve/embedding-inference.yaml

# Restart CloudFlare Tunnel
ssh user@gpu-server
sudo systemctl restart cloudflared

# Wait for pods to restart
kubectl rollout status -n kserve inferenceservice/vllm-qwen
kubectl rollout status -n kserve inferenceservice/embedding-service
```

### Verify Improvements

Re-run key tests from Day 2:

```bash
# Test vLLM throughput
hey -n 1000 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"Hello"}],"max_tokens":20}' \
  https://llm.blockchainradar.xyz/v1/chat/completions

# Compare results with Day 2 baseline
# Target: 20% improvement in throughput or latency
```

### Deliverable

Create `docs/phase-3/reports/optimization-results.md`:

```markdown
# Optimization Results

**Date**: 2025-11-21

## Configuration Changes

### vLLM Optimizations
| Parameter | Before | After | Rationale |
|-----------|--------|-------|-----------|
| gpu-memory-utilization | 0.5 | 0.95 | Day 1 showed only 85% memory usage |
| max-num-seqs | 256 | 512 | Increase batch size for throughput |
| [other] | X | Y | [reason] |

### Embedding Optimizations
| Parameter | Before | After | Rationale |
|-----------|--------|-------|-----------|
| MAX_BATCH_SIZE | 32 | 128 | Day 1 identified optimal at 128 |
| [other] | X | Y | [reason] |

### CloudFlare Tunnel
- Added keepAliveConnections: 100
- Reduced connection overhead by ~Xms

## Performance Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| vLLM Throughput | XXX TPS | XXX TPS | +XX% |
| vLLM P95 Latency | XXXms | XXXms | -XX% |
| GPU Utilization | XX% | XX% | +XX% |
| Embedding P95 Latency | XXXms | XXXms | -XX% |

**Target**: 20% improvement ✅ / ❌

## Grafana Dashboard Verification

[Include screenshot showing improved metrics]

## Recommendations

- [If target not met, suggest additional optimizations]
- [If target exceeded, document safe operating parameters]
```

---

## ✅ Day 3 Completion Checklist

- [ ] Prometheus metrics verified for vLLM and embedding
- [ ] ServiceMonitors created and applied
- [ ] Grafana dashboard created with 10+ panels
- [ ] Dashboard imported and verified in Grafana
- [ ] Alerting rules configured (6 rules)
- [ ] Alerts verified in Prometheus
- [ ] vLLM configuration optimized based on data
- [ ] Embedding configuration optimized
- [ ] CloudFlare Tunnel optimized
- [ ] Performance improvements validated (20%+ target)
- [ ] Optimization results documented

**Success Criteria**:
- All Prometheus targets showing UP status
- Grafana dashboard displaying real-time metrics
- At least 6 alert rules active
- 20%+ performance improvement achieved
- Optimization rationale documented

---

## 🔧 Troubleshooting

### Issue: ServiceMonitor not discovered by Prometheus
```bash
# Check ServiceMonitor labels match Prometheus selector
kubectl get prometheus -n observability -o yaml | grep serviceMonitorSelector

# Ensure namespace is monitored
kubectl label namespace kserve monitoring=enabled
```

### Issue: Grafana shows "No data" for panels
```bash
# Verify Prometheus can scrape targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[] | select(.labels.job | contains("vllm"))'

# Check metric names in Prometheus
curl http://localhost:9090/api/v1/label/__name__/values | jq . | grep vllm
```

### Issue: Optimizations caused pods to crash
```bash
# Check pod logs
kubectl logs -n kserve -l serving.kserve.io/inferenceservice=vllm-qwen

# Common issues:
# - OOM: Reduce --gpu-memory-utilization
# - Invalid args: Check vLLM documentation

# Rollback to previous config
kubectl rollout undo -n kserve inferenceservice/vllm-qwen
```

---

## 📚 Resources

- [Prometheus ServiceMonitor](https://prometheus-operator.dev/docs/operator/design/#servicemonitor)
- [Grafana Dashboard Best Practices](https://grafana.com/docs/grafana/latest/dashboards/build-dashboards/best-practices/)
- [vLLM Performance Tuning](https://docs.vllm.ai/en/latest/serving/performance_optimization.html)

---

**Next**: [Day 4: NGINX Ingress & TLS](./day4-nginx-tls.md)

**Last Updated**: 2025-11-21
