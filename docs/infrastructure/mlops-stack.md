# MLOps Infrastructure Documentation

**Version**: 1.0
**Date**: 2025-10-22
**Status**: Implementation Guide

---

## Executive Summary

This document defines the complete MLOps infrastructure for IntelliRAG, covering CI/CD pipelines, model versioning, data versioning, and deployment automation. The infrastructure enforces >80% test coverage, enables reproducible experiments, and provides automated deployment to GKE.

**Key Components:**
- **CI/CD**: GitHub Actions with 3-stage pipeline (Test → Build → Deploy)
- **Model Versioning**: MLFlow model registry with lineage tracking
- **Data Versioning**: DVC with GCS remote storage
- **Quality Gates**: Automated test coverage enforcement (>80%)
- **Deployment**: Manual trigger to GKE with Helm/Helmfile

---

## Architecture Overview

```
Developer
    ↓
Git Push → GitHub Actions
            ↓
    ┌───────┴───────┐
    │  STAGE 1:     │
    │  TEST         │ ← Pytest + Coverage (>80% gate)
    │  ✓ Unit       │ ← pytest-asyncio
    │  ✓ Integration│ ← Mock services
    │  ✓ RAGAS eval │ ← RAG metrics
    └───────┬───────┘
            ↓ (auto)
    ┌───────┴───────┐
    │  STAGE 2:     │
    │  BUILD        │ ← Docker multi-stage
    │  ✓ FastAPI    │ ← Slim image
    │  ✓ Push to GCR│ ← Artifact Registry
    └───────┬───────┘
            ↓ (manual trigger)
    ┌───────┴───────┐
    │  STAGE 3:     │
    │  DEPLOY       │ ← Helm/Helmfile
    │  ✓ Update GKE │ ← kubectl + helm
    │  ✓ KServe     │ ← Model serving
    │  ✓ Smoke tests│ ← Health checks
    └───────────────┘

MLFlow (Parallel)          DVC (Parallel)
    ↓                          ↓
Model Registry          Data Versioning
    ├─ Qwen3-0.6B           ├─ Raw documents
    ├─ MiniCPM-V-2          ├─ Processed chunks
    └─ Embeddings           └─ Evaluation datasets
```

---

## 1. CI/CD Pipeline (GitHub Actions)

### 1.1 Pipeline Configuration

**File**: `.github/workflows/ci-cd.yml`

