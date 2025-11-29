# Phase 4: MLOps Pipeline - Implementation Summary

**Completed**: 2025-11-28
**Duration**: 1 day
**Status**: ✅ Core Components Deployed

---

## 📋 Overview

Phase 4 successfully deployed the MLOps pipeline for IntelliRAG, establishing model lifecycle management, experiment tracking, and data drift monitoring capabilities.

---

## ✅ Completed Components

### 1. PostgreSQL Database (In-Cluster)
**Status**: ✅ Deployed
- **Deployment Method**: Helm (Bitnami PostgreSQL chart)
- **Namespace**: `mlflow`
- **Configuration**:
  - Database: `mlflow`
  - User: `mlflow`
  - Storage: 20Gi PVC (standard-rwo)
  - Resources: 500m CPU, 512Mi RAM
- **Service**: `postgresql.mlflow.svc.cluster.local:5432`
- **Note**: Currently not used by MLFlow (using SQLite instead due to psycopg2 dependency issue)

### 2. GCS Bucket for MLFlow Artifacts
**Status**: ✅ Created
- **Bucket Name**: `intellirag-mlflow-artifacts`
- **Location**: `asia-southeast1`
- **Storage Class**: STANDARD
- **Lifecycle Policy**: 90-day retention
- **Access**: Granted to `intellirag-cluster-workload-sa`
- **Purpose**: Store model artifacts, experiment data, drift reports

### 3. MLFlow Tracking Server
**Status**: ✅ Deployed via Helm
- **Deployment Method**: Custom Helm chart (`helm/mlflow/`)
- **Chart Version**: 1.0.0
- **App Version**: 2.9.2
- **Namespace**: `mlflow`
- **Backend Store**: SQLite (`/mlflow/mlflow.db`)
- **Artifact Store**: GCS (`gs://intellirag-mlflow-artifacts`)
- **Persistent Storage**: 10Gi PVC
- **Resources**: 500m-1000m CPU, 1Gi-2Gi RAM
- **Service Account**: `mlflow-sa` (with Workload Identity)
- **Ingress**: `https://mlflow.blockchainradar.xyz`
- **TLS**: cert-manager with Let's Encrypt

**Helm Chart Structure**:
```
helm/mlflow/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── serviceaccount.yaml
│   ├── ingress.yaml
│   ├── pvc.yaml
│   ├── NOTES.txt
│   └── _helpers.tpl
```

### 4. Model Registration
**Status**: ✅ Script Created
- **Script**: `mlops/register_models.py`
- **Models to Register**:
  1. **qwen3-0.6b-instruct**
     - Framework: vLLM
     - Endpoint: https://llm.blockchainradar.xyz/v1
     - Metrics: 793 TPS, 80ms P99 latency
  2. **embeddinggemma-300m**
     - Framework: KServe/Sentence Transformers
     - Endpoint: https://embed.blockchainradar.xyz
     - Metrics: 287ms avg latency, 128 batch throughput

**Execution**: Pending DNS configuration

### 5. Evidently Drift Monitoring
**Status**: ✅ Implemented
- **Package**: evidently==0.7.17
- **Module**: `mlops/monitoring/drift_detector.py`
- **Features**:
  - Data drift detection (DataDriftPreset)
  - Data quality monitoring (DataQualityPreset)
  - MLFlow integration for logging
  - HTML report generation
- **CronJob**: `kubernetes/mlops/drift-monitoring-cronjob.yaml`
  - Schedule: Daily at 4 AM
  - Namespace: mlflow
  - Resources: 500m-1000m CPU, 1Gi-2Gi RAM

### 6. MLOps Grafana Dashboard
**Status**: ✅ Created
- **File**: `observability/grafana/provisioning/dashboards/json/mlops-metrics.json`
- **Panels**:
  - MLFlow status
  - Data drift score (with thresholds)
  - Model inference latency (P95)
  - Throughput metrics (requests/s, tokens/s)
- **Refresh**: 10s
- **Time Range**: Last 1 hour

---

## 🔧 Technical Decisions

### Why SQLite Instead of PostgreSQL?
The official MLFlow Docker image (`ghcr.io/mlflow/mlflow:v2.9.2`) does not include the `psycopg2` Python package required for PostgreSQL connectivity. 

**Options considered**:
1. ✅ **Use SQLite with persistent volume** (chosen)
   - Simple, no dependencies
   - Works out-of-the-box
   - Suitable for single-instance MLFlow
   - 10Gi PVC provides sufficient storage
