# IntelliRAG Grafana Chart

Grafana dashboarding with pre-configured datasources for Prometheus, Loki, and Jaeger.

## Features

✅ **Pre-configured Datasources**:
- Prometheus (metrics) - default
- Loki (logs)
- Jaeger (traces)

✅ **Pre-installed Dashboards**:
- Kubernetes Cluster Monitoring
- Node Exporter Metrics
- Loki Logs Explorer

✅ **Ready for IntelliRAG**:
- All observability stack integrated
- Trace-to-logs correlation enabled
- Metrics-to-traces correlation ready

## Prerequisites

Deploy the observability stack first:

```bash
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG/kubernetes/observability/charts

# Deploy required datasources
./deploy.sh prometheus
./deploy.sh loki
./deploy.sh jaeger
```

## Installation

```bash
# Build dependencies
helm dependency build

# Install
helm install grafana . -n observability

# Upgrade
helm upgrade grafana . -n observability
```

## Access Grafana

### Port Forward (Development)

```bash
kubectl port-forward -n observability svc/grafana 3000:80
```

Visit: http://localhost:3000

**Default Credentials**:
- Username: `admin`
- Password: `admin` (⚠️ Change in production!)

### Change Admin Password

```bash
# Via values.yaml
adminPassword: your-secure-password

# Or via kubectl
kubectl exec -it -n observability deployment/grafana -- grafana-cli admin reset-admin-password newpassword
```

### Run this after changing the password
```
kubectl create secret generic grafana-admin-secret \
  --from-literal=admin-user=admin \
  --from-literal=admin-password=admin \
  --from-literal=GF_SECURITY_ADMIN_USER=admin \
  --from-literal=GF_SECURITY_ADMIN_PASSWORD=admin \
  -n observability
```

## Pre-configured Datasources

All datasources are automatically configured:

### Prometheus (Default)
- URL: `http://prometheus-kube-prometheus-prometheus.observability.svc.cluster.local:9090`
- Type: Metrics
- Usage: System & application metrics

### Loki
- URL: `http://loki-gateway.observability.svc.cluster.local`
- Type: Logs
- Usage: Application & system logs

### Jaeger
- URL: `http://jaeger-query.observability.svc.cluster.local:16686`
- Type: Traces
- Usage: Distributed tracing

## Create Your First Dashboard

### 1. IntelliRAG API Metrics

```
Dashboard → New → Add visualization → Prometheus

Query: rate(http_requests_total{job="intellirag-api"}[5m])
Legend: {{method}} {{endpoint}}
```

### 2. Application Logs

```
Dashboard → New → Add visualization → Loki

Query: {namespace="default", app="intellirag"} |= "error"
```

### 3. Request Traces

```
Dashboard → New → Add visualization → Jaeger

Service: intellirag-api
Operation: All
```

## Correlation Features

### Logs to Traces

1. Open Explore → Select Loki
2. Query logs with `trace_id` label
3. Click on trace_id → Jump to Jaeger

### Metrics to Traces

1. Create alert in Prometheus
2. Add Jaeger link with trace context
3. Click to view related traces

### Traces to Logs

1. Open trace in Jaeger view
2. Click "Logs" tab in trace details
3. See correlated log entries

## Pre-installed Dashboards

### Kubernetes Cluster (ID: 7249)
- Node CPU/Memory usage
- Pod statistics
- Persistent volumes
- Network I/O

### Node Exporter (ID: 1860)
- System metrics
- CPU, memory, disk, network
- Per-node breakdown

### Loki Logs (ID: 13639)
- Log volume
- Log levels
- Top log producers

## Custom Dashboard Tips

### IntelliRAG-Specific Panels

**API Request Rate**:
```promql
sum(rate(http_requests_total{job="intellirag-api"}[5m])) by (endpoint)
```

**API Error Rate**:
```promql
sum(rate(http_requests_total{job="intellirag-api", status=~"5.."}[5m])) 
/ 
sum(rate(http_requests_total{job="intellirag-api"}[5m]))
```

**API Latency (P95)**:
```promql
histogram_quantile(0.95, 
  sum(rate(http_request_duration_seconds_bucket{job="intellirag-api"}[5m])) by (le)
)
```

**Vector DB Query Performance**:
```promql
rate(qdrant_requests_total[5m])
```

**Application Logs by Level**:
```logql
sum(count_over_time({namespace="default", app="intellirag"} [5m])) by (level)
```

## Configuration

### Add Custom Datasource

Edit `values.yaml`:

```yaml
datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
      - name: MyDatabase
        type: postgres
        url: postgresql.default.svc.cluster.local:5432
        database: mydb
        user: grafana
        secureJsonData:
          password: ${DB_PASSWORD}
```

### Import Dashboard

```bash
# Via UI: + → Import → Enter dashboard ID or upload JSON

# Via values.yaml:
dashboards:
  default:
    my-dashboard:
      gnetId: 12345
      revision: 1
      datasource: Prometheus
```

### Add Plugins

Edit `values.yaml`:

```yaml
plugins:
  - grafana-piechart-panel
  - grafana-worldmap-panel
  - grafana-clock-panel
```

## Resource Usage

- CPU: 100m request, 500m limit
- Memory: 256Mi request, 512Mi limit
- Storage: 10Gi (dashboards & settings)

## Production Recommendations

1. **Change admin password**:
   ```yaml
   adminPassword: use-secret-manager
   ```

2. **Enable ingress**:
   ```yaml
   ingress:
     enabled: true
     ingressClassName: nginx
     hosts:
       - grafana.yourdomain.com
   ```

3. **Use secret for passwords**:
   ```yaml
   admin:
     existingSecret: grafana-admin-secret
   ```

4. **Increase resources**:
   ```yaml
   resources:
     requests:
       cpu: 200m
       memory: 512Mi
   ```

5. **Enable HA** (for critical deployments):
   ```yaml
   replicas: 2
   ```

## Alerting

Grafana includes unified alerting:

1. Go to Alerting → Alert rules
2. Create alert rule from dashboard panel
3. Configure notification channels
4. Set up alert routes

## Backup Dashboards

```bash
# Export dashboards
kubectl exec -n observability deployment/grafana -- \
  grafana-cli admin export-dashboards /tmp/dashboards

# Copy to local
kubectl cp observability/grafana-xxx:/tmp/dashboards ./dashboards-backup
```

## Troubleshooting

### Can't login
```bash
# Reset password
kubectl exec -it -n observability deployment/grafana -- \
  grafana-cli admin reset-admin-password newpassword
```

### Datasource not working
```bash
# Check connectivity
kubectl exec -it -n observability deployment/grafana -- \
  curl http://prometheus-kube-prometheus-prometheus.observability.svc.cluster.local:9090/-/healthy
```

### Dashboards not loading
```bash
# Check logs
kubectl logs -n observability deployment/grafana

# Check dashboard provisioning
kubectl exec -it -n observability deployment/grafana -- \
  ls -la /var/lib/grafana/dashboards/
```

## Links

- [Grafana Documentation](https://grafana.com/docs/grafana/latest/)
- [Dashboard Gallery](https://grafana.com/grafana/dashboards/)
- [Prometheus Queries](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [Loki LogQL](https://grafana.com/docs/loki/latest/logql/)