```yaml
name: IntelliRAG CI/CD Pipeline

on:
  push:
    branches:
      - develop
      - main
  pull_request:
    branches:
      - develop
      - main
  workflow_dispatch:  # Manual deployment trigger
    inputs:
      environment:
        description: 'Target environment'
        required: true
        type: choice
        options:
          - staging
          - production

env:
  PYTHON_VERSION: '3.12'
  GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  GCP_REGION: 'us-central1'
  GKE_CLUSTER: 'intellirag-cluster'
  COVERAGE_THRESHOLD: 80

jobs:
  # ========================================
  # STAGE 1: TEST
  # ========================================
  test:
    name: Test & Coverage
    runs-on: ubuntu-latest
    timeout-minutes: 30

    services:
      qdrant:
        image: qdrant/qdrant:v1.15.1
        ports:
          - 6333:6333
        options: >-
          --health-cmd "curl -f http://localhost:6333/health || exit 1"
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # For DVC

      - name: Set up Python ${{ env.PYTHON_VERSION }}
        uses: actions/setup-python@v5
        with:
          python-version: ${{ env.PYTHON_VERSION }}
          cache: 'pip'

      - name: Install uv
        run: |
          curl -LsSf https://astral.sh/uv/install.sh | sh
          echo "$HOME/.cargo/bin" >> $GITHUB_PATH

      - name: Install dependencies
        run: |
          uv pip install --system -r requirements.txt
          uv pip install --system -r requirements-dev.txt

      - name: Run unit tests with coverage
        run: |
          pytest tests/unit/ \
            --cov=app \
            --cov-report=xml \
            --cov-report=html \
            --cov-report=term-missing \
            --cov-fail-under=${{ env.COVERAGE_THRESHOLD }} \
            -v \
            -m "not slow"
        env:
          QDRANT_HOST: localhost
          QDRANT_PORT: 6333

      - name: Run integration tests
        run: |
          pytest tests/integration/ \
            --cov=app \
            --cov-append \
            --cov-report=xml \
            -v \
            -m integration
        env:
          QDRANT_HOST: localhost
          QDRANT_PORT: 6333

      - name: Check coverage threshold
        run: |
          coverage report --fail-under=${{ env.COVERAGE_THRESHOLD }}

      - name: Upload coverage reports
        uses: codecov/codecov-action@v4
        with:
          file: ./coverage.xml
          flags: unittests
          name: codecov-umbrella
          fail_ci_if_error: true

      - name: Upload coverage artifacts
        uses: actions/upload-artifact@v4
        with:
          name: coverage-report
          path: htmlcov/

  # ========================================
  # STAGE 2: BUILD
  # ========================================
  build:
    name: Build & Push Docker Image
    runs-on: ubuntu-latest
    needs: test
    if: github.event_name == 'push' && (github.ref == 'refs/heads/develop' || github.ref == 'refs/heads/main')
    timeout-minutes: 20

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v3

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Configure Docker for GCR
        run: |
          gcloud auth configure-docker ${{ env.GCP_REGION }}-docker.pkg.dev

      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: ${{ env.GCP_REGION }}-docker.pkg.dev/${{ env.GCP_PROJECT_ID }}/intellirag/fastapi
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}
            type=semver,pattern={{major}}.{{minor}}

      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
          build-args: |
            PYTHON_VERSION=${{ env.PYTHON_VERSION }}

      - name: Generate SBOM
        uses: anchore/sbom-action@v0
        with:
          image: ${{ steps.meta.outputs.tags }}
          format: spdx-json
          output-file: sbom.spdx.json

      - name: Upload SBOM
        uses: actions/upload-artifact@v4
        with:
          name: sbom
          path: sbom.spdx.json

  # ========================================
  # STAGE 3: DEPLOY (Manual Trigger)
  # ========================================
  deploy:
    name: Deploy to GKE
    runs-on: ubuntu-latest
    needs: build
    if: github.event_name == 'workflow_dispatch'
    timeout-minutes: 15
    environment:
      name: ${{ github.event.inputs.environment }}
      url: https://${{ github.event.inputs.environment }}.intellirag.io

    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}

      - name: Get GKE credentials
        uses: google-github-actions/get-gke-credentials@v2
        with:
          cluster_name: ${{ env.GKE_CLUSTER }}
          location: ${{ env.GCP_REGION }}

      - name: Install Helm
        uses: azure/setup-helm@v4
        with:
          version: 'v3.13.0'

      - name: Install Helmfile
        run: |
          wget https://github.com/helmfile/helmfile/releases/download/v0.157.0/helmfile_0.157.0_linux_amd64.tar.gz
          tar -xzf helmfile_0.157.0_linux_amd64.tar.gz
          sudo mv helmfile /usr/local/bin/
          helmfile --version

      - name: Deploy with Helmfile
        run: |
          cd kubernetes/helm
          helmfile --environment ${{ github.event.inputs.environment }} apply --wait
        env:
          IMAGE_TAG: ${{ github.sha }}

      - name: Wait for rollout
        run: |
          kubectl rollout status deployment/intellirag-fastapi -n intellirag --timeout=5m

      - name: Run smoke tests
        run: |
          kubectl run smoke-test \
            --image=curlimages/curl:latest \
            --restart=Never \
            --rm -i \
            --namespace=intellirag \
            -- curl -f http://intellirag-fastapi:8000/health

      - name: Notify deployment
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: |
            Deployment to ${{ github.event.inputs.environment }} completed
            Image: ${{ github.sha }}
            Environment: https://${{ github.event.inputs.environment }}.intellirag.io
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK }}
        if: always()
```

### 1.2 Quality Gates

**Coverage Enforcement**:
```yaml
# pytest.ini
[tool:pytest]
addopts =
    --cov=app
    --cov-report=term-missing
    --cov-report=html
    --cov-report=xml
    --cov-fail-under=80
    --strict-markers
    -v

markers =
    unit: Unit tests with mocked dependencies
    integration: Integration tests with real services
    slow: Tests that take >10 seconds
    benchmark: Performance benchmarking tests
```

