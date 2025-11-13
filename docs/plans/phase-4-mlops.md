# Phase 4: MLOps Pipeline

**Duration**: 5-7 days
**Status**: Pending
**Dependencies**: Phase 0-3 (Infrastructure, Application, Model Serving, Production Hardening)

---

## 📋 Overview

This phase establishes a comprehensive MLOps pipeline for model lifecycle management. We'll deploy MLFlow for model tracking and registry, implement automated RAG evaluation using RAGAS metrics, set up data drift monitoring with Evidently, and create webhooks for automated model deployment to KServe.

**Key Components**:
- **MLFlow**: Model tracking, versioning, and registry
- **RAGAS**: Automated RAG evaluation (faithfulness, relevance, context precision)
- **Evidently**: Data drift detection and model performance monitoring
- **Model Deployment Webhooks**: Automated KServe deployments from MLFlow registry
- **Experiment Tracking**: Centralized logging of model experiments

---

## 🎯 Objectives

### Primary Goals
1. Deploy MLFlow tracking server to GKE
2. Configure model registry with GCS artifact storage
3. Implement RAGAS-based automated evaluation pipeline
4. Set up Evidently for data drift monitoring
5. Create webhook for model deployment from MLFlow to KServe
6. Establish experiment tracking for hyperparameter tuning
7. Build dashboards for model performance monitoring

### Success Criteria
- ✅ MLFlow UI accessible and operational
- ✅ Models registered with versioning and metadata
- ✅ RAGAS metrics computed automatically for each model update
- ✅ Data drift reports generated daily
- ✅ Automated deployment from MLFlow → KServe working
- ✅ Experiment tracking integrated with training pipelines
- ✅ Model performance dashboards in Grafana

---

## 🛠️ Prerequisites

- Phase 0-3 completed (GKE, app, models, security)
- PostgreSQL or MySQL database for MLFlow backend (can use Cloud SQL)
- GCS bucket for MLFlow artifacts
- Sufficient compute for evaluation workloads

---

## 📦 Task 1: Deploy MLFlow Tracking Server

### 1.1 Create PostgreSQL Database for MLFlow

**Option A: Cloud SQL (Recommended for production)**
```bash
# Create Cloud SQL PostgreSQL instance
gcloud sql instances create mlflow-db \
  --database-version=POSTGRES_14 \
  --tier=db-f1-micro \
  --region=us-central1 \
  --root-password=STRONG_PASSWORD \
  --storage-type=SSD \
  --storage-size=20GB

# Create database
gcloud sql databases create mlflow --instance=mlflow-db

# Create user
gcloud sql users create mlflow \
  --instance=mlflow-db \
  --password=STRONG_PASSWORD

# Get connection name
gcloud sql instances describe mlflow-db --format='get(connectionName)'
# Output: PROJECT_ID:us-central1:mlflow-db
```

**Option B: PostgreSQL in Kubernetes (Development)**
```bash
# Add Bitnami Helm repo
helm repo add bitnami https://charts.bitnami.com/bitnami
helm repo update

# Install PostgreSQL
helm install postgresql bitnami/postgresql \
  --namespace mlflow \
  --create-namespace \
  --set auth.username=mlflow \
  --set auth.password=mlflow \
  --set auth.database=mlflow \
  --set primary.persistence.size=20Gi
```

### 1.2 Create GCS Bucket for MLFlow Artifacts

```bash
# Create bucket
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l us-central1 gs://intellirag-mlflow-artifacts

# Set lifecycle (delete artifacts older than 90 days)
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

# Grant access to Workload Identity SA
gsutil iam ch serviceAccount:intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://intellirag-mlflow-artifacts
```

### 1.3 Create MLFlow Deployment

