# IntelliRAG Pre-Deployment Action Plan

**Version:** 1.0  
**Date:** 2025-11-02  
**Target:** Full Production Deployment to GKE  
**Budget:** $300/month  
**Timeline:** 10-14 days  
**Methodology:** TDD + Infrastructure as Code

---

## 📊 Executive Summary

### Current Status: **Code Complete, Infrastructure Pending**

| Component | Status | Coverage | Notes |
|-----------|--------|----------|-------|
| FastAPI Services | ✅ Complete | >80% | 312 tests passing |
| Document Loaders | ✅ Complete | 100% | 7 loader types |
| Query Router (LangGraph) | ✅ Complete | 100% | 26/26 tests |
| Observability (Basic) | ✅ Complete | 95% | Prometheus metrics, structured logging |
| **Infrastructure** | ❌ **Missing** | 0% | **Critical blocker** |
| **Deployment Manifests** | ❌ **Missing** | 0% | **Critical blocker** |
| **MLOps Stack** | ❌ **Missing** | 0% | **High priority** |
| **Advanced Observability** | ⚠️ Partial | 30% | Tracing, dashboards needed |
| **CI/CD Pipeline** | ❌ **Missing** | 0% | **High priority** |

### Deployment Readiness: **35% Complete**

**What's Working:**
- ✅ Application code is production-ready
- ✅ Local development environment functional
- ✅ GCP project provisioned
- ✅ Required tools installed (gcloud, kubectl, helm)

**What's Blocking Deployment:**
- ❌ No Docker image for FastAPI application
- ❌ No Kubernetes cluster (GKE)
- ❌ No Helm charts or manifests
- ❌ No infrastructure as code (Terraform)
- ❌ No model registry or versioning (MLFlow/DVC)
- ❌ No observability stack deployed
- ❌ No CI/CD pipeline

---

## 🎯 Deployment Architecture Overview

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         GKE Cluster ($240/month)                │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │ 
│  │   NGINX      │  │   FastAPI    │  │   KServe     │           │ 
│  │   Ingress    │─→│   Service    │─→│   (vLLM)     │           │
│  │              │  │  (3 replicas)│  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                           │                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │   Qdrant     │←─│   GCS        │  │   MLFlow     │           │
│  │   VectorDB   │  │   Storage    │  │   Registry   │           │
│  │              │  │              │  │              │           │
│  └──────────────┘  └──────────────┘  └──────────────┘           │
│                                                                 │
│  ┌────────────────────────────────────────────────────┐         │
│  │         Observability Stack ($40/month)            │         │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐   │         │
│  │  │Prometheus│ │ Grafana  │ │ Jaeger │ │  Loki  │   │         │
│  │  └──────────┘ └──────────┘ └────────┘ └────────┘   │         │
│  └────────────────────────────────────────────────────┘         │
└─────────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴──────────┐
                    │  GitHub Actions    │
                    │  CI/CD Pipeline    │
                    └────────────────────┘
```

### Cost Breakdown (Target: $300/month)

| Component | Instance Type | Monthly Cost | Notes |
|-----------|--------------|--------------|-------|
| **GKE Autopilot Cluster** | e2-medium (3 nodes) | $120 | Core services |
| **GKE GPU Node** | n1-standard-4 + T4 GPU | $120 | KServe vLLM (preemptible) |
| **GCS Storage** | Standard | $10 | Document storage (384GB) |
| **Persistent Disks** | SSD | $20 | Qdrant, MLFlow, Prometheus |
| **Load Balancer** | Network LB | $20 | Ingress |
| **Cloud Logging** | Basic | $10 | Log retention |
| **Total** | | **$300** | Within budget ✅ |

### Cost Optimization Strategies

1. **Use Preemptible GPU Nodes** (save 70%)
2. **GKE Autopilot** for efficient resource usage
3. **Scale to Zero** for non-critical services (KServe)
4. **Lifecycle Policies** on GCS (archive old documents)
5. **Resource Limits** on all pods
6. **Spot VMs** for batch processing

---

## 📋 Phase-by-Phase Action Plan

### **Phase 0: Pre-Deployment Setup (Day 0) - 2-3 hours**

#### 0.1 GCP Project Configuration
**Status:** ❌ **REQUIRED**

**Actions:**
- [ ] Verify GCP project ID and billing account
- [ ] Enable required APIs:
  ```bash
  gcloud services enable \
    container.googleapis.com \
    compute.googleapis.com \
    storage-api.googleapis.com \
    iam.googleapis.com \
    cloudresourcemanager.googleapis.com \
    servicenetworking.googleapis.com \
    sqladmin.googleapis.com
  ```
- [ ] Create service account for Terraform:
  ```bash
  gcloud iam service-accounts create terraform-sa \
    --display-name="Terraform Service Account"
  
  gcloud projects add-iam-policy-binding PROJECT_ID \
    --member="serviceAccount:terraform-sa@PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/editor"
  ```
- [ ] Download and store service account key securely
- [ ] Set up GCS bucket for Terraform state:
  ```bash
  gsutil mb -l us-central1 gs://PROJECT_ID-terraform-state
  gsutil versioning set on gs://PROJECT_ID-terraform-state
  ```

**Deliverables:**
- ✅ GCP APIs enabled
- ✅ Service account created with keys
- ✅ Terraform state bucket ready

---

### **Phase 1: Infrastructure Foundation (Days 1-3) - 18-24 hours**

#### 1.1 Terraform Setup for GKE
**Status:** ❌ **CRITICAL**

**Directory Structure:**
```
terraform/
├── main.tf                 # Root module
├── variables.tf            # Input variables
├── outputs.tf              # Output values
├── backend.tf              # Remote state config
├── versions.tf             # Provider versions
├── modules/
│   ├── gke/
│   │   ├── main.tf         # GKE cluster config
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── networking/
│   │   ├── main.tf         # VPC, subnets, firewall
│   │   ├── variables.tf
│   │   └── outputs.tf
│   ├── gcs/
│   │   ├── main.tf         # Storage buckets
│   │   ├── variables.tf
│   │   └── outputs.tf
│   └── iam/
│       ├── main.tf         # Service accounts, IAM
│       ├── variables.tf
│       └── outputs.tf
├── environments/
│   ├── dev.tfvars
│   └── prod.tfvars
└── README.md
```

**Key Terraform Resources:**

**GKE Cluster Configuration (`modules/gke/main.tf`):**
```hcl
resource "google_container_cluster" "intellirag" {
  name     = var.cluster_name
  location = var.region
  
  # Autopilot mode for cost optimization
  enable_autopilot = true
  
  # Release channel for automatic updates
  release_channel {
    channel = "REGULAR"
  }
  
  # Network configuration
  network    = var.network_name
  subnetwork = var.subnet_name
  
  # IP allocation for pods and services
  ip_allocation_policy {
    cluster_ipv4_cidr_block  = "/16"
    services_ipv4_cidr_block = "/22"
  }
  
  # Workload identity for secure GCS access
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }
  
  # Add GPU node pool for KServe
  node_pool {
    name = "gpu-pool"
    
    node_config {
      machine_type = "n1-standard-4"
      
      guest_accelerator {
        type  = "nvidia-tesla-t4"
        count = 1
      }
      
      preemptible = true  # 70% cost savings
      
      oauth_scopes = [
        "https://www.googleapis.com/auth/cloud-platform"
      ]
    }
    
    autoscaling {
      min_node_count = 0
      max_node_count = 2
    }
  }
}
```

**Actions:**
- [ ] Create Terraform directory structure
- [ ] Write GKE module (Autopilot + GPU node pool)
- [ ] Write networking module (VPC, subnets, firewall)
- [ ] Write GCS module (document storage bucket)
- [ ] Write IAM module (service accounts, workload identity)
- [ ] Configure remote state backend
- [ ] Test Terraform plan
- [ ] Apply Terraform to provision GKE cluster

**Commands:**
```bash
cd terraform/
terraform init
terraform plan -var-file=environments/prod.tfvars
terraform apply -var-file=environments/prod.tfvars
```

**Deliverables:**
- ✅ GKE Autopilot cluster running
- ✅ GPU node pool configured
- ✅ VPC and networking set up
- ✅ GCS buckets created
- ✅ Service accounts with proper IAM roles
- ✅ Terraform state stored in GCS

**Time Estimate:** 8-10 hours

---

#### 1.2 Dockerization - FastAPI Application
**Status:** ❌ **CRITICAL**

**Dockerfile (Multi-stage build for efficiency):**
```dockerfile
# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libmagic1 \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.cargo/bin:$PATH"

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen

# Stage 2: Runtime image
FROM python:3.12-slim

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY app/ ./app/
COPY main.py ./

# Create non-root user for security
RUN useradd -m -u 1000 intellirag && chown -R intellirag:intellirag /app
USER intellirag

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**.dockerignore:**
```
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
.venv/
venv/
ENV/
env/
tests/
docs/
.git/
.gitignore
*.md
.pytest_cache/
.coverage
htmlcov/
*.log
.env
.env.*
terraform/
kubernetes/
deploy/
qdrant_storage/
```

**Actions:**
- [ ] Create multi-stage Dockerfile
- [ ] Create .dockerignore
- [ ] Build Docker image locally
- [ ] Test Docker image locally with docker-compose
- [ ] Push to Google Container Registry (GCR)
- [ ] Set up automated image builds in CI/CD

**Commands:**
```bash
# Build image
docker build -t gcr.io/PROJECT_ID/intellirag-api:v1.0.0 .

# Test locally
docker run -p 8000:8000 \
  -e GCP_PROJECT_ID=PROJECT_ID \
  -e GCS_BUCKET_NAME=intellirag-documents \
  gcr.io/PROJECT_ID/intellirag-api:v1.0.0

# Push to GCR
gcloud auth configure-docker
docker push gcr.io/PROJECT_ID/intellirag-api:v1.0.0
```

**Deliverables:**
- ✅ Optimized multi-stage Dockerfile
- ✅ Docker image <500MB
- ✅ Image pushed to GCR
- ✅ Health checks working

**Time Estimate:** 4-5 hours

---

#### 1.3 Helm Charts - Core Services
**Status:** ❌ **CRITICAL**

**Helm Chart Structure:**
```
kubernetes/helm/
├── intellirag/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-dev.yaml
│   ├── values-prod.yaml
│   ├── templates/
│   │   ├── _helpers.tpl
│   │   ├── deployment.yaml
│   │   ├── service.yaml
│   │   ├── ingress.yaml
│   │   ├── hpa.yaml
│   │   ├── configmap.yaml
│   │   ├── secret.yaml
│   │   ├── serviceaccount.yaml
│   │   └── networkpolicy.yaml
│   └── README.md
├── qdrant/
│   ├── Chart.yaml
│   ├── values.yaml
│   └── templates/
│       ├── statefulset.yaml
│       ├── service.yaml
│       └── pvc.yaml
└── helmfile.yaml
```