**Pre-commit Hooks** (`.pre-commit-config.yaml`):
```yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.5.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
        args: ['--maxkb=1000']
      - id: detect-private-key

  - repo: https://github.com/psf/black
    rev: 23.12.0
    hooks:
      - id: black
        language_version: python3.12

  - repo: https://github.com/PyCQA/isort
    rev: 5.13.2
    hooks:
      - id: isort

  - repo: https://github.com/PyCQA/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
        args: ['--max-line-length=120', '--extend-ignore=E203,W503']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
        args: ['--ignore-missing-imports']
```

---

## 2. MLFlow Model Registry

### 2.1 Architecture

```
Model Training/Fine-tuning
        ↓
MLFlow Tracking Server
        ├─ Experiments
        │   ├─ Run ID
        │   ├─ Parameters
        │   ├─ Metrics
        │   └─ Artifacts
        ↓
MLFlow Model Registry
        ├─ Model Name: Qwen3-0.6B-instruct
        │   ├─ Version 1 (Staging)
        │   ├─ Version 2 (Production)
        │   └─ Version 3 (Archived)
        ├─ Model Name: embedding-model
        │   └─ Version 1 (Production)
        └─ Metadata
            ├─ Model signature
            ├─ Input schema
            └─ Dependencies
        ↓
KServe InferenceService
        ├─ Load from MLFlow URI
        └─ Deploy to GKE
```

### 2.2 MLFlow Setup

**Docker Compose** (`mlops/mlflow/docker-compose.yml`):
```yaml
version: '3.8'

services:
  mlflow-db:
    image: postgres:15-alpine
    container_name: mlflow-postgres
    environment:
      POSTGRES_USER: mlflow
      POSTGRES_PASSWORD: ${MLFLOW_DB_PASSWORD}
      POSTGRES_DB: mlflow
    volumes:
      - mlflow-db-data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U mlflow"]
      interval: 10s
      timeout: 5s
      retries: 5

  mlflow-server:
    image: ghcr.io/mlflow/mlflow:v2.10.0
    container_name: mlflow-server
    depends_on:
      mlflow-db:
        condition: service_healthy
    environment:
      MLFLOW_BACKEND_STORE_URI: postgresql://mlflow:${MLFLOW_DB_PASSWORD}@mlflow-db:5432/mlflow
      MLFLOW_ARTIFACT_ROOT: gs://${GCS_BUCKET}/mlflow-artifacts
      GOOGLE_APPLICATION_CREDENTIALS: /secrets/gcp-sa-key.json
    volumes:
      - ${GCP_SA_KEY_PATH}:/secrets/gcp-sa-key.json:ro
    ports:
      - "5000:5000"
    command: >
      mlflow server
      --backend-store-uri ${MLFLOW_BACKEND_STORE_URI}
      --default-artifact-root ${MLFLOW_ARTIFACT_ROOT}
      --host 0.0.0.0
      --port 5000
      --serve-artifacts

volumes:
  mlflow-db-data:
```

### 2.3 Model Registration

**Python Client** (`app/services/mlops/mlflow_client.py`):
```python
"""MLFlow client for model versioning and registry."""
import os
from typing import Dict, Optional, Any

import mlflow
from mlflow.tracking import MlflowClient
from mlflow.models import infer_signature
from pydantic import BaseModel


class ModelMetadata(BaseModel):
    """Model metadata schema."""
    name: str
    version: str
    framework: str
    task: str
    base_model: str
    parameters: Dict[str, Any]
    metrics: Dict[str, float]


class MLFlowService:
    """Service for managing models with MLFlow."""

    def __init__(self, tracking_uri: str = "http://localhost:5000"):
        """Initialize MLFlow client."""
        mlflow.set_tracking_uri(tracking_uri)
        self.client = MlflowClient(tracking_uri=tracking_uri)

    def log_model(
        self,
        model_path: str,
        model_name: str,
        metadata: ModelMetadata,
        input_example: Optional[Any] = None,
        signature: Optional[Any] = None,
    ) -> str:
        """Log model to MLFlow with metadata.

        Args:
            model_path: Path to model artifacts
            model_name: Registered model name
            metadata: Model metadata
            input_example: Example input for signature inference
            signature: MLFlow model signature

        Returns:
            Model version string
        """
        with mlflow.start_run(run_name=f"{model_name}-{metadata.version}"):
            # Log parameters
            mlflow.log_params(metadata.parameters)

            # Log metrics
            mlflow.log_metrics(metadata.metrics)

            # Log model
            if signature is None and input_example is not None:
                signature = infer_signature(input_example)

            mlflow.log_artifact(model_path)

            # Register model
            model_uri = f"runs:/{mlflow.active_run().info.run_id}/{model_name}"
            registered_model = mlflow.register_model(
                model_uri=model_uri,
                name=model_name,
            )

            # Add metadata
            self.client.update_model_version(
                name=model_name,
                version=registered_model.version,
                description=f"Model: {metadata.base_model}, Task: {metadata.task}",
            )

            return registered_model.version

    def promote_model(
        self,
        model_name: str,
        version: str,
        stage: str = "Production",
    ) -> None:
        """Promote model to a specific stage.

        Args:
            model_name: Registered model name
            version: Model version
            stage: Target stage (Staging/Production/Archived)
        """
        self.client.transition_model_version_stage(
            name=model_name,
            version=version,
            stage=stage,
            archive_existing_versions=True,
        )

    def get_production_model(self, model_name: str) -> Optional[str]:
        """Get production model version.

        Args:
            model_name: Registered model name

        Returns:
            Model URI or None if not found
        """
        try:
            versions = self.client.get_latest_versions(
                name=model_name,
                stages=["Production"],
            )
            if versions:
                return versions[0].source
            return None
        except Exception:
            return None

    def load_model(self, model_name: str, stage: str = "Production"):
        """Load model from registry.

        Args:
            model_name: Registered model name
            stage: Model stage

        Returns:
            Loaded model
        """
        model_uri = f"models:/{model_name}/{stage}"
        return mlflow.pyfunc.load_model(model_uri)
```