**File**: `kubernetes/mlflow/deployment.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: mlflow
  labels:
    name: mlflow
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: mlflow-sa
  namespace: mlflow
  annotations:
    iam.gke.io/gcp-service-account: intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-server
  namespace: mlflow
spec:
  replicas: 2
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
        - --backend-store-uri=$(BACKEND_STORE_URI)
        - --default-artifact-root=$(ARTIFACT_ROOT)
        - --serve-artifacts
        env:
        - name: BACKEND_STORE_URI
          valueFrom:
            secretKeyRef:
              name: mlflow-db-secret
              key: connection-string
        - name: ARTIFACT_ROOT
          value: "gs://intellirag-mlflow-artifacts"
        - name: GOOGLE_APPLICATION_CREDENTIALS
          value: /var/secrets/gcp/key.json
        ports:
        - containerPort: 5000
          name: http
        resources:
          requests:
            cpu: 500m
            memory: 1Gi
          limits:
            cpu: 2000m
            memory: 4Gi
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
---
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
---
apiVersion: v1
kind: Secret
metadata:
  name: mlflow-db-secret
  namespace: mlflow
type: Opaque
stringData:
  # For Cloud SQL (use Cloud SQL Proxy sidecar)
  connection-string: "postgresql://mlflow:PASSWORD@127.0.0.1:5432/mlflow"
  # For in-cluster PostgreSQL
  # connection-string: "postgresql://mlflow:mlflow@postgresql.mlflow.svc.cluster.local:5432/mlflow"
```

### 1.4 Deploy MLFlow with Cloud SQL Proxy (if using Cloud SQL)

**File**: `kubernetes/mlflow/deployment-with-proxy.yaml`
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-server
  namespace: mlflow
spec:
  replicas: 2
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
      # MLFlow container
      - name: mlflow
        image: ghcr.io/mlflow/mlflow:v2.9.2
        args:
        - server
        - --host=0.0.0.0
        - --port=5000
        - --backend-store-uri=postgresql://mlflow:PASSWORD@127.0.0.1:5432/mlflow
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
            cpu: 2000m
            memory: 4Gi
      # Cloud SQL Proxy sidecar
      - name: cloud-sql-proxy
        image: gcr.io/cloud-sql-connectors/cloud-sql-proxy:2.8.0
        args:
        - "--structured-logs"
        - "--port=5432"
        - "PROJECT_ID:us-central1:mlflow-db"
        securityContext:
          runAsNonRoot: true
        resources:
          requests:
            memory: "256Mi"
            cpu: "100m"
          limits:
            memory: "512Mi"
            cpu: "200m"
```

```bash
# Apply MLFlow deployment
kubectl apply -f kubernetes/mlflow/deployment.yaml

# Verify deployment
kubectl get pods -n mlflow
kubectl logs -n mlflow -l app=mlflow-server

# Port-forward to access UI
kubectl port-forward -n mlflow svc/mlflow-server 5000:5000

# Visit http://localhost:5000
```

### 1.5 Expose MLFlow via Ingress

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
    - mlflow.intellirag.example.com
    secretName: mlflow-tls
  rules:
  - host: mlflow.intellirag.example.com
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

```bash
# Apply Ingress
kubectl apply -f kubernetes/mlflow/ingress.yaml

# Wait for certificate
kubectl get certificate -n mlflow -w

# Access MLFlow UI
# https://mlflow.intellirag.example.com
```

---

## 📦 Task 2: Model Registry and Versioning

### 2.1 Register Models in MLFlow

**File**: `mlops/register_models.py`
```python
"""
Register models in MLFlow registry.
Manual registration for models deployed via KServe.
"""
import mlflow
from mlflow.tracking import MlflowClient

# Configure MLFlow tracking URI
MLFLOW_TRACKING_URI = "https://mlflow.intellirag.example.com"
mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)

def register_llm_model():
    """Register LLM model in MLFlow."""
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
                "use_case": "rag"
            }
        )
    except Exception as e:
        print(f"Model already exists: {e}")

    # Register version (model artifacts in GCS)
    model_uri = "gs://intellirag-models/Qwen3-0.6B/"

    mv = client.create_model_version(
        name="qwen3-0.6b-instruct",
        source=model_uri,
        run_id=None,  # Manual registration
        tags={
            "deployment": "kserve",
            "endpoint": "https://llm.intellirag.example.com/v1",
            "version": "v1.0.0"
        }
    )

    print(f"Registered model version: {mv.version}")

    # Transition to production
    client.transition_model_version_stage(
        name="qwen3-0.6b-instruct",
        version=mv.version,
        stage="Production"
    )