**FastAPI Deployment (`intellirag/templates/deployment.yaml`):**
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "intellirag.fullname" . }}
  labels:
    {{- include "intellirag.labels" . | nindent 4 }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      {{- include "intellirag.selectorLabels" . | nindent 6 }}
  template:
    metadata:
      annotations:
        prometheus.io/scrape: "true"
        prometheus.io/path: "/metrics"
        prometheus.io/port: "8000"
      labels:
        {{- include "intellirag.selectorLabels" . | nindent 8 }}
    spec:
      serviceAccountName: {{ include "intellirag.serviceAccountName" . }}
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
      containers:
      - name: intellirag-api
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        imagePullPolicy: {{ .Values.image.pullPolicy }}
        ports:
        - name: http
          containerPort: 8000
          protocol: TCP
        env:
        - name: GCP_PROJECT_ID
          valueFrom:
            configMapKeyRef:
              name: {{ include "intellirag.fullname" . }}-config
              key: gcp_project_id
        - name: GCS_BUCKET_NAME
          valueFrom:
            configMapKeyRef:
              name: {{ include "intellirag.fullname" . }}-config
              key: gcs_bucket_name
        - name: QDRANT_URL
          value: "http://qdrant:6333"
        - name: LLM_BASE_URL
          value: "http://kserve-vllm-predictor:8000/v1"
        - name: LLM_MODEL
          value: {{ .Values.llm.model }}
        livenessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
        resources:
          {{- toYaml .Values.resources | nindent 12 }}
```

**HPA Configuration (`intellirag/templates/hpa.yaml`):**
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: {{ include "intellirag.fullname" . }}
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: {{ include "intellirag.fullname" . }}
  minReplicas: {{ .Values.autoscaling.minReplicas }}
  maxReplicas: {{ .Values.autoscaling.maxReplicas }}
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: {{ .Values.autoscaling.targetCPUUtilizationPercentage }}
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: {{ .Values.autoscaling.targetMemoryUtilizationPercentage }}
```

**values.yaml (Production Config):**
```yaml
replicaCount: 3

image:
  repository: gcr.io/PROJECT_ID/intellirag-api
  pullPolicy: IfNotPresent
  tag: "v1.0.0"

serviceAccount:
  create: true
  annotations:
    iam.gke.io/gcp-service-account: intellirag-sa@PROJECT_ID.iam.gserviceaccount.com

resources:
  limits:
    cpu: 1000m
    memory: 2Gi
  requests:
    cpu: 500m
    memory: 1Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70
  targetMemoryUtilizationPercentage: 80

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/rate-limit: "100"
  hosts:
    - host: intellirag.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: intellirag-tls
      hosts:
        - intellirag.example.com

llm:
  model: "Qwen/Qwen3-0.6B-Instruct"
```

**Qdrant StatefulSet (`qdrant/templates/statefulset.yaml`):**
```yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
spec:
  serviceName: qdrant
  replicas: 1
  selector:
    matchLabels:
      app: qdrant
  template:
    metadata:
      labels:
        app: qdrant
    spec:
      containers:
      - name: qdrant
        image: qdrant/qdrant:v1.7.0
        ports:
        - containerPort: 6333
          name: http
        - containerPort: 6334
          name: grpc
        volumeMounts:
        - name: qdrant-storage
          mountPath: /qdrant/storage
        resources:
          limits:
            cpu: 2000m
            memory: 4Gi
          requests:
            cpu: 1000m
            memory: 2Gi
  volumeClaimTemplates:
  - metadata:
      name: qdrant-storage
    spec:
      accessModes: [ "ReadWriteOnce" ]
      storageClassName: standard-rwo
      resources:
        requests:
          storage: 50Gi
```

**Helmfile Configuration:**
```yaml
# kubernetes/helm/helmfile.yaml
repositories:
  - name: prometheus-community
    url: https://prometheus-community.github.io/helm-charts
  - name: grafana
    url: https://grafana.github.io/helm-charts
  - name: jaegertracing
    url: https://jaegertracing.github.io/helm-charts

releases:
  # Core Application
  - name: intellirag
    namespace: intellirag
    chart: ./intellirag
    values:
      - intellirag/values-{{ .Environment.Name }}.yaml
  
  # Vector Database
  - name: qdrant
    namespace: intellirag
    chart: ./qdrant
    values:
      - qdrant/values.yaml
  
  # Observability Stack (Phase 2)
  - name: prometheus
    namespace: monitoring
    chart: prometheus-community/kube-prometheus-stack
    values:
      - monitoring/prometheus-values.yaml
  
  - name: jaeger
    namespace: monitoring
    chart: jaegertracing/jaeger
    values:
      - monitoring/jaeger-values.yaml
  
  - name: loki
    namespace: monitoring
    chart: grafana/loki-stack
    values:
      - monitoring/loki-values.yaml
```

**Actions:**
- [ ] Create Helm chart structure
- [ ] Write deployment manifests with proper resource limits
- [ ] Configure HPA for autoscaling
- [ ] Set up NGINX ingress with SSL/TLS
- [ ] Create ConfigMaps and Secrets
- [ ] Configure workload identity for GCS access
- [ ] Write Qdrant StatefulSet with persistent storage
- [ ] Create Helmfile for multi-chart deployment
- [ ] Test Helm chart locally with minikube/kind
- [ ] Deploy to GKE cluster

**Commands:**
```bash
# Create namespace
kubectl create namespace intellirag

# Install with Helm
helm install intellirag ./kubernetes/helm/intellirag \
  --namespace intellirag \
  --values ./kubernetes/helm/intellirag/values-prod.yaml

# Or use Helmfile
helmfile -e prod apply
```

**Deliverables:**
- ✅ Production-ready Helm charts
- ✅ FastAPI service deployed with 3 replicas
- ✅ Qdrant StatefulSet with persistent storage
- ✅ HPA configured for autoscaling
- ✅ Ingress with SSL/TLS
- ✅ Helmfile for orchestration

**Time Estimate:** 6-8 hours

---

### **Phase 2: MLOps Stack (Days 4-5) - 12-16 hours**

#### 2.1 MLFlow Deployment
**Status:** ❌ **HIGH PRIORITY**

**Purpose:** Model registry, versioning, and experiment tracking

**Architecture:**
```
MLFlow Server
├── Backend: PostgreSQL (metadata store)
├── Artifact Store: GCS bucket
└── Tracking UI: Web interface
```

**MLFlow Helm Chart (`mlops/mlflow/values.yaml`):**
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mlflow-config
data:
  MLFLOW_BACKEND_STORE_URI: "postgresql://mlflow:password@postgresql:5432/mlflow"
  MLFLOW_DEFAULT_ARTIFACT_ROOT: "gs://PROJECT_ID-mlflow-artifacts"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: mlflow-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: mlflow
  template:
    metadata:
      labels:
        app: mlflow
    spec:
      serviceAccountName: mlflow-sa
      containers:
      - name: mlflow
        image: ghcr.io/mlflow/mlflow:v2.9.0
        command:
          - mlflow
          - server
          - --backend-store-uri
          - $(MLFLOW_BACKEND_STORE_URI)
          - --default-artifact-root
          - $(MLFLOW_DEFAULT_ARTIFACT_ROOT)
          - --host
          - "0.0.0.0"
          - --port
          - "5000"
        envFrom:
          - configMapRef:
              name: mlflow-config
        ports:
        - containerPort: 5000
        resources:
          limits:
            cpu: 1000m
            memory: 2Gi
          requests:
            cpu: 500m
            memory: 1Gi
---
apiVersion: v1
kind: Service
metadata:
  name: mlflow
spec:
  selector:
    app: mlflow
  ports:
  - port: 5000
    targetPort: 5000
```

**PostgreSQL for MLFlow (using Helm):**
```bash
helm install postgresql bitnami/postgresql \
  --namespace mlops \
  --set auth.username=mlflow \
  --set auth.password=SECURE_PASSWORD \
  --set auth.database=mlflow \
  --set primary.persistence.size=20Gi
```

**Model Registration Script (`scripts/register_model.py`):**
```python
"""Register models to MLFlow for deployment."""
import mlflow
from mlflow.tracking import MlflowClient

# Configure MLFlow
mlflow.set_tracking_uri("http://mlflow.mlops.svc.cluster.local:5000")

# Register Qwen2.5 model
client = MlflowClient()
model_name = "qwen2-5-7b-instruct"

# Log model metadata
with mlflow.start_run(run_name="vllm-qwen2.5-production") as run:
    mlflow.log_param("model_id", "Qwen/Qwen3-0.6B-Instruct")
    mlflow.log_param("framework", "vllm")
    mlflow.log_param("gpu", "nvidia-t4")
    mlflow.log_param("max_tokens", 8192)
    mlflow.log_param("quantization", "none")
    
    # Log model artifact (Hugging Face model ID)
    mlflow.log_text("Qwen/Qwen3-0.6B-Instruct", "model_id.txt")
    
    # Register model
    model_uri = f"runs:/{run.info.run_id}/model"
    mlflow.register_model(model_uri, model_name)

# Promote to production
client.transition_model_version_stage(
    name=model_name,
    version=1,
    stage="Production"
)
```

**Actions:**
- [ ] Deploy PostgreSQL for MLFlow backend
- [ ] Create GCS bucket for MLFlow artifacts
- [ ] Deploy MLFlow server to GKE
- [ ] Expose MLFlow UI via ingress
- [ ] Register Qwen3-0.6B model
- [ ] Register BGE-M3 embedding model
- [ ] Set up model versioning workflow
- [ ] Integrate MLFlow with CI/CD

**Commands:**
```bash
# Deploy MLFlow
kubectl apply -f kubernetes/mlops/mlflow/

# Register models
python scripts/register_model.py

# Access MLFlow UI
kubectl port-forward -n mlops svc/mlflow 5000:5000
# Open http://localhost:5000
```

**Deliverables:**
- ✅ MLFlow server running on GKE
- ✅ PostgreSQL backend for metadata
- ✅ GCS artifact storage
- ✅ Models registered (Qwen2.5, BGE-M3)
- ✅ UI accessible via ingress

**Time Estimate:** 6-8 hours

---

#### 2.2 DVC Setup
**Status:** ❌ **HIGH PRIORITY**

**Purpose:** Dataset versioning, pipeline tracking

**Configuration (`.dvc/config`):**
```ini
[core]
    remote = gcs
    autostage = true
[remote "gcs"]
    url = gs://PROJECT_ID-dvc-storage
    projectname = PROJECT_ID
```

**Dataset Versioning:**
```bash
# Initialize DVC
dvc init

# Add remote storage
dvc remote add -d gcs gs://PROJECT_ID-dvc-storage

# Track test dataset
dvc add tests/fixtures/
git add tests/fixtures.dvc .gitignore
git commit -m "feat(dvc): track test datasets"

# Push to remote
dvc push
```

**Pipeline Definition (`dvc.yaml`):**
```yaml
stages:
  prepare_data:
    cmd: python scripts/prepare_data.py
    deps:
      - scripts/prepare_data.py
      - data/raw/
    outs:
      - data/processed/
  
  evaluate_embeddings:
    cmd: python scripts/evaluate_embeddings.py
    deps:
      - scripts/evaluate_embeddings.py
      - data/processed/
    metrics:
      - metrics/embedding_quality.json:
          cache: false
    plots:
      - plots/embedding_tsne.png
```

**Actions:**
- [ ] Initialize DVC in repository
- [ ] Create GCS bucket for DVC storage
- [ ] Configure DVC remote
- [ ] Track test datasets
- [ ] Define data pipeline stages
- [ ] Set up pipeline metrics
- [ ] Integrate with CI/CD
- [ ] Document DVC workflow

**Deliverables:**
- ✅ DVC configured with GCS remote
- ✅ Test datasets tracked and versioned
- ✅ Data pipeline defined
- ✅ Metrics tracking enabled

**Time Estimate:** 3-4 hours

---

#### 2.3 KServe Deployment for vLLM
**Status:** ❌ **HIGH PRIORITY**

**Purpose:** Deploy vLLM for LLM inference with autoscaling

**Install KServe:**
```bash
# Install Knative Serving (prerequisite)
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.11.0/serving-crds.yaml
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.11.0/serving-core.yaml

# Install Istio for networking
kubectl apply -l knative.dev/crd-install=true -f https://github.com/knative/net-istio/releases/download/knative-v1.11.0/istio.yaml
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.11.0/net-istio.yaml

# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Install KServe
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.11.0/kserve.yaml
```

**InferenceService Manifest (`kubernetes/kserve/vllm-inference.yaml`):**
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-qwen
  namespace: intellirag
spec:
  predictor:
    model:
      modelFormat:
        name: vllm
      storageUri: "gs://PROJECT_ID-mlflow-artifacts/models/qwen2-5-7b"
      resources:
        limits:
          cpu: "4"
          memory: 16Gi
          nvidia.com/gpu: "1"
        requests:
          cpu: "2"
          memory: 8Gi
          nvidia.com/gpu: "1"
      env:
        - name: VLLM_MODEL_NAME
          value: "Qwen/Qwen3-0.6B-Instruct"
        - name: VLLM_GPU_MEMORY_UTILIZATION
          value: "0.95"
        - name: VLLM_MAX_MODEL_LEN
          value: "8192"
        - name: VLLM_ENABLE_PREFIX_CACHING
          value: "true"
        - name: VLLM_TRUST_REMOTE_CODE
          value: "true"
      nodeSelector:
        cloud.google.com/gke-accelerator: nvidia-tesla-t4
      tolerations:
        - key: nvidia.com/gpu
          operator: Exists
          effect: NoSchedule
  scaleTarget: 1
  scaleMetric: concurrency
  autoscaling:
    minReplicas: 0  # Scale to zero when idle
    maxReplicas: 2
    target: 5  # Target 5 concurrent requests per pod
```

**Actions:**
- [ ] Install Knative Serving + Istio
- [ ] Install cert-manager
- [ ] Install KServe CRDs and controller
- [ ] Create InferenceService for vLLM
- [ ] Configure GPU node affinity
- [ ] Test inference endpoint
- [ ] Set up autoscaling (scale to zero)
- [ ] Monitor cold start times

**Commands:**
```bash
# Deploy InferenceService
kubectl apply -f kubernetes/kserve/vllm-inference.yaml

# Check status
kubectl get inferenceservice -n intellirag

# Test inference
curl -X POST http://vllm-qwen-predictor.intellirag.svc.cluster.local/v1/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "Qwen/Qwen3-0.6B-Instruct", "prompt": "Hello", "max_tokens": 50}'
```

**Deliverables:**
- ✅ KServe + Knative installed
- ✅ vLLM InferenceService deployed
- ✅ GPU utilization optimized (95%)
- ✅ Autoscaling configured (0-2 replicas)
- ✅ OpenAI-compatible API exposed

**Time Estimate:** 6-8 hours

---

### **Phase 3: Observability Stack (Days 6-7) - 12-16 hours**

#### 3.1 Prometheus + Grafana
**Status:** ⚠️ **Basic metrics exist, dashboards needed**

**Install kube-prometheus-stack:**
```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values kubernetes/monitoring/prometheus-values.yaml
```

**Prometheus Configuration (`monitoring/prometheus-values.yaml`):**
```yaml
prometheus:
  prometheusSpec:
    retention: 15d
    storageSpec:
      volumeClaimTemplate:
        spec:
          storageClassName: standard-rwo
          resources:
            requests:
              storage: 50Gi
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    
grafana:
  enabled: true
  adminPassword: SECURE_PASSWORD
  persistence:
    enabled: true
    size: 10Gi
  dashboardProviders:
    dashboardproviders.yaml:
      apiVersion: 1
      providers:
      - name: 'intellirag'
        orgId: 1
        folder: 'IntelliRAG'
        type: file
        disableDeletion: false
        editable: true
        options:
          path: /var/lib/grafana/dashboards/intellirag
  dashboardsConfigMaps:
    intellirag: "grafana-dashboards"

alertmanager:
  enabled: true
  config:
    route:
      receiver: 'slack'
      group_by: ['alertname', 'severity']
    receivers:
    - name: 'slack'
      slack_configs:
      - api_url: 'SLACK_WEBHOOK_URL'
        channel: '#intellirag-alerts'
```

**ServiceMonitor for FastAPI (`monitoring/servicemonitor.yaml`):**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: intellirag-api
  namespace: monitoring
spec:
  selector:
    matchLabels:
      app: intellirag-api
  endpoints:
  - port: http
    path: /metrics
    interval: 30s
```

**Grafana Dashboard - RAG Pipeline (`monitoring/dashboards/rag-pipeline.json`):**
```json
{
  "dashboard": {
    "title": "IntelliRAG Pipeline Metrics",
    "panels": [
      {
        "title": "Ingestion Job Duration (P95)",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(ingestion_job_duration_seconds_bucket[5m]))"
        }]
      },
      {
        "title": "Query Response Time",
        "targets": [{
          "expr": "histogram_quantile(0.95, rate(http_request_duration_seconds_bucket{path=\"/api/v1/query\"}[5m]))"
        }]
      },
      {
        "title": "Error Rate by Stage",
        "targets": [{
          "expr": "rate(ingestion_errors_total[5m])"
        }]
      },
      {
        "title": "Active Ingestion Jobs",
        "targets": [{
          "expr": "ingestion_jobs_active"
        }]
      }
    ]
  }
}
```

**Alert Rules (`monitoring/alerts/intellirag-rules.yaml`):**
```yaml
apiVersion: monitoring.coreos.com/v1
kind: PrometheusRule
metadata:
  name: intellirag-alerts
  namespace: monitoring
