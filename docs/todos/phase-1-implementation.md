# Phase 1: Application Deployment to GKE - Implementation Plan

**Created**: 2025-11-18
**Project**: IntelliRAG
**Phase**: 1 - Application Deployment
**Timeline**: 5-7 days
**Priority**: CRITICAL - Deployment Blocker

---

## 📊 Executive Summary

### Current State Assessment

**What Exists (Complete):**
- ✅ FastAPI application fully implemented (app/main.py)
- ✅ Health endpoint: GET /health (returns {"status": "healthy", "service": "IntelliRAG"})
- ✅ Metrics endpoint: GET /metrics (Prometheus format)
- ✅ 3 API routers: upload, ingest, query (v1)
- ✅ Observability instrumentation in code (OpenTelemetry, Prometheus, structured logging)
- ✅ 50+ unit tests with >80% coverage
- ✅ Terraform configuration for GKE (not deployed)
- ✅ Observability Helm charts ready (Prometheus, Grafana, Jaeger, Loki)
- ✅ docker-compose.yml for local development

**What's Missing (Required for Deployment):**
- ❌ Dockerfile for FastAPI application
- ❌ Helm chart for application deployment
- ❌ Kubernetes manifests (Deployment, Service, ConfigMap, Secret)
- ❌ GKE cluster (Terraform not applied)
- ❌ Container registry setup
- ❌ CI/CD pipeline
- ❌ Production environment configuration

---

## 🎯 Phase 1 Objectives

Deploy the IntelliRAG FastAPI application to GKE with:
1. Containerized application with production-ready Dockerfile
2. Helm chart for reproducible deployments
3. Health checks and readiness probes
4. Observability stack integration
5. Secure configuration management
6. Basic CI/CD for automated deployments

---

## 🏗️ Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                    GKE Cluster (asia-southeast1)            │
│                                                             │
│  Namespace: intellirag                                      │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Deployment: intellirag-api                         │    │
│  │  - Replicas: 3                                      │    │
│  │  - Image: gcr.io/PROJECT/intellirag:VERSION        │    │
│  │  - Resources: 1CPU/2Gi per pod                     │    │
│  │  - Health: /health                                  │    │
│  │  - Ready: /health                                   │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Service: intellirag-api-service                    │    │
│  │  - Type: ClusterIP                                  │    │
│  │  - Port: 80 → 8000                                  │    │
│  └─────────────────────────────────────────────────────┘    │
│                           │                                 │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Ingress: intellirag-ingress (NGINX)                │    │
│  │  - Host: api.intellirag.example.com                 │    │
│  │  - TLS: cert-manager                                │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Namespace: qdrant                                          │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  StatefulSet: qdrant                                │    │
│  │  - PVC: 10Gi SSD                                    │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                             │
│  Namespace: observability                                   │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Prometheus, Grafana, Jaeger, Loki (Helm)           │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 Prerequisites Checklist

### ✅ Already Completed
- [x] GCP Project: intellirag-aide1-capstone
- [x] Application code complete
- [x] Test coverage >80%
- [x] Terraform configuration ready
- [x] Observability Helm charts ready

### ❌ To Be Completed
- [ ] GKE cluster provisioned
- [ ] Container registry enabled
- [ ] Service accounts created
- [ ] DNS configured
- [ ] SSL certificates

---

## 🚀 Implementation Tasks

### PRIORITY 1: Infrastructure Foundation (Day 1)

#### Task 1.1: Provision GKE Cluster
**TDD Approach**: Write infrastructure tests first
```bash
# Test: Verify cluster exists and is accessible
# Test: Verify node pool configuration
# Test: Verify network policies
```

**Implementation Steps**:
1. Create Terraform state bucket:
   ```bash
   gsutil mb -p intellirag-aide1-capstone -c STANDARD \
     -l asia-southeast1 gs://intellirag-aide1-capstone-terraform-state
   ```
2. Initialize and apply Terraform:
   ```bash
   cd terraform/
   terraform init
   terraform plan -out=tfplan
   terraform apply tfplan
   ```
3. Get cluster credentials:
   ```bash
   gcloud container clusters get-credentials intellirag-cluster \
     --region asia-southeast1 \
     --project intellirag-aide1-capstone
   ```
4. Create namespaces:
   ```bash
   kubectl apply -f kubernetes/namespaces.yaml
   ```

