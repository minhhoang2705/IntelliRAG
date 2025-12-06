# Phase 4: MLOps Pipeline (Simplified)

**Duration**: 3-4 days
**Status**: Active
**Dependencies**: Phase 0-3 (Infrastructure, Application, Model Serving, Production Hardening)
**Last Updated**: 2025-11-27

---

## 📋 Overview

This phase establishes a focused MLOps pipeline for model lifecycle management and monitoring. We'll deploy MLFlow for model tracking and registry, set up Evidently for data drift monitoring, create automated deployment webhooks, and build comprehensive dashboards.

**Key Components** (Simplified):
- **MLFlow**: Model tracking, versioning, and registry
- **Evidently**: Data drift detection and model performance monitoring
- **Model Deployment Webhooks**: Automated KServe deployments from MLFlow registry
- **Grafana Dashboards**: Enhanced visualizations for MLOps metrics

**Removed from Original Plan**:
- ~~RAGAS evaluation~~ (Removed per user decision)

---

## 🎯 Objectives

### Primary Goals

1. ✅ Deploy MLFlow tracking server to GKE
2. ✅ Configure in-cluster PostgreSQL for MLFlow backend
3. ✅ Set up GCS artifact storage for MLFlow
4. ✅ Register existing models (vLLM, Embedding) in MLFlow
5. ✅ Implement Evidently data drift monitoring
6. ✅ Create webhook for MLFlow → KServe deployments
7. ✅ Build MLOps dashboards in Grafana

### Success Criteria

- ✅ MLFlow UI accessible at https://mlflow.blockchainradar.xyz
- ✅ Models registered with versioning and metadata
- ✅ Data drift reports generated daily
- ✅ Automated deployment from MLFlow → KServe working
- ✅ MLOps metrics visible in Grafana
- ✅ Complete documentation

---

## 🛠️ Prerequisites

✅ **All prerequisites met:**
- Phase 0-3 completed (GKE, app, models, security)
- GKE cluster operational
- Observability stack deployed (Prometheus, Grafana)
- GCS bucket available: `intellirag-mlflow-artifacts` (to be created)

---

## 📦 Implementation Plan

### Task 1: Deploy PostgreSQL for MLFlow (In-Cluster)

**Duration**: 30 minutes

#### 1.1 Install PostgreSQL via Helm

```bash
# Add Bitnami Helm repo
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Create namespace
kubectl create namespace mlflow

# Install PostgreSQL
helm install postgresql bitnami/postgresql \
  --namespace mlflow \
  --set auth.username=mlflow \
  --set auth.password=mlflow \
  --set auth.database=mlflow \
  --set primary.persistence.size=20Gi \
  --set primary.resources.requests.cpu=500m \
  --set primary.resources.requests.memory=512Mi
```

#### 1.2 Verify PostgreSQL Installation

```bash
# Check pod status
kubectl get pods -n mlflow

# Get PostgreSQL connection details
export POSTGRES_PASSWORD=$(kubectl get secret --namespace mlflow postgresql -o jsonpath="{.data.postgres-password}" | base64 -d)

# Test connection
kubectl run postgresql-client --rm --tty -i --restart='Never' \
  --namespace mlflow \
  --image docker.io/bitnami/postgresql:14 \
  --env="PGPASSWORD=$POSTGRES_PASSWORD" \
  --command -- psql --host postgresql.mlflow.svc.cluster.local -U mlflow -d mlflow -c '\l'
```

**Expected Output**:
```
List of databases
   Name    |  Owner
-----------+----------
 mlflow    | mlflow
```

---

### Task 2: Create GCS Bucket for MLFlow Artifacts

**Duration**: 15 minutes

```bash
# Create bucket
gsutil mb -p intellirag-aide1-capstone \
  -c STANDARD \
  -l asia-southeast1 \
  gs://intellirag-mlflow-artifacts

# Set lifecycle policy (delete artifacts older than 90 days)
cat > mlflow-lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"age": 90}
    }]
  }
}
EOF

gsutil lifecycle set mlflow-lifecycle.json gs://intellirag-mlflow-artifacts

# Grant access to workload identity service account
gsutil iam ch serviceAccount:intellirag-cluster-workload-sa@intellirag-aide1-capstone.iam.gserviceaccount.com:objectAdmin \
  gs://intellirag-mlflow-artifacts

# Verify
gsutil ls -L -b gs://intellirag-mlflow-artifacts
```

---

### Task 3: Deploy MLFlow Tracking Server

**Duration**: 1 hour