**Example Usage**:
```python
# Register new model
mlflow_service = MLFlowService(tracking_uri="http://mlflow:5000")

metadata = ModelMetadata(
    name="Qwen3-0.6B-instruct",
    version="v1.0.0",
    framework="transformers",
    task="text-generation",
    base_model="Qwen/Qwen3-0.6B-Instruct",
    parameters={
        "max_tokens": 8192,
        "temperature": 0.7,
        "quantization": "fp16",
    },
    metrics={
        "perplexity": 12.5,
        "ragas_faithfulness": 0.89,
        "ragas_relevance": 0.92,
    },
)

version = mlflow_service.log_model(
    model_path="./models/Qwen3-0.6B-instruct",
    model_name="Qwen3-0.6B-instruct",
    metadata=metadata,
)

# Promote to production
mlflow_service.promote_model(
    model_name="Qwen3-0.6B-instruct",
    version=version,
    stage="Production",
)
```

---

## 3. DVC Data Versioning

### 3.1 Architecture

```
Raw Data Sources
    ├─ PDF documents
    ├─ CSV datasets
    ├─ Images
    └─ Evaluation sets
        ↓
DVC Track & Version
        ↓
GCS Remote Storage
    gs://intellirag-data/
        ├─ raw/
        ├─ processed/
        ├─ embeddings/
        └─ evaluations/
        ↓
DVC Pull/Push
        ↓
Reproducible Pipeline
```

### 3.2 DVC Setup

**Installation & Configuration**:
```bash
# Install DVC
uv pip install dvc[gs]

# Initialize DVC
dvc init

# Configure GCS remote
dvc remote add -d gcs gs://intellirag-data/dvc-storage
dvc remote modify gcs credentialpath /path/to/gcp-sa-key.json

# Enable autostage
dvc config core.autostage true
```

**Directory Structure** (`mlops/dvc/`):
```
mlops/dvc/
├── .dvc/
│   ├── config
│   └── .gitignore
├── data/
│   ├── raw/
│   │   ├── documents.dvc
│   │   └── .gitignore
│   ├── processed/
│   │   ├── chunks.dvc
│   │   └── .gitignore
│   └── embeddings/
│       ├── vectors.dvc
│       └── .gitignore
├── models/
│   └── .gitignore
└── pipelines/
    ├── preprocess.dvc
    └── evaluate.dvc
```

### 3.3 DVC Pipeline Definition

**Preprocessing Pipeline** (`.dvc/preprocess.dvc`):
```yaml
cmd: python scripts/preprocess.py
deps:
  - data/raw/documents/
  - scripts/preprocess.py
  - app/services/preprocessing/
params:
  - preprocess:
      chunk_size: 1000
      chunk_overlap: 200
      embedding_model: all-MiniLM-L6-v2
outs:
  - data/processed/chunks/:
      cache: true
      persist: true
  - data/embeddings/vectors/:
      cache: true
      persist: true
metrics:
  - metrics/preprocess_metrics.json:
      cache: false
```

