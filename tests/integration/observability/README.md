# Observability Stack Integration Tests

Comprehensive integration tests for the IntelliRAG observability stack (Prometheus, Grafana, Jaeger, Loki).

## Prerequisites

1. **Kubernetes Cluster**: Local (minikube/kind) or GKE cluster running
2. **Observability Stack Deployed**:
   ```bash
   cd kubernetes/observability
   export GRAFANA_ADMIN_PASSWORD="admin"
   export GRAFANA_SECRET_KEY="changeme"
   export PROMETHEUS_PASSWORD="prometheus"
   helmfile apply
   ```

3. **Port-Forwards Active**: Before running tests, establish port-forwards to all services:
   ```bash
   # Terminal 1: Prometheus
   kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090

   # Terminal 2: Grafana
   kubectl port-forward -n observability svc/grafana 3000:80

   # Terminal 3: Jaeger
   kubectl port-forward -n observability svc/jaeger-query 16686:16686

   # Terminal 4: Loki
   kubectl port-forward -n observability svc/loki 3100:3100
   ```

## Test Structure

```
tests/integration/observability/
├── test_prometheus_integration.py    # Prometheus metrics and query API
├── test_grafana_integration.py      # Grafana health, datasources, dashboards
├── test_jaeger_integration.py       # Jaeger UI and tracing API
├── test_loki_integration.py         # Loki readiness and log ingestion
├── test_observability_e2e.py        # End-to-end stack verification
└── test_metrics_collection_mock.py  # Mocked metrics for CI/CD
```

## Running Tests

### Run All Observability Tests

```bash
pytest tests/integration/observability/ -v
```

### Run Specific Component Tests

```bash
# Prometheus only
pytest tests/integration/observability/test_prometheus_integration.py -v

# Grafana only
pytest tests/integration/observability/test_grafana_integration.py -v

# Jaeger only
pytest tests/integration/observability/test_jaeger_integration.py -v

# Loki only
pytest tests/integration/observability/test_loki_integration.py -v

# End-to-end test
pytest tests/integration/observability/test_observability_e2e.py -v
```

### Run with Coverage

```bash
pytest tests/integration/observability/ --cov=app --cov-report=term-missing -v
```

## Test Coverage

| Component | Tests | What's Tested |
|-----------|-------|---------------|
| **Prometheus** | 4 | Health, readiness, query API, IntelliRAG metrics |
| **Grafana** | 3 | Health, datasources (Prometheus/Loki/Jaeger), dashboards |
| **Jaeger** | 2 | UI accessibility, services API |
| **Loki** | 1 | Readiness for log ingestion |
| **E2E** | 1 | All services healthy and integrated |
| **Mocked** | 1 | CI/CD-friendly metrics validation |
| **Total** | **12** | Complete observability stack |

## Test Behavior

### Service Availability Checks

Each test file includes a fixture that checks if the required service is accessible:

```python
@pytest.fixture(scope="module", autouse=True)
def check_prometheus():
    if not prometheus_available():
        pytest.skip("Prometheus not accessible...")
```

**Tests are automatically skipped** if services are unavailable, making them CI/CD-friendly.

### Expected Outcomes

✅ **All 12 tests pass** when:
- Observability stack is deployed
- All port-forwards are active
- Services are healthy

⏭️ **Tests are skipped** when:
- Port-forwards are not active
- Services are not deployed
- Network connectivity issues

## Troubleshooting

### Tests Skipped

**Problem**: All tests show as "SKIPPED"

**Solution**: Verify port-forwards are active:
```bash
curl http://localhost:9090/-/healthy  # Should return "Prometheus Server is Healthy."
curl http://localhost:3000/api/health  # Should return {"database":"ok"}
curl http://localhost:16686/  # Should return HTML with "Jaeger"
curl http://localhost:3100/ready  # Should return "ready"
```

### Connection Refused

**Problem**: `ConnectionRefusedError` or `ConnectionError`

**Solution**:
1. Check observability namespace pods are running:
   ```bash
   kubectl get pods -n observability
   ```
2. Verify services exist:
   ```bash
   kubectl get svc -n observability
   ```
3. Restart port-forwards

### Test Timeout

**Problem**: Tests timeout after 5 seconds

**Solution**:
1. Check pod logs for errors:
   ```bash
   kubectl logs -n observability <pod-name>
   ```
2. Verify sufficient cluster resources:
   ```bash
   kubectl top nodes
   kubectl top pods -n observability
   ```

## CI/CD Integration

For CI/CD pipelines where Kubernetes services may not be available:

```bash
# Run only mocked tests (no K8s required)
pytest tests/integration/observability/test_metrics_collection_mock.py -v
```

The mocked tests validate metric definitions and formats without requiring deployed services.

## Port-Forward Helper Script

Create `scripts/port-forward-observability.sh`:

```bash
#!/bin/bash
# Start all observability port-forwards in background

kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090 &
kubectl port-forward -n observability svc/grafana 3000:80 &
kubectl port-forward -n observability svc/jaeger-query 16686:16686 &
kubectl port-forward -n observability svc/loki 3100:3100 &

echo "Port-forwards started. Run 'pkill -f kubectl port-forward' to stop."
```

Usage:
```bash
chmod +x scripts/port-forward-observability.sh
./scripts/port-forward-observability.sh
pytest tests/integration/observability/ -v
```

## Verification Checklist

Before running tests, verify:

- [ ] Observability namespace exists (`kubectl get ns observability`)
- [ ] All pods are running (`kubectl get pods -n observability`)
- [ ] Prometheus accessible (`curl localhost:9090/-/healthy`)
- [ ] Grafana accessible (`curl localhost:3000/api/health`)
- [ ] Jaeger accessible (`curl localhost:16686/`)
- [ ] Loki accessible (`curl localhost:3100/ready`)

## Documentation

- [Metrics Implementation Summary](../../../docs/METRICS_COMPLETE_SUMMARY.md)
- [Quick Start Guide](../../../docs/metrics-and-monitoring-quickstart.md)
- [Grafana Dashboards & Alerts](../../../docs/grafana-dashboards-and-alerts.md)
- [Observability Stack Deployment](../../../kubernetes/observability/README.md)
