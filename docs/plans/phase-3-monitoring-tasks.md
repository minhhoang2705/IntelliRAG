# Phase 3: Monitoring & Optimization Tasks (from Phase 2)

**Created**: 2025-11-20
**Status**: Pending
**Prerequisites**: Phase 2 Core Complete ✅
**Timeline**: 3-5 hours

---

## 📋 Overview

These tasks were transferred from Phase 2 after core model serving functionality was verified as 100% operational. They focus on **performance profiling, load testing, and observability** rather than functional deployment.

**Why Transferred**:
- Core functionality is production-ready
- These are optimization and monitoring concerns
- Fit better with Phase 3's "Production Hardening" theme
- Don't block Phase 2 completion

---

## 🎯 Task Categories

### 1. Performance Profiling (GPU/CPU Monitoring)
### 2. Load Testing (Stress & Capacity Planning)
### 3. Observability Integration (Prometheus & Grafana)
### 4. Performance Optimization (Based on Findings)

---

## 📊 Task 1: Performance Profiling

### Objective
Measure actual resource utilization under realistic load to validate Phase 0 benchmark claims and identify optimization opportunities.

### 1.1 GPU Utilization Monitoring

**Prerequisites**:
- SSH/console access to local GPU server
- Minikube running vLLM InferenceService

**Commands**:

```bash
# On local GPU server
# Monitor GPU in real-time
watch -n 1 nvidia-smi

# While monitoring, generate load from another terminal:
for i in {1..20}; do
  curl -s -X POST https://llm.blockchainradar.xyz/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"Explain machine learning"}],"max_tokens":100}' \
    &
done
wait

# Record observations:
# - GPU Utilization %
# - GPU Memory Used / Total
# - GPU Temperature
# - Power Draw
```

**Expected Results** (from Phase 0 benchmarks):
- GPU Utilization: >90%
- Memory Usage: ~10GB / 12GB
- Temperature: 70-80°C

**Deliverable**: GPU utilization report with screenshots

### 1.2 CPU Utilization Monitoring (Embedding Service)

```bash
# On local GPU server
# Get embedding pod
kubectl config use-context minikube
POD=$(kubectl get pods -n kserve -l serving.kserve.io/inferenceservice=embedding-service -o jsonpath='{.items[0].metadata.name}')

# Monitor CPU/memory
kubectl top pod -n kserve $POD --containers

# Generate load
for i in {1..50}; do
  curl -s -X POST https://embed.blockchainradar.xyz/vectorize \
    -H "Content-Type: application/json" \
    -d '{"texts":["text1","text2","text3","text4","text5"],"normalize":true}' \
    &
done
wait

# Record CPU % and memory usage
```

**Expected Results**:
- CPU Utilization: 80-90% under load
- Memory Usage: ~3-4GB
- Response time degradation: <10%

**Deliverable**: CPU utilization report

---

## 🔥 Task 2: Load Testing

### Objective
Validate system can handle 100+ concurrent users and identify breaking points.

### 2.1 Install Load Testing Tools

**Option A: hey (Simple HTTP benchmarking)**

```bash
# Install hey
go install github.com/rakyll/hey@latest

# Verify installation
hey -version
```

**Option B: locust (Complex scenarios)**

```bash
# Install locust
pip install locust

# Create locustfile.py (see section 2.4)
```

### 2.2 vLLM Load Test

```bash
# Simple load test with hey
hey -n 1000 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-0.6B","messages":[{"role":"user","content":"Hello"}],"max_tokens":20}' \
  https://llm.blockchainradar.xyz/v1/chat/completions

# Analyze results:
# - Total requests
# - Success rate (should be 100%)
# - Requests/sec
# - Latency distribution (P50, P95, P99)
# - Errors (should be 0)
```

**Success Criteria**:
- ✅ 100% success rate
- ✅ P95 latency <500ms
- ✅ Throughput >50 req/sec
- ✅ No timeouts or connection errors

### 2.3 Embedding Load Test

```bash
# Batch embedding load test
hey -n 2000 -c 100 -m POST \
  -H "Content-Type: application/json" \
  -d '{"texts":["doc1","doc2","doc3"],"normalize":true}' \
  https://embed.blockchainradar.xyz/vectorize

# Analyze results
```

**Success Criteria**:
- ✅ 100% success rate
- ✅ P95 latency <300ms
- ✅ Throughput >100 req/sec

### 2.4 End-to-End RAG Load Test (Advanced)

**Create locustfile.py**:

```python
from locust import HttpUser, task, between
import random

class RAGUser(HttpUser):
    wait_time = between(1, 3)  # 1-3 seconds between requests

    @task(3)  # Weight: 3x more likely than upload
    def query(self):
        queries = [
            "What is machine learning?",
            "Explain neural networks",
            "How does RAG work?",
            "What are transformers?",
        ]
        self.client.post("/api/v1/query", json={
            "query": random.choice(queries)
        })

    @task(1)
    def health_check(self):
        self.client.get("/ready")
```

