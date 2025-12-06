# IntelliRAG Observability - Quick Start Guide

## 🚀 Deploy Everything (One Command)

```bash
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG/kubernetes/observability/charts
./deploy.sh all
```

## 📦 Deploy Individual Components

```bash
# Prometheus only
./deploy.sh prometheus

# Loki only
./deploy.sh loki

# Jaeger only
./deploy.sh jaeger
```

## 🔍 Access Services

### Prometheus
```bash
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
```
Open: http://localhost:9090

### Loki (Query API)
```bash
kubectl port-forward -n observability svc/loki-gateway 3100:80
```
Query logs:
```bash
curl "http://localhost:3100/loki/api/v1/query_range" \
  --data-urlencode 'query={namespace="default"}' \
  --data-urlencode 'limit=10'
```

### Jaeger UI
```bash
kubectl port-forward -n observability svc/jaeger-query 16686:16686
```
Open: http://localhost:16686

## 🔄 Update/Upgrade

```bash
# Upgrade specific component
cd prometheus  # or loki, or jaeger
helm dependency update
helm upgrade prometheus . -n observability
```

## 🧹 Cleanup

```bash
# Remove everything
./cleanup.sh all

# Remove specific component
./cleanup.sh prometheus
./cleanup.sh loki
./cleanup.sh jaeger
```

## 📊 Check Status

```bash
# All pods
kubectl get pods -n observability

# All services
kubectl get svc -n observability

# Resource usage
kubectl top pods -n observability
```

## 🔧 Customize Configuration

Edit `values.yaml` in each chart directory, then upgrade:

```bash
cd prometheus
# Edit values.yaml
helm upgrade prometheus . -n observability
```

## 📝 Common Configurations

### Adjust Retention

**Prometheus** (`prometheus/values.yaml`):
```yaml
prometheus:
  prometheusSpec:
    retention: 30d  # Change from 15d
```

**Loki** (`loki/values.yaml`):
```yaml
loki:
  loki:
    limits_config:
      retention_period: 336h  # 14 days
```

**Jaeger** (`jaeger/values.yaml`):
```yaml
jaeger:
  schema:
    ttl:
      days: 14  # Change from 7
```

### Scale for Production

**Prometheus** - Add more storage:
```yaml
prometheus:
  prometheusSpec:
    storageSpec:
      volumeClaimTemplate:
        spec:
          resources:
            requests:
              storage: 100Gi  # Increase from 20Gi
```

**Loki** - Use object storage:
```yaml
loki:
  loki:
    storage:
      type: s3
      s3:
        endpoint: s3.amazonaws.com
        bucketnames: my-loki-bucket
```

**Jaeger** - Scale Elasticsearch:
```yaml
jaeger:
  elasticsearch:
    replicas: 3  # Change from 1 for HA
  collector:
    autoscaling:
      enabled: true
      minReplicas: 2
      maxReplicas: 5
```

## 🆘 Troubleshooting

### Pods stuck in Pending
```bash
# Check why
kubectl describe pod <pod-name> -n observability

# Common issues:
# - Insufficient CPU/Memory: Scale down replicas or increase node resources
# - PVC not bound: Check storage class exists
```

### Check logs
```bash
kubectl logs <pod-name> -n observability
kubectl logs <pod-name> -n observability --previous  # Previous instance
```

### Delete and reinstall
```bash
./cleanup.sh <component>
./deploy.sh <component>
```

## 💡 Pro Tips

1. **Deploy Prometheus first** - Other components expose metrics for it
2. **Start with minimal config** - Scale up based on actual usage
3. **Monitor resource usage** - Adjust limits based on `kubectl top`
4. **Use labels consistently** - Makes querying easier across all tools
5. **Set up alerts early** - Configure Alertmanager for critical issues

## 📚 Full Documentation

See individual READMEs:
- `prometheus/README.md`
- `loki/README.md`
- `jaeger/README.md`
- `README.md` (comprehensive guide)


