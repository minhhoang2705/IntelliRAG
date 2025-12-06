# Day 1: Performance Profiling

**Duration**: 4-5 hours
**Prerequisites**: Local GPU server access, nvidia-smi, kubectl
**Output**: GPU/CPU profiling reports, bottleneck analysis

---

## 🎯 Objectives

1. Establish baseline GPU utilization metrics under various load patterns
2. Profile CPU usage for embedding service
3. Document current performance characteristics
4. Identify resource bottlenecks

---

## 📋 Tasks Overview

| Task | Duration | Output |
|------|----------|--------|
| 1.1 GPU Utilization Profiling | 2 hours | GPU profiling report with screenshots |
| 1.2 CPU Utilization Profiling | 1.5 hours | CPU profiling report |
| 1.3 GKE Application Health | 30 min | GKE baseline metrics |
| 1.4 Analysis & Bottlenecks | 1 hour | Day 1 analysis document |

---

## Task 1.1: GPU Utilization Profiling (2 hours)

### Objective
Measure GPU utilization, memory usage, and temperature under light, medium, and heavy load.

### Setup

```bash
# SSH to local GPU server
ssh user@gpu-server

# Verify GPU is accessible
nvidia-smi

# Expected output: RTX 4070Ti with 12GB memory
```

### Test 1: Light Load (5 concurrent requests)

```bash
# Terminal 1: Start real-time monitoring
watch -n 1 nvidia-smi

# Terminal 2: Generate light load
for i in {1..5}; do
  curl -s -X POST https://llm.blockchainradar.xyz/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model":"Qwen/Qwen3-0.6B",
      "messages":[{"role":"user","content":"Explain machine learning in 50 words"}],
      "max_tokens":100
    }' &
done
wait

# Record observations:
# - GPU Utilization %: ____
# - GPU Memory Used: ____GB / 12GB
# - GPU Temperature: ____°C
# - Power Draw: ____W
```

### Test 2: Medium Load (20 concurrent requests)

```bash
for i in {1..20}; do
  curl -s -X POST https://llm.blockchainradar.xyz/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model":"Qwen/Qwen3-0.6B",
      "messages":[{"role":"user","content":"What are neural networks?"}],
      "max_tokens":150
    }' &
done
wait

# Record observations (same metrics as Test 1)
```

### Test 3: Heavy Load (50 concurrent requests)

```bash
for i in {1..50}; do
  curl -s -X POST https://llm.blockchainradar.xyz/v1/chat/completions \
    -H "Content-Type: application/json" \
    -d '{
      "model":"Qwen/Qwen3-0.6B",
      "messages":[{"role":"user","content":"Describe transformers architecture"}],
      "max_tokens":200
    }' &
done
wait

# Record observations
```

### Deliverable

Create `docs/phase-3/reports/gpu-profiling-report.md`:

```markdown
# GPU Profiling Report

**Date**: 2025-11-21
**GPU**: NVIDIA RTX 4070Ti 12GB
**Driver Version**: XXX

## Test Results

| Load Level | Concurrent Requests | GPU Util % | Memory Used | Temperature | Power Draw |
|------------|-------------------|------------|-------------|-------------|------------|
| Light      | 5                 | XX%        | X.XGB       | XX°C        | XXXW       |
| Medium     | 20                | XX%        | X.XGB       | XX°C        | XXXW       |
| Heavy      | 50                | XX%        | X.XGB       | XX°C        | XXXW       |

## Screenshots

[Include nvidia-smi screenshots for each load level]

## Observations

- Peak GPU utilization: XX% (target: >90%)
- Memory usage pattern: [describe]
- Temperature stability: [describe]
- Bottlenecks identified: [list]

## Recommendations

1. [Optimization suggestion based on findings]
2. [Configuration adjustment needed]
```

---

## Task 1.2: CPU Utilization Profiling (1.5 hours)

### Objective
Measure CPU and memory usage for embedding service under various batch sizes.

### Setup