spec:
  groups:
  - name: intellirag
    interval: 30s
    rules:
    - alert: HighIngestionLatency
      expr: histogram_quantile(0.95, rate(ingestion_job_duration_seconds_bucket[5m])) > 300
      for: 5m
      labels:
        severity: warning
      annotations:
        summary: "High ingestion latency detected"
        description: "P95 ingestion latency is {{ $value }}s (threshold: 300s)"
    
    - alert: HighErrorRate
      expr: rate(ingestion_errors_total[5m]) > 0.1
      for: 5m
      labels:
        severity: critical
      annotations:
        summary: "High error rate in ingestion pipeline"
        description: "Error rate is {{ $value }} errors/sec"
    
    - alert: VLLMDown
      expr: up{job="vllm-qwen"} == 0
      for: 2m
      labels:
        severity: critical
      annotations:
        summary: "vLLM inference service is down"
```

**Actions:**
- [ ] Install kube-prometheus-stack
- [ ] Configure Prometheus retention and storage
- [ ] Create ServiceMonitors for FastAPI, Qdrant, vLLM
- [ ] Import/create Grafana dashboards:
  - System Overview
  - RAG Pipeline Metrics
  - Ingestion Performance
  - Query Performance
  - Error Tracking
- [ ] Configure alert rules
- [ ] Set up Slack/email alerting
- [ ] Test alerts with simulated failures

**Deliverables:**
- ✅ Prometheus collecting metrics
- ✅ Grafana with 5 custom dashboards
- ✅ Alert rules configured
- ✅ Slack alerting working

**Time Estimate:** 6-8 hours

---

#### 3.2 Jaeger Distributed Tracing
**Status:** ❌ **NOT IMPLEMENTED**

**Install Jaeger Operator:**
```bash
kubectl create namespace observability
kubectl apply -f https://github.com/jaegertracing/jaeger-operator/releases/download/v1.51.0/jaeger-operator.yaml -n observability
```

**Jaeger Instance (`monitoring/jaeger.yaml`):**
```yaml
apiVersion: jaegertracing.io/v1
kind: Jaeger
metadata:
  name: intellirag-jaeger
  namespace: observability
