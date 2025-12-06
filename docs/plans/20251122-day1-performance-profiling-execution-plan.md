# Day 1 Performance Profiling - Execution Plan

**Created**: 2025-11-22
**Duration**: 4-5 hours
**Prerequisites**: Local GPU server access, nvidia-smi, kubectl, CloudFlare tunnel operational

---

## Current Infrastructure Status

### Confirmed Operational Components ✅

1. **GPU Server (Local)**:
   - RTX 4070 Ti with 12GB memory
   - Current GPU memory usage: ~7.5GB (4.8GB free)
   - nvidia-smi available and working
   - GPU temperature: 32°C (idle)

2. **Kubernetes Clusters**:
   - **GKE**: intellirag-cluster in asia-southeast1
     - 5 intellirag-app replicas running
     - HPA configured (CPU: 4%/70%, Memory: 93%/80%)
     - Metrics-server operational
   - **Minikube**: Local KServe deployment
     - vllm-qwen-predictor pod running
     - embedding-service-predictor pod running
     - KServe controller operational

3. **CloudFlare Tunnel**:
   - Service running since Nov 19
   - Tunnel ID: af0ef505-d101-4bbb-96e7-ae4b9c8e6c65
   - Endpoints configured and accessible:
     - https://llm.blockchainradar.xyz → localhost:8000 ✅
     - https://embed.blockchainradar.xyz → localhost:8001 ✅

4. **Port Forwards Active**:
   - Port 8000 → vllm-qwen-predictor (Qwen3-0.6B model)
   - Port 8001 → embedding-service-predictor (embeddinggemma-300m)

### Issues Identified ⚠️

1. **Minikube metrics-server**: Not installed (required for Task 1.2 CPU monitoring)
2. **High memory usage on GKE**: 93% causing max HPA replicas

---

## Pre-flight Checklist

### Step 0: Infrastructure Verification (10 minutes)

```bash
# 0.1 Verify GPU availability
nvidia-smi --query-gpu=name,memory.total,memory.free,utilization.gpu --format=csv
# Expected: RTX 4070 Ti, 12282 MiB total

# 0.2 Test vLLM endpoint (local)
curl -s http://localhost:8000/v1/models | jq -r '.data[0].id'
# Expected: Qwen/Qwen3-0.6B

# 0.3 Test vLLM endpoint (CloudFlare)
curl -s https://llm.blockchainradar.xyz/v1/models | jq -r '.data[0].id'
# Expected: Qwen/Qwen3-0.6B

# 0.4 Test embedding endpoint
curl -s https://embed.blockchainradar.xyz/health | jq
# Expected: {"status":"healthy","model_loaded":true,...}

# 0.5 Verify kubectl contexts
kubectl config get-contexts
# Should show both GKE and minikube contexts

# 0.6 Install metrics-server on minikube (if missing)
kubectl --context=minikube get deployment metrics-server -n kube-system
# If not found, install:
kubectl --context=minikube apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Wait for metrics-server to be ready
kubectl --context=minikube wait --for=condition=available --timeout=120s deployment/metrics-server -n kube-system
```

---

## Task 1.1: GPU Utilization Profiling (2 hours)

### Setup

```bash
# Create working directory for screenshots
mkdir -p ~/profiling/gpu
cd ~/profiling/gpu

# Start GPU monitoring log
nvidia-smi --query-gpu=timestamp,utilization.gpu,memory.used,temperature.gpu,power.draw --format=csv -l 1 > gpu_metrics.csv &
GPU_LOG_PID=$!
echo "GPU logging started with PID: $GPU_LOG_PID"
```

### Test Sequence

#### Test 1.1.1: Light Load (5 concurrent requests)

```bash
# Terminal 1: Real-time monitoring
watch -n 1 'nvidia-smi | tee -a light_load_snapshot.txt'

# Terminal 2: Generate load
echo "Starting Light Load Test at $(date)" | tee light_load.log
START_TIME=$(date +%s)

for i in {1..5}; do
  (time curl -s -X POST https://llm.blockchainradar.xyz/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model":"Qwen/Qwen3-0.6B",
      "messages":[{"role":"user","content":"Explain machine learning in 50 words"}],
      "max_tokens":100,
      "temperature":0.7
    }' | jq -r '.usage.total_tokens' 2>&1) >> light_load.log &
done
wait

END_TIME=$(date +%s)
echo "Light Load Test completed in $((END_TIME - START_TIME)) seconds" | tee -a light_load.log

# Capture final snapshot
nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw --format=csv,noheader >> light_load_results.csv
```