**Evaluation Pipeline** (`.dvc/evaluate.dvc`):
```yaml
cmd: python scripts/evaluate.py
deps:
  - data/processed/chunks/
  - data/embeddings/vectors/
  - scripts/evaluate.py
  - tests/evaluation/
params:
  - evaluate:
      test_size: 100
      ragas_metrics:
        - faithfulness
        - answer_relevance
        - context_relevance
outs:
  - reports/evaluation/:
      cache: false
metrics:
  - metrics/ragas_scores.json:
      cache: false
plots:
  - plots/ragas_distribution.json:
      cache: false
      x: metric
      y: score
```

### 3.4 DVC Workflow

**Version Data**:
```bash
# Add raw documents
dvc add data/raw/documents
git add data/raw/documents.dvc .gitignore
git commit -m "data: add raw documents v1.0"

# Push to GCS
dvc push

# Tag version
git tag -a data-v1.0 -m "Dataset v1.0"
git push origin data-v1.0
```

**Reproduce Pipeline**:
```bash
# Pull data
dvc pull

# Run preprocessing
dvc repro preprocess

# Run evaluation
dvc repro evaluate

# Check metrics
dvc metrics show

# Compare experiments
dvc exp show
```

**CI/CD Integration** (in `.github/workflows/ci-cd.yml`):
```yaml
- name: Setup DVC
  run: |
    pip install dvc[gs]
    dvc remote modify gcs credentialpath $GOOGLE_APPLICATION_CREDENTIALS

- name: Pull DVC data
  run: |
    dvc pull

- name: Run evaluation pipeline
  run: |
    dvc repro evaluate

- name: Check metrics regression
  run: |
    python scripts/check_metrics_regression.py \
      --baseline metrics/ragas_scores_baseline.json \
      --current metrics/ragas_scores.json \
      --threshold 0.05
```

---

## 4. Deployment Automation

### 4.1 Helmfile Configuration

**File**: `kubernetes/helm/helmfile.yaml`

```yaml
repositories:
  - name: bitnami
    url: https://charts.bitnami.com/bitnami
  - name: kserve
    url: https://kserve.github.io/charts
  - name: qdrant
    url: https://qdrant.github.io/qdrant-helm

environments:
  staging:
    values:
      - environments/staging-values.yaml
  production:
    values:
      - environments/production-values.yaml

releases:
  # Main FastAPI application
  - name: intellirag-fastapi
    namespace: intellirag
    chart: ./intellirag
    version: 0.1.0
    values:
      - intellirag/values.yaml
      - intellirag/values-{{ .Environment.Name }}.yaml
    set:
      - name: image.tag
        value: {{ env "IMAGE_TAG" }}
    secrets:
      - secrets/{{ .Environment.Name }}-secrets.yaml

  # Qdrant vector database
  - name: qdrant
    namespace: intellirag
    chart: qdrant/qdrant
    version: 0.8.0
    values:
      - qdrant/values.yaml
      - qdrant/values-{{ .Environment.Name }}.yaml

  # KServe for model serving
  - name: kserve-runtime
    namespace: intellirag
    chart: kserve/kserve-runtime
    version: 0.11.0
    values:
      - kserve/values.yaml
    set:
      - name: vllm.modelUri
        value: gs://{{ env "GCS_BUCKET" }}/models/Qwen3-0.6B-instruct

  # NGINX Ingress Controller
  - name: nginx-ingress
    namespace: ingress-nginx
    chart: bitnami/nginx-ingress-controller
    version: 10.0.0
    values:
      - nginx/values.yaml
```

**Application Chart Values** (`kubernetes/helm/intellirag/values.yaml`):
```yaml
replicaCount: 2

image:
  repository: us-central1-docker.pkg.dev/intellirag/intellirag/fastapi
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 8000
  targetPort: 8000

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/auth-type: basic
  hosts:
    - host: api.intellirag.io
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: intellirag-tls
      hosts:
        - api.intellirag.io

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

env:
  - name: QDRANT_HOST
    value: qdrant
  - name: QDRANT_PORT
    value: "6333"
  - name: VLLM_API_BASE
    value: http://kserve-runtime.intellirag.svc.cluster.local:8000/v1
  - name: GCS_BUCKET
    valueFrom:
      secretKeyRef:
        name: gcs-config
        key: bucket-name
  - name: MLFLOW_TRACKING_URI
    value: http://mlflow:5000

healthCheck:
  enabled: true
  path: /health
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

serviceMonitor:
  enabled: true
  interval: 30s
  path: /metrics
```

