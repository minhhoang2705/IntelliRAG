# Day 2: Load Testing & Capacity Planning

**Duration**: 5-6 hours
**Prerequisites**: hey and locust installed, Day 1 profiling complete
**Output**: Load test reports, capacity analysis, breaking point identification

---

## 🎯 Objectives

1. Determine maximum concurrent users the system can handle
2. Measure P50/P95/P99 latency distributions under stress
3. Identify breaking points for vLLM, embedding, and end-to-end RAG
4. Create capacity planning recommendations for HPA tuning

---

## 📋 Tasks Overview

| Task | Duration | Output |
|------|----------|--------|
| 2.1 Install Load Testing Tools | 15 min | hey and locust verified |
| 2.2 vLLM Load Testing | 2 hours | vLLM load test report |
| 2.3 Embedding Load Testing | 1.5 hours | Embedding load test report |
| 2.4 End-to-End RAG Testing | 2 hours | E2E load test report |
| 2.5 Capacity Analysis | 30 min | Capacity planning document |

---

## Task 2.1: Install Load Testing Tools (15 minutes)

### Install hey (Simple HTTP benchmarking)

```bash
# Install Go if not already installed
go version || sudo apt install golang-go

# Install hey
go install github.com/rakyll/hey@latest

# Add Go bin to PATH if not already
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
source ~/.bashrc

# Verify installation
hey -version
# Expected: hey version x.x.x
```

### Install locust (Complex scenario testing)

```bash
# Install locust
pip install locust

# Verify installation
locust -version
# Expected: locust x.x.x
```

### Success Criteria
- ✅ `hey -version` returns version number
- ✅ `locust -version` returns version number

---

## Task 2.2: vLLM Load Testing (2 hours)

### Objective
Find vLLM breaking point and measure latency distribution.

### Test 1: Baseline (50 concurrent, 1000 requests)

```bash
hey -n 1000 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{
    "model":"Qwen/Qwen3-0.6B",
    "messages":[{"role":"user","content":"Hello"}],
    "max_tokens":20
  }' \
  https://llm.blockchainradar.xyz/v1/chat/completions

# Save output to file
hey -n 1000 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{
    "model":"Qwen/Qwen3-0.6B",
    "messages":[{"role":"user","content":"Hello"}],
    "max_tokens":20
  }' \
  https://llm.blockchainradar.xyz/v1/chat/completions \
  > /tmp/vllm-test1-baseline.txt

# Analyze results - look for:
# - Success rate (target: 100%)
# - Requests/sec (target: >50)
# - P50/P95/P99 latency
# - Error count (should be 0)
```

**Expected Output Analysis**:
```
Summary:
  Total:        X.XXXX secs
  Slowest:      X.XXXX secs
  Fastest:      X.XXXX secs
  Average:      X.XXXX secs
  Requests/sec: XX.XX

Response time histogram:
  X.XXX [xxx]   |■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■■

Latency distribution:
  10% in X.XXXX secs
  25% in X.XXXX secs
  50% in X.XXXX secs (P50)
  75% in X.XXXX secs
  90% in X.XXXX secs
  95% in X.XXXX secs (P95)
  99% in X.XXXX secs (P99)

Status code distribution:
  [200] XXX responses
```

### Test 2: Stress Test (100 concurrent, 2000 requests)

```bash
hey -n 2000 -c 100 -m POST \
  -H "Content-Type: application/json" \
  -d '{
    "model":"Qwen/Qwen3-0.6B",
    "messages":[{"role":"user","content":"Explain AI in 30 words"}],
    "max_tokens":50
  }' \
  https://llm.blockchainradar.xyz/v1/chat/completions \
  > /tmp/vllm-test2-stress.txt

# Compare with baseline - latency should increase but stay <500ms P95
```

### Test 3: Breaking Point Analysis

```bash
# Test incrementally until failure rate >1%
# Start at 100 concurrent, increase by 50 each test

for concurrent in 100 150 200 250 300; do
  echo "================================"
  echo "Testing with $concurrent concurrent connections..."
  echo "================================"

  hey -n 500 -c $concurrent -m POST \
    -H "Content-Type: application/json" \
    -d '{
      "model":"Qwen/Qwen3-0.6B",
      "messages":[{"role":"user","content":"Test"}],
      "max_tokens":10
    }' \
    https://llm.blockchainradar.xyz/v1/chat/completions \
    > /tmp/vllm-breaking-$concurrent.txt

  # Review results
  cat /tmp/vllm-breaking-$concurrent.txt | grep -E "Success rate|Status code"

  echo "Press Enter to continue to next level (or Ctrl+C to stop)..."
  read
done

# Identify breaking point: Where error rate exceeds 1% or P95 latency >1s
```