#### 3.1 Create MLFlow Deployment Manifests

**File**: `kubernetes/mlflow/namespace.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mlflow
  labels:
    name: mlflow
```

**File**: `kubernetes/mlflow/serviceaccount.yaml`
```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mlflow-sa
  namespace: mlflow
  annotations:
    iam.gke.io/gcp-service-account: intellirag-cluster-workload-sa@intellirag-aide1-capstone.iam.gserviceaccount.com
```

**File**: `kubernetes/mlflow/deployment.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-server
  namespace: mlflow
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mlflow-server
  template:
    metadata:
      labels:
        app: mlflow-server
    spec:
      serviceAccountName: mlflow-sa
      containers:
      - name: mlflow
        image: ghcr.io/mlflow/mlflow:v2.9.2
        args:
        - server
        - --host=0.0.0.0
        - --port=5000
        - --backend-store-uri=postgresql://mlflow:mlflow@postgresql.mlflow.svc.cluster.local:5432/mlflow
        - --default-artifact-root=gs://intellirag-mlflow-artifacts
        - --serve-artifacts
        ports:
        - containerPort: 5000
          name: http
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 1000m
            memory: 2Gi
        livenessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 5000
          initialDelaySeconds: 10
          periodSeconds: 5
```

**File**: `kubernetes/mlflow/service.yaml`
```yaml
apiVersion: v1
kind: Service
metadata:
  name: mlflow-server
  namespace: mlflow
spec:
  type: ClusterIP
  ports:
  - port: 5000
    targetPort: 5000
    name: http
  selector:
    app: mlflow-server
```

**File**: `kubernetes/mlflow/ingress.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: mlflow-ingress
  namespace: mlflow
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "100m"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - mlflow.blockchainradar.xyz
    secretName: mlflow-tls
  rules:
  - host: mlflow.blockchainradar.xyz
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: mlflow-server
            port:
              number: 5000
```

#### 3.2 Deploy MLFlow

```bash
# Apply manifests
kubectl apply -f kubernetes/mlflow/namespace.yaml
kubectl apply -f kubernetes/mlflow/serviceaccount.yaml
kubectl apply -f kubernetes/mlflow/deployment.yaml
kubectl apply -f kubernetes/mlflow/service.yaml
kubectl apply -f kubernetes/mlflow/ingress.yaml

# Verify deployment
kubectl get pods -n mlflow
kubectl logs -n mlflow -l app=mlflow-server

# Wait for certificate
kubectl get certificate -n mlflow -w
```

#### 3.3 Add DNS Record

```
Type: A
Host: mlflow
Domain: blockchainradar.xyz
Value: 34.143.244.90
TTL: 300
```

#### 3.4 Access MLFlow UI

```
URL: https://mlflow.blockchainradar.xyz
```

---

### Task 4: Register Models in MLFlow

**Duration**: 30 minutes