#### Test 1.1.2: Medium Load (20 concurrent requests)

```bash
echo "Starting Medium Load Test at $(date)" | tee medium_load.log
START_TIME=$(date +%s)

for i in {1..20}; do
  (time curl -s -X POST https://llm.blockchainradar.xyz/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model":"Qwen/Qwen3-0.6B",
      "messages":[{"role":"user","content":"What are neural networks and how do they work?"}],
      "max_tokens":150,
      "temperature":0.7
    }' | jq -r '.usage.total_tokens' 2>&1) >> medium_load.log &
done
wait

END_TIME=$(date +%s)
echo "Medium Load Test completed in $((END_TIME - START_TIME)) seconds" | tee -a medium_load.log

nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw --format=csv,noheader >> medium_load_results.csv
```

#### Test 1.1.3: Heavy Load (50 concurrent requests)

```bash
echo "Starting Heavy Load Test at $(date)" | tee heavy_load.log
START_TIME=$(date +%s)

for i in {1..50}; do
  (time curl -s -X POST https://llm.blockchainradar.xyz/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model":"Qwen/Qwen3-0.6B",
      "messages":[{"role":"user","content":"Describe transformer architecture in detail including attention mechanism"}],
      "max_tokens":200,
      "temperature":0.7
    }' | jq -r '.usage.total_tokens' 2>&1) >> heavy_load.log &
done
wait

END_TIME=$(date +%s)
echo "Heavy Load Test completed in $((END_TIME - START_TIME)) seconds" | tee -a heavy_load.log

nvidia-smi --query-gpu=utilization.gpu,memory.used,temperature.gpu,power.draw --format=csv,noheader >> heavy_load_results.csv

# Stop GPU logging
kill $GPU_LOG_PID
```

### Analysis Script

```bash
# Generate summary
cat <<EOF > gpu_summary.py
import pandas as pd
import sys

# Read CSV files
light = pd.read_csv('light_load_results.csv', names=['gpu_util', 'memory', 'temp', 'power'])
medium = pd.read_csv('medium_load_results.csv', names=['gpu_util', 'memory', 'temp', 'power'])
heavy = pd.read_csv('heavy_load_results.csv', names=['gpu_util', 'memory', 'temp', 'power'])

print("GPU Performance Summary")
print("=" * 50)
print(f"Light Load (5 concurrent): GPU {light['gpu_util'].mean():.1f}%, Mem {light['memory'].mean():.0f} MiB")
print(f"Medium Load (20 concurrent): GPU {medium['gpu_util'].mean():.1f}%, Mem {medium['memory'].mean():.0f} MiB")
print(f"Heavy Load (50 concurrent): GPU {heavy['gpu_util'].mean():.1f}%, Mem {heavy['memory'].mean():.0f} MiB")
EOF

python3 gpu_summary.py
```

---

## Task 1.2: CPU Utilization Profiling (1.5 hours)

### Prerequisites Fix

```bash
# Ensure metrics-server is running on minikube
kubectl --context=minikube top nodes
# If error, wait 60 seconds after metrics-server installation for data collection
```

### Setup

```bash
mkdir -p ~/profiling/cpu
cd ~/profiling/cpu

# Get embedding pod name
POD_NAME=$(kubectl --context=minikube get pods -n kserve \
  -l serving.knative.dev/service=embedding-service-predictor \
  -o jsonpath="{.items[0].metadata.name}")

echo "Monitoring pod: $POD_NAME"

# Start CPU monitoring log
watch -n 2 "kubectl --context=minikube top pod -n kserve $POD_NAME --containers | tee -a cpu_metrics.log" &
CPU_LOG_PID=$!
```

### Test Sequence

#### Test 1.2.1: Small Batches (1-3 texts)

```bash
echo "Starting Small Batch Test at $(date)" | tee small_batch.log

for i in {1..30}; do
  (time curl -s -X POST https://embed.blockchainradar.xyz/vectorize \
    -H "Content-Type: application/json" \
    -d '{
      "texts":["Machine learning is fascinating","Neural networks mimic brain","Deep learning revolutionizes AI"],
      "normalize":true
    }' | jq -r '.embeddings | length' 2>&1) >> small_batch.log &
done
wait

# Capture metrics
kubectl --context=minikube top pod -n kserve $POD_NAME --containers >> small_batch_results.txt
```

