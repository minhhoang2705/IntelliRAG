# IntelliRAG Prometheus Chart

Minimal production-ready Prometheus stack for IntelliRAG monitoring.

## Components

- **Prometheus Server**: Metrics collection and storage
- **Alertmanager**: Alert routing and management
- **Node Exporter**: System-level metrics
- **Kube State Metrics**: Kubernetes cluster metrics
- **Prometheus Operator**: Manages Prometheus instances

## Installation

```bash
# Build dependencies
helm dependency build

# Install
helm install prometheus . -n observability --create-namespace

# Upgrade
helm upgrade prometheus . -n observability
```

## Access Prometheus

```bash
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
```

Visit: http://localhost:9090

## Configuration

Key values to customize:
- `kube-prometheus-stack.prometheus.prometheusSpec.retention`: Data retention period
- `kube-prometheus-stack.prometheus.prometheusSpec.storageSpec`: Storage configuration
- `kube-prometheus-stack.alertmanager.config`: Alert routing configuration

## Resource Usage

- CPU: ~550m request, ~2000m limit
- Memory: ~2Gi request, ~3.5Gi limit
- Storage: 20Gi (configurable)