**File**: `mlops/register_models.py`
```python
"""
Register IntelliRAG models in MLFlow registry.
"""
import mlflow
from mlflow.tracking import MlflowClient
import os

# Configure MLFlow tracking URI
MLFLOW_TRACKING_URI = os.getenv(
    "MLFLOW_TRACKING_URI",
    "https://mlflow.blockchainradar.xyz"
)
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

def register_llm_model():
    """Register vLLM Qwen3-0.6B model."""
    client = MlflowClient()

    # Create registered model
    try:
        client.create_registered_model(
            name="qwen3-0.6b-instruct",
            description="Qwen3-0.6B-Instruct LLM for RAG generation",
            tags={
                "task": "text-generation",
                "framework": "vllm",
                "model_size": "0.6B",
                "use_case": "rag",
                "deployment": "kserve-local-gpu"
            }
        )
        print("✅ Created model: qwen3-0.6b-instruct")
    except Exception as e:
        print(f"Model already exists: {e}")

    # Register version
    model_uri = "models:/qwen3-0.6b-instruct"

    with mlflow.start_run(run_name="qwen3-0.6b-v1.0.0") as run:
        # Log model metadata
        mlflow.log_param("model_name", "Qwen/Qwen3-0.6B")
        mlflow.log_param("framework", "vLLM")
        mlflow.log_param("endpoint", "https://llm.blockchainradar.xyz/v1")
        mlflow.log_param("max_tokens", 8192)
        mlflow.log_param("deployment_type", "kserve")
        mlflow.log_param("gpu", "NVIDIA RTX 4070Ti 12GB")

        # Log performance metrics
        mlflow.log_metric("throughput_tps", 793)
        mlflow.log_metric("p99_latency_ms", 80)
        mlflow.log_metric("gpu_utilization", 0.95)

        # Register model version
        mv = client.create_model_version(
            name="qwen3-0.6b-instruct",
            source=f"runs:/{run.info.run_id}",
            tags={
                "version": "v1.0.0",
                "deployment": "production",
                "endpoint": "https://llm.blockchainradar.xyz/v1"
            }
        )

        print(f"✅ Registered model version: {mv.version}")

        # Transition to production
        client.transition_model_version_stage(
            name="qwen3-0.6b-instruct",
            version=mv.version,
            stage="Production"
        )
        print(f"✅ Transitioned to Production stage")

def register_embedding_model():
    """Register EmbeddingGemma-300m model."""
    client = MlflowClient()

    # Create registered model
    try:
        client.create_registered_model(
            name="embeddinggemma-300m",
            description="Google EmbeddingGemma-300M for document embeddings",
            tags={
                "task": "embedding",
                "framework": "sentence-transformers",
                "model_size": "300M",
                "embedding_dim": "768",
                "deployment": "kserve-local-gpu"
            }
        )
        print("✅ Created model: embeddinggemma-300m")
    except Exception as e:
        print(f"Model already exists: {e}")

    # Register version
    with mlflow.start_run(run_name="embeddinggemma-300m-v1.0.0") as run:
        # Log model metadata
        mlflow.log_param("model_name", "google/embeddinggemma-300m")
        mlflow.log_param("framework", "KServe")
        mlflow.log_param("endpoint", "https://embed.blockchainradar.xyz")
        mlflow.log_param("embedding_dimension", 768)
        mlflow.log_param("max_batch_size", 16)
        mlflow.log_param("device", "cuda")

        # Log performance metrics
        mlflow.log_metric("avg_latency_ms", 287)
        mlflow.log_metric("batch_throughput", 128)

        # Register model version
        mv = client.create_model_version(
            name="embeddinggemma-300m",
            source=f"runs:/{run.info.run_id}",
            tags={
                "version": "v1.0.0",
                "deployment": "production",
                "endpoint": "https://embed.blockchainradar.xyz"
            }
        )

        print(f"✅ Registered model version: {mv.version}")

        # Transition to production
        client.transition_model_version_stage(
            name="embeddinggemma-300m",
            version=mv.version,
            stage="Production"
        )
        print(f"✅ Transitioned to Production stage")

if __name__ == "__main__":
    print("🚀 Registering IntelliRAG models in MLFlow...")
    print(f"MLFlow Tracking URI: {MLFLOW_TRACKING_URI}\n")

    register_llm_model()
    print()
    register_embedding_model()

    print("\n✅ All models registered successfully!")
    print(f"View models at: {MLFLOW_TRACKING_URI}/#/models")
```

**Run registration:**
```bash
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG
python mlops/register_models.py
```

---

### Task 5: Evidently Data Drift Monitoring

**Duration**: 1.5 hours

#### 5.1 Install Evidently

```bash
uv add evidently
```

#### 5.2 Create Drift Detection Service

**File**: `mlops/monitoring/drift_detector.py`
```python
"""
Data drift monitoring using Evidently.
Tracks input distribution shifts and model performance degradation.
"""
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, DataQualityPreset
import pandas as pd
import mlflow
from typing import List, Dict
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class DriftDetector:
    def __init__(self, mlflow_tracking_uri: str):
        self.mlflow_tracking_uri = mlflow_tracking_uri
        mlflow.set_tracking_uri(mlflow_tracking_uri)

    def detect_drift(
        self,
        reference_data: pd.DataFrame,
        current_data: pd.DataFrame,
        column_mapping: ColumnMapping
    ) -> Dict:
        """
        Detect data drift between reference and current data.

        Args:
            reference_data: Historical/baseline data
            current_data: Recent data
            column_mapping: Evidently column mapping

        Returns:
            Dict with drift detection results
        """
        # Create Evidently report
        report = Report(metrics=[
            DataDriftPreset(),
            DataQualityPreset()
        ])

        report.run(
            reference_data=reference_data,
            current_data=current_data,
            column_mapping=column_mapping
        )

        # Extract results
        results = report.as_dict()

        # Log to MLFlow
        with mlflow.start_run(run_name=f"drift-detection-{datetime.now().isoformat()}"):
            mlflow.log_param("reference_size", len(reference_data))
            mlflow.log_param("current_size", len(current_data))

            # Log drift metrics
            drift_share = results["metrics"][0]["result"]["drift_share"]
            mlflow.log_metric("drift_share", drift_share)

            # Save HTML report
            report_path = f"drift_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
            report.save_html(report_path)
            mlflow.log_artifact(report_path)

        logger.info(f"Drift detection complete. Drift share: {drift_share:.2%}")

        return results

    def monitor_query_patterns(
        self,
        lookback_days: int = 7
    ):
        """
        Monitor drift in query patterns over time.

        Compares last 24 hours against previous 7 days baseline.
        """
        # This would integrate with your query logs
        # For now, placeholder structure

        logger.info(f"Monitoring query patterns (lookback: {lookback_days} days)")

        # TODO: Fetch query data from logs/database
        # reference_queries = fetch_queries(start_date - lookback_days, start_date)
        # current_queries = fetch_queries(start_date, now)

        # For demo purposes:
        reference_data = pd.DataFrame({
            "query_length": [50, 60, 55, 70, 45],
            "num_keywords": [3, 4, 3, 5, 2]
        })

        current_data = pd.DataFrame({
            "query_length": [80, 90, 85, 95, 75],
            "num_keywords": [5, 6, 5, 7, 4]
        })

        column_mapping = ColumnMapping()
        column_mapping.numerical_features = ["query_length", "num_keywords"]

        return self.detect_drift(reference_data, current_data, column_mapping)
```