### Deliverable

Create `docs/phase-3/reports/vllm-load-test-report.md`:

```markdown
# vLLM Load Test Report

**Date**: 2025-11-21
**Endpoint**: https://llm.blockchainradar.xyz/v1/chat/completions
**Model**: Qwen/Qwen3-0.6B

## Test Results Summary

| Test | Concurrent Users | Total Requests | Success Rate | P50 Latency | P95 Latency | P99 Latency | Throughput (req/s) |
|------|-----------------|----------------|--------------|-------------|-------------|-------------|-------------------|
| Baseline | 50 | 1000 | XXX% | XXms | XXms | XXms | XX.X |
| Stress | 100 | 2000 | XXX% | XXms | XXms | XXms | XX.X |
| Breaking 150 | 150 | 500 | XXX% | XXms | XXms | XXms | XX.X |
| Breaking 200 | 200 | 500 | XXX% | XXms | XXms | XXms | XX.X |
| Breaking 250 | 250 | 500 | XXX% | XXms | XXms | XXms | XX.X |

## Breaking Point Analysis

**Breaking Point Identified**: XXX concurrent users
- Success rate drops below 99% at: XXX concurrent users
- P95 latency exceeds 500ms at: XXX concurrent users
- Error types observed: [list error codes/messages]

## Recommendations

1. **Safe Operating Range**: 0-XXX concurrent users
2. **Maximum Capacity**: XXX concurrent users (before degradation)
3. **HPA Max Replicas**: Calculate based on XXX users per pod

## Detailed Metrics

[Paste full hey output for each test]
```

---

## Task 2.3: Embedding Service Load Testing (1.5 hours)

### Objective
Test embedding service throughput and find breaking point.

### Test 1: Standard Load (100 concurrent, 2000 requests)

```bash
hey -n 2000 -c 100 -m POST \
  -H "Content-Type: application/json" \
  -d '{"texts":["doc1","doc2","doc3","doc4","doc5"],"normalize":true}' \
  https://embed.blockchainradar.xyz/vectorize \
  > /tmp/embedding-test1-standard.txt

# Analyze results
cat /tmp/embedding-test1-standard.txt
```

**Success Criteria**:
- ✅ 100% success rate
- ✅ P95 latency <300ms
- ✅ Throughput >100 req/sec

### Test 2: Large Batch (50 concurrent, 1000 requests, 10 texts each)

```bash
# Generate 10-text payload
TEXTS=$(printf '"%s",' text{1..10} | sed 's/,$//')

hey -n 1000 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d "{\"texts\":[$TEXTS],\"normalize\":true}" \
  https://embed.blockchainradar.xyz/vectorize \
  > /tmp/embedding-test2-large-batch.txt

# Compare latency vs single-text batches
```

### Test 3: Breaking Point

```bash
for concurrent in 100 150 200 250 300; do
  echo "Testing embedding with $concurrent concurrent connections..."

  hey -n 500 -c $concurrent -m POST \
    -H "Content-Type: application/json" \
    -d '{"texts":["t1","t2","t3"],"normalize":true}' \
    https://embed.blockchainradar.xyz/vectorize \
    > /tmp/embedding-breaking-$concurrent.txt

  cat /tmp/embedding-breaking-$concurrent.txt | grep -E "Success rate|P95"

  read -p "Press Enter to continue..."
done
```

### Deliverable

Create `docs/phase-3/reports/embedding-load-test-report.md`:

```markdown
# Embedding Service Load Test Report

**Date**: 2025-11-21
**Endpoint**: https://embed.blockchainradar.xyz/vectorize
**Model**: embeddinggemma-300m (768 dimensions)

## Test Results

| Test | Concurrent | Batch Size | Total Requests | Success Rate | P95 Latency | Throughput |
|------|-----------|------------|----------------|--------------|-------------|------------|
| Standard | 100 | 5 texts | 2000 | XXX% | XXms | XX.X req/s |
| Large Batch | 50 | 10 texts | 1000 | XXX% | XXms | XX.X req/s |
| Breaking 150 | 150 | 3 texts | 500 | XXX% | XXms | XX.X req/s |
| Breaking 200 | 200 | 3 texts | 500 | XXX% | XXms | XX.X req/s |

## Breaking Point

**Maximum Capacity**: XXX concurrent users
- CPU saturation at: XXX concurrent requests
- Latency acceptable up to: XXX concurrent users

## Batch Size Impact

- 5-text batch: XXms P95 latency
- 10-text batch: XXms P95 latency
- 20-text batch: XXms P95 latency (from Day 1)

**Optimal batch size**: XX texts (balances throughput and latency)
```

---

## Task 2.4: End-to-End RAG Load Testing (2 hours)