**Run load test**:

```bash
# Port-forward GKE service
kubectl port-forward -n app svc/intellirag-app 8000:8000 &

# Run locust
locust -f locustfile.py --host=http://localhost:8000 --users 100 --spawn-rate 10 --run-time 5m

# Access web UI at http://localhost:8089
```

**Success Criteria**:
- ✅ Handle 100 concurrent users
- ✅ P95 end-to-end <5s
- ✅ Failure rate <1%

**Deliverable**: Load test reports with charts

---

## 📈 Task 3: Observability Integration

### Objective
Validate Prometheus metrics collection and create Grafana dashboards for model serving metrics.

### 3.1 Verify Prometheus Scraping

```bash
# Check if InferenceServices export metrics
kubectl get pods -n kserve

# Port-forward to vLLM pod
POD=$(kubectl get pods -n kserve -l serving.kserve.io/inferenceservice=vllm-qwen -o jsonpath='{.items[0].metadata.name}')
kubectl port-forward -n kserve $POD 8000:8000 &

# Check metrics endpoint
curl http://localhost:8000/metrics | head -50

# Look for vLLM-specific metrics:
# - vllm:num_requests_running
# - vllm:num_requests_waiting
# - vllm:gpu_cache_usage_perc
# - vllm:time_to_first_token_seconds
```

### 3.2 Configure Prometheus ServiceMonitor

**Create**: `kubernetes/kserve/servicemonitor-vllm.yaml`

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: vllm-metrics
  namespace: kserve
spec:
  selector:
    matchLabels:
      serving.kserve.io/inferenceservice: vllm-qwen
  endpoints:
    - port: http
      path: /metrics
      interval: 15s
```

Apply on GKE (if Prometheus Operator installed):

```bash
kubectl apply -f kubernetes/kserve/servicemonitor-vllm.yaml
```

### 3.3 Create Grafana Dashboard

**File**: `observability/grafana/provisioning/dashboards/json/model-serving.json`

**Panels to include**:
1. vLLM Request Rate (requests/sec)
2. vLLM P95 Latency
3. vLLM Queue Depth
4. GPU Utilization %
5. GPU Memory Usage
6. Embedding Request Rate
7. Embedding P95 Latency
8. Embedding CPU Usage

**Example panel query** (vLLM request rate):
```promql
rate(http_requests_total{service="vllm-qwen"}[5m])
```

**Import to Grafana**:
```bash
# Port-forward to Grafana
kubectl port-forward -n observability svc/grafana 3000:80