```bash
# On local GPU server (minikube context)
kubectl config use-context minikube

# Get embedding pod name
POD=$(kubectl get pods -n kserve -l serving.kserve.io/inferenceservice=embedding-service -o jsonpath='{.items[0].metadata.name}')

echo "Embedding pod: $POD"
```

### Test 1: Small Batches (1-3 texts)

```bash
# Terminal 1: Monitor CPU/memory
watch -n 2 "kubectl top pod -n kserve $POD --containers"

# Terminal 2: Generate small batch load
for i in {1..30}; do
  curl -s -X POST https://embed.blockchainradar.xyz/vectorize \
    -H "Content-Type: application/json" \
    -d '{"texts":["sample text 1","sample text 2","sample text 3"],"normalize":true}' &
done
wait

# Record:
# - CPU utilization %: ____
# - Memory usage: ____MB
# - Average response time: ____ms
```

### Test 2: Medium Batches (5-10 texts)

```bash
for i in {1..30}; do
  curl -s -X POST https://embed.blockchainradar.xyz/vectorize \
    -H "Content-Type: application/json" \
    -d '{"texts":["text1","text2","text3","text4","text5","text6","text7","text8","text9","text10"],"normalize":true}' &
done
wait

# Record same metrics
```

### Test 3: Large Batches (20 texts)

```bash
for i in {1..20}; do
  # Generate 20 texts
  texts=$(printf '"text%s",' {1..20} | sed 's/,$//')
  curl -s -X POST https://embed.blockchainradar.xyz/vectorize \
    -H "Content-Type: application/json" \
    -d "{\"texts\":[$texts],\"normalize\":true}" &
done
wait

# Record metrics
```

### Deliverable

Create `docs/phase-3/reports/cpu-profiling-report.md`:

```markdown
# CPU Profiling Report (Embedding Service)

**Date**: 2025-11-21
**Service**: embeddinggemma-300m (768 dimensions)
**Pod**: embedding-service-xxx

## Test Results

| Batch Size | Concurrent Requests | CPU Util % | Memory MB | Avg Response Time |
|------------|-------------------|------------|-----------|-------------------|
| 1-3 texts  | 30                | XX%        | XXXMB     | XXXms             |
| 5-10 texts | 30                | XX%        | XXXMB     | XXXms             |
| 20 texts   | 20                | XX%        | XXXMB     | XXXms             |

## Analysis

- Optimal batch size: XX texts (balances CPU usage and latency)
- CPU bottleneck at: XX concurrent requests
- Memory growth pattern: [describe]
- Response time degradation: [describe relationship to batch size]

## Recommendations for Day 3

- Target CPU utilization: 80-90%
- Recommended MAX_BATCH_SIZE: XX
- Consider GPU if CPU exceeds XX%
```

---

## Task 1.3: GKE Application Health Check (30 minutes)

### Objective
Establish baseline metrics for FastAPI application on GKE.

```bash
# Switch to GKE context
kubectl config use-context <your-gke-context>

# Check current resource usage
kubectl top pods -n app
kubectl top nodes

# Get current HPA status
kubectl get hpa -n app
kubectl describe hpa intellirag-app-hpa -n app

# Test readiness probe latency (run 10 times)
for i in {1..10}; do
  time curl -s https://api.intellirag.example.com/ready > /dev/null
done
```

### Deliverable

Create `docs/phase-3/reports/gke-baseline-metrics.md`:

```markdown
# GKE Baseline Metrics

**Date**: 2025-11-21
**Cluster**: intellirag-cluster

## Current State

- **Pods**: X/X running
- **CPU usage**: XX% average
- **Memory usage**: XX% average
- **HPA current replicas**: X
- **Readiness probe latency**: XXXms average

## Resource Requests/Limits

[Include kubectl describe output showing resources]

## Network

- Ingress: [Status]
- CloudFlare Tunnel connectivity: [Test result]
```

---

## Task 1.4: Analysis & Bottleneck Identification (1 hour)

### Objective
Synthesize findings from Tasks 1.1-1.3 and identify bottlenecks.

### Analysis Questions

1. **GPU Utilization**: Did we achieve >90% utilization under heavy load?
   - If NO: Why? (batch size too small, queue depth limited, etc.)
   - If YES: Is memory the bottleneck? (>95% memory usage)