### 4.2 Manual Deployment Trigger

**GitHub UI Workflow Dispatch**:
1. Navigate to Actions tab
2. Select "IntelliRAG CI/CD Pipeline"
3. Click "Run workflow"
4. Select environment (staging/production)
5. Click "Run workflow"

**CLI Trigger**:
```bash
# Trigger deployment via gh CLI
gh workflow run ci-cd.yml \
  --field environment=production \
  --ref main

# Monitor deployment
gh run watch

# Check logs
kubectl logs -f deployment/intellirag-fastapi -n intellirag
```

---

## 5. Integration Points

### 5.1 MLFlow + KServe

**InferenceService with MLFlow URI** (`kubernetes/helm/kserve/inferenceservice.yaml`):
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: qwen-vllm
  namespace: intellirag
spec:
  predictor:
    model:
      modelFormat:
        name: vllm
      storageUri: mlflow://Qwen3-0.6B-instruct/Production  # MLFlow model registry
      resources:
        limits:
          cpu: "8"
          memory: 32Gi
          nvidia.com/gpu: "1"
        requests:
          cpu: "4"
          memory: 16Gi
          nvidia.com/gpu: "1"
      env:
        - name: MLFLOW_TRACKING_URI
          value: http://mlflow:5000
        - name: VLLM_GPU_MEMORY_UTILIZATION
          value: "0.95"
        - name: VLLM_MAX_MODEL_LEN
          value: "8192"
    minReplicas: 1
    maxReplicas: 5
    scaleTarget: 50  # Target concurrent requests
    scaleMetric: concurrency
```

### 5.2 DVC + CI/CD

**Data Versioning in Pipeline**:
```yaml
# In .github/workflows/ci-cd.yml
- name: Setup DVC with GCS
  run: |
    pip install dvc[gs]
    echo '${{ secrets.GCP_SA_KEY }}' > /tmp/gcp-sa-key.json
    dvc remote modify gcs credentialpath /tmp/gcp-sa-key.json

- name: Pull evaluation datasets
  run: |
    dvc pull data/evaluation/ragas_test_set.dvc

- name: Run RAGAS evaluation
  run: |
    pytest tests/evaluation/test_ragas.py \
      --data-path data/evaluation/ragas_test_set/ \
      --metrics-output metrics/ragas_scores.json
```

---

## 6. Monitoring Integration

### 6.1 MLFlow Metrics Export

**Prometheus Exporter for MLFlow**:
```python
# app/services/monitoring/mlflow_exporter.py
from prometheus_client import Gauge
import mlflow

# Define metrics
model_version = Gauge('mlflow_model_version', 'Current production model version', ['model_name'])
model_accuracy = Gauge('mlflow_model_accuracy', 'Model accuracy metric', ['model_name', 'version'])

def export_mlflow_metrics():
    """Export MLFlow metrics to Prometheus."""
    client = mlflow.tracking.MlflowClient()

    for model_name in ["Qwen3-0.6B-instruct", "embedding-model"]:
        versions = client.get_latest_versions(name=model_name, stages=["Production"])

        if versions:
            version = versions[0]
            model_version.labels(model_name=model_name).set(int(version.version))

            # Get metrics
            run = client.get_run(version.run_id)
            for metric_key, metric_value in run.data.metrics.items():
                model_accuracy.labels(model_name=model_name, version=version.version).set(metric_value)
```

### 6.2 DVC Metrics Dashboard

**Grafana Dashboard for Data Metrics**:
```json
{
  "dashboard": {
    "title": "IntelliRAG Data Metrics",
    "panels": [
      {
        "title": "Dataset Size Trend",
        "targets": [
          {
            "expr": "dvc_dataset_size_bytes{dataset='raw_documents'}"
          }
        ]
      },
      {
        "title": "RAGAS Scores",
        "targets": [
          {
            "expr": "ragas_faithfulness_score{environment='production'}"
          },
          {
            "expr": "ragas_answer_relevance{environment='production'}"
          }
        ]
      }
    ]
  }
}
```

---

## 7. TDD Integration

### 7.1 Test Structure for MLOps

**MLFlow Service Tests** (`tests/unit/test_mlflow_service.py`):
```python
import pytest
from unittest.mock import Mock, patch
from app.services.mlops.mlflow_client import MLFlowService, ModelMetadata


