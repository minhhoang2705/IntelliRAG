# IntelliRAG Load Testing Framework

Comprehensive load testing suite for Day 2 performance validation of the IntelliRAG system.

## Overview

This framework provides automated load testing for three critical components:

1. **vLLM Service** - GPU inference endpoint
2. **Embedding Service** - Text vectorization endpoint
3. **End-to-End RAG** - Complete query pipeline

## Directory Structure

```
tests/load/
├── config/                      # Test configurations
│   ├── endpoints.yaml           # Service endpoints
│   ├── test_profiles.yaml       # Test scenarios and parameters
│   └── thresholds.yaml          # Success criteria and limits
├── scripts/                     # Reusable bash scripts
│   ├── run-hey-test.sh         # Generic hey test runner
│   ├── test-vllm.sh            # vLLM test suite
│   └── test-embedding.sh       # Embedding test suite
├── locust/                      # Python locust tests
│   ├── locustfile.py           # Main locust configuration
│   ├── tasks/                  # Modular task sets
│   │   └── rag_tasks.py
│   └── users/                  # User behavior profiles
│       ├── normal_user.py
│       └── stress_user.py
├── reports/                     # Report generation
│   └── generate_report.sh      # Report aggregator
├── results/                     # Test results storage
│   ├── vllm/                   # vLLM test outputs
│   ├── embedding/              # Embedding test outputs
│   └── e2e/                    # Locust test outputs
├── run-all-tests.sh            # Main orchestrator
└── README.md                   # This file
```

## Prerequisites

### Required Tools

1. **hey** - HTTP load testing tool
   ```bash
   go install github.com/rakyll/hey@latest
   ```

2. **locust** - Python load testing framework
   ```bash
   pip install locust
   ```

3. **kubectl** - Kubernetes CLI (for E2E tests)
   ```bash
   # Already installed for GKE management
   ```

### Service Availability

Ensure the following endpoints are accessible:

- vLLM: `https://llm.blockchainradar.xyz`
- Embedding: `https://embed.blockchainradar.xyz`
- GKE App: Accessible via `kubectl port-forward`

## Quick Start

### Run Complete Test Suite

```bash
cd tests/load
./run-all-tests.sh
```

This will:
1. Run pre-flight health checks
2. Execute vLLM load tests (baseline, stress, breaking point)
3. Execute embedding service tests (standard, batch optimization, breaking point)
4. Execute end-to-end RAG tests (50, 100, 200 users)
5. Generate comprehensive reports

### Run Specific Tests

```bash
# vLLM only
./run-all-tests.sh --vllm-only

# Embedding only
./run-all-tests.sh --embedding-only

# E2E only
./run-all-tests.sh --e2e-only

# Skip breaking point tests (faster)
./run-all-tests.sh --skip-breaking
```

## Individual Test Scripts

### vLLM Load Testing

```bash
cd tests/load/scripts

# Run all vLLM tests
./test-vllm.sh

# Run specific profile
./test-vllm.sh --profile baseline
./test-vllm.sh --profile stress
./test-vllm.sh --profile breaking

# Skip breaking point test
./test-vllm.sh --skip-breaking
```

**Test Profiles:**
- **Baseline**: 50 concurrent, 1000 requests
- **Stress**: 100 concurrent, 2000 requests
- **Breaking Point**: Incremental 100→300 concurrent

### Embedding Service Testing

```bash
cd tests/load/scripts

# Run all embedding tests
./test-embedding.sh

# Run specific profile
./test-embedding.sh --profile standard
./test-embedding.sh --profile large-batch
./test-embedding.sh --profile optimize
./test-embedding.sh --profile breaking
```

**Test Profiles:**
- **Standard**: 100 concurrent, 5 texts/batch
- **Large Batch**: 50 concurrent, 10 texts/batch
- **Batch Optimization**: Test 1, 3, 5, 10, 20 texts/batch
- **Breaking Point**: Incremental 100→300 concurrent

### End-to-End RAG Testing

```bash
cd tests/load/locust

# Setup port-forward first
kubectl port-forward -n app svc/intellirag-app 8000:8000 &

# Run normal load (50 users, 5 min)
locust -f locustfile.py \
  --headless \
  --users 50 \
  --spawn-rate 5 \
  --run-time 5m \
  --host http://localhost:8000 \
  --html report.html

# Run stress test (200 users)
locust -f locustfile.py \
  --user-classes StressTestUser \
  --headless \
  --users 200 \
  --spawn-rate 20 \
  --run-time 3m \
  --host http://localhost:8000
```

**User Classes:**
- `NormalRAGUser` - Balanced query patterns (1-3s wait)
- `CasualUser` - Infrequent queries (3-8s wait)
- `PowerUser` - Frequent complex queries (0.5-2s wait)
- `StressTestUser` - Aggressive patterns (0.5-1s wait)
- `BurstUser` - Burst traffic patterns
- `SpikeUser` - Extreme load simulation