def register_embedding_model():
    """Register embedding model in MLFlow."""
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
                "embedding_dim": "300"
            }
        )
    except Exception as e:
        print(f"Model already exists: {e}")

    # Register version
    model_uri = "gs://intellirag-models/embeddinggemma-300m/"

    mv = client.create_model_version(
        name="embeddinggemma-300m",
        source=model_uri,
        run_id=None,
        tags={
            "deployment": "kserve",
            "endpoint": "https://embeddings.intellirag.example.com",
            "version": "v1.0.0"
        }
    )

    print(f"Registered model version: {mv.version}")

    # Transition to production
    client.transition_model_version_stage(
        name="embeddinggemma-300m",
        version=mv.version,
        stage="Production"
    )

if __name__ == "__main__":
    register_llm_model()
    register_embedding_model()
    print("Models registered successfully")
```

```bash
# Run registration script
python mlops/register_models.py

# Verify in MLFlow UI
# Visit https://mlflow.intellirag.example.com/#/models
```

### 2.2 Integrate Model Tracking in Application

**File**: `app/core/mlflow_client.py`
```python
"""MLFlow client for logging RAG performance metrics."""
import mlflow
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class MLFlowClient:
    def __init__(self):
        mlflow.set_tracking_uri(settings.MLFLOW_TRACKING_URI)
        self.experiment_name = "intellirag-rag-queries"

        # Create experiment if it doesn't exist
        try:
            mlflow.create_experiment(self.experiment_name)
        except:
            pass

        mlflow.set_experiment(self.experiment_name)

    def log_query_metrics(
        self,
        query: str,
        response: str,
        retrieval_time: float,
        generation_time: float,
        total_time: float,
        num_docs_retrieved: int,
        avg_relevance_score: float
    ):
        """Log metrics for a single RAG query."""
        with mlflow.start_run():
            # Log parameters
            mlflow.log_param("query_length", len(query))
            mlflow.log_param("response_length", len(response))
            mlflow.log_param("num_docs_retrieved", num_docs_retrieved)

            # Log metrics
            mlflow.log_metric("retrieval_time_seconds", retrieval_time)
            mlflow.log_metric("generation_time_seconds", generation_time)
            mlflow.log_metric("total_time_seconds", total_time)
            mlflow.log_metric("avg_relevance_score", avg_relevance_score)

            # Log text artifacts
            mlflow.log_text(query, "query.txt")
            mlflow.log_text(response, "response.txt")

# Global client instance
mlflow_client = MLFlowClient()
```

---

## 📦 Task 3: Automated RAG Evaluation with RAGAS

### 3.1 Install RAGAS Dependencies

```bash
pip install ragas datasets langchain
```

### 3.2 Create RAGAS Evaluation Pipeline

**File**: `mlops/evaluation/ragas_eval.py`
```python
"""
Automated RAG evaluation using RAGAS metrics.
"""
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall
)
from datasets import Dataset
import pandas as pd
import mlflow
import asyncio
from typing import List, Dict
import httpx