#### 5.3 Create Drift Monitoring CronJob

**File**: `kubernetes/mlops/drift-monitoring-cronjob.yaml`
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: drift-monitoring
  namespace: mlflow
spec:
  schedule: "0 4 * * *"  # Daily at 4 AM
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: mlflow-sa
          restartPolicy: OnFailure
          containers:
          - name: drift-monitor
            image: gcr.io/intellirag-aide1-capstone/intellirag-api:latest
            command:
            - python
            - -c
            - |
              from mlops.monitoring.drift_detector import DriftDetector
              detector = DriftDetector("http://mlflow-server.mlflow.svc.cluster.local:5000")
              detector.monitor_query_patterns(lookback_days=7)
            env:
            - name: MLFLOW_TRACKING_URI
              value: "http://mlflow-server.mlflow.svc.cluster.local:5000"
            resources:
              requests:
                cpu: 500m
                memory: 1Gi
              limits:
                cpu: 1000m
                memory: 2Gi
```

---

### Task 6: MLOps Dashboards in Grafana

**Duration**: 1 hour

#### 6.1 Create MLOps Dashboard

**File**: `observability/grafana/provisioning/dashboards/json/mlops-metrics.json`

```json
{
  "dashboard": {
    "title": "MLOps Model Performance",
    "uid": "mlops-dashboard",
    "version": 1,
    "panels": [
      {
        "title": "Model Versions",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 0, "y": 0},
        "targets": [{
          "expr": "count(mlflow_model_versions)",
          "legendFormat": "Total Versions"
        }]
      },
      {
        "title": "Active Models (Production)",
        "type": "stat",
        "gridPos": {"h": 4, "w": 6, "x": 6, "y": 0},
        "targets": [{
          "expr": "count(mlflow_model_versions{stage='Production'})",
          "legendFormat": "Production Models"
        }]
      },
      {
        "title": "Data Drift Score",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 4},
        "targets": [{
          "expr": "evidently_drift_share",
          "legendFormat": "Drift Share"
        }],
        "alert": {
          "name": "High Data Drift",
          "conditions": [{
            "evaluator": {
              "params": [0.3],
              "type": "gt"
            },
            "operator": {"type": "and"},
            "query": {"params": ["A", "5m", "now"]},
            "reducer": {"type": "avg"}
          }]
        }
      },
      {
        "title": "Model Inference Latency (P95)",
        "type": "graph",
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 4},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{endpoint='/api/v1/query'}[5m]))",
            "legendFormat": "RAG Query P95"
          },
          {
            "expr": "histogram_quantile(0.95, rate(vllm_request_duration_seconds_bucket[5m]))",
            "legendFormat": "vLLM Inference P95"
          }
        ]
      }
    ]
  }
}
```

#### 6.2 Configure Dashboard in Grafana

```bash
# Add dashboard via ConfigMap
kubectl create configmap mlops-dashboard \
  --from-file=observability/grafana/provisioning/dashboards/json/mlops-metrics.json \
  -n observability