2. ❌ Create custom Docker image with psycopg2
   - More complex, requires CI/CD
   - Adds maintenance overhead
3. ❌ Use PostgreSQL via init container
   - Complex workaround
   - Not sustainable

**Recommendation**: For production scale-out, consider creating a custom MLFlow image with PostgreSQL support.

---

## 📂 File Structure

```
IntelliRAG/
├── helm/
│   └── mlflow/                           # MLFlow Helm chart
│       ├── Chart.yaml
│       ├── values.yaml
│       └── templates/
│           ├── deployment.yaml
│           ├── service.yaml
│           ├── serviceaccount.yaml
│           ├── ingress.yaml
│           ├── pvc.yaml
│           └── NOTES.txt
├── kubernetes/
│   └── mlops/
│       └── drift-monitoring-cronjob.yaml # Evidently CronJob
├── mlops/
│   ├── register_models.py                # Model registration script
│   └── monitoring/
│       ├── __init__.py
│       └── drift_detector.py             # Drift detection service
├── observability/
│   └── grafana/
│       └── provisioning/
│           └── dashboards/
│               └── json/
│                   └── mlops-metrics.json # MLOps dashboard
└── docs/
    ├── plans/
    │   └── phase-4-mlops-simplified.md   # Implementation plan
    ├── todos/
    │   └── phase-4-mlops-todos.md        # Task checklist
    └── summaries/
        └── phase-4-mlops-completion-summary.md  # This file
```

---

## 🚀 Next Steps (Manual Actions Required)

### 1. Add DNS Record for MLFlow
**Required for**:
- Accessing MLFlow UI
- TLS certificate issuance
- Model registration

**Configuration**:
```
Type: A
Host: mlflow
Domain: blockchainradar.xyz
Value: 34.143.244.90
TTL: 300
```

**Status Check**:
```bash
# Wait for certificate to be ready
kubectl get certificate -n mlflow -w

# Should show: mlflow-tls   True   mlflow-tls
```

### 2. Register Models in MLFlow
```bash
# Once DNS is configured and MLFlow UI is accessible
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG
python mlops/register_models.py

# Verify in UI
open https://mlflow.blockchainradar.xyz/#/models
```

### 3. Deploy Drift Monitoring CronJob
```bash
kubectl apply -f kubernetes/mlops/drift-monitoring-cronjob.yaml

# Manually trigger first run for testing
kubectl create job --from=cronjob/drift-monitoring drift-manual -n mlflow
kubectl logs -n mlflow -l job-name=drift-manual -f
```

### 4. Add MLOps Dashboard to Grafana
```bash
# Create ConfigMap
kubectl create configmap mlops-dashboard \
  --from-file=observability/grafana/provisioning/dashboards/json/mlops-metrics.json \
  -n observability \
  --dry-run=client -o yaml | kubectl apply -f -

# Restart Grafana
kubectl rollout restart deployment prometheus-grafana -n observability

# Access dashboard
open https://grafana.blockchainradar.xyz
# Navigate to: Dashboards → MLOps Model Performance
```

---

## 🔍 Verification Commands

### Check MLFlow Status
```bash
# Pod status
kubectl get pods -n mlflow

# Service endpoints
kubectl get svc -n mlflow

# Ingress
kubectl get ingress -n mlflow

# Logs
kubectl logs -n mlflow -l app.kubernetes.io/name=mlflow -f
```

### Check Persistent Storage
```bash
# PVCs
kubectl get pvc -n mlflow

# Volume usage
kubectl exec -n mlflow deployment/mlflow-server -- df -h /mlflow
```

### Access MLFlow UI (after DNS)
```bash
# Via browser
open https://mlflow.blockchainradar.xyz

# Via port-forward (temporary)
kubectl port-forward -n mlflow svc/mlflow-server 5000:5000
open http://localhost:5000
```

---

## 💰 Cost Impact

| Component | Monthly Cost |
|-----------|-------------|
| PostgreSQL (20GB PVC) | ~$4 |
| MLFlow PVC (10GB) | ~$2 |
| MLFlow server (500m CPU, 1GB RAM) | ~$10 |
| GCS artifacts (~5GB initial) | ~$0.13 |
| Drift monitoring CronJob | ~$1 |
| **Phase 4 Total** | **~$17/month** |
| **New Project Total** | **~$131/month** ✅ |

**Status**: ✅ Well within $300/month budget

---

## 📊 Architecture