class RAGASEvaluator:
    def __init__(
        self,
        mlflow_tracking_uri: str,
        rag_endpoint: str,
        llm_endpoint: str
    ):
        self.rag_endpoint = rag_endpoint
        self.llm_endpoint = llm_endpoint
        mlflow.set_tracking_uri(mlflow_tracking_uri)

    async def run_rag_query(self, query: str) -> Dict:
        """Run a query through the RAG system."""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.rag_endpoint}/api/v1/query",
                json={"query": query}
            )
            response.raise_for_status()
            return response.json()

    def prepare_evaluation_dataset(
        self,
        test_queries: List[str],
        ground_truths: List[str]
    ) -> Dataset:
        """
        Prepare dataset for RAGAS evaluation.

        Args:
            test_queries: List of test questions
            ground_truths: List of expected answers

        Returns:
            Dataset with required fields for RAGAS
        """
        data = {
            "question": [],
            "answer": [],
            "contexts": [],
            "ground_truth": []
        }

        for query, truth in zip(test_queries, ground_truths):
            # Run query through RAG system
            result = asyncio.run(self.run_rag_query(query))

            data["question"].append(query)
            data["answer"].append(result["answer"])
            data["contexts"].append(result.get("retrieved_contexts", []))
            data["ground_truth"].append(truth)

        return Dataset.from_dict(data)

    def evaluate(
        self,
        test_queries: List[str],
        ground_truths: List[str],
        experiment_name: str = "ragas-evaluation"
    ) -> pd.DataFrame:
        """
        Run RAGAS evaluation and log to MLFlow.

        Returns:
            DataFrame with evaluation metrics
        """
        mlflow.set_experiment(experiment_name)

        with mlflow.start_run():
            # Prepare dataset
            dataset = self.prepare_evaluation_dataset(test_queries, ground_truths)

            # Run RAGAS evaluation
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,
                    answer_relevancy,
                    context_precision,
                    context_recall
                ]
            )

            # Log metrics to MLFlow
            mlflow.log_metric("faithfulness", result["faithfulness"])
            mlflow.log_metric("answer_relevancy", result["answer_relevancy"])
            mlflow.log_metric("context_precision", result["context_precision"])
            mlflow.log_metric("context_recall", result["context_recall"])

            # Log dataset
            mlflow.log_text(dataset.to_pandas().to_csv(), "evaluation_dataset.csv")

            # Log results
            results_df = pd.DataFrame([result])
            mlflow.log_text(results_df.to_csv(), "ragas_results.csv")

            print(f"RAGAS Evaluation Results:\n{results_df}")

            return results_df

# Example usage
if __name__ == "__main__":
    evaluator = RAGASEvaluator(
        mlflow_tracking_uri="https://mlflow.intellirag.example.com",
        rag_endpoint="https://api.intellirag.example.com",
        llm_endpoint="https://llm.intellirag.example.com/v1"
    )

    # Test queries
    test_queries = [
        "What is retrieval-augmented generation?",
        "How does vLLM improve inference performance?",
        "What is PagedAttention?"
    ]

    ground_truths = [
        "RAG is a technique that combines retrieval with generation...",
        "vLLM uses PagedAttention and continuous batching...",
        "PagedAttention is a memory management technique..."
    ]

    results = evaluator.evaluate(test_queries, ground_truths)
```

### 3.3 Create Scheduled Evaluation Job

**File**: `kubernetes/mlops/ragas-evaluation-cronjob.yaml`
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: ragas-evaluation
  namespace: mlflow
spec:
  schedule: "0 3 * * 0"  # Weekly on Sunday at 3 AM
  successfulJobsHistoryLimit: 4
  failedJobsHistoryLimit: 2
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: mlflow-sa
          restartPolicy: OnFailure
          containers:
          - name: ragas-eval
            image: gcr.io/YOUR_PROJECT_ID/intellirag-api:latest
            command:
            - python
            - mlops/evaluation/ragas_eval.py
            env:
            - name: MLFLOW_TRACKING_URI
              value: "http://mlflow-server.mlflow.svc.cluster.local:5000"
            - name: RAG_ENDPOINT
              value: "http://intellirag-app.app.svc.cluster.local:8000"
            - name: LLM_ENDPOINT
              value: "https://llm.intellirag.example.com/v1"
            resources:
              requests:
                cpu: 1000m
                memory: 2Gi
              limits:
                cpu: 2000m
                memory: 4Gi
```

```bash
# Apply CronJob
kubectl apply -f kubernetes/mlops/ragas-evaluation-cronjob.yaml

# Manually trigger for testing
kubectl create job --from=cronjob/ragas-evaluation ragas-manual -n mlflow
kubectl logs -n mlflow -l job-name=ragas-manual -f
```

---

## 📦 Task 4: Data Drift Monitoring with Evidently

### 4.1 Implement Drift Detection

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
        with mlflow.start_run():
            mlflow.log_param("reference_size", len(reference_data))
            mlflow.log_param("current_size", len(current_data))

            # Log drift metrics
            drift_share = results["metrics"][0]["result"]["drift_share"]
            mlflow.log_metric("drift_share", drift_share)

            # Save HTML report
            report.save_html("drift_report.html")
            mlflow.log_artifact("drift_report.html")

        logger.info(f"Drift detection complete. Drift share: {drift_share:.2%}")

        return results

    def monitor_query_embeddings(
        self,
        reference_embeddings: List[List[float]],
        current_embeddings: List[List[float]]
    ):
        """Monitor drift in query embeddings."""
        # Convert to DataFrame
        ref_df = pd.DataFrame(reference_embeddings)
        curr_df = pd.DataFrame(current_embeddings)

        column_mapping = ColumnMapping()
        column_mapping.numerical_features = list(ref_df.columns)

        return self.detect_drift(ref_df, curr_df, column_mapping)

