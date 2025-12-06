# IntelliRAG Loki Chart

Minimal production-ready Loki stack for IntelliRAG logging.

## Components

- **Loki**: Log aggregation and storage (SingleBinary mode)
- **Promtail**: Log collection agent (DaemonSet)
- **Gateway**: NGINX gateway for API access

## Installation

```bash
# Build dependencies
helm dependency build

# Install
helm install loki . -n observability --create-namespace

# Upgrade
helm upgrade loki . -n observability
```

## Access Loki

```bash
# Port forward to Loki gateway
kubectl port-forward -n observability svc/loki-gateway 3100:80

# Query logs
curl "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={namespace="default"}' \
  --data-urlencode 'limit=10'
```

## Grafana Integration

Add Loki as a datasource in Grafana:
- **URL**: `http://loki-gateway.observability.svc.cluster.local`
- **Type**: Loki

## Configuration

Key values to customize:
- `loki.loki.limits_config.retention_period`: Log retention
- `loki.singleBinary.persistence.size`: Storage size
- `loki.promtail.config.scrapeConfigs`: Log collection rules

## Resource Usage

- CPU: ~700m request, ~1500m limit
- Memory: ~1.5Gi request, ~2Gi limit
- Storage: 20Gi (configurable)

## Production Considerations

For production scale-out:
- Switch to `deploymentMode: SimpleScalable`
- Use object storage (S3/GCS) instead of filesystem
- Increase retention period
- Add compactor for log cleanup