**Risks**:
- GCP quota limits
- Network configuration issues
- IAM permissions

---

### PRIORITY 2: Application Containerization (Day 2)

#### Task 2.1: Create Production Dockerfile
**TDD Approach**:
```python
# tests/test_dockerfile.py
def test_dockerfile_exists():
    assert Path("Dockerfile").exists()

def test_dockerfile_uses_python_312():
    # Verify base image

def test_dockerfile_has_healthcheck():
    # Verify HEALTHCHECK instruction
```

**Implementation**:
Create `Dockerfile`:
```dockerfile
# Multi-stage build for smaller image
FROM python:3.12-slim AS builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN pip install uv && \
    uv pip install --system --no-cache -r <(uv pip compile pyproject.toml)

# Production stage
FROM python:3.12-slim

# Security: Run as non-root user
RUN useradd -m -u 1000 appuser

WORKDIR /app

# Copy dependencies from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=appuser:appuser app/ ./app/

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Task 2.2: Build and Push Container Image
**Test**: Verify image builds and runs locally
```bash
# Build image
docker build -t intellirag:latest .

# Test locally
docker run -p 8000:8000 intellirag:latest

# Verify health endpoint
curl http://localhost:8000/health
```

**Push to Registry**:
```bash
# Tag for GCR
docker tag intellirag:latest gcr.io/intellirag-aide1-capstone/intellirag:v0.1.0

# Push
docker push gcr.io/intellirag-aide1-capstone/intellirag:v0.1.0
```

---

### PRIORITY 3: Helm Chart Creation (Day 3)

#### Task 3.1: Create Helm Chart Structure
**TDD Approach**: Test chart structure and templating
```bash
# Test: helm lint passes
# Test: helm template generates valid K8s manifests
# Test: values.yaml contains all required configs
```

**Implementation**:
```bash
# Create chart
helm create kubernetes/charts/intellirag

# Directory structure
kubernetes/charts/intellirag/
├── Chart.yaml
├── values.yaml
├── templates/
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secret.yaml
│   ├── ingress.yaml
│   ├── hpa.yaml
│   └── _helpers.tpl
```

#### Task 3.2: Configure Chart Values
**values.yaml**:
```yaml
replicaCount: 3

image:
  repository: gcr.io/intellirag-aide1-capstone/intellirag
  pullPolicy: IfNotPresent
  tag: "v0.1.0"

service:
  type: ClusterIP
  port: 80
  targetPort: 8000

ingress:
  enabled: true
  className: "nginx"
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
  hosts:
    - host: api.intellirag.example.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: intellirag-tls
      hosts:
        - api.intellirag.example.com

resources:
  limits:
    cpu: 2000m
    memory: 4Gi
  requests:
    cpu: 1000m
    memory: 2Gi

autoscaling:
  enabled: true
  minReplicas: 2
  maxReplicas: 10
  targetCPUUtilizationPercentage: 70

env:
  - name: QDRANT_URL
    value: "http://qdrant.qdrant.svc.cluster.local:6333"
  - name: VLLM_BASE_URL
    value: "http://vllm.kserve.svc.cluster.local:8000/v1"
  - name: GCS_PROJECT_ID
    value: "intellirag-aide1-capstone"
  - name: GCS_BUCKET_NAME
    value: "intellirag-documents"
  - name: JAEGER_HOST
    value: "jaeger-collector.observability.svc.cluster.local"
  - name: EMBEDDING_SERVICE_URL
    value: "http://embedding.kserve.svc.cluster.local:8001"

livenessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 10
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: http
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

### PRIORITY 4: Deploy Observability Stack (Day 4)

#### Task 4.1: Deploy Observability Components
**Test**: Verify each component is accessible
```bash
# Deploy observability stack
cd kubernetes/observability/charts
./deploy.sh

# Verify pods
kubectl get pods -n observability

# Port-forward for testing
kubectl port-forward -n observability svc/prometheus-server 9090:80
kubectl port-forward -n observability svc/grafana 3000:80
```

#### Task 4.2: Configure Application Integration
**Test**: Verify metrics are being scraped
```python
# tests/integration/test_observability.py
def test_prometheus_scrapes_app_metrics():
    # Query Prometheus for app metrics

def test_jaeger_receives_traces():
    # Verify traces in Jaeger

def test_loki_receives_logs():
    # Query Loki for app logs
```