spec:
  strategy: production
  storage:
    type: elasticsearch
    options:
      es:
        server-urls: http://elasticsearch:9200
        index-prefix: jaeger
  ingress:
    enabled: true
    hosts:
      - jaeger.intellirag.example.com
```

**OpenTelemetry Instrumentation (FastAPI):**

**Add to `pyproject.toml`:**
```toml
[project.dependencies]
opentelemetry-api = ">=1.20.0"
opentelemetry-sdk = ">=1.20.0"
opentelemetry-instrumentation-fastapi = ">=0.41b0"
opentelemetry-instrumentation-httpx = ">=0.41b0"
opentelemetry-exporter-jaeger = ">=1.20.0"
```

**Instrumentation Code (`app/core/tracing.py`):**
```python
"""OpenTelemetry tracing configuration."""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

def setup_tracing(app, service_name: str = "intellirag-api"):
    """Configure OpenTelemetry tracing."""
    # Create tracer provider
    provider = TracerProvider()
    trace.set_tracer_provider(provider)
    
    # Configure Jaeger exporter
    jaeger_exporter = JaegerExporter(
        agent_host_name="jaeger-agent.observability.svc.cluster.local",
        agent_port=6831,
    )
    
    # Add span processor
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument httpx (for external API calls)
    HTTPXClientInstrumentor().instrument()
```

**Usage in `app/main.py`:**
```python
from app.core.tracing import setup_tracing

app = FastAPI(title="IntelliRAG API")

# Set up tracing
setup_tracing(app)
```

**Custom Spans for Services:**
```python
# app/services/embedding.py
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

class EmbeddingService:
    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        with tracer.start_as_current_span("embed_texts") as span:
            span.set_attribute("text_count", len(texts))
            span.set_attribute("model", self.model_name)
            
            embeddings = await self._embed(texts)
            
            span.set_attribute("embedding_dimension", len(embeddings[0]))
            return embeddings
```

**Actions:**
- [ ] Install Jaeger operator and instance
- [ ] Deploy Elasticsearch for Jaeger storage
- [ ] Add OpenTelemetry dependencies
- [ ] Implement tracing in FastAPI app
- [ ] Add custom spans to key services:
  - Embedding generation
  - Vector search
  - LLM inference
  - Document processing
- [ ] Configure trace sampling (100% dev, 10% prod)
- [ ] Test end-to-end tracing
- [ ] Create Jaeger dashboards

**Deliverables:**
- ✅ Jaeger deployed with Elasticsearch backend
- ✅ OpenTelemetry instrumentation complete
- ✅ Custom spans in all services
- ✅ Trace correlation with logs
- ✅ Jaeger UI accessible

**Time Estimate:** 6-8 hours

---

#### 3.3 Loki Log Aggregation
**Status:** ❌ **NOT IMPLEMENTED**

**Install Loki Stack:**
```bash
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --values kubernetes/monitoring/loki-values.yaml
```

**Loki Configuration (`monitoring/loki-values.yaml`):**
```yaml
loki:
  enabled: true
  persistence:
    enabled: true
    size: 50Gi
  config:
    auth_enabled: false
    ingester:
      chunk_idle_period: 3m
      chunk_retain_period: 1m
      max_transfer_retries: 0
    limits_config:
      retention_period: 168h  # 7 days
    schema_config:
      configs:
      - from: 2023-01-01
        store: boltdb-shipper
        object_store: gcs
        schema: v11
        index:
          prefix: loki_index_
          period: 24h
    storage_config:
      boltdb_shipper:
        active_index_directory: /loki/boltdb-shipper-active
        cache_location: /loki/boltdb-shipper-cache
      gcs:
        bucket_name: PROJECT_ID-loki-chunks

promtail:
  enabled: true
  config:
    clients:
    - url: http://loki:3100/loki/api/v1/push
    scrape_configs:
    - job_name: kubernetes-pods
      kubernetes_sd_configs:
      - role: pod
      relabel_configs:
      - source_labels: [__meta_kubernetes_pod_label_app]
        target_label: app
      - source_labels: [__meta_kubernetes_namespace]
        target_label: namespace
      - source_labels: [__meta_kubernetes_pod_name]
        target_label: pod
```

**Structured Logging with Trace Correlation:**
```python
# app/core/logging.py
import logging
import json
from opentelemetry import trace

class StructuredLogFormatter(logging.Formatter):
    """Format logs as JSON with trace context."""
    
    def format(self, record):
        # Get current span context
        span = trace.get_current_span()
        trace_id = span.get_span_context().trace_id
        span_id = span.get_span_context().span_id
        
        log_data = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "trace_id": f"{trace_id:032x}" if trace_id else None,
            "span_id": f"{span_id:016x}" if span_id else None,
        }
        
        # Add extra fields
        if hasattr(record, "correlation_id"):
            log_data["correlation_id"] = record.correlation_id
        
        return json.dumps(log_data)
```

**Grafana Explore (Logs + Traces):**
- Link logs to traces via trace_id
- View logs alongside metrics
- Search logs by trace_id, span_id, correlation_id

**Actions:**
- [ ] Install Loki and Promtail
- [ ] Create GCS bucket for Loki chunks
- [ ] Configure log retention (7 days)
- [ ] Update logging to include trace context
- [ ] Configure Grafana Explore
- [ ] Test log querying with Loki
- [ ] Create log-based alerts (e.g., error rate)

**Deliverables:**
- ✅ Loki deployed with GCS backend
- ✅ Promtail collecting pod logs
- ✅ Logs correlated with traces
- ✅ Grafana Explore configured
- ✅ Log retention policy set

**Time Estimate:** 4-5 hours

---

### **Phase 4: CI/CD Pipeline (Days 8-9) - 8-12 hours**

#### 4.1 GitHub Actions Workflow
**Status:** ❌ **NOT IMPLEMENTED**

**Workflow Structure:**
```
.github/workflows/
├── ci.yml              # Test + Lint (on PR)
├── build.yml           # Build Docker image (on merge to develop)
├── deploy-staging.yml  # Deploy to staging (manual)
├── deploy-prod.yml     # Deploy to production (manual)
└── mlops.yml           # Model versioning (on model changes)
```

**CI Workflow (`.github/workflows/ci.yml`):**
```yaml
name: CI - Test & Lint

on:
  pull_request:
    branches: [develop, main]
  push:
    branches: [develop]

jobs:
  test:
    runs-on: ubuntu-latest
    
    services:
      qdrant:
        image: qdrant/qdrant:latest
        ports:
          - 6333:6333
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python 3.12
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install uv
        run: curl -LsSf https://astral.sh/uv/install.sh | sh
      
      - name: Install dependencies
        run: uv sync
      
      - name: Run linting
        run: |
          uv run ruff check app/ tests/
          uv run black --check app/ tests/
      
      - name: Run type checking
        run: uv run mypy app/
      
      - name: Run unit tests
        run: |
          uv run pytest tests/unit/ -v --cov=app --cov-report=xml --cov-report=term-missing
      
      - name: Run integration tests
        env:
          QDRANT_URL: http://localhost:6333
        run: |
          uv run pytest tests/integration/ -v
      
      - name: Check coverage threshold
        run: |
          coverage report --fail-under=80
      
      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: true
```

**Build Workflow (`.github/workflows/build.yml`):**
```yaml
name: Build & Push Docker Image