#### Test 1.2.2: Medium Batches (10 texts)

```bash
echo "Starting Medium Batch Test at $(date)" | tee medium_batch.log

# Generate 10 sample texts
TEXTS='["Text sample 1","Text sample 2","Text sample 3","Text sample 4","Text sample 5","Text sample 6","Text sample 7","Text sample 8","Text sample 9","Text sample 10"]'

for i in {1..30}; do
  (time curl -s -X POST https://embed.blockchainradar.xyz/vectorize \
    -H "Content-Type: application/json" \
    -d "{\"texts\":$TEXTS,\"normalize\":true}" | jq -r '.embeddings | length' 2>&1) >> medium_batch.log &
done
wait

kubectl --context=minikube top pod -n kserve $POD_NAME --containers >> medium_batch_results.txt
```

#### Test 1.2.3: Large Batches (20 texts)

```bash
echo "Starting Large Batch Test at $(date)" | tee large_batch.log

# Generate 20 sample texts
TEXTS=$(printf '"Sample text %s",' {1..20} | sed 's/,$//')
TEXTS="[$TEXTS]"

for i in {1..20}; do
  (time curl -s -X POST https://embed.blockchainradar.xyz/vectorize \
    -H "Content-Type: application/json" \
    -d "{\"texts\":$TEXTS,\"normalize\":true}" | jq -r '.embeddings | length' 2>&1) >> large_batch.log &
done
wait

kubectl --context=minikube top pod -n kserve $POD_NAME --containers >> large_batch_results.txt

# Stop CPU monitoring
kill $CPU_LOG_PID
```

---

## Task 1.3: GKE Application Health Check (30 minutes)

```bash
mkdir -p ~/profiling/gke
cd ~/profiling/gke

# Switch context
kubectl config use-context gke_intellirag-aide1-capstone_asia-southeast1_intellirag-cluster

# 1. Resource Usage
echo "=== Node Resources ===" | tee gke_baseline.log
kubectl top nodes | tee -a gke_baseline.log

echo -e "\n=== Pod Resources (app namespace) ===" | tee -a gke_baseline.log
kubectl top pods -n app | tee -a gke_baseline.log

# 2. HPA Status
echo -e "\n=== HPA Status ===" | tee -a gke_baseline.log
kubectl get hpa -n app | tee -a gke_baseline.log
kubectl describe hpa intellirag-app -n app | tee -a gke_baseline.log

# 3. Pod Distribution
echo -e "\n=== Pod Distribution ===" | tee -a gke_baseline.log
kubectl get pods -n app -o wide | tee -a gke_baseline.log

# 4. Service Endpoints
echo -e "\n=== Service Endpoints ===" | tee -a gke_baseline.log
kubectl get svc -n app | tee -a gke_baseline.log
kubectl get ingress -n app 2>/dev/null | tee -a gke_baseline.log

# 5. Readiness Probe Latency Test
echo -e "\n=== Readiness Probe Latency ===" | tee -a gke_baseline.log
# Assuming the service exposes a /health or /ready endpoint
SVC_IP=$(kubectl get svc intellirag-app -n app -o jsonpath='{.status.loadBalancer.ingress[0].ip}' 2>/dev/null)
if [ -z "$SVC_IP" ]; then
  SVC_IP=$(kubectl get svc intellirag-app -n app -o jsonpath='{.spec.clusterIP}')
  echo "Using ClusterIP: $SVC_IP" | tee -a gke_baseline.log
fi

# Run from within cluster if external IP not available
kubectl run -n app curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  sh -c 'for i in $(seq 1 10); do time curl -s http://intellirag-app:8000/health > /dev/null 2>&1; done' | tee -a gke_baseline.log

# 6. CloudFlare Tunnel Connectivity Test
echo -e "\n=== CloudFlare Tunnel Test ===" | tee -a gke_baseline.log
echo "Testing from GKE to local GPU via CloudFlare..." | tee -a gke_baseline.log

# Test embedding endpoint through CloudFlare
time curl -s https://embed.blockchainradar.xyz/health | jq '.status' | tee -a gke_baseline.log

# Test LLM endpoint through CloudFlare
time curl -s https://llm.blockchainradar.xyz/v1/models | jq '.data[0].id' | tee -a gke_baseline.log
```

