# Production Deployment Implementation Plan

**Created**: 2025-11-13
**Status**: Active
**Timeline**: 4-6 weeks
**Budget**: $300/month (GKE + Local GPU hybrid)

---

## 📋 Document Overview

This is the master implementation plan for deploying IntelliRAG to production. The plan is structured into 6 sequential phases, each with detailed implementation instructions in separate sub-documents.

**Architecture Strategy**: Hybrid deployment combining GKE Autopilot (stateless app services) with local GPU inference (RTX 4070Ti) to optimize costs while maintaining production-grade capabilities.

**Key Design Decisions**:
- Single production environment (no dev/staging separation)
- Manual model registration in MLFlow
- KServe for both local and production model serving
- Minikube for local Kubernetes development
- CloudFlare Tunnel for secure GKE ↔ Local GPU connectivity

---

## 🎯 Mission Objectives

### Primary Goals
1. **Infrastructure as Code**: Provision GKE cluster via Terraform with complete state management
2. **Application Deployment**: Deploy FastAPI services to Kubernetes with health checks and observability
3. **Model Serving**: Establish KServe-based inference on local GPU with OpenAI-compatible API
4. **Production Hardening**: Implement security, scaling, and reliability features
5. **MLOps Pipeline**: Create model versioning, monitoring, and deployment workflows
6. **CI/CD Automation**: Build automated testing, building, and deployment pipelines

### Success Criteria
- ✅ 100% infrastructure reproducibility via Terraform
- ✅ Zero-downtime deployments with rolling updates
- ✅ <200ms P95 query latency
- ✅ >80% test coverage maintained in CI
- ✅ Complete observability stack operational (metrics, logs, traces)
- ✅ Automated model deployment from MLFlow to KServe

---

## 📚 Implementation Phases

### Phase 0: Infrastructure Foundation
**Duration**: 3-5 days
**Objective**: Provision GKE cluster and establish local Kubernetes environment

**Key Deliverables**:
- Terraform modules for GKE Autopilot cluster
- Minikube setup with GPU support on local server
- CloudFlare Tunnel for secure connectivity
- Kubernetes namespaces and RBAC configurations

**Detailed Instructions**: [phase-0-infrastructure-foundation.md](./phase-0-infrastructure-foundation.md)

---

### Phase 1: Application Deployment
**Duration**: 4-6 days
**Objective**: Deploy FastAPI application to GKE with full observability

**Key Deliverables**:
- Helm charts for FastAPI services
- Kubernetes deployments, services, and ConfigMaps
- Integration with existing observability stack
- Health check endpoints and readiness probes

**Detailed Instructions**: [phase-1-application-deployment.md](./phase-1-application-deployment.md)

---

### Phase 2: Model Serving
**Duration**: 5-7 days
**Objective**: Deploy KServe inference services for LLM and embedding models

**Key Deliverables**:
- KServe InferenceServices for vLLM (Qwen3-0.6B)
- KServe InferenceServices for embeddings
- Model artifacts stored in GCS
- OpenAI-compatible API endpoints
- Update application to use KServe endpoints
- Performance benchmarks and optimization

**Detailed Instructions**: [phase-2-model-serving.md](./phase-2-model-serving.md)

---

### Phase 3: Production Hardening
**Duration**: 4-5 days
**Objective**: Implement security, scaling, and reliability features

**Key Deliverables**:
- NGINX Ingress Controller with TLS
- Horizontal Pod Autoscaler (HPA) configurations
- Resource limits and requests tuning
- Security policies and network policies
- Backup and disaster recovery procedures

**Detailed Instructions**: [phase-3-production-hardening.md](./phase-3-production-hardening.md)

---

### Phase 4: MLOps Pipeline
**Duration**: 5-7 days
**Objective**: Establish model lifecycle management and monitoring

**Key Deliverables**:
- MLFlow tracking server deployment
- Model registry with versioning
- Automated model evaluation (RAGAS metrics)
- Data drift monitoring (Evidently)
- Model deployment webhooks

**Detailed Instructions**: [phase-4-mlops.md](./phase-4-mlops.md)

---

### Phase 5: CI/CD Pipeline
**Duration**: 4-6 days
**Objective**: Automate testing, building, and deployment workflows

**Key Deliverables**:
- GitHub Actions workflows
- Automated pytest with >80% coverage enforcement
- Docker image builds and registry pushes
- Automated Helm deployments
- Rollback mechanisms

**Detailed Instructions**: [phase-5-cicd-pipeline.md](./phase-5-cicd-pipeline.md)

---

## 📦 Project-Wide Deliverables

### Infrastructure Artifacts
```
terraform/
├── main.tf              # GKE cluster configuration
├── variables.tf         # Environment-specific variables
├── outputs.tf           # Cluster endpoints and credentials
├── backend.tf           # GCS state backend
└── modules/
    ├── gke/             # GKE Autopilot module
    ├── networking/      # VPC and firewall rules
    └── iam/             # Service accounts and roles
```

### Kubernetes Resources
```
kubernetes/
├── app/
│   ├── namespace.yaml
│   ├── deployment.yaml
│   ├── service.yaml
│   ├── configmap.yaml
│   ├── secrets.yaml
│   └── ingress.yaml
├── kserve/
│   ├── vllm-qwen-inference.yaml
│   └── embedding-google-embeddinggemma-300m-inference.yaml
└── autoscaling/
    └── hpa.yaml
```

### Helm Charts
```
helm/
├── intellirag-app/
│   ├── Chart.yaml
│   ├── values.yaml
│   ├── values-prod.yaml
│   └── templates/
│       ├── deployment.yaml
│       ├── service.yaml
│       ├── configmap.yaml
│       └── ingress.yaml
└── mlflow/
    ├── Chart.yaml
    ├── values.yaml
    └── templates/
```

### CI/CD Workflows
```
.github/
└── workflows/
    ├── ci.yml           # Test and build
    ├── cd-app.yml       # Deploy FastAPI app
    ├── cd-models.yml    # Deploy models to KServe
    └── rollback.yml     # Emergency rollback
```

---

## 🔧 Troubleshooting Guides

### Common Issues and Solutions

#### 1. GKE Cluster Creation Failures
**Symptom**: Terraform fails with quota or permission errors

**Solutions**:
```bash
# Check GCP quotas
gcloud compute project-info describe --project=YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable storage-api.googleapis.com

# Verify IAM permissions
gcloud projects get-iam-policy YOUR_PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:terraform@YOUR_PROJECT.iam.gserviceaccount.com"
```

#### 2. KServe Model Loading Failures
**Symptom**: InferenceService pods crash or timeout

**Debugging Steps**:
```bash
# Check InferenceService status
kubectl get inferenceservices -n kserve

# View detailed events
kubectl describe inferenceservice vllm-qwen -n kserve

# Check pod logs
kubectl logs -n kserve -l serving.kserve.io/inferenceservice=vllm-qwen -c kserve-container

# Verify model artifacts in GCS
gsutil ls gs://YOUR_BUCKET/models/qwen3-0.6b/
```

**Common Fixes**:
- Increase memory limits (vLLM requires ~14GB for Qwen3-0.6B)
- Verify GCS credentials in service account secret
- Check GPU availability: `nvidia-smi` on local server
- Validate model path in InferenceService spec

#### 3. CloudFlare Tunnel Connectivity Issues
**Symptom**: GKE cannot reach local KServe endpoints

**Debugging**:
```bash
# Check tunnel status
cloudflared tunnel info intellirag-gpu

# Test connectivity from GKE pod
kubectl run -n app -it --rm debug --image=curlimages/curl --restart=Never \
  -- curl -v https://gpu.intellirag.example.com/health

# View tunnel logs
journalctl -u cloudflared -f
```

**Common Fixes**:
- Restart tunnel: `sudo systemctl restart cloudflared`
- Verify DNS records in CloudFlare dashboard
- Check firewall rules on local server
- Ensure KServe gateway is accessible: `curl http://localhost:8080/health`

#### 4. Helm Deployment Failures
**Symptom**: `helm install` or `helm upgrade` fails

**Debugging**:
```bash
# Dry-run to validate templates
helm install intellirag ./helm/intellirag-app --dry-run --debug

# Check existing resources
kubectl get all -n app

# View Helm release history
helm history intellirag -n app

# Rollback if needed
helm rollback intellirag -n app
```

#### 5. Application Pod CrashLoopBackOff
**Symptom**: FastAPI pods repeatedly crash

**Debugging Steps**:
```bash
# Check pod status
kubectl get pods -n app

# View pod logs
kubectl logs -n app <pod-name> --previous

# Describe pod for events
kubectl describe pod -n app <pod-name>

# Check ConfigMap and Secret values
kubectl get configmap -n app intellirag-config -o yaml
kubectl get secret -n app intellirag-secrets -o yaml
```

**Common Issues**:
- Missing environment variables
- Incorrect Qdrant connection string
- GCS credentials not mounted
- Health check endpoint returning errors

#### 6. High Latency or Timeout Errors
**Symptom**: Query requests exceed timeout or have high P95 latency

**Investigation**:
```bash
# Check Prometheus metrics
kubectl port-forward -n observability svc/prometheus-server 9090:80
# Visit http://localhost:9090 and query:
# - http_request_duration_seconds_bucket
# - vllm_request_duration_seconds
# - qdrant_grpc_duration_seconds

# View Jaeger traces
kubectl port-forward -n observability svc/jaeger-query 16686:80
# Visit http://localhost:16686

# Check resource utilization
kubectl top pods -n app
kubectl top nodes
```

**Optimization Steps**:
- Scale up FastAPI replicas: `kubectl scale deployment/intellirag-api -n app --replicas=3`
- Increase HPA max replicas
- Optimize Qdrant query parameters (limit, score_threshold)
- Enable vLLM prefix caching
- Review slow traces in Jaeger

---

## 📖 Usage Guide

### 1. Initial Setup

**Prerequisites**:
- GCP account with billing enabled
- Local server with NVIDIA RTX 4070Ti
- Ubuntu 22.04 on local server
- kubectl, helm, terraform installed

**Environment Setup**:
```bash
# Clone repository
git clone https://github.com/your-org/intellirag.git
cd intellirag

# Install dependencies
uv sync

# Copy environment template
cp .env.example .env
# Edit .env with your credentials

# Authenticate with GCP
gcloud auth login
gcloud auth application-default login
```

### 2. Infrastructure Provisioning

```bash
# Navigate to Terraform directory
cd terraform/

# Initialize Terraform
terraform init

# Plan infrastructure
terraform plan -out=tfplan

# Apply infrastructure (creates GKE cluster)
terraform apply tfplan

# Get cluster credentials
gcloud container clusters get-credentials intellirag-cluster \
  --region us-central1 --project YOUR_PROJECT_ID
```

### 3. Deploy Observability Stack

```bash
# Create observability namespace
kubectl apply -f kubernetes/observability/namespace.yaml

# Deploy observability stack with Helmfile
cd kubernetes/observability/
cp .env.example .env
# Edit .env with passwords
helmfile apply
```

### 4. Deploy Application

```bash
# Build and push Docker image
docker build -t gcr.io/YOUR_PROJECT/intellirag-api:latest .
docker push gcr.io/YOUR_PROJECT/intellirag-api:latest

# Deploy with Helm
helm install intellirag ./helm/intellirag-app \
  -n app --create-namespace \
  -f helm/intellirag-app/values-prod.yaml
```

### 5. Deploy KServe Models

**Local Server (Minikube)**:
```bash
# Install minikube with GPU support
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Start minikube with GPU
minikube start --driver=docker --gpus=all

# Install KServe
curl -s "https://raw.githubusercontent.com/kserve/kserve/release-0.11/hack/quick_install.sh" | bash

# Deploy inference services
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml
kubectl apply -f kubernetes/kserve/embedding-inference.yaml
```

### 6. Setup CloudFlare Tunnel

```bash
# Install cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate
cloudflared tunnel login

# Create tunnel
cloudflared tunnel create intellirag-gpu

# Configure tunnel
cat > ~/.cloudflared/config.yml <<EOF
tunnel: intellirag-gpu
credentials-file: /home/user/.cloudflared/TUNNEL_ID.json
ingress:
  - hostname: gpu.intellirag.example.com
    service: http://localhost:8080
  - service: http_status:404
EOF

# Run tunnel
cloudflared tunnel run intellirag-gpu
```

### 7. Verify Deployment

```bash
# Check all pods are running
kubectl get pods -A

# Test application health
kubectl port-forward -n app svc/intellirag-api 8000:8000
curl http://localhost:8000/health

# Test query endpoint
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is IntelliRAG?"}'

# View Grafana dashboards
kubectl port-forward -n observability svc/grafana 3000:80
# Visit http://localhost:3000 (admin/prom-operator)
```

### 8. Monitor System

**Prometheus Metrics**:
```bash
kubectl port-forward -n observability svc/prometheus-server 9090:80
# Visit http://localhost:9090
```

**Grafana Dashboards**:
- **IntelliRAG Overview**: System health, request rates, error rates
- **Infrastructure**: Node resources, pod metrics, network I/O
- **Ingestion Pipeline**: Document processing, embedding generation
- **Query Performance**: Latency percentiles, throughput, cache hit rates
- **LLM Metrics**: Token generation, GPU utilization, model latency

**Jaeger Tracing**:
```bash
kubectl port-forward -n observability svc/jaeger-query 16686:80
# Visit http://localhost:16686
```

**Loki Logs**:
```bash
# Query logs via Grafana Explore
# Or use logcli:
logcli query '{namespace="app"}' --limit=100 --since=1h
```

---

## 📊 Summary

This implementation plan provides a comprehensive roadmap for deploying IntelliRAG to production with enterprise-grade reliability, observability, and automation.

**Key Achievements**:
- **Cost Efficiency**: Hybrid architecture saves $500/month vs full GKE GPU deployment
- **Performance**: vLLM achieves 19x throughput improvement vs Ollama
- **Observability**: Complete metrics, logs, and traces for all services
- **Reliability**: Autoscaling, health checks, and automated rollbacks
- **Maintainability**: Infrastructure as Code, GitOps, and automated testing

**Timeline Overview**:
- **Phase 0**: Infrastructure (3-5 days)
- **Phase 1**: Application (4-6 days)
- **Phase 2**: Model Serving (5-7 days)
- **Phase 3**: Production Hardening (4-5 days)
- **Phase 4**: MLOps (5-7 days)
- **Phase 5**: CI/CD (4-6 days)
- **Total**: 25-36 days (4-6 weeks)

**Next Steps**:
1. Review Phase 0 detailed instructions
2. Provision GKE cluster with Terraform
3. Setup local minikube environment
4. Establish CloudFlare tunnel
5. Proceed to Phase 1 application deployment

**Documentation Structure**:
- [Phase 0: Infrastructure Foundation](./phase-0-infrastructure-foundation.md)
- [Phase 1: Application Deployment](./phase-1-application-deployment.md)
- [Phase 2: Model Serving](./phase-2-model-serving.md)
- [Phase 3: Production Hardening](./phase-3-production-hardening.md)
- [Phase 4: MLOps Pipeline](./phase-4-mlops.md)
- [Phase 5: CI/CD Pipeline](./phase-5-cicd-pipeline.md)

---

**Document Version**: 1.0
**Last Updated**: 2025-11-13
**Maintainer**: IntelliRAG Team