# Access: http://localhost:3000
# Login: admin / <password>
# Import dashboard JSON
```

**Deliverable**: Grafana dashboard with 8+ panels

### 3.4 Set Up Alerts

**Create**: `observability/grafana/alerts/model-serving-alerts.yaml`

```yaml
groups:
  - name: model_serving
    interval: 30s
    rules:
      - alert: HighVLLMLatency
        expr: histogram_quantile(0.95, rate(vllm_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        annotations:
          summary: "vLLM P95 latency >1s"

      - alert: VLLMServiceDown
        expr: up{job="vllm-qwen"} == 0
        for: 2m
        annotations:
          summary: "vLLM service is down"

      - alert: GPUMemoryHigh
        expr: nvidia_gpu_memory_used_bytes / nvidia_gpu_memory_total_bytes > 0.95
        for: 10m
        annotations:
          summary: "GPU memory >95% for 10 minutes"
```

**Deliverable**: Alerting rules configured

---

## 🚀 Task 4: Performance Optimization

### Objective
Based on profiling and load testing results, optimize configurations for better performance.

### 4.1 vLLM Optimization

**If GPU utilization <90%**, increase parallelism:

```yaml
# Update kubernetes/kserve/vllm-qwen-inference.yaml
args:
  - --gpu-memory-utilization=0.95  # Increase from 0.5
  - --max-model-len=4096  # Increase if memory allows
  - --max-num-seqs=256  # Increase batch size
```

**If latency >100ms**, enable optimizations:

```yaml
args:
  - --enable-prefix-caching  # Already enabled
  - --enable-chunked-prefill  # Add this
  - --kv-cache-dtype=fp8  # Use FP8 for KV cache
```

### 4.2 Embedding Optimization

**If CPU <80%**, increase batch size:

```yaml
# Update kubernetes/kserve/embedding-inference.yaml
env:
  - name: MAX_BATCH_SIZE
    value: "64"  # Increase from 32
```

**If memory allows**, load on GPU:

```yaml
env:
  - name: DEVICE
    value: "cuda"  # Change from cpu (requires GPU available)
resources:
  limits:
    nvidia.com/gpu: "1"
```

### 4.3 CloudFlare Tunnel Optimization

**Increase connection pool**:

```yaml
# ~/.cloudflared/config.yml
ingress:
  - hostname: llm.blockchainradar.xyz
    service: http://localhost:8000
    originRequest:
      connectTimeout: 60s
      keepAliveConnections: 100  # Add this
      keepAliveTimeout: 90s      # Add this
```

**Deliverable**: Optimized configurations with before/after metrics

---

## ✅ Deliverables Checklist

### Performance Profiling
- [ ] GPU utilization report (screenshots + metrics)
- [ ] CPU utilization report for embedding service
- [ ] Memory usage analysis
- [ ] Bottleneck identification document

### Load Testing
- [ ] `hey` or `locust` installed
- [ ] vLLM load test report (1000 requests, 50 concurrent)
- [ ] Embedding load test report (2000 requests, 100 concurrent)
- [ ] End-to-end RAG load test report (100 users, 5 minutes)
- [ ] Breaking point analysis (max concurrent users)

### Observability
- [ ] Prometheus scraping verified for both services
- [ ] ServiceMonitor resources created
- [ ] Grafana dashboard created (8+ panels)
- [ ] Alerting rules configured
- [ ] Dashboard accessible and functional

### Optimization
- [ ] vLLM configuration optimized based on profiling
- [ ] Embedding service optimized
- [ ] CloudFlare Tunnel optimized
- [ ] Before/after performance comparison

**Total**: 18 deliverables

---

## 📊 Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| GPU Utilization | >90% | nvidia-smi under load |
| CPU Utilization (embedding) | 80-90% | kubectl top pod |
| vLLM Load Test Success Rate | 100% | hey report |
| Embedding Load Test Success Rate | 100% | hey report |
| End-to-End 100 Users | <1% failure | locust report |
| Prometheus Metrics Visible | Yes | Grafana datasource |
| Grafana Dashboard Panels | 8+ | Visual confirmation |
| Alert Rules Active | 3+ | Prometheus alerts UI |

---

## 🔧 Tools Required

### Install Before Starting

```bash
# Load testing
go install github.com/rakyll/hey@latest
pip install locust

# Monitoring (if not already installed)
# Prometheus, Grafana already running from Phase 1

# Verification
hey -version
locust -version
```

---

## 📝 Documentation Template

After completing tasks, document results in:

**File**: `docs/summaries/phase-3-monitoring-results.md`

**Sections**:
1. Performance Profiling Results
   - GPU utilization screenshots
   - CPU utilization graphs
   - Bottlenecks identified

2. Load Testing Results
   - vLLM load test report
   - Embedding load test report
   - End-to-end test results
   - Charts and graphs

3. Observability Setup
   - Prometheus configuration
   - Grafana dashboard screenshots
   - Alert rules

4. Optimization Outcomes
   - Before/after comparisons
   - Configuration changes
   - Performance improvements

5. Recommendations
   - Further optimization opportunities
   - Scaling strategies
   - Cost optimization

---

## 🚀 Quick Start Guide

### Day 1: Profiling (2 hours)

```bash
# 1. GPU profiling (30 min)
# Run nvidia-smi + load test + screenshots

# 2. CPU profiling (30 min)
# Run kubectl top + load test + record

# 3. Analysis (1 hour)
# Document findings, identify bottlenecks
```

### Day 2: Load Testing (2 hours)

```bash
# 1. Install tools (15 min)
go install github.com/rakyll/hey@latest

# 2. Run load tests (1 hour)
# vLLM, embedding, end-to-end

# 3. Analyze results (45 min)
# Generate reports, identify issues
```

### Day 3: Observability (2 hours)

```bash
# 1. Verify Prometheus (30 min)
# Check metrics endpoints

# 2. Create Grafana dashboard (1 hour)
# 8+ panels with queries

# 3. Configure alerts (30 min)
# 3+ alerting rules
```

### Day 4: Optimization (Optional, 1 hour)

```bash
# Based on findings:
# - Update vLLM config
# - Update embedding config
# - Update CloudFlare config
# - Measure improvements
```

**Total Time**: 3-5 hours spread across 3-4 days

---

## 🔜 After Completion

Once these monitoring tasks are complete:
1. Update Phase 3 status to 100%
2. Mark Phase 3 as ready for production
3. Create comprehensive monitoring runbook
4. Proceed to Phase 4 (if applicable) or production launch

---

**Status**: Pending
**Prerequisites**: Phase 2 Core Complete ✅
**Estimated Effort**: 6-8 hours total
**Last Updated**: 2025-11-20