2. **CPU Utilization (Embedding)**: What's the optimal batch size?
   - Target: 80-90% CPU utilization
   - Trade-off: Batch size vs latency

3. **Network Latency**: What's the CloudFlare Tunnel overhead?
   - Measure: Direct vLLM call vs through GKE app
   - Acceptable: +10-30ms

4. **Memory Constraints**: Any OOM risks?
   - GPU: Should stay <11GB (out of 12GB)
   - Pods: Check for memory pressure

### Deliverable

Create `docs/phase-3/reports/day1-analysis.md`:

```markdown
# Day 1: Performance Analysis

**Date**: 2025-11-21

## Summary

[3-4 sentence executive summary of findings]

## Key Findings

### GPU Performance
- Peak utilization: XX%
- Memory usage: X.XGB / 12GB (XX%)
- Bottleneck: [GPU compute / GPU memory / Network / None]

### Embedding Service
- Optimal batch size: XX texts
- CPU utilization at optimal: XX%
- Bottleneck: [CPU / Memory / None]

### Network
- CloudFlare Tunnel overhead: ~XXms
- GKE app response time: XXXms
- Bottleneck: [Network / None]

## Bottlenecks Identified

1. **[Bottleneck Name]**
   - Symptom: [What we observed]
   - Impact: [Performance degradation]
   - Proposed fix: [Optimization for Day 3]

2. **[Bottleneck Name]**
   - ...

## Recommendations for Day 3 Optimization

1. **vLLM Configuration**
   - Adjust `--gpu-memory-utilization` to X.XX
   - Adjust `--max-num-seqs` to XXX
   - [Other parameters]

2. **Embedding Configuration**
   - Set `MAX_BATCH_SIZE` to XX
   - [Other optimizations]

3. **CloudFlare Tunnel**
   - [If overhead >50ms, suggest keepAlive tuning]

## HPA Threshold Recommendations for Day 5

Based on observed resource usage:
- CPU target: XX% (current: XX% at medium load)
- Memory target: XX% (current: XX% at medium load)
- Min replicas: 3
- Max replicas: 15

## Next Steps

- Day 2: Run load tests to find breaking points
- Day 3: Apply optimizations based on these findings
```

---

## ✅ Day 1 Completion Checklist

- [ ] GPU profiling report created with 3 load tests
- [ ] CPU profiling report created with 3 batch sizes
- [ ] GKE baseline metrics documented
- [ ] Day 1 analysis document created
- [ ] Bottlenecks identified and documented
- [ ] Optimization recommendations drafted for Day 3
- [ ] HPA thresholds recommended for Day 5

**Success Criteria**:
- GPU utilization data collected for 3 load levels
- Embedding service optimal batch size identified
- At least 1 bottleneck identified (or confirmed none exist)
- Clear optimization plan for Day 3

---

## 🔧 Troubleshooting

### Issue: nvidia-smi not found
```bash
# Verify GPU driver installation
lspci | grep -i nvidia

# Reinstall NVIDIA drivers if needed
sudo apt update
sudo apt install nvidia-driver-545  # Or latest version
sudo reboot
```

### Issue: Cannot reach CloudFlare Tunnel endpoints
```bash
# Check tunnel status
sudo systemctl status cloudflared

# Restart if needed
sudo systemctl restart cloudflared

# Test connectivity
curl https://llm.blockchainradar.xyz/health
```

### Issue: kubectl top pods shows `<unknown>`
```bash
# Check metrics-server
kubectl get deployment metrics-server -n kube-system

# If not running, install:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

---

## 📚 Resources

- [nvidia-smi Documentation](https://developer.nvidia.com/nvidia-system-management-interface)
- [kubectl top Command](https://kubernetes.io/docs/reference/kubectl/generated/kubectl_top/)
- [vLLM Metrics](https://docs.vllm.ai/en/latest/serving/metrics.html)

---

**Next**: [Day 2: Load Testing](./day2-load-testing.md)

**Last Updated**: 2025-11-21