# Update Grafana to load new dashboard
kubectl rollout restart deployment prometheus-grafana -n observability
```

---

### Task 7: Model Deployment Webhook (Optional - Advanced)

**Duration**: 1 hour

**File**: `mlops/webhooks/mlflow_webhook_handler.py`
```python
"""
MLFlow webhook handler for model stage transitions.
Triggers KServe deployment when model is promoted to Production.
"""
from fastapi import FastAPI, Request, HTTPException
import httpx
import logging

app = FastAPI()
logger = logging.getLogger(__name__)

KSERVE_WEBHOOK_URL = "http://LOCAL_SERVER_IP:5001/deploy"

@app.post("/mlflow/webhook")
async def handle_mlflow_webhook(request: Request):
    """
    Handle MLFlow model registry webhook.
    Triggered when model stage changes to 'Production'.
    """
    payload = await request.json()

    # Extract event information
    event_type = payload.get("event")
    model_name = payload.get("model_name")
    model_version = payload.get("model_version")
    new_stage = payload.get("to_stage")

    logger.info(f"Received webhook: {event_type} for {model_name} v{model_version}")

    # Only deploy when model is promoted to Production
    if event_type == "MODEL_VERSION_TRANSITIONED_STAGE" and new_stage == "Production":
        try:
            # Trigger KServe deployment
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    KSERVE_WEBHOOK_URL,
                    json={
                        "model_name": model_name,
                        "model_version": model_version,
                        "model_uri": payload.get("model_uri"),
                        "action": "deploy"
                    },
                    timeout=300.0
                )
                response.raise_for_status()

            logger.info(f"Successfully triggered deployment for {model_name} v{model_version}")
            return {"status": "success", "message": "Deployment triggered"}

        except Exception as e:
            logger.error(f"Failed to trigger deployment: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    return {"status": "ignored", "message": "No action taken"}
```

---

## ✅ Deliverables Checklist

- [ ] PostgreSQL deployed in-cluster
- [ ] GCS bucket for MLFlow artifacts created
- [ ] MLFlow tracking server deployed on GKE
- [ ] MLFlow UI accessible via HTTPS (mlflow.blockchainradar.xyz)
- [ ] LLM model (Qwen3-0.6B) registered in MLFlow
- [ ] Embedding model (EmbeddingGemma-300m) registered in MLFlow
- [ ] Evidently drift detection implemented
- [ ] Daily drift monitoring CronJob scheduled
- [ ] MLOps dashboard added to Grafana
- [ ] Documentation complete

---

## 📊 Architecture Summary

```
┌─────────────────────────────────────────────────────┐
│              GKE CLUSTER (Cloud)                    │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │   MLFlow     │  │  PostgreSQL  │  │ Grafana  │ │
│  │   Server     │──│  (Backend)   │  │Dashboard │ │
│  │              │  │              │  │          │ │
│  └──────┬───────┘  └──────────────┘  └──────────┘ │
│         │                                          │
│         │ Logs experiments & models                │
│         ↓                                          │
│  ┌──────────────────────────────────────────────┐ │
│  │  GCS Bucket: intellirag-mlflow-artifacts     │ │
│  │  - Model artifacts                           │ │
│  │  - Experiment data                           │ │
│  │  - Drift reports                             │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
│  ┌──────────────────────────────────────────────┐ │
│  │  CronJob: Drift Monitoring (Daily 4 AM)     │ │
│  │  - Evidently drift detection                │ │
│  │  - Reports logged to MLFlow                 │ │
│  └──────────────────────────────────────────────┘ │
│                                                     │
└─────────────────────────────────────────────────────┘

External Access:
• https://mlflow.blockchainradar.xyz (MLFlow UI)
• https://grafana.blockchainradar.xyz (Dashboards)
```

---

## 💰 Cost Breakdown

| Component | Monthly Cost |
|-----------|-------------|
| PostgreSQL (20GB storage) | ~$5 |
| MLFlow pod (500m CPU, 1GB RAM) | ~$10 |
| GCS artifacts (~10GB) | ~$0.26 |
| Drift monitoring CronJob | ~$2 |
| **Total Phase 4 Addition** | **~$17** |
| **New Total Cost** | **~$131/month** ✅ |

**Budget Status**: ✅ Well under $300/month limit

---

## 📝 Next Steps

After Phase 4 completion:
- **Phase 5**: CI/CD Pipeline automation
- **Future Enhancements**:
  - Add RAGAS evaluation (if needed)
  - Implement A/B testing framework
  - Add model retraining pipelines

---

**Phase Status**: Ready to Start
**Duration Estimate**: 3-4 days
**Last Updated**: 2025-11-27