# Example usage
if __name__ == "__main__":
    detector = DriftDetector("https://mlflow.intellirag.example.com")

    # Load reference and current data
    # This would typically come from your query logs
    reference_data = pd.read_csv("reference_queries.csv")
    current_data = pd.read_csv("current_queries.csv")

    column_mapping = ColumnMapping()
    column_mapping.text_features = ["query"]

    results = detector.detect_drift(reference_data, current_data, column_mapping)
```

### 4.2 Create Drift Monitoring CronJob

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
            image: gcr.io/YOUR_PROJECT_ID/intellirag-api:latest
            command:
            - python
            - mlops/monitoring/drift_detector.py
            env:
            - name: MLFLOW_TRACKING_URI
              value: "http://mlflow-server.mlflow.svc.cluster.local:5000"
            - name: GCS_BUCKET
              value: "intellirag-data"
            resources:
              requests:
                cpu: 500m
                memory: 1Gi
              limits:
                cpu: 1000m
                memory: 2Gi
```

```bash
# Apply CronJob
kubectl apply -f kubernetes/mlops/drift-monitoring-cronjob.yaml
```

---

## 📦 Task 5: Model Deployment Webhook

### 5.1 Create Webhook Server (Already Exists)

The webhook server for deploying models from MLFlow to KServe was designed in the conversation history. Reference implementation at `local_server/kserve_deploy_webhook.py`.

### 5.2 Implement MLFlow Model Stage Transition Hook

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

## 📦 Task 6: Model Performance Dashboards

### 6.1 Create Grafana Dashboard for MLOps

**File**: `observability/grafana/provisioning/dashboards/json/mlops-metrics.json`
```json
{
  "dashboard": {
    "title": "MLOps Model Performance",
    "panels": [
      {
        "title": "RAGAS Metrics Over Time",
        "targets": [
          {
            "expr": "mlflow_metric{metric_name='faithfulness'}"
          },
          {
            "expr": "mlflow_metric{metric_name='answer_relevancy'}"
          },
          {
            "expr": "mlflow_metric{metric_name='context_precision'}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Data Drift Score",
        "targets": [
          {
            "expr": "evidently_drift_share"
          }
        ],
        "type": "graph",
        "alert": {
          "conditions": [{
            "evaluator": {
              "params": [0.3],
              "type": "gt"
            }
          }]
        }
      },
      {
        "title": "Model Inference Latency (P95)",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(vllm_request_duration_seconds_bucket[5m]))"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Active Model Versions",
        "targets": [
          {
            "expr": "mlflow_model_versions{stage='Production'}"
          }
        ],
        "type": "stat"
      }
    ]
  }
}
```

---

## ✅ Deliverables Checklist

- [ ] MLFlow tracking server deployed on GKE
- [ ] PostgreSQL/Cloud SQL database configured
- [ ] GCS bucket for artifacts created
- [ ] MLFlow UI accessible via HTTPS
- [ ] LLM and embedding models registered in MLFlow
- [ ] Model versioning and tagging implemented
- [ ] RAGAS evaluation pipeline created
- [ ] Automated weekly RAGAS evaluation CronJob scheduled
- [ ] Evidently drift detection implemented
- [ ] Daily drift monitoring CronJob scheduled
- [ ] Model deployment webhook configured
- [ ] MLFlow → KServe deployment automation working
- [ ] Grafana dashboards for model performance
- [ ] Alerting rules for drift detection
- [ ] Documentation for model registry workflows

---

## 📝 Next Steps

After completing Phase 4, proceed to:
- **[Phase 5: CI/CD Pipeline](./phase-5-cicd-pipeline.md)** - Automate testing, building, and deployment

---

**Phase Status**: Pending
**Last Updated**: 2025-11-13