---

### PRIORITY 5: Deploy Qdrant Vector Database (Day 5)

#### Task 5.1: Create Qdrant StatefulSet
**Implementation**: `kubernetes/qdrant/statefulset.yaml`
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: qdrant
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant
  namespace: qdrant
spec:
  type: ClusterIP
  ports:
    - port: 6333
      targetPort: 6333
      name: http
    - port: 6334
      targetPort: 6334
      name: grpc
  selector:
    app: qdrant
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
  namespace: qdrant
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
        image: qdrant/qdrant:latest
        ports:
        - containerPort: 6333
          name: http
        - containerPort: 6334
          name: grpc
        volumeMounts:
        - name: qdrant-storage
          mountPath: /qdrant/storage
        resources:
          requests:
            memory: "1Gi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "1000m"
  volumeClaimTemplates:
  - metadata:
      name: qdrant-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: "fast-ssd"
      resources:
        requests:
          storage: 10Gi
```

---

### PRIORITY 6: Application Deployment (Day 6)

#### Task 6.1: Deploy Application with Helm
**Test**: Verify deployment success
```bash
# Deploy application
helm install intellirag kubernetes/charts/intellirag \
  --namespace intellirag \
  --create-namespace

# Verify pods are running
kubectl get pods -n intellirag

# Check logs
kubectl logs -n intellirag -l app=intellirag

# Test endpoints
kubectl port-forward -n intellirag svc/intellirag 8000:80
curl http://localhost:8000/health
curl http://localhost:8000/metrics
```

#### Task 6.2: Configure Ingress and TLS
**Test**: Verify external access
```bash
# Install cert-manager for TLS
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Apply ingress
kubectl apply -f kubernetes/ingress.yaml

# Verify certificate issued
kubectl get certificate -n intellirag
```

---

### PRIORITY 7: CI/CD Pipeline (Day 7)

#### Task 7.1: Create GitHub Actions Workflow
**Implementation**: `.github/workflows/deploy.yml`
```yaml
name: Build and Deploy

on:
  push:
    branches: [main, develop]
  pull_request:
    branches: [main]

env:
  PROJECT_ID: intellirag-aide1-capstone
  GKE_CLUSTER: intellirag-cluster
  GKE_ZONE: asia-southeast1
  IMAGE: intellirag

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.12'

    - name: Install dependencies
      run: |
        pip install uv
        uv pip install -r requirements.txt
        uv pip install -r requirements-dev.txt

    - name: Run tests
      run: |
        pytest --cov=app --cov-report=xml --cov-fail-under=80

    - name: Upload coverage
      uses: codecov/codecov-action@v3

  build-and-push:
    needs: test
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ${{ env.PROJECT_ID }}

    - name: Configure Docker
      run: gcloud auth configure-docker

    - name: Build and Push
      run: |
        docker build -t gcr.io/$PROJECT_ID/$IMAGE:$GITHUB_SHA .
        docker push gcr.io/$PROJECT_ID/$IMAGE:$GITHUB_SHA

    - name: Update Helm values
      run: |
        sed -i "s|tag:.*|tag: $GITHUB_SHA|" kubernetes/charts/intellirag/values.yaml

  deploy:
    needs: build-and-push
    if: github.ref == 'refs/heads/main'
    runs-on: ubuntu-latest

    steps:
    - uses: actions/checkout@v3

    - name: Set up Cloud SDK
      uses: google-github-actions/setup-gcloud@v1
      with:
        service_account_key: ${{ secrets.GCP_SA_KEY }}
        project_id: ${{ env.PROJECT_ID }}

    - name: Get GKE credentials
      run: |
        gcloud container clusters get-credentials $GKE_CLUSTER \
          --zone $GKE_ZONE --project $PROJECT_ID

    - name: Deploy with Helm
      run: |
        helm upgrade --install intellirag kubernetes/charts/intellirag \
          --namespace intellirag \
          --set image.tag=$GITHUB_SHA \
          --wait