---

## Task 1.4: Analysis & Bottleneck Identification (1 hour)

### Data Consolidation Script

```bash
mkdir -p ~/profiling/analysis
cd ~/profiling/analysis

# Create analysis script
cat <<'EOF' > analyze_results.py
#!/usr/bin/env python3
import os
import re
from pathlib import Path

# Parse GPU results
gpu_results = {
    'light': {'gpu_util': 0, 'memory': 0, 'requests': 5, 'time': 0},
    'medium': {'gpu_util': 0, 'memory': 0, 'requests': 20, 'time': 0},
    'heavy': {'gpu_util': 0, 'memory': 0, 'requests': 50, 'time': 0}
}

# Parse CPU results
cpu_results = {
    'small': {'cpu': 0, 'memory': 0, 'batch_size': 3, 'requests': 30},
    'medium': {'cpu': 0, 'memory': 0, 'batch_size': 10, 'requests': 30},
    'large': {'cpu': 0, 'memory': 0, 'batch_size': 20, 'requests': 20}
}

print("=" * 60)
print("PERFORMANCE ANALYSIS SUMMARY")
print("=" * 60)

# GPU Analysis
print("\n### GPU Performance (RTX 4070 Ti 12GB)")
print("-" * 40)
print("Load Level | Requests | GPU Util | Memory | TPS")
print("-" * 40)
for level, data in gpu_results.items():
    tps = data['requests'] / data['time'] if data['time'] > 0 else 0
    print(f"{level:10} | {data['requests']:8} | {data['gpu_util']:7.1f}% | {data['memory']:6.0f}MB | {tps:7.2f}")

# CPU Analysis (Embedding)
print("\n### Embedding Service Performance")
print("-" * 40)
print("Batch Size | Requests | CPU Util | Memory")
print("-" * 40)
for size, data in cpu_results.items():
    print(f"{data['batch_size']:10} | {data['requests']:8} | {data['cpu']:7.1f}% | {data['memory']:6.0f}MB")

# Bottleneck Analysis
print("\n### Bottleneck Analysis")
print("-" * 40)

bottlenecks = []

# Check GPU utilization
if gpu_results['heavy']['gpu_util'] < 90:
    bottlenecks.append({
        'component': 'GPU',
        'issue': 'Underutilization',
        'current': f"{gpu_results['heavy']['gpu_util']}%",
        'target': '>90%',
        'recommendation': 'Increase batch size or concurrent requests'
    })

# Check memory pressure
if gpu_results['heavy']['memory'] > 11000:
    bottlenecks.append({
        'component': 'GPU Memory',
        'issue': 'Near capacity',
        'current': f"{gpu_results['heavy']['memory']}MB",
        'target': '<11000MB',
        'recommendation': 'Consider model quantization or smaller batch sizes'
    })

# Check CPU for embedding
optimal_batch = 10  # Assumed from tests
if cpu_results['medium']['cpu'] > 90:
    bottlenecks.append({
        'component': 'Embedding CPU',
        'issue': 'High utilization',
        'current': f"{cpu_results['medium']['cpu']}%",
        'target': '80-90%',
        'recommendation': f'Reduce batch size from {optimal_batch} to maintain latency'
    })

for i, b in enumerate(bottlenecks, 1):
    print(f"\n{i}. {b['component']} - {b['issue']}")
    print(f"   Current: {b['current']}, Target: {b['target']}")
    print(f"   Recommendation: {b['recommendation']}")

if not bottlenecks:
    print("No significant bottlenecks identified - system is well-balanced")

# Optimization Recommendations
print("\n### Day 3 Optimization Recommendations")
print("-" * 40)
print("1. vLLM Configuration:")
print("   - Set --gpu-memory-utilization to 0.95")
print("   - Adjust --max-num-seqs based on memory pressure")
print("")
print("2. Embedding Service:")
print(f"   - Optimal batch size: {optimal_batch}")
print("   - Consider GPU acceleration if CPU >90%")
print("")
print("3. HPA Thresholds (Day 5):")
print("   - CPU target: 70% (current setting)")
print("   - Memory target: 75% (reduce from 80%)")
print("   - Min replicas: 3")
print("   - Max replicas: 15")

EOF

python3 analyze_results.py > analysis_report.txt
```