on:
  push:
    branches: [develop, main]
  workflow_dispatch:

env:
  GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  IMAGE_NAME: intellirag-api

jobs:
  build:
    runs-on: ubuntu-latest
    
    permissions:
      contents: read
      id-token: write
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v2
      
      - name: Configure Docker for GCR
        run: gcloud auth configure-docker
      
      - name: Extract metadata
        id: meta
        uses: docker/metadata-action@v5
        with:
          images: gcr.io/${{ env.GCP_PROJECT_ID }}/${{ env.IMAGE_NAME }}
          tags: |
            type=ref,event=branch
            type=sha,prefix={{branch}}-
            type=semver,pattern={{version}}
      
      - name: Build and push Docker image
        uses: docker/build-push-action@v5
        with:
          context: .
          push: true
          tags: ${{ steps.meta.outputs.tags }}
          labels: ${{ steps.meta.outputs.labels }}
          cache-from: type=gha
          cache-to: type=gha,mode=max
      
      - name: Output image digest
        run: echo "Image pushed with digest ${{ steps.docker_build.outputs.digest }}"
```

**Deploy to Staging (`.github/workflows/deploy-staging.yml`):**
```yaml
name: Deploy to Staging

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Docker image tag to deploy'
        required: true
        default: 'develop-latest'

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: staging
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Get GKE credentials
        uses: google-github-actions/get-gke-credentials@v2
        with:
          cluster_name: intellirag-staging
          location: us-central1
      
      - name: Deploy with Helm
        run: |
          helm upgrade --install intellirag ./kubernetes/helm/intellirag \
            --namespace intellirag \
            --create-namespace \
            --values ./kubernetes/helm/intellirag/values-staging.yaml \
            --set image.tag=${{ github.event.inputs.image_tag }} \
            --wait \
            --timeout 10m
      
      - name: Verify deployment
        run: |
          kubectl rollout status deployment/intellirag -n intellirag
          kubectl get pods -n intellirag
      
      - name: Run smoke tests
        run: |
          kubectl wait --for=condition=ready pod -l app=intellirag -n intellirag --timeout=5m
          # Add smoke test commands here
```

**Deploy to Production (`.github/workflows/deploy-prod.yml`):**
```yaml
name: Deploy to Production

on:
  workflow_dispatch:
    inputs:
      image_tag:
        description: 'Docker image tag to deploy'
        required: true
      approval:
        description: 'Type "APPROVE" to confirm production deployment'
        required: true

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: production
    if: github.event.inputs.approval == 'APPROVE'
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Authenticate to Google Cloud
        uses: google-github-actions/auth@v2
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Get GKE credentials
        uses: google-github-actions/get-gke-credentials@v2
        with:
          cluster_name: intellirag-prod
          location: us-central1
      
      - name: Deploy with Helm
        run: |
          helm upgrade --install intellirag ./kubernetes/helm/intellirag \
            --namespace intellirag \
            --create-namespace \
            --values ./kubernetes/helm/intellirag/values-prod.yaml \
            --set image.tag=${{ github.event.inputs.image_tag }} \
            --wait \
            --timeout 15m
      
      - name: Verify deployment
        run: |
          kubectl rollout status deployment/intellirag -n intellirag
          kubectl get pods -n intellirag
      
      - name: Run health checks
        run: |
          kubectl wait --for=condition=ready pod -l app=intellirag -n intellirag --timeout=5m
          # Run comprehensive health checks
      
      - name: Notify deployment
        uses: slackapi/slack-github-action@v1
        with:
          payload: |
            {
              "text": "✅ IntelliRAG deployed to production",
              "blocks": [
                {
                  "type": "section",
                  "text": {
                    "type": "mrkdwn",
                    "text": "*Deployment Status:* Success\n*Image:* ${{ github.event.inputs.image_tag }}\n*Deployed by:* ${{ github.actor }}"
                  }
                }
              ]
            }
        env:
          SLACK_WEBHOOK_URL: ${{ secrets.SLACK_WEBHOOK_URL }}
```

**MLOps Workflow (`.github/workflows/mlops.yml`):**
```yaml
name: MLOps - Model Registration

on:
  push:
    paths:
      - 'models/**'
  workflow_dispatch:

jobs:
  register_model:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v4
      
      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          pip install mlflow boto3
      
      - name: Register model to MLFlow
        env:
          MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
        run: |
          python scripts/register_model.py
      
      - name: Update DVC
        run: |
          pip install dvc dvc-gs
          dvc pull
          dvc push
```

**GitHub Secrets Required:**
```
GCP_PROJECT_ID
GCP_SA_KEY
MLFLOW_TRACKING_URI
SLACK_WEBHOOK_URL
```

**Actions:**
- [ ] Create all workflow files
- [ ] Configure GitHub secrets
- [ ] Set up branch protection rules (require CI to pass)
- [ ] Test CI workflow on sample PR
- [ ] Test build workflow
- [ ] Test manual staging deployment
- [ ] Test manual production deployment
- [ ] Configure Slack notifications
- [ ] Document deployment process

**Deliverables:**
- ✅ CI pipeline (test + lint) on PRs
- ✅ Build pipeline for Docker images
- ✅ Manual deployment workflows (staging + prod)
- ✅ MLOps workflow for model versioning
- ✅ Slack notifications

**Time Estimate:** 8-10 hours

---

### **Phase 5: Production Hardening (Days 10-11) - 8-12 hours**

#### 5.1 Secrets Management
**Status:** ❌ **REQUIRED**

**Google Secret Manager Integration:**

**Create Secrets:**
```bash
# Create secrets in GCP
echo -n "MLFLOW_PASSWORD" | gcloud secrets create mlflow-password --data-file=-
echo -n "POSTGRES_PASSWORD" | gcloud secrets create postgres-password --data-file=-
echo -n "QDRANT_API_KEY" | gcloud secrets create qdrant-api-key --data-file=-
```

**Workload Identity Binding:**
```bash
# Bind Kubernetes SA to GCP SA
gcloud iam service-accounts add-iam-policy-binding \
  intellirag-sa@PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:PROJECT_ID.svc.id.goog[intellirag/intellirag-sa]"
```

**External Secrets Operator (ESO):**
```bash
# Install ESO
helm repo add external-secrets https://charts.external-secrets.io
helm install external-secrets external-secrets/external-secrets \
  --namespace external-secrets-system \
  --create-namespace
```

**SecretStore Configuration (`kubernetes/secrets/secretstore.yaml`):**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: SecretStore
metadata:
  name: gcpsm-secret-store
  namespace: intellirag
spec:
  provider:
    gcpsm:
      projectID: PROJECT_ID
      auth:
        workloadIdentity:
          clusterLocation: us-central1
          clusterName: intellirag-prod
          serviceAccountRef:
            name: intellirag-sa
```

**ExternalSecret (`kubernetes/secrets/externalsecret.yaml`):**
```yaml
apiVersion: external-secrets.io/v1beta1
kind: ExternalSecret
metadata:
  name: intellirag-secrets
  namespace: intellirag
spec:
  refreshInterval: 1h
  secretStoreRef:
    name: gcpsm-secret-store
    kind: SecretStore
  target:
    name: intellirag-secrets
    creationPolicy: Owner
  data:
  - secretKey: mlflow-password
    remoteRef:
      key: mlflow-password
  - secretKey: postgres-password
    remoteRef:
      key: postgres-password
  - secretKey: qdrant-api-key
    remoteRef:
      key: qdrant-api-key
```

**Actions:**
- [ ] Create secrets in Google Secret Manager
- [ ] Install External Secrets Operator
- [ ] Configure SecretStore with workload identity
- [ ] Create ExternalSecrets for all sensitive data
- [ ] Update Helm charts to use secrets
- [ ] Rotate test secrets to verify setup
- [ ] Document secret management process