## Test Results

### Output Locations

- **vLLM results**: `tests/load/results/vllm/*.txt`
- **Embedding results**: `tests/load/results/embedding/*.txt`
- **E2E results**: `tests/load/results/e2e/*.html` (Locust reports)

### Generated Reports

- **vLLM report**: `docs/phase-3/reports/vllm-load-test-report.md`
- **Embedding report**: `docs/phase-3/reports/embedding-load-test-report.md`
- **E2E report**: View Locust HTML reports directly

## Configuration

### Endpoints (config/endpoints.yaml)

Update service URLs and connection parameters:

```yaml
endpoints:
  vllm:
    url: "https://llm.blockchainradar.xyz"
    model: "Qwen/Qwen3-0.6B"

  embedding:
    url: "https://embed.blockchainradar.xyz"
    model: "embeddinggemma-300m"
```

### Test Profiles (config/test_profiles.yaml)

Customize test parameters:

```yaml
vllm:
  baseline:
    concurrent: 50
    total_requests: 1000
```

### Thresholds (config/thresholds.yaml)

Define success criteria:

```yaml
vllm:
  success_rate_min: 99.0
  latency:
    p95_max_ms: 500
```

## Interpreting Results

### Key Metrics

**hey output metrics:**
- **Success Rate**: Should be >99%
- **P50/P95/P99 Latency**: Measure response time distribution
- **Throughput (RPS)**: Requests per second capacity
- **Breaking Point**: Concurrent users where errors >1%

**Locust metrics:**
- **Failure Rate**: Should be <1% for normal load
- **Response Time**: P50/P95/P99 percentiles
- **RPS**: Sustained request rate
- **User Count**: Maximum concurrent users supported

### Breaking Point Analysis

Identify system capacity limits:

1. **vLLM Breaking Point**: GPU compute saturation
2. **Embedding Breaking Point**: CPU capacity limit
3. **E2E Breaking Point**: Overall system bottleneck

Use breaking point data to:
- Calculate safe operating range (70% of breaking point)
- Configure HPA thresholds
- Plan capacity scaling

## Troubleshooting

### hey command not found

```bash
# Check Go path
echo $PATH | grep go

# Add to PATH
export PATH=$PATH:$(go env GOPATH)/bin
echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
```

### locust connection refused

```bash
# Verify port-forward
ps aux | grep "port-forward"

# Restart port-forward
pkill -f "port-forward"
kubectl port-forward -n app svc/intellirag-app 8000:8000 &

# Test connectivity
curl http://localhost:8000/ready
```

### Endpoint not reachable

```bash
# Check CloudFlare Tunnel
sudo systemctl status cloudflared

# Check vLLM service
curl https://llm.blockchainradar.xyz/health

# Check embedding service
curl https://embed.blockchainradar.xyz/health

# Check GKE app
kubectl get pods -n app
kubectl logs -n app -l app.kubernetes.io/name=intellirag-app
```

## CI/CD Integration

The framework is designed for CI/CD integration:

```bash
# Example GitHub Actions workflow
- name: Run Load Tests
  run: |
    cd tests/load
    ./run-all-tests.sh --skip-e2e
```

Exit codes:
- `0` - All tests passed
- `1` - One or more tests failed or had degraded performance

## Performance Baselines

From Day 1 analysis:

| Component | Metric | Current | Target (Post-Day 3) |
|-----------|--------|---------|---------------------|
| vLLM | GPU Utilization | 99% | 99% (maintain) |
| vLLM | GPU Memory | 7GB (57%) | 10-11GB (85-90%) |
| vLLM | Max Concurrent | 50 tested | 100+ expected |
| Embedding | Peak CPU | 1094m (109%) | 770m per pod (70% with HPA) |
| Embedding | Memory | 1325Mi | 1325Mi (stable) |
| GKE App | Replicas | 5 (maxed) | 2-3 (optimal) |

## Next Steps

After completing Day 2 load testing:

1. **Review Reports**: Analyze generated reports for insights
2. **Identify Bottlenecks**: Compare results against Day 1 analysis
3. **Calculate HPA Thresholds**: Use breaking point data
4. **Plan Optimizations**: Prioritize fixes for Day 3
5. **Update Documentation**: Record capacity planning recommendations

## References

- [Day 1 Analysis Report](../../docs/phase-3/reports/day1-analysis.md)
- [Day 2 Task Documentation](../../docs/phase-3/tasks/day2-load-testing.md)
- [hey Documentation](https://github.com/rakyll/hey)
- [Locust Documentation](https://docs.locust.io/)

---

**Last Updated**: 2025-11-23
**Framework Version**: 1.0.0