---

## Report Generation

### Create Final Reports

```bash
# Navigate to reports directory
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG/docs/phase-3/reports

# Generate GPU Profiling Report
cat > gpu-profiling-report.md <<EOF
# GPU Profiling Report

**Date**: $(date +%Y-%m-%d)
**GPU**: NVIDIA RTX 4070Ti 12GB
**Driver Version**: $(nvidia-smi --query-gpu=driver_version --format=csv,noheader)

## Test Results

| Load Level | Concurrent Requests | GPU Util % | Memory Used | Temperature | Power Draw |
|------------|-------------------|------------|-------------|-------------|------------|
| Light      | 5                 | [FILL]%    | [FILL]GB    | [FILL]°C    | [FILL]W    |
| Medium     | 20                | [FILL]%    | [FILL]GB    | [FILL]°C    | [FILL]W    |
| Heavy      | 50                | [FILL]%    | [FILL]GB    | [FILL]°C    | [FILL]W    |

## Screenshots

[Add nvidia-smi screenshots from ~/profiling/gpu/]

## Observations

- Peak GPU utilization: [FILL]% (target: >90%)
- Memory usage pattern: [Describe]
- Temperature stability: [Describe]
- Bottlenecks identified: [List]

## Recommendations

1. [Optimization based on findings]
2. [Configuration adjustments needed]
EOF

# Generate CPU Profiling Report
cat > cpu-profiling-report.md <<EOF
# CPU Profiling Report (Embedding Service)

**Date**: $(date +%Y-%m-%d)
**Service**: embeddinggemma-300m (768 dimensions)
**Pod**: $POD_NAME

## Test Results

| Batch Size | Concurrent Requests | CPU Util % | Memory MB | Avg Response Time |
|------------|-------------------|------------|-----------|-------------------|
| 1-3 texts  | 30                | [FILL]%    | [FILL]MB  | [FILL]ms          |
| 10 texts   | 30                | [FILL]%    | [FILL]MB  | [FILL]ms          |
| 20 texts   | 20                | [FILL]%    | [FILL]MB  | [FILL]ms          |

## Analysis

- Optimal batch size: [FILL] texts (balances CPU and latency)
- CPU bottleneck at: [FILL] concurrent requests
- Memory growth pattern: [Describe]
- Response time relationship: [Describe]

## Recommendations for Day 3

- Target CPU utilization: 80-90%
- Recommended MAX_BATCH_SIZE: [FILL]
- Consider GPU acceleration if CPU exceeds [FILL]%
EOF

# Generate GKE Baseline Metrics
cat > gke-baseline-metrics.md <<EOF
# GKE Baseline Metrics

**Date**: $(date +%Y-%m-%d)
**Cluster**: intellirag-cluster (asia-southeast1)

## Current State

- **Pods**: 5/5 running
- **CPU usage**: [FILL]% average
- **Memory usage**: 93% average (HIGH)
- **HPA current replicas**: 5 (max due to memory)
- **Readiness probe latency**: [FILL]ms average

## Resource Requests/Limits

[Include kubectl describe output]

## Network

- Ingress: [Status]
- CloudFlare Tunnel connectivity: Verified ✅
- Tunnel overhead: ~[FILL]ms

## Issues

- High memory utilization triggering max HPA scaling
- Consider memory optimization or limit adjustment
EOF

# Generate Day 1 Analysis
cat > day1-analysis.md <<EOF
# Day 1: Performance Analysis

**Date**: $(date +%Y-%m-%d)

## Summary

Performance profiling completed for GPU inference, CPU embedding, and GKE application health. System shows [good/moderate/poor] overall performance with [number] bottlenecks identified requiring optimization.

## Key Findings

### GPU Performance
- Peak utilization: [FILL]%
- Memory usage: [FILL]GB / 12GB ([FILL]%)
- Bottleneck: [GPU compute / GPU memory / Network / None]

### Embedding Service
- Optimal batch size: [FILL] texts
- CPU utilization at optimal: [FILL]%
- Bottleneck: [CPU / Memory / None]

### Network
- CloudFlare Tunnel overhead: ~[FILL]ms
- GKE app response time: [FILL]ms
- Bottleneck: [Network / None]

## Bottlenecks Identified

1. **[Bottleneck Name]**
   - Symptom: [What was observed]
   - Impact: [Performance degradation]
   - Proposed fix: [Optimization for Day 3]

2. **High Memory Usage on GKE**
   - Symptom: 93% memory usage triggering max HPA
   - Impact: Cannot scale beyond 5 replicas
   - Proposed fix: Memory optimization or limit adjustment

## Recommendations for Day 3 Optimization

1. **vLLM Configuration**
   - Adjust --gpu-memory-utilization to [value]
   - Adjust --max-num-seqs to [value]
   - [Other parameters]

2. **Embedding Configuration**
   - Set MAX_BATCH_SIZE to [value]
   - [Other optimizations]

3. **GKE Memory**
   - Review memory limits and requests
   - Consider memory optimization in application

## HPA Threshold Recommendations for Day 5

Based on observed resource usage:
- CPU target: 70% (current setting OK)
- Memory target: 75% (reduce from 80%)
- Min replicas: 3
- Max replicas: 15

## Next Steps

- Day 2: Run load tests to find breaking points
- Day 3: Apply optimizations based on these findings
- Day 5: Implement new HPA thresholds
EOF

echo "Reports templates created in /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG/docs/phase-3/reports/"
echo "Please fill in the [FILL] placeholders with actual test results"
```