**Deliverables:**
- ✅ All secrets stored in Google Secret Manager
- ✅ External Secrets Operator syncing secrets
- ✅ No hardcoded secrets in code or configs
- ✅ Secret rotation process documented

**Time Estimate:** 3-4 hours

---

#### 5.2 Network Policies & Security
**Status:** ❌ **REQUIRED**

**Network Policies:**

**Default Deny All (`kubernetes/network-policies/deny-all.yaml`):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: intellirag
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

**Allow FastAPI → Qdrant (`kubernetes/network-policies/allow-fastapi-qdrant.yaml`):**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-fastapi-qdrant
  namespace: intellirag
spec:
  podSelector:
    matchLabels:
      app: intellirag-api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: qdrant
    ports:
    - protocol: TCP
      port: 6333
```

**Allow FastAPI → KServe vLLM:**
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-fastapi-vllm
  namespace: intellirag
spec:
  podSelector:
    matchLabels:
      app: intellirag-api
  policyTypes:
  - Egress
  egress:
  - to:
    - podSelector:
        matchLabels:
          serving.kserve.io/inferenceservice: vllm-qwen
    ports:
    - protocol: TCP
      port: 8000
```

**Pod Security Standards:**

**Enable PSS for Namespace:**
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: intellirag
  labels:
    pod-security.kubernetes.io/enforce: restricted
    pod-security.kubernetes.io/audit: restricted
    pod-security.kubernetes.io/warn: restricted
```

**SecurityContext in Deployment:**
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
  capabilities:
    drop:
    - ALL
```

**Actions:**
- [ ] Create network policies (default deny + allow rules)
- [ ] Enable Pod Security Standards (restricted)
- [ ] Add security contexts to all deployments
- [ ] Test network connectivity
- [ ] Enable GKE Workload Identity
- [ ] Configure IAM least privilege
- [ ] Run security scan (trivy)

**Deliverables:**
- ✅ Network policies implemented
- ✅ Pod Security Standards enforced
- ✅ Workload Identity configured
- ✅ Security scan passing

**Time Estimate:** 3-4 hours

---

#### 5.3 Rate Limiting & API Throttling
**Status:** ❌ **REQUIRED**

**NGINX Ingress Rate Limiting:**

**Ingress Annotations (`kubernetes/helm/intellirag/templates/ingress.yaml`):**
```yaml
annotations:
  nginx.ingress.kubernetes.io/rate-limit: "100"  # 100 req/sec per IP
  nginx.ingress.kubernetes.io/limit-rps: "10"    # 10 req/sec burst
  nginx.ingress.kubernetes.io/limit-connections: "50"  # 50 concurrent connections
  nginx.ingress.kubernetes.io/limit-whitelist: "10.0.0.0/8"  # Whitelist internal IPs
```

**Application-Level Rate Limiting (FastAPI):**

**Add to `pyproject.toml`:**
```toml
slowapi = ">=0.1.9"
```

**Middleware (`app/api/middleware/rate_limit.py`):**
```python
"""Rate limiting middleware using SlowAPI."""
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from fastapi import Request

# Create limiter instance
limiter = Limiter(key_func=get_remote_address)

def setup_rate_limiting(app):
    """Configure rate limiting for FastAPI app."""
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Usage in endpoints
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/query")
@limiter.limit("10/minute")  # 10 queries per minute per IP
async def query_endpoint(request: Request, query: QueryRequest):
    pass
```

**Actions:**
- [ ] Configure NGINX ingress rate limiting
- [ ] Implement application-level rate limiting
- [ ] Set rate limits per endpoint:
  - /api/v1/upload: 20/minute
  - /api/v1/ingest: 10/minute
  - /api/v1/query: 30/minute
- [ ] Test rate limiting with load tests
- [ ] Add rate limit headers to responses

**Deliverables:**
- ✅ NGINX rate limiting configured
- ✅ Application rate limiting implemented
- ✅ Different limits per endpoint
- ✅ Rate limit headers in responses

**Time Estimate:** 2-3 hours

---

### **Phase 6: Testing & Documentation (Days 12-14) - 8-12 hours**

#### 6.1 End-to-End Testing
**Status:** ⚠️ **Basic tests exist, deployment tests needed**

**Deployment Smoke Tests (`tests/deployment/test_smoke.py`):**
```python
"""Smoke tests for deployed services."""
import pytest
import httpx
from kubernetes import client, config

@pytest.fixture
def api_base_url(request):
    """Get API base URL from command line or env."""
    return request.config.getoption("--api-url", "http://localhost:8000")

@pytest.mark.asyncio
async def test_health_endpoint(api_base_url):
    """Health endpoint should return 200."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{api_base_url}/health")
        assert response.status_code == 200

@pytest.mark.asyncio
async def test_upload_ingest_query_flow(api_base_url):
    """Full E2E flow: upload → ingest → query."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        # 1. Upload document
        files = {"file": ("test.txt", "Hello IntelliRAG", "text/plain")}
        upload_response = await client.post(
            f"{api_base_url}/api/v1/upload",
            files=files,
            params={"collection_name": "test"}
        )
        assert upload_response.status_code == 200
        file_id = upload_response.json()["file_id"]
        
        # 2. Ingest document
        ingest_response = await client.post(
            f"{api_base_url}/api/v1/ingest",
            json={"file_id": file_id, "collection_name": "test"}
        )
        assert ingest_response.status_code == 202
        job_id = ingest_response.json()["job_id"]
        
        # 3. Wait for ingestion to complete
        import asyncio
        for _ in range(60):  # Wait up to 60 seconds
            status_response = await client.get(
                f"{api_base_url}/api/v1/ingest/status/{job_id}"
            )
            status = status_response.json()["status"]
            if status == "completed":
                break
            await asyncio.sleep(1)
        assert status == "completed"
        
        # 4. Query
        query_response = await client.post(
            f"{api_base_url}/api/v1/query",
            json={"query": "What is IntelliRAG?", "collection_name": "test"}
        )
        assert query_response.status_code == 200
        assert "answer" in query_response.json()

def test_kubernetes_deployments():
    """All deployments should be ready."""
    config.load_incluster_config()
    apps_v1 = client.AppsV1Api()
    
    deployments = apps_v1.list_namespaced_deployment(namespace="intellirag")
    for deployment in deployments.items:
        assert deployment.status.ready_replicas >= 1

def test_prometheus_targets():
    """Prometheus should scrape all targets."""
    # Test that Prometheus is scraping FastAPI /metrics
    pass

def test_jaeger_traces():
    """Jaeger should receive traces."""
    # Test that Jaeger received traces from test requests
    pass
```

**Load Testing (`tests/load/locustfile.py`):**
```python
"""Load testing with Locust."""
from locust import HttpUser, task, between

class IntelliRAGUser(HttpUser):
    wait_time = between(1, 3)
    
    @task(3)
    def query(self):
        """Query endpoint (most common)."""
        self.client.post("/api/v1/query", json={
            "query": "What is machine learning?",
            "collection_name": "docs"
        })
    
    @task(1)
    def upload(self):
        """Upload endpoint (less frequent)."""
        files = {"file": ("test.txt", "Test content", "text/plain")}
        self.client.post("/api/v1/upload", files=files, params={"collection_name": "test"})
```

**Actions:**
- [ ] Create deployment smoke tests
- [ ] Create load tests with Locust
- [ ] Run smoke tests against staging
- [ ] Run load tests (100 concurrent users)
- [ ] Verify autoscaling behavior
- [ ] Test failure scenarios (pod crash, network issues)
- [ ] Document test results