### Objective
Test full RAG flow with realistic user scenarios using locust.

### Create Locustfile

Create `tests/load/locustfile.py`:

```python
from locust import HttpUser, task, between
import random
import json

class RAGUser(HttpUser):
    wait_time = between(1, 3)  # 1-3 seconds between requests
    host = "http://localhost:8000"  # Will use port-forward

    @task(5)  # 5x more likely than health check
    def query_rag(self):
        """RAG query endpoint"""
        queries = [
            "What is machine learning?",
            "Explain neural networks in simple terms",
            "How does RAG work?",
            "What are transformers in NLP?",
            "Describe gradient descent",
            "What is deep learning?",
            "Explain convolutional neural networks",
        ]

        payload = {
            "query": random.choice(queries),
            "top_k": 5
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            catch_response=True,
            timeout=30
        ) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "answer" in data:
                        response.success()
                    else:
                        response.failure("Missing answer in response")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")

    @task(1)
    def health_check(self):
        """Health check endpoint"""
        self.client.get("/ready")


class StressTestUser(RAGUser):
    """More aggressive user for stress testing"""
    wait_time = between(0.5, 1)  # Faster requests
```

### Test 1: Normal Load (50 users, 5 minutes)

```bash
# Terminal 1: Port-forward GKE service
kubectl port-forward -n app svc/intellirag-app 8000:8000 &

# Terminal 2: Run locust test
cd tests/load

locust -f locustfile.py \
  --headless \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --html /tmp/locust-normal-50users.html \
  --csv /tmp/locust-normal

# Analyze results
cat /tmp/locust-normal_stats.csv
```

### Test 2: High Load (100 users, 5 minutes)

```bash
locust -f locustfile.py \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 5m \
  --html /tmp/locust-high-100users.html \
  --csv /tmp/locust-high

# Analyze failure rate and latency
```

### Test 3: Stress Test (200 users, 3 minutes)

```bash
locust -f locustfile.py \
  --user-classes StressTestUser \
  --headless \
  --users 200 \
  --spawn-rate 20 \
  --run-time 3m \
  --html /tmp/locust-stress-200users.html \
  --csv /tmp/locust-stress

# Check for failures and degradation
```

**Success Criteria**:
- ✅ 100 users: <1% failure rate, P95 <5s
- ✅ 200 users: Acceptable degradation (identify limits)

### Deliverable

Create `docs/phase-3/reports/e2e-load-test-report.md`:

```markdown
# End-to-End RAG Load Test Report

**Date**: 2025-11-21
**Endpoint**: http://localhost:8000/api/v1/query (via port-forward)
**Tool**: Locust

## Test Results

| Test | Users | Duration | Total Requests | Failures | P50 | P95 | P99 | RPS |
|------|-------|----------|----------------|----------|-----|-----|-----|-----|
| Normal | 50 | 5 min | XXXX | X.X% | Xs | Xs | Xs | XX |
| High | 100 | 5 min | XXXX | X.X% | Xs | Xs | Xs | XX |
| Stress | 200 | 3 min | XXXX | X.X% | Xs | Xs | Xs | XX |

## Locust Charts

[Include screenshots from HTML reports]

## Error Analysis

**Failure Types**:
1. Timeout errors: XX%
2. 5xx errors: XX%
3. Connection errors: XX%

**Failure Pattern**:
- Failures start at: XXX concurrent users
- Most common error: [error message]

## System Behavior Under Load

**At 50 users** (Normal):
- Stable performance
- Low error rate
- Acceptable latency

**At 100 users** (High):
- [Describe behavior]
- [Any degradation observed]

**At 200 users** (Stress):
- [Describe breaking point]
- [System limits reached]

## Recommendations

- Safe operating capacity: XXX concurrent users
- Recommended HPA max replicas: XX (based on XXX users per pod)
- Bottleneck identified: [vLLM / Embedding / Application / Network]
```

---

## Task 2.5: Capacity Planning Analysis (30 minutes)

### Objective
Synthesize all load test results into capacity recommendations.

### Analysis

**Calculate capacity per pod**:
```
From tests:
- vLLM breaking point: XXX concurrent users
- Embedding breaking point: XXX concurrent users
- E2E RAG breaking point: XXX concurrent users

Bottleneck: [Lowest number above]
Safe capacity per pod: [Bottleneck * 0.7 for 30% buffer]
```

**HPA calculations**:
```
Target capacity: 500 concurrent users (example)
Safe capacity per pod: 50 users
Required pods: 500 / 50 = 10 pods

Add 50% overhead: 10 * 1.5 = 15 pods
HPA max replicas: 15
```

### Deliverable

Create `docs/phase-3/reports/day2-capacity-analysis.md`:

```markdown
# Day 2: Capacity Planning Analysis

**Date**: 2025-11-21

## Load Test Summary

| Service | Breaking Point | P95 Latency @ Breaking | Bottleneck |
|---------|---------------|----------------------|------------|
| vLLM | XXX concurrent | XXXms | [GPU/Network] |
| Embedding | XXX concurrent | XXXms | [CPU/Memory] |
| E2E RAG | XXX concurrent | X.Xs | [Component] |

## System Capacity

**Overall Bottleneck**: [vLLM / Embedding / Application]
- Breaks at: XXX concurrent users
- Safe operating range: 0-XXX users (70% of breaking point)

## HPA Configuration Recommendations

Based on load testing data:

### CPU Threshold
- Current CPU at 50 users: XX%
- Current CPU at 100 users: XX%
- **Recommended target**: 70% (scales at XX users per pod)

### Memory Threshold
- Current memory at 50 users: XX%
- Current memory at 100 users: XX%
- **Recommended target**: 75% (scales at XX users per pod)

### Replica Counts
- **Min replicas**: 3 (maintain availability)
- **Max replicas**: 15 (cost constraint + capacity limit)
- **Capacity at max scale**: XXX concurrent users

## Cost Projections

**At different scales**:
- 3 replicas (baseline): ~$XXX/month
- 8 replicas (typical): ~$XXX/month
- 15 replicas (peak): ~$XXX/month

**Per-user cost**: ~$X.XX/month per concurrent user

## Resource Quota Recommendations

Based on max scale (15 replicas):
- **CPU requests**: 30 CPU (15 pods × 2 CPU)
- **CPU limits**: 60 CPU (15 pods × 4 CPU)
- **Memory requests**: 60Gi (15 pods × 4Gi)
- **Memory limits**: 120Gi (15 pods × 8Gi)

Add 50% buffer for Qdrant and other services:
- **Total CPU quota**: 45 CPU requests, 90 CPU limits
- **Total memory quota**: 90Gi requests, 180Gi limits

## Next Steps for Day 5

1. Configure HPA with:
   - `averageUtilization: 70` (CPU)
   - `averageUtilization: 75` (Memory)
   - `minReplicas: 3`
   - `maxReplicas: 15`

2. Set ResourceQuota:
   - `requests.cpu: 45`
   - `requests.memory: 90Gi`
   - `limits.cpu: 90`
   - `limits.memory: 180Gi`

3. Test autoscaling under actual load (repeat Test 2.4)
```

---

## ✅ Day 2 Completion Checklist

- [ ] hey and locust installed and verified
- [ ] vLLM load test completed (3 tests: baseline, stress, breaking point)
- [ ] Embedding load test completed (3 tests)
- [ ] End-to-end RAG test completed (3 user levels: 50, 100, 200)
- [ ] vLLM load test report created
- [ ] Embedding load test report created
- [ ] E2E load test report created with Locust HTML charts
- [ ] Capacity analysis document created
- [ ] HPA thresholds calculated and documented
- [ ] ResourceQuota recommendations prepared

**Success Criteria**:
- All load tests show clear success rates and latency distributions
- Breaking point identified for each service
- Data-driven HPA thresholds calculated
- Capacity planning document ready for Day 5

---

## 🔧 Troubleshooting

### Issue: hey command not found after install
```bash
# Check Go path
echo $PATH | grep go

# Add to PATH manually
export PATH=$PATH:$(go env GOPATH)/bin

# Make permanent
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
```

### Issue: locust connection refused
```bash
# Verify port-forward is running
ps aux | grep "port-forward"

# Restart port-forward
pkill -f "port-forward"
kubectl port-forward -n app svc/intellirag-app 8000:8000 &

# Test connectivity
curl http://localhost:8000/ready
```

### Issue: Load tests showing 100% failure
```bash
# Check if services are up
curl https://llm.blockchainradar.xyz/health
curl https://embed.blockchainradar.xyz/health

# Check CloudFlare Tunnel
sudo systemctl status cloudflared

# Check application logs
kubectl logs -n app -l app.kubernetes.io/name=intellirag-app --tail=50
```

### Issue: Locust HTML report not generated
```bash
# Ensure output directory exists
mkdir -p /tmp

# Run with explicit output path
locust -f locustfile.py \
  --headless \
  --users 50 \
  --spawn-rate 5 \
  --run-time 2m \
  --html "$(pwd)/locust-report.html"
```

---

## 📚 Resources

- [hey Documentation](https://github.com/rakyll/hey)
- [Locust Documentation](https://docs.locust.io/)
- [Load Testing Best Practices](https://k6.io/docs/testing-guides/)

---

**Next**: [Day 3: Observability & Optimization](./day3-observability-optimization.md)

**Last Updated**: 2025-11-21