```

---

## 🧪 Testing Strategy

### Unit Tests (Existing - Maintain)
- All existing 50+ unit tests must pass
- Coverage must remain >80%
- Add tests for new configuration code

### Integration Tests (New)
```python
# tests/integration/test_deployment.py
class TestDeployment:
    def test_health_endpoint_accessible():
        """Test /health returns 200"""

    def test_metrics_endpoint_accessible():
        """Test /metrics returns Prometheus metrics"""

    def test_can_connect_to_qdrant():
        """Test Qdrant connection from pod"""

    def test_can_access_gcs():
        """Test GCS bucket access with service account"""

    def test_observability_integration():
        """Test metrics appear in Prometheus"""
```

### End-to-End Tests
```python
# tests/e2e/test_full_pipeline.py
def test_document_upload_and_query():
    """Test complete RAG pipeline in K8s"""
    # 1. Upload document
    # 2. Wait for processing
    # 3. Query document
    # 4. Verify response
```

---

## 🔒 Security Considerations

1. **Secrets Management**:
   - Use Kubernetes Secrets for sensitive configs
   - Implement Google Secret Manager for API keys
   - Never commit secrets to repository

2. **Network Security**:
   - Configure network policies
   - Use private GKE cluster
   - Implement rate limiting on ingress

3. **Container Security**:
   - Run containers as non-root user
   - Use minimal base images
   - Regular vulnerability scanning

4. **Access Control**:
   - RBAC for service accounts
   - Workload Identity for GCP access
   - Least privilege principle

---

## 📊 Success Metrics

### Deployment Success Criteria
- [ ] All pods running and healthy
- [ ] Health checks passing
- [ ] Metrics being collected
- [ ] Logs aggregated in Loki
- [ ] Traces visible in Jaeger
- [ ] External API accessible via ingress
- [ ] TLS certificates active
- [ ] Autoscaling functional

### Performance Targets
- API latency P95 < 200ms
- Pod startup time < 30s
- Memory usage < 2Gi per pod
- CPU usage < 1 core per pod
- Zero downtime deployments

---

## ⚠️ Risk Mitigation

### High-Risk Areas
1. **GCP Quota Limits**
   - Mitigation: Check quotas before deployment
   - Fallback: Request quota increase

2. **Container Registry Access**
   - Mitigation: Test push/pull permissions
   - Fallback: Use Docker Hub temporarily

3. **DNS Configuration**
   - Mitigation: Use kubectl port-forward initially
   - Fallback: Use IP address access

4. **Resource Constraints**
   - Mitigation: Start with minimal replicas
   - Fallback: Increase node pool if needed

---

## 📅 Daily Execution Plan

### Day 1: Infrastructure
- [ ] Apply Terraform
- [ ] Verify cluster access
- [ ] Create namespaces

### Day 2: Containerization
- [ ] Create Dockerfile
- [ ] Build and test locally
- [ ] Push to registry

### Day 3: Helm Charts
- [ ] Create chart structure
- [ ] Configure values
- [ ] Test with helm template

### Day 4: Observability
- [ ] Deploy stack
- [ ] Verify connectivity
- [ ] Configure dashboards

### Day 5: Qdrant Deployment
- [ ] Deploy StatefulSet
- [ ] Verify persistence
- [ ] Test connectivity

### Day 6: Application Deployment
- [ ] Deploy with Helm
- [ ] Configure ingress
- [ ] End-to-end testing

### Day 7: CI/CD
- [ ] Setup GitHub Actions
- [ ] Configure secrets
- [ ] Test pipeline

---

## 📚 Documentation Updates Required

After deployment:
1. Update README with deployment instructions
2. Document environment variables in production
3. Create runbook for common operations
4. Document monitoring and alerting setup
5. Create troubleshooting guide

---

## ✅ Definition of Done

Phase 1 is complete when:
- [ ] Application deployed to GKE and accessible
- [ ] All health checks passing
- [ ] Observability stack operational
- [ ] CI/CD pipeline functional
- [ ] Documentation updated
- [ ] All tests passing with >80% coverage
- [ ] Security scan passed
- [ ] Performance targets met

---

## 🔄 Next Phase Preview

**Phase 2: Production Hardening**
- Implement CloudFlare tunnel for GPU access
- Deploy KServe for model serving
- Implement MLFlow for model registry
- Add DVC for data versioning
- Enhanced monitoring and alerting
- Disaster recovery procedures
- Load testing and optimization

---

**End of Phase 1 Implementation Plan**