class TestMLFlowService:
    """Test MLFlow service functionality."""

    @pytest.fixture
    def mlflow_service(self):
        """Create MLFlow service instance."""
        return MLFlowService(tracking_uri="http://localhost:5000")

    @pytest.fixture
    def model_metadata(self):
        """Create model metadata."""
        return ModelMetadata(
            name="test-model",
            version="v1.0.0",
            framework="transformers",
            task="text-generation",
            base_model="test/model",
            parameters={"max_tokens": 512},
            metrics={"accuracy": 0.95},
        )

    @patch("mlflow.start_run")
    @patch("mlflow.log_params")
    @patch("mlflow.log_metrics")
    @patch("mlflow.log_artifact")
    @patch("mlflow.register_model")
    def test_log_model(
        self,
        mock_register,
        mock_log_artifact,
        mock_log_metrics,
        mock_log_params,
        mock_start_run,
        mlflow_service,
        model_metadata,
    ):
        """Test model logging."""
        # Arrange
        mock_register.return_value = Mock(version="1")

        # Act
        version = mlflow_service.log_model(
            model_path="./test_model",
            model_name="test-model",
            metadata=model_metadata,
        )

        # Assert
        assert version == "1"
        mock_log_params.assert_called_once_with(model_metadata.parameters)
        mock_log_metrics.assert_called_once_with(model_metadata.metrics)

    def test_promote_model(self, mlflow_service):
        """Test model promotion."""
        with patch.object(mlflow_service.client, "transition_model_version_stage") as mock_transition:
            mlflow_service.promote_model(
                model_name="test-model",
                version="1",
                stage="Production",
            )

            mock_transition.assert_called_once_with(
                name="test-model",
                version="1",
                stage="Production",
                archive_existing_versions=True,
            )
```

### 7.2 DVC Pipeline Tests

**DVC Workflow Tests** (`tests/integration/test_dvc_pipeline.py`):
```python
import pytest
import subprocess
from pathlib import Path