**Deliverables:**
- ✅ Smoke tests passing in staging
- ✅ Load tests completed (100+ users)
- ✅ Autoscaling verified
- ✅ Failure recovery tested

**Time Estimate:** 4-5 hours

---

#### 6.2 Documentation
**Status:** ⚠️ **Partial, deployment docs needed**

**Documentation to Create:**

1. **Deployment Guide** (`docs/deployment/deployment-guide.md`)
   - Prerequisites
   - Terraform setup
   - Helm deployment
   - MLOps configuration
   - Observability setup

2. **Operations Runbook** (`docs/deployment/operations-runbook.md`)
   - Starting/stopping services
   - Scaling guidelines
   - Monitoring and alerting
   - Troubleshooting common issues
   - Incident response procedures

3. **API Documentation** (`docs/api/api-reference.md`)
   - Endpoint specifications
   - Request/response examples
   - Rate limits
   - Error codes
   - Authentication (if applicable)

4. **Cost Optimization** (`docs/deployment/cost-optimization.md`)
   - Current cost breakdown
   - Optimization strategies
   - Monitoring costs
   - Budget alerts

**Actions:**
- [ ] Write deployment guide
- [ ] Write operations runbook
- [ ] Generate OpenAPI spec (FastAPI auto-generates)
- [ ] Write cost optimization guide
- [ ] Update CLAUDE.md with deployment info
- [ ] Create architecture diagrams (draw.io)

**Deliverables:**
- ✅ Complete deployment documentation
- ✅ Operations runbook
- ✅ API reference
- ✅ Cost optimization guide
- ✅ Updated architecture diagrams

**Time Estimate:** 4-6 hours

---

## 📊 Final Checklist

### Infrastructure
- [ ] GKE Autopilot cluster provisioned (Terraform)
- [ ] GPU node pool configured (T4, preemptible)
- [ ] VPC and networking set up
- [ ] GCS buckets created (documents, mlflow, dvc, loki)
- [ ] IAM and service accounts configured

### Application
- [ ] Docker image built and pushed to GCR
- [ ] FastAPI deployed with 3 replicas
- [ ] Qdrant StatefulSet running
- [ ] NGINX ingress with SSL/TLS
- [ ] HPA configured (2-10 replicas)

### MLOps
- [ ] MLFlow deployed with PostgreSQL backend
- [ ] Models registered (Qwen2.5, BGE-M3)
- [ ] DVC configured for dataset versioning
- [ ] KServe + vLLM InferenceService deployed
- [ ] Autoscaling configured (0-2 replicas, scale to zero)

### Observability
- [ ] Prometheus collecting metrics
- [ ] Grafana dashboards created (5 dashboards)
- [ ] Jaeger distributed tracing enabled
- [ ] Loki log aggregation configured
- [ ] Alert rules set up with Slack notifications

### CI/CD
- [ ] GitHub Actions workflows created
- [ ] CI pipeline (test + lint) working
- [ ] Build pipeline pushing to GCR
- [ ] Manual deployment workflows (staging + prod)
- [ ] MLOps workflow for model versioning

### Security
- [ ] Secrets in Google Secret Manager
- [ ] External Secrets Operator syncing
- [ ] Network policies enforced
- [ ] Pod Security Standards enabled
- [ ] Workload Identity configured
- [ ] Rate limiting implemented

### Testing
- [ ] Smoke tests passing
- [ ] Load tests completed (100+ users)
- [ ] E2E flow verified (upload → ingest → query)
- [ ] Autoscaling behavior validated
- [ ] Failure recovery tested

### Documentation
- [ ] Deployment guide written
- [ ] Operations runbook created
- [ ] API documentation generated
- [ ] Cost optimization guide published
- [ ] Architecture diagrams updated

---

## 💰 Cost Estimate & Optimization

### Monthly Cost Breakdown

| Component | Configuration | Monthly Cost | Optimization Notes |
|-----------|--------------|--------------|-------------------|
| **GKE Autopilot** | 3x e2-medium nodes | $120 | Use spot instances where possible |
| **GPU Node Pool** | 1x n1-standard-4 + T4 (preemptible) | $120 | Scale to zero when idle (KServe) |
| **GCS Storage** | 500GB standard | $10 | Lifecycle policies: archive > 90 days |
| **Persistent Disks** | 150GB SSD | $30 | Qdrant (50GB), Prometheus (50GB), MLFlow (20GB), Loki (30GB) |
| **Load Balancer** | 1x Network LB | $20 | Single ingress for all services |
| **Cloud Logging** | 50GB/month | $10 | 7-day retention, export to Loki |
| **Secrets Manager** | 10 secrets | $5 | Only production secrets |
| **Networking** | Data transfer | $10 | Minimize cross-region traffic |
| **Buffer** | Unexpected costs | $5 | 5% buffer |
| **Total** | | **$330** | **⚠️ $30 over budget** |

### Cost Optimization Strategies to Hit $300

**Option 1: Reduce GPU Node Pool (Save $40/month)**
- Use 1x e2-medium for CPU inference (Qwen3-0.6B) instead of GPU
- Trade-off: 10x slower inference, lower throughput
- **New Total: $290/month** ✅

**Option 2: Reduce Observability (Save $30/month)**
- Use lightweight Loki alternative or external SaaS
- Reduce Prometheus retention to 7 days (10GB disk)
- **New Total: $300/month** ✅

**Option 3: Hybrid Deployment (Recommended)**
- Keep local vLLM for development/testing
- Deploy to GKE without GPU node pool initially
- Add GPU when budget allows
- **New Total: $290/month** ✅

**Recommendation:** Start with Option 3 (Hybrid), monitor usage for 1 month, then add GPU node pool if needed.

---

## 📅 Implementation Timeline

### Week 1: Infrastructure Foundation
- **Day 0 (2-3h):** GCP setup, enable APIs, service accounts
- **Day 1 (8-10h):** Terraform for GKE, Dockerize FastAPI
- **Day 2 (6-8h):** Helm charts, deploy to GKE
- **Day 3 (4-5h):** Test deployment, fix issues

### Week 2: MLOps & Observability
- **Day 4 (6-8h):** MLFlow deployment, model registration
- **Day 5 (6-8h):** DVC setup, KServe for vLLM
- **Day 6 (6-8h):** Prometheus + Grafana, dashboards
- **Day 7 (6-8h):** Jaeger tracing, Loki logging

### Week 3: CI/CD & Hardening
- **Day 8 (5-6h):** GitHub Actions CI/CD
- **Day 9 (3-4h):** Secrets management, security
- **Day 10 (3-4h):** Network policies, rate limiting
- **Day 11 (2-3h):** Final testing

### Week 4: Testing & Documentation
- **Day 12 (4-5h):** E2E tests, load tests
- **Day 13 (4-6h):** Documentation
- **Day 14 (2-3h):** Final review, go-live preparation

**Total Estimated Time:** 75-95 hours over 14 days

---

## 🚀 Next Steps

1. **Review this plan** with stakeholders
2. **Get approval** for budget ($300/month with optimizations)
3. **Set up GCP project** (if not already done)
4. **Start Phase 0** (GCP setup)
5. **Follow TDD methodology** for all code changes
6. **Track progress** in TODO list

---

## 📞 Support & Questions

For any questions or issues during deployment:
1. Check the operations runbook (to be created)
2. Review Grafana dashboards for system health
3. Check Slack #intellirag-alerts channel
4. Escalate to on-call engineer if critical

---

**Document Version:** 1.0  
**Last Updated:** 2025-11-02  
**Author:** IntelliRAG Development Team  
**Approval Status:** Pending Review