```
┌──────────────────────────────────────────────────────────┐
│                  GKE CLUSTER (Cloud)                     │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Namespace: mlflow                                 │ │
│  │                                                    │ │
│  │  ┌──────────────┐  ┌──────────────┐              │ │
│  │  │   MLFlow     │  │  PostgreSQL  │              │ │
│  │  │   Server     │  │  (Reserved)  │              │ │
│  │  │  (SQLite)    │  │              │              │ │
│  │  └──────┬───────┘  └──────────────┘              │ │
│  │         │                                         │ │
│  │         │ Logs to                                 │ │
│  │         ↓                                         │ │
│  │  ┌────────────────────────────────────┐          │ │
│  │  │  GCS: intellirag-mlflow-artifacts  │          │ │
│  │  │  - Model artifacts                 │          │ │
│  │  │  - Experiment data                 │          │ │
│  │  │  - Drift reports (HTML)            │          │ │
│  │  └────────────────────────────────────┘          │ │
│  │                                                   │ │
│  │  ┌────────────────────────────────────┐          │ │
│  │  │  CronJob: drift-monitoring         │          │ │
│  │  │  Schedule: 0 4 * * *               │          │ │
│  │  └────────────────────────────────────┘          │ │
│  └────────────────────────────────────────────────────┘ │
│                                                          │
│  ┌────────────────────────────────────────────────────┐ │
│  │  Namespace: observability                          │ │
│  │                                                    │ │
│  │  ┌──────────────┐                                 │ │
│  │  │   Grafana    │◄── MLOps Dashboard              │ │
│  │  │              │    (mlops-metrics.json)         │ │
│  │  └──────────────┘                                 │ │
│  └────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────┘

External Access:
• https://mlflow.blockchainradar.xyz (pending DNS)
• https://grafana.blockchainradar.xyz (MLOps dashboard)
```

---

## 🎯 Success Metrics

- ✅ MLFlow tracking server deployed and running
- ✅ Backend store configured (SQLite + PVC)
- ✅ Artifact store connected (GCS)
- ✅ Model registration script ready
- ✅ Drift monitoring implemented
- ✅ Grafana dashboard created
- ⏳ DNS configuration pending (user action)
- ⏳ Model registration pending (after DNS)
- ⏳ Dashboard deployment pending (after DNS)

---

## 🔄 Rollback Instructions

If issues occur, rollback Phase 4 changes:

```bash
# Uninstall MLFlow
helm uninstall mlflow -n mlflow

# Delete namespace (keeps PostgreSQL for future use)
# kubectl delete namespace mlflow  # Optional

# Delete GCS bucket
gsutil rm -r gs://intellirag-mlflow-artifacts

# Remove Python package
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG
uv remove evidently

# Git reset (if needed)
git checkout -- .
```

---

## 📝 Known Issues

### 1. PostgreSQL Not Used
**Issue**: MLFlow using SQLite instead of PostgreSQL
**Reason**: Missing `psycopg2` in MLFlow Docker image
**Impact**: Limited to single-instance deployment
**Workaround**: SQLite with persistent volume (current)
**Future Fix**: Create custom MLFlow image with psycopg2

### 2. Model Registration Pending
**Issue**: Cannot register models yet
**Reason**: DNS not configured
**Resolution**: User must add DNS A record
**Timeline**: 5-10 minutes after DNS propagation

### 3. Drift Monitoring Not Active
**Issue**: CronJob not deployed
**Reason**: Requires Docker image with MLOps code
**Resolution**: Build and push new image, then deploy CronJob
**Timeline**: After model registration

---

## 🎓 Lessons Learned

1. **Helm for All Deployments**: Following the "Helm for everything" rule simplified management
2. **Check Dependencies**: Should have verified psycopg2 availability before PostgreSQL setup
3. **SQLite is Sufficient**: For single-instance MLFlow, SQLite + PVC works well
4. **Persistent Storage Critical**: PVC ensures data survives pod restarts
5. **DNS Setup Blocks Access**: Certificate issuance requires DNS to be configured first

---

## 📚 References

- [MLFlow Documentation](https://mlflow.org/docs/latest/index.html)
- [Evidently Documentation](https://docs.evidentlyai.com/)
- [Helm Charts Best Practices](https://helm.sh/docs/chart_best_practices/)
- [GKE Workload Identity](https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity)

---

**Next Phase**: CI/CD Pipeline (Phase 5)
**Status**: Ready to proceed after Phase 4 verification
**Estimated Duration**: 2-3 days