class TestDVCPipeline:
    """Test DVC pipeline reproducibility."""

    def test_preprocess_pipeline_reproducible(self, tmp_path):
        """Test preprocessing pipeline is reproducible."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Act - Run pipeline twice
        result1 = subprocess.run(
            ["dvc", "repro", "preprocess"],
            cwd=workspace,
            capture_output=True,
        )
        result2 = subprocess.run(
            ["dvc", "repro", "preprocess"],
            cwd=workspace,
            capture_output=True,
        )

        # Assert
        assert result1.returncode == 0
        assert result2.returncode == 0
        assert "already cached" in result2.stdout.decode()

    def test_dvc_push_pull(self, tmp_path):
        """Test DVC remote operations."""
        # Arrange
        workspace = tmp_path / "workspace"
        workspace.mkdir()

        # Act
        push_result = subprocess.run(
            ["dvc", "push"],
            cwd=workspace,
            capture_output=True,
        )
        pull_result = subprocess.run(
            ["dvc", "pull"],
            cwd=workspace,
            capture_output=True,
        )

        # Assert
        assert push_result.returncode == 0
        assert pull_result.returncode == 0
```

---

## 8. Security & Secrets Management

### 8.1 GitHub Secrets

**Required Secrets**:
```
GCP_SA_KEY              # Service account key for GCS/GKE access
GCP_PROJECT_ID          # GCP project ID
MLFLOW_DB_PASSWORD      # MLFlow PostgreSQL password
CODECOV_TOKEN           # Codecov upload token
SLACK_WEBHOOK           # Deployment notifications
GCS_BUCKET              # GCS bucket name for artifacts
```

### 8.2 Kubernetes Secrets

**Create Secrets**:
```bash
# GCS credentials
kubectl create secret generic gcs-credentials \
  --from-file=key.json=/path/to/gcp-sa-key.json \
  --namespace=intellirag

# MLFlow credentials
kubectl create secret generic mlflow-credentials \
  --from-literal=postgres-password=$MLFLOW_DB_PASSWORD \
  --from-literal=tracking-uri=http://mlflow:5000 \
  --namespace=intellirag

# Model registry access
kubectl create secret generic mlflow-model-access \
  --from-literal=mlflow-tracking-uri=http://mlflow:5000 \
  --namespace=intellirag
```

---

## 9. Cost Optimization

### 9.1 Budget Allocation ($300/month)

```
GKE Autopilot:          $150/month
  ├─ Control plane:     $73/month (managed)
  ├─ Worker nodes:      $50/month (2x n2-standard-2)
  └─ GPU node pool:     $27/month (1x g2-standard-4, spot instance)

GCS Storage:            $50/month
  ├─ Standard storage:  $30/month (~1TB)
  ├─ Nearline (archive):$10/month
  └─ Network egress:    $10/month

Artifact Registry:      $20/month
  └─ Docker images:     ~100GB

Load Balancer:          $20/month
  └─ NGINX ingress

External IP:            $10/month

Monitoring (Free Tier):  $0/month
  ├─ Prometheus:        Community edition
  ├─ Grafana:           OSS version
  └─ GCP Cloud Logging: Free quota

MLFlow (Self-hosted):    $0/month
  └─ Running on GKE cluster

Total:                  $250/month
Buffer:                 $50/month
```

### 9.2 Cost-Saving Strategies

1. **Use Spot Instances for GPU nodes**:
   ```yaml
   # In GKE node pool config
   nodeConfig:
     spot: true
     machineType: g2-standard-4
   ```

2. **Scale to Zero with KServe**:
   ```yaml
   spec:
     predictor:
       minReplicas: 0  # Scale to zero when idle
       scaleTarget: 50
   ```

3. **GCS Lifecycle Policies**:
   ```json
   {
     "lifecycle": {
       "rule": [
         {
           "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
           "condition": {"age": 30}
         },
         {
           "action": {"type": "Delete"},
           "condition": {"age": 90}
         }
       ]
     }
   }
   ```

---

## 10. Troubleshooting

### 10.1 Common Issues

**Issue**: Coverage below 80%
```bash
# Solution: Check uncovered lines
pytest --cov=app --cov-report=html
open htmlcov/index.html

# Add missing tests
vim tests/unit/test_<missing_module>.py
```

**Issue**: MLFlow model not found
```bash
# Solution: Check model registry
mlflow models list --model-name Qwen3-0.6B-instruct

# Promote model to production
mlflow models update \
  --name Qwen3-0.6B\
  --version 1 \
  --stage Production
```

**Issue**: DVC pull fails
```bash
# Solution: Check GCS credentials
dvc remote list
dvc remote modify gcs credentialpath /path/to/key.json

# Retry pull
dvc pull -v
```

**Issue**: Deployment failed
```bash
# Solution: Check rollout status
kubectl rollout status deployment/intellirag-fastapi -n intellirag

# Check logs
kubectl logs -f deployment/intellirag-fastapi -n intellirag

# Rollback if needed
helm rollback intellirag-fastapi -n intellirag
```

---

## 11. Next Steps

1. **Setup MLFlow Server**:
   ```bash
   cd mlops/mlflow
   docker-compose up -d
   ```

2. **Configure DVC**:
   ```bash
   dvc init
   dvc remote add -d gcs gs://intellirag-data/dvc-storage
   ```

3. **Create GitHub Secrets**:
   - Add all required secrets in repository settings

4. **Deploy Infrastructure**:
   ```bash
   cd terraform
   terraform init
   terraform apply
   ```

5. **Run First Pipeline**:
   ```bash
   git push origin develop  # Triggers CI/CD
   ```

---

## Appendix

### A. GitHub Actions Badge

Add to `README.md`:
```markdown
[![CI/CD Pipeline](https://github.com/your-org/intellirag/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/your-org/intellirag/actions/workflows/ci-cd.yml)
[![Coverage](https://codecov.io/gh/your-org/intellirag/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/intellirag)
```

### B. References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [MLFlow Model Registry](https://mlflow.org/docs/latest/model-registry.html)
- [DVC Get Started](https://dvc.org/doc/start)
- [KServe Documentation](https://kserve.github.io/website/)
- [Helm Best Practices](https://helm.sh/docs/chart_best_practices/)

---

**Document Status**: ✅ Ready for Implementation
**Last Updated**: 2025-10-22
**Next Review**: After Phase 5 Completion