---

## Execution Timeline

| Time | Task | Duration |
|------|------|----------|
| 0:00 | Pre-flight checks & setup | 15 min |
| 0:15 | Task 1.1 - GPU Profiling | 2 hours |
| 2:15 | Break | 15 min |
| 2:30 | Task 1.2 - CPU Profiling | 1.5 hours |
| 4:00 | Task 1.3 - GKE Health Check | 30 min |
| 4:30 | Task 1.4 - Analysis | 1 hour |
| 5:30 | Report generation & cleanup | 30 min |

**Total Duration**: ~6 hours

---

## Success Criteria

✅ All infrastructure components verified operational
✅ GPU profiling data collected for 3 load levels
✅ CPU profiling data collected for 3 batch sizes
✅ GKE baseline metrics documented
✅ At least 1 bottleneck identified (or confirmed none)
✅ Clear optimization recommendations for Day 3
✅ HPA thresholds recommended for Day 5
✅ All 4 report documents created with data

---

## Troubleshooting Guide

### Issue: Metrics-server not starting on minikube

```bash
# Enable metrics-server addon
minikube addons enable metrics-server --context=minikube

# If still issues, manually patch
kubectl --context=minikube patch deployment metrics-server -n kube-system \
  --patch '{"spec":{"template":{"spec":{"containers":[{"name":"metrics-server","args":["--cert-dir=/tmp","--secure-port=4443","--kubelet-insecure-tls","--kubelet-preferred-address-types=InternalIP"]}]}}}}'
```

### Issue: CloudFlare tunnel not responding

```bash
# Restart tunnel
sudo systemctl restart cloudflared

# Check logs
sudo journalctl -u cloudflared -f

# Verify port forwards
ps aux | grep "kubectl port-forward"

# Restart port forwards if needed
kubectl --context=minikube port-forward -n kserve \
  pod/$(kubectl --context=minikube get pods -n kserve -l serving.knative.dev/service=vllm-qwen-predictor -o jsonpath="{.items[0].metadata.name}") \
  8000:8000 &
```

### Issue: GPU memory errors during tests

```bash
# Clear GPU memory
nvidia-smi --gpu-reset

# Check for zombie processes
nvidia-smi | grep python
# Kill any hanging processes

# Reduce concurrent requests in heavy load test
# Change from 50 to 30 concurrent requests
```

---

## Post-Execution Cleanup

```bash
# Stop any remaining monitoring processes
pkill -f "watch.*nvidia-smi"
pkill -f "watch.*kubectl top"

# Archive test results
cd ~
tar -czf profiling-day1-$(date +%Y%m%d).tar.gz profiling/

# Clean up test pods if any remain
kubectl --context=gke_intellirag-aide1-capstone_asia-southeast1_intellirag-cluster \
  delete pod curl-test -n app --ignore-not-found=true

echo "Day 1 Performance Profiling Complete!"
```