# IntelliRAG Observability Stack Deployment Guide

**Version**: 1.0
**Last Updated**: 2025-11-06
**Target Platform**: Kubernetes (GKE Autopilot recommended)

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture Overview](#architecture-overview)
- [Quick Start](#quick-start)
- [Detailed Installation](#detailed-installation)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

### Required Tools
```bash
# Helm 3.12+
helm version

# Helmfile 0.165.0+
helmfile version

# kubectl 1.28+
kubectl version --client

# Access to Kubernetes cluster
kubectl cluster-info
```

### Required Permissions
- `cluster-admin` role or equivalent
- Ability to create namespaces
- Ability to create persistent volumes

### Resource Requirements

| Component    | CPU Request | CPU Limit | Memory Request | Memory Limit | Storage |
|--------------|-------------|-----------|----------------|--------------|---------|
| Prometheus   | 1 core      | 2 cores   | 2Gi            | 4Gi          | 50Gi    |
| Grafana      | 500m        | 1 core    | 512Mi          | 1Gi          | 10Gi    |
| Jaeger       | 500m        | 1 core    | 512Mi          | 1Gi          | 50Gi    |
| Loki         | 1 core      | 2 cores   | 1Gi            | 2Gi          | 50Gi    |
| **Total**    | **3 cores** | **6 cores** | **4Gi**      | **8Gi**      | **160Gi** |

---

## Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                     IntelliRAG Application                       │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐                │
│  │   FastAPI  │  │   vLLM     │  │   Qdrant   │                │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘                │
└────────┼────────────────┼────────────────┼──────────────────────┘
         │ metrics        │ traces         │ logs
         │ /metrics       │ OTLP           │ stdout/stderr
         ▼                ▼                ▼
┌────────────────────────────────────────────────────────────────┐
│              Observability Stack (namespace: observability)    │
│                                                                 │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐       │
│  │ Prometheus  │────│   Grafana   │────│   Jaeger    │       │
│  │  (Metrics)  │    │(Dashboards) │    │  (Traces)   │       │
│  └─────────────┘    └─────────────┘    └─────────────┘       │
│                             │                                   │
│                     ┌───────┴────────┐                         │
│                     │      Loki      │                         │
│                     │     (Logs)     │                         │
│                     └────────────────┘                         │
└────────────────────────────────────────────────────────────────┘
```

### Data Flow
1. **Metrics**: Prometheus scrapes `/metrics` endpoints every 30s
2. **Traces**: Applications send traces via OTLP to Jaeger agents
3. **Logs**: Promtail collects pod logs and ships to Loki
4. **Visualization**: Grafana queries all three datasources with correlation

---

## Quick Start

### One-Command Deployment

```bash
# Set required environment variables
export GRAFANA_ADMIN_PASSWORD="your-secure-password"
export GRAFANA_SECRET_KEY="your-secret-key"
export PROMETHEUS_PASSWORD="prometheus-password"

# Deploy entire observability stack
cd kubernetes/observability
helmfile sync
```

**Deployment Time**: ~5-10 minutes

### Quick Verification

```bash
# Check all pods are running
kubectl get pods -n observability

# Expected output:
# prometheus-kube-prometheus-prometheus-0    2/2     Running
# grafana-xxx                                 1/1     Running
# jaeger-xxx                                  1/1     Running
# loki-0                                      1/1     Running
# promtail-xxx                                1/1     Running
```

---

## Detailed Installation

### Step 1: Add Helm Repositories

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update
```

### Step 2: Create Namespace

```bash
kubectl apply -f kubernetes/observability/namespace.yaml
```

### Step 3: Set Environment Variables

```bash
# Required variables
export GRAFANA_ADMIN_PASSWORD="$(openssl rand -base64 32)"
export GRAFANA_SECRET_KEY="$(openssl rand -base64 32)"
export PROMETHEUS_PASSWORD="$(openssl rand -base64 32)"

# Save credentials securely
echo "Grafana Admin Password: $GRAFANA_ADMIN_PASSWORD" >> observability-credentials.txt
chmod 600 observability-credentials.txt
```

### Step 4: Deploy Components

#### Option A: Using Root Helmfile (Recommended)

```bash
cd kubernetes/observability
helmfile sync

# Watch deployment progress
watch kubectl get pods -n observability
```

#### Option B: Deploy Components Individually

```bash
# 1. Prometheus (metrics backend)
cd kubernetes/observability/prometheus
helmfile sync

# 2. Loki (logging backend)
cd ../loki
helmfile sync

# 3. Jaeger (tracing backend)
cd ../jaeger
helmfile sync

# 4. Grafana (visualization)
cd ../grafana
helmfile sync
```

### Step 5: Configure Ingress (Optional)

```bash
# Apply ingress for external access
kubectl apply -f - <<EOF
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: observability-ingress
  namespace: observability
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
    - hosts:
        - grafana.intellirag.local
        - prometheus.intellirag.local
        - jaeger.intellirag.local
      secretName: observability-tls
  rules:
    - host: grafana.intellirag.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: grafana
                port:
                  number: 80
    - host: prometheus.intellirag.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: prometheus-kube-prometheus-prometheus
                port:
                  number: 9090
    - host: jaeger.intellirag.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: jaeger-query
                port:
                  number: 16686
EOF
```

---

## Configuration

### Prometheus Configuration

**Scrape Interval**: 30s (configurable in `prometheus/values.yaml`)

```yaml
prometheus:
  prometheusSpec:
    additionalScrapeConfigs:
      - job_name: 'intellirag-metrics'
        scrape_interval: 30s  # Adjust as needed
        static_configs:
          - targets:
              - 'intellirag-service.default:8000'
```

### Grafana Dashboard Provisioning

Dashboards are automatically provisioned from `observability/grafana/provisioning/dashboards/json/`:
- `intellirag-overview.json`
- `query-performance.json`
- `ingestion-pipeline.json`
- `llm-metrics.json`
- `infrastructure.json`

To add custom dashboards:
```bash
# Add JSON file to dashboards directory
cp my-dashboard.json observability/grafana/provisioning/dashboards/json/

# Recreate ConfigMap
kubectl create configmap grafana-dashboards-intellirag \
  --from-file=observability/grafana/provisioning/dashboards/json/ \
  --namespace=observability \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart Grafana
kubectl rollout restart deployment/grafana -n observability
```

### Retention Policies

| Component  | Default Retention | Configuration Location                |
|------------|-------------------|---------------------------------------|
| Prometheus | 30 days           | `prometheus/values.yaml` → retention  |
| Loki       | 7 days            | `loki/values.yaml` → retention_period |
| Jaeger     | 7 days            | `jaeger/values.yaml` → ttl.days       |

---

## Verification

### Check Pod Status

```bash
kubectl get pods -n observability
```

**All pods should be `Running` with `READY 1/1` or `2/2`.**

### Test Prometheus

```bash
# Port-forward Prometheus
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090

# Open browser: http://localhost:9090
# Run test query: up{job="intellirag"}
```

### Test Grafana

```bash
# Port-forward Grafana
kubectl port-forward -n observability svc/grafana 3000:80

# Open browser: http://localhost:3000
# Login: admin / $GRAFANA_ADMIN_PASSWORD
# Navigate to: Dashboards → IntelliRAG → IntelliRAG Overview
```

### Test Jaeger

```bash
# Port-forward Jaeger UI
kubectl port-forward -n observability svc/jaeger-query 16686:16686

# Open browser: http://localhost:16686
# Search for service: intellirag-api
```

### Test Loki

```bash
# Port-forward Loki
kubectl port-forward -n observability svc/loki-gateway 3100:80

# Test log query
curl -G -s "http://localhost:3100/loki/api/v1/query" \
  --data-urlencode 'query={app="intellirag"}' | jq
```

---

## Troubleshooting

### Pods Not Starting

```bash
# Check pod events
kubectl describe pod <pod-name> -n observability

# Check logs
kubectl logs <pod-name> -n observability

# Common issues:
# - Insufficient resources: Increase node resources
# - PVC not bound: Check storage provisioner
# - ImagePullBackOff: Check network/registry access
```

### Metrics Not Appearing

```bash
# 1. Verify Prometheus is scraping
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
# Open http://localhost:9090/targets
# Check if intellirag-metrics target is UP

# 2. Verify application exposes /metrics
kubectl port-forward -n default svc/intellirag-service 8000:8000
curl http://localhost:8000/metrics

# 3. Check Prometheus logs
kubectl logs -n observability prometheus-kube-prometheus-prometheus-0 -c prometheus
```

### Dashboards Not Loading

```bash
# 1. Check ConfigMap exists
kubectl get configmap grafana-dashboards-intellirag -n observability

# 2. Restart Grafana
kubectl rollout restart deployment/grafana -n observability

# 3. Check Grafana logs
kubectl logs -n observability deployment/grafana
```

### High Resource Usage

```bash
# Check resource usage
kubectl top pods -n observability

# Adjust resource limits
kubectl edit deployment/<component> -n observability

# For Prometheus: Enable query log sampling
# For Loki: Reduce log retention
# For Jaeger: Implement trace sampling
```

---

## Next Steps

1. **Configure Alerting**: Set up Alertmanager receivers (Slack, PagerDuty, etc.)
2. **Set up Authentication**: Enable OAuth2/OIDC for Grafana
3. **Implement Backup**: Schedule etcd snapshots and PV backups
4. **Review Best Practices**: See `observability-best-practices.md`
5. **Monitor Costs**: Track storage and compute costs in GCP console

---

## Support

- **Documentation**: `docs/deployment/observability/`
- **Issues**: GitHub Issues
- **Slack**: `#observability` channel
