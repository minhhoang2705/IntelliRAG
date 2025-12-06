# IntelliRAG Hybrid Deployment Architecture

**Status**: ✅ Active
**Created**: 2025-11-16
**Architecture Type**: Hybrid Cloud + Local GPU
**Version**: 3.0

---

## 📋 Overview

IntelliRAG uses a **hybrid deployment architecture** that combines cloud infrastructure (GKE) for stateless application services with local GPU infrastructure (RTX 4070Ti) for ML model serving. This design optimizes costs while maintaining production-grade capabilities and performance.

**Key Design Principle**: Separate compute-intensive ML inference (local GPU) from scalable application logic (cloud).

**Cost Target**: <$300/month total infrastructure cost

---

## 🏗️ Architecture Components

### Cloud Infrastructure (GKE Standard)

**Platform**: Google Kubernetes Engine (GKE Standard)
**Region**: asia-southeast1
**Cluster Configuration**:
- Cluster Type: **Standard** (NOT Autopilot)
- Current: 1 node (e2-standard-4, 4 vCPUs, 16GB RAM)
- Max Scale: 3 nodes (autoscaling configured)
- Node Pools: **CPU-only** (no GPU nodes)
- Expected Load: **150 requests/minute** (~2.5 req/sec)

**Deployed Services**:
```
GKE Cluster (asia-southeast1)
├── Namespace: app
│   ├── FastAPI API (ingestion + query endpoints)
│   │   └── Resources: 500m CPU, 1Gi RAM per pod
│   └── Qdrant (vector database)
│       └── Resources: 1 CPU, 4Gi RAM
├── Namespace: observability
│   ├── Prometheus (metrics collection)
│   ├── Grafana (visualization)
│   ├── Jaeger (distributed tracing)
│   └── Loki (centralized logging)
└── Namespace: kserve
    └── (Empty - reserved for future use)
```

**Why GKE Standard (not Autopilot)?**
- More control over node types and scaling
- Lower cost for small workloads (1-3 nodes)
- Faster deployment (no Autopilot provisioning delays)
- Better for mixed workload types

**Why No GPU in GKE?**
- **Cost**: GKE GPU nodes cost $2-3/hour (~$1,500-2,000/month)
- **Utilization**: GPU would be underutilized in cloud (batch inference only)
- **Local Advantage**: RTX 4070Ti already available and optimized

---

### Local GPU Infrastructure

**Hardware**: NVIDIA RTX 4070Ti 12GB VRAM
**Operating System**: Ubuntu 22.04 LTS
**Kubernetes**: Minikube v1.32.0+ with Docker driver

**Software Stack**:
```
Local Server (RTX 4070Ti)
├── Minikube (local Kubernetes cluster)
│   ├── Driver: Docker (--gpus all)
│   ├── Resources: 8 CPUs, 32GB RAM, 100GB disk
│   └── GPU: Passthrough enabled
├── KServe v0.14.1 (model serving platform)
│   ├── InferenceService: vLLM (Qwen3-0.6B)
│   │   └── Endpoint: /v1/chat/completions (OpenAI-compatible)
│   └── InferenceService: BGE-M3 Embeddings
│       └── Endpoint: /v1/embeddings (OpenAI-compatible)
└── CloudFlare Tunnel (cloudflared)
    └── Exposes: https://gpu.intellirag.example.com
```

**Development vs Production on Local GPU**:
| Environment | ML Serving Method | Use Case | Port |
|-------------|-------------------|----------|------|
| **Development** | vLLM Docker container | Rapid iteration, testing | 8000 |
| **Production/Demo** | KServe InferenceService on minikube | Production parity, demo-ready | 8080 |

**Important**: "Production" here means **demo-ready**. Both dev and production model serving run on the same local GPU server, just with different serving methods.

---

## 🌐 Network Architecture

### CloudFlare Tunnel Configuration

**Purpose**: Securely expose local KServe endpoints to GKE without public IP or port forwarding.

**Architecture**:
```
┌─────────────────────────────────────────────┐
│  GKE FastAPI (Cloud)                        │
│  https://intellirag.example.com             │
└──────────────┬──────────────────────────────┘
               │ HTTPS Request
               ↓
┌─────────────────────────────────────────────┐
│  CloudFlare Edge Network                    │
│  - TLS termination                          │
│  - DDoS protection                          │
│  - CDN caching (optional)                   │
└──────────────┬──────────────────────────────┘
               │ Encrypted Tunnel
               ↓
┌─────────────────────────────────────────────┐
│  Local cloudflared Daemon                   │
│  (Ubuntu server, systemd service)           │
└──────────────┬──────────────────────────────┘
               │ HTTP (localhost)
               ↓
┌─────────────────────────────────────────────┐
│  Minikube KServe Gateway                    │
│  localhost:8080                             │
└──────────────┬──────────────────────────────┘
               │ Kubernetes Service
               ↓
┌─────────────────────────────────────────────┐
│  InferenceServices                          │
│  - vLLM (Qwen3-0.6B)                        │
│  - BGE-M3 Embeddings                        │
└─────────────────────────────────────────────┘
```

**Exposed Endpoints**:
```bash
# LLM Inference (Qwen3-0.6B)
https://gpu.intellirag.example.com/v1/chat/completions

# Embedding Generation (BGE-M3)
https://gpu.intellirag.example.com/v1/embeddings

# Health Check
https://gpu.intellirag.example.com/health
```

**Security Features**:
- ✅ End-to-end TLS encryption
- ✅ No inbound firewall rules needed
- ✅ No public IP exposure
- ✅ CloudFlare Access for authentication (optional)
- ✅ API key validation at KServe layer
- ✅ Rate limiting at CloudFlare edge

**Tunnel Performance**:
- Latency overhead: +10-30ms
- Throughput: 1Gbps+ (CloudFlare edge)
- Reliability: 99.99% uptime SLA

---

## 🔄 System Flows

### 1. Document Ingestion Flow

```
User Browser
  ↓ POST /api/v1/ingest (multipart/form-data)
NGINX Ingress (GKE)
  ↓ Route to FastAPI
FastAPI Orchestrator (GKE pod)
  ↓ Validate file (size, type, virus scan)
Store Raw Document in GCS
  ↓ Background task triggered
Ingestion Pipeline (FastAPI background worker):
  ├─ 1. Load from GCS (LangChain GCSFileLoader)
  ├─ 2. Parse document (Docling for PDF/images)
  ├─ 3. Chunk text (LangChain RecursiveCharacterTextSplitter)
  └─ 4. Generate embeddings for each chunk
      ↓ HTTPS POST request
      CloudFlare Tunnel
      ↓ Encrypted tunnel
      Local GPU: BGE-M3 InferenceService
      ↓ Return embeddings (1024-dim vectors)
FastAPI (GKE)
  ↓ Store vectors + metadata
Qdrant (GKE pod)
  └─ Collection: documents
      ├─ Vector: [0.1, 0.2, ...] (1024-dim)
      └─ Payload: {document_id, gcs_path, chunk_text, metadata}
  ↓ Update job state
Job State Management (in-memory or Redis)
  ↓ Return response
User: {job_id, status: "completed", chunks_processed: 42}
```

**Network Hops for Embedding**:
1. FastAPI (GKE) → CloudFlare Edge (~10ms)
2. CloudFlare Edge → cloudflared (local) (~5ms)
3. cloudflared → Minikube KServe Gateway (~1ms)
4. KServe Gateway → BGE-M3 Pod (~1ms)
5. BGE-M3 Processing (~10-20ms per chunk)
6. Response follows reverse path

**Total Latency per Chunk**: ~30-50ms

---

### 2. Query/RAG Flow

```
User Browser
  ↓ POST /api/v1/query {"query": "What is IntelliRAG?"}
NGINX Ingress (GKE)
  ↓
FastAPI Orchestrator (GKE pod)
  ↓
LangGraph Query Router (in-process)
  ├─ Analyze query intent
  ├─ Classify: factual, conversational, domain-specific, document-based
  └─ Decision: RAG needed?
      ├─ NO → Direct LLM call (skip retrieval)
      └─ YES → RAG pipeline
          ↓
          1. Generate Query Embedding
             ↓ HTTPS POST
             CloudFlare Tunnel
             ↓
             Local GPU: BGE-M3 InferenceService
             ↓ Return query embedding (1024-dim)
          ↓
          2. Retrieve Similar Chunks
             ↓ Query Qdrant
             Qdrant (GKE pod)
             └─ Vector search (cosine similarity)
                 ├─ Top K=5 similar chunks
                 └─ Filter by score_threshold=0.7
             ↓ Return chunks with metadata
          ↓
          3. Format RAG Prompt
             Template:
             """
             Context: {retrieved_chunks}

             Question: {user_query}

             Answer based on the context above:
             """
          ↓
          4. Generate Answer
             ↓ HTTPS POST
             CloudFlare Tunnel
             ↓
             Local GPU: vLLM InferenceService (Qwen3-0.6B)
             ↓ Stream tokens (SSE)
FastAPI (GKE)
  ↓ Format response
User: {answer: "...", sources: [...], latency: "180ms"}
```

**Critical Path Latency Breakdown**:
- Embedding generation: 30-50ms (includes tunnel)
- Qdrant retrieval: 10-30ms (local in GKE)
- LLM generation: 80-120ms (P95, vLLM on RTX 4070Ti)
- **Total P95 latency**: ~150-200ms ✅ Meets <200ms target

---

### 3. Service Discovery & Configuration

**Environment Variables (FastAPI on GKE)**:

```python
# app/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Model serving endpoints (via CloudFlare Tunnel)
    LLM_ENDPOINT: str = "https://gpu.intellirag.example.com/v1/chat/completions"
    EMBEDDING_ENDPOINT: str = "https://gpu.intellirag.example.com/v1/embeddings"

    # API authentication (for CloudFlare Access or KServe)
    MODEL_API_KEY: str = ""  # Optional, set if using auth

    # GKE-local services (cluster DNS)
    QDRANT_HOST: str = "qdrant.app.svc.cluster.local"
    QDRANT_PORT: int = 6333
    QDRANT_GRPC_PORT: int = 6334

    # GCS configuration
    GCS_BUCKET: str = "intellirag-data"
    GCS_PROJECT_ID: str = "intellirag-aide1-capstone"

    # Observability
    JAEGER_AGENT_HOST: str = "jaeger-agent.observability.svc.cluster.local"
    JAEGER_AGENT_PORT: int = 6831

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
```

**Kubernetes ConfigMap** (GKE):
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: intellirag-config
  namespace: app
data:
  # CloudFlare Tunnel endpoints
  LLM_ENDPOINT: "https://gpu.intellirag.example.com/v1/chat/completions"
  EMBEDDING_ENDPOINT: "https://gpu.intellirag.example.com/v1/embeddings"

  # GKE-local services
  QDRANT_HOST: "qdrant.app.svc.cluster.local"
  QDRANT_PORT: "6333"

  # GCS configuration
  GCS_BUCKET: "intellirag-data"
  GCS_PROJECT_ID: "intellirag-aide1-capstone"

  # Observability
  JAEGER_AGENT_HOST: "jaeger-agent.observability.svc.cluster.local"
  JAEGER_AGENT_PORT: "6831"
  OTEL_SERVICE_NAME: "intellirag-api"
```

**Kubernetes Secret** (GKE):
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: intellirag-secrets
  namespace: app
type: Opaque
stringData:
  MODEL_API_KEY: "your-api-key-here"  # If using CloudFlare Access
  GCS_SERVICE_ACCOUNT_KEY: |
    {
      "type": "service_account",
      ...
    }
```

---

## 🔐 Security Architecture

### 1. CloudFlare Tunnel Authentication

**Recommended: CloudFlare Access (Zero Trust)**

```yaml
# CloudFlare Access Policy (configured via Dashboard)
name: "IntelliRAG GPU Endpoints"
decision: allow
includes:
  - Service Auth: intellirag-gke-sa@intellirag-aide1-capstone.iam.gserviceaccount.com
  - IP Range: <GKE NAT IP range>
excludes: []
```

**Alternative: API Key at KServe Layer**

```python
# Add to KServe InferenceService
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-qwen
  annotations:
    serving.kserve.io/headers: |
      Authorization: Bearer ${MODEL_API_KEY}
```

**FastAPI Client Code**:
```python
import httpx

async def call_llm(prompt: str):
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.MODEL_API_KEY}"
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            settings.LLM_ENDPOINT,
            headers=headers,
            json={"messages": [{"role": "user", "content": prompt}]}
        )
        return response.json()
```

---

### 2. GKE Security

**Workload Identity** (GCS Access):
```bash
# Already configured in Phase 0
gcloud iam service-accounts add-iam-policy-binding \
  intellirag-cluster-workload-sa@intellirag-aide1-capstone.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:intellirag-aide1-capstone.svc.id.goog[app/intellirag-app]"
```

**Network Policies**:
```yaml
# Allow app namespace to access observability
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: allow-app-to-observability
  namespace: app
spec:
  podSelector: {}
  policyTypes:
    - Egress
  egress:
    - to:
        - namespaceSelector:
            matchLabels:
              name: observability
      ports:
        - protocol: TCP
          port: 9090  # Prometheus
        - protocol: TCP
          port: 6831  # Jaeger
```

---

### 3. Local Server Security

**Firewall Rules**:
```bash
# Only allow outbound connections (no inbound)
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh  # For management only
sudo ufw enable
```

**cloudflared Systemd Service**:
```ini
# /etc/systemd/system/cloudflared.service
[Unit]
Description=CloudFlare Tunnel
After=network.target

[Service]
Type=simple
User=cloudflared
ExecStart=/usr/local/bin/cloudflared tunnel --no-autoupdate run --token ${TUNNEL_TOKEN}
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 📊 Resource Allocation

### GKE Cluster Resources

**Current Configuration** (1 node):
```
Node: e2-standard-4
├── vCPUs: 2
├── Memory: 8 GB
├── Disk: 50 GB SSD
└── Allocatable:
    ├── CPU: ~1.8 (after system pods)
    └── Memory: ~6.5 GB
```

**Max Configuration** (3 nodes, autoscaling):
```
Total Cluster Resources:
├── vCPUs: 6 (2 per node × 3)
├── Memory: 24 GB
└── Disk: 150 GB SSD

Expected Workload (150 req/min):
├── FastAPI pods: 2-3 replicas
│   └── 500m CPU, 1Gi RAM each
├── Qdrant: 1 replica
│   └── 1 CPU, 4Gi RAM
└── Observability: ~2 CPU, 4Gi RAM total

Utilization: ~50-60% at peak
```

**Pod Resource Specifications**:
```yaml
# FastAPI Deployment
resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 2Gi

# Qdrant StatefulSet
resources:
  requests:
    cpu: 1000m
    memory: 4Gi
  limits:
    cpu: 4000m
    memory: 8Gi
```

---

### Local GPU Server Resources

**NVIDIA RTX 4070Ti Specifications**:
```
GPU: NVIDIA RTX 4070Ti
├── VRAM: 12 GB GDDR6X
├── CUDA Cores: 7,680
├── Tensor Cores: 240 (4th gen)
├── Memory Bandwidth: 504 GB/s
├── TDP: 285W
└── Architecture: Ada Lovelace
```

**Model Resource Allocation**:
```
vLLM (Qwen3-0.6B):
├── Model Weights: ~1.2 GB (FP16)
├── KV Cache: ~4 GB (PagedAttention managed)
└── Total VRAM: ~5.5 GB

BGE-M3 Embeddings:
├── Model Weights: ~1.1 GB
├── Batch Buffer: ~1 GB
└── Total VRAM: ~2.2 GB

System Reserved: ~0.5 GB
Available for future models: ~3.8 GB ✅
```

**Minikube Configuration**:
```bash
minikube start \
  --driver=docker \
  --gpus=all \
  --cpus=8 \
  --memory=32g \
  --disk-size=100g \
  --kubernetes-version=v1.28.3
```

---

## 💰 Cost Analysis

### Monthly Cost Breakdown (Detailed)

**GKE Cluster** (asia-southeast1):
```
Scenario 1: Current (1 node)
├── Cluster management: $0 (Standard tier)
├── Compute: 1 × e2-standard-4 = $97.82/month
│   └── 2 vCPUs, 8GB RAM, 730 hours
├── Storage: 50GB SSD = $8.50/month
├── Networking: Egress 10GB = $1.20/month
└── Total: ~$58.61/month

Scenario 2: Peak (3 nodes)
├── Cluster management: $0
├── Compute: 3 × e2-standard-4 = $293.46/month
├── Storage: 150GB SSD = $25.50/month
├── Networking: Egress 30GB = $3.60/month
└── Total: ~$175.83/month
```

**GCS Storage**:
```
Data bucket (50GB documents):
├── Storage: 50GB × $0.026/GB = $1.30/month
├── Operations: ~10k reads/month = $0.40/month
└── Total: ~$1.70/month

Model artifacts (10GB):
├── Storage: 10GB × $0.026/GB = $0.26/month
└── Total: ~$0.26/month

GCS Total: ~$1.96/month
```

**CloudFlare**:
```
CloudFlare Tunnel:
├── Free tier (up to 50 users)
└── Total: $0/month ✅

Optional CloudFlare Access:
├── First 50 users: Free
└── Total: $0/month ✅
```

**Local GPU Server**:
```
Electricity (RTX 4070Ti):
├── TDP: 285W
├── Usage: 24h/day × 30 days = 720 hours
├── Consumption: 285W × 720h = 205 kWh/month
├── Rate: $0.12/kWh (US average)
└── Total: $24.60/month

Internet (optional dedicated line):
├── Business fiber 1Gbps: ~$100/month
└── OR use existing internet: $0/month

Local Total: $24.60-124.60/month
```

**Total Monthly Cost Summary**:
```
Conservative Estimate (1 GKE node, existing internet):
├── GKE: $58.61
├── GCS: $1.96
├── CloudFlare: $0
├── Local GPU: $24.60
└── Total: $85.17/month ✅ Well under budget!

Peak Estimate (3 GKE nodes, dedicated internet):
├── GKE: $175.83
├── GCS: $1.96
├── CloudFlare: $0
├── Local GPU: $124.60
└── Total: $302.39/month (slightly over $300 target)
```

**Cost Optimization Tips**:
1. Use existing internet (save $100/month)
2. Implement GKE autoscaling (scale down to 1 node off-peak)
3. Use GCS lifecycle policies (delete old docs after 90 days)
4. Enable CloudFlare caching (reduce GCS egress)

**Savings vs Full Cloud GPU**:
```
Alternative: GKE with T4 GPU
├── 1 × n1-standard-4 with T4 = $450/month
└── Savings with hybrid: $364-447/month ✅

Alternative: GKE with A100 GPU
├── 1 × a2-highgpu-1g = $2,500/month
└── Savings with hybrid: $2,414-2,497/month ✅
```

---

## 🚀 Deployment Workflow

### ✅ Phase 0: Infrastructure Foundation (COMPLETED)

**Status**: ✅ Completed
**Deliverables**:
- [x] GKE Standard cluster provisioned
- [x] 1 node running (e2-standard-4)
- [x] Namespaces created (app, kserve, observability)
- [x] Service accounts with Workload Identity
- [x] RBAC configured
- [x] GCS buckets created
- [x] Terraform state in GCS

---

### 📍 Phase 1: Local GPU Setup (NEXT)

**Objective**: Setup minikube with KServe and deploy InferenceServices

**Steps**:
1. **Install Minikube with GPU support** (30 min)
   ```bash
   # Install nvidia-container-toolkit
   # Configure Docker with NVIDIA runtime
   # Start minikube with GPU
   ```

2. **Install KServe v0.14.1** (20 min)
   ```bash
   # Install cert-manager (prerequisite)
   # Install KServe with Helm
   # Verify installation
   ```

3. **Deploy vLLM InferenceService** (15 min)
   ```bash
   # Create InferenceService manifest
   # Apply to minikube
   # Test endpoint
   ```

4. **Deploy BGE-M3 InferenceService** (15 min)
   ```bash
   # Create InferenceService manifest
   # Apply to minikube
   # Test endpoint
   ```

5. **Setup CloudFlare Tunnel** (30 min)
   ```bash
   # Install cloudflared
   # Create tunnel
   # Configure routing
   # Start as systemd service
   ```

6. **Integration Testing** (30 min)
   ```bash
   # Test local endpoints
   # Test CloudFlare Tunnel
   # Performance benchmarks
   ```

**Total Time**: ~2.5 hours

---

### Phase 2: GKE Application Deployment

**Objective**: Deploy FastAPI and Qdrant to GKE

**Steps**:
1. **Build FastAPI Docker Image** (20 min)
2. **Push to GCR** (10 min)
3. **Deploy Qdrant StatefulSet** (15 min)
4. **Deploy FastAPI Deployment** (20 min)
5. **Configure environment variables** (10 min)
6. **Test end-to-end flow** (30 min)

**Total Time**: ~2 hours

---

### Phase 3: Observability Stack Deployment

**Objective**: Deploy Prometheus, Grafana, Jaeger, Loki

**Steps**:
1. **Deploy with Helmfile** (30 min)
2. **Import Grafana dashboards** (20 min)
3. **Configure Prometheus scrape targets** (15 min)
4. **Validate distributed tracing** (15 min)

**Total Time**: ~1.5 hours

---

### Phase 4: Production Hardening

**Objective**: NGINX Ingress, TLS, HPA, security policies

**Steps**:
1. **NGINX Ingress Controller** (30 min)
2. **TLS certificates (Let's Encrypt)** (30 min)
3. **HPA configuration** (20 min)
4. **Network policies** (20 min)
5. **Resource limits tuning** (20 min)

**Total Time**: ~2 hours

---

## 🔧 Troubleshooting Guide

### Issue 1: CloudFlare Tunnel Connection Failed

**Symptoms**:
- FastAPI cannot reach model endpoints
- HTTP 502/504 errors from CloudFlare
- Timeout on embedding/LLM calls

**Debugging Steps**:
```bash
# 1. Check tunnel status on local server
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -f

# 2. Test local KServe gateway directly
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "qwen", "messages": [{"role": "user", "content": "test"}]}'

# 3. Check tunnel connectivity
curl https://gpu.intellirag.example.com/health

# 4. Test from GKE pod
kubectl run -n app -it --rm debug --image=curlimages/curl --restart=Never \
  -- curl -v https://gpu.intellirag.example.com/v1/chat/completions
```

**Common Solutions**:
```bash
# Restart tunnel
sudo systemctl restart cloudflared

# Verify DNS records in CloudFlare dashboard
# Check A/AAAA records point to CloudFlare IPs

# Check firewall (allow outbound HTTPS)
sudo ufw status

# Validate tunnel config
cat ~/.cloudflared/config.yml

# Re-authenticate tunnel
cloudflared tunnel login
cloudflared tunnel create intellirag-gpu
```

---

### Issue 2: KServe InferenceService Not Ready

**Symptoms**:
- InferenceService stuck in "Creating" or "Failed" state
- Pods crashing with OOM or GPU errors
- `kubectl get isvc` shows "READY: False"

**Debugging Steps**:
```bash
# 1. Check InferenceService status
kubectl get inferenceservices -n kserve

# 2. Describe InferenceService for events
kubectl describe inferenceservice vllm-qwen -n kserve

# 3. Check pod logs
kubectl logs -n kserve -l serving.kserve.io/inferenceservice=vllm-qwen -c kserve-container

# 4. Verify GPU availability in pod
kubectl exec -n kserve <pod-name> -- nvidia-smi

# 5. Check model loading
kubectl logs -n kserve <pod-name> | grep -i "model loaded"
```

**Common Solutions**:
```yaml
# Increase memory limits (vLLM needs ~8GB)
resources:
  limits:
    nvidia.com/gpu: 1
    memory: 10Gi
  requests:
    nvidia.com/gpu: 1
    memory: 8Gi

# Verify GPU is schedulable
kubectl describe nodes | grep -A 10 "Allocatable"

# Check model path in GCS
gsutil ls gs://intellirag-models/qwen3-0.6b/

# Validate service account permissions
kubectl get sa -n kserve
kubectl describe sa kserve-sa -n kserve
```

---

### Issue 3: High Latency on Query Requests

**Symptoms**:
- P95 latency >500ms (target: <200ms)
- Timeouts on complex queries
- Users complaining about slow responses

**Investigation**:
```bash
# 1. Check Jaeger traces
kubectl port-forward -n observability svc/jaeger-query 16686:80
# Visit http://localhost:16686, search for slow traces

# 2. Query Prometheus metrics
kubectl port-forward -n observability svc/prometheus-server 9090:80
# Query: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))

# 3. Check component-level latency
# - Embedding: embedding_request_duration_seconds
# - Qdrant: qdrant_search_duration_seconds
# - LLM: vllm_request_duration_seconds
```

**Common Causes & Solutions**:

**1. CloudFlare Tunnel Latency** (+50ms overhead):
```python
# Solution: Batch embedding calls
async def embed_chunks_batch(chunks: List[str], batch_size: int = 32):
    embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i+batch_size]
        # Single CloudFlare Tunnel call for batch
        batch_embeddings = await embedding_client.embed(batch)
        embeddings.extend(batch_embeddings)
    return embeddings
```

**2. Qdrant Query Slow** (>100ms):
```python
# Solution: Optimize HNSW index parameters
from qdrant_client.models import VectorParams, Distance, HnswConfigDiff

client.create_collection(
    collection_name="documents",
    vectors_config=VectorParams(size=1024, distance=Distance.COSINE),
    hnsw_config=HnswConfigDiff(
        m=16,  # Number of connections (default: 16)
        ef_construct=200,  # Construction time/accuracy tradeoff
    )
)
```

**3. vLLM Queue Depth** (batch processing delay):
```bash
# Solution: Adjust vLLM settings in InferenceService
--max-model-len 4096  # Reduce if not needed
--max-num-seqs 8      # Increase for more concurrent requests
--gpu-memory-utilization 0.9  # Default is 0.9
```

---

### Issue 4: Minikube GPU Not Detected

**Symptoms**:
- Pods scheduled but can't access GPU
- `nvidia-smi` fails inside pods
- "No GPU devices found" errors

**Debugging Steps**:
```bash
# 1. Verify GPU on host
nvidia-smi

# 2. Check Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base nvidia-smi

# 3. Check minikube started with GPU
minikube ssh
nvidia-smi  # Should work inside minikube VM

# 4. Verify NVIDIA device plugin
kubectl get pods -n kube-system | grep nvidia
```

**Solutions**:
```bash
# 1. Install nvidia-container-toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit

# 2. Configure Docker daemon
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 3. Restart minikube with GPU
minikube delete
minikube start --driver=docker --gpus=all

# 4. Install NVIDIA device plugin
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

---

## 📚 Related Documentation

**Setup Guides**:
- [CloudFlare Tunnel Configuration Guide](./cloudflare-tunnel-setup.md) *(to be created)*
- [Local KServe with Minikube Setup](../deployment/local-kserve-setup-guide.md)
- [Phase 0 Execution Guide](../plans/phase-0-execution-guide.md)

**Architecture Docs**:
- [Current Architecture Overview](./current-architecture.md)
- [High-Level Architecture Diagram](../../images/high_level_architecture_v2.jpg)

**Deployment Plans**:
- [Production Deployment Plan](../plans/20251113-production-deployment-plan.md)
- [Phase 1: Application Deployment](../plans/phase-1-application-deployment.md)
- [Phase 2: Model Serving](../plans/phase-2-model-serving.md)

---

## 🎯 Next Steps After GKE Provisioning

**You are here**: ✅ Phase 0 Complete (GKE provisioned)

**Next**: 🚀 Phase 1 - Local GPU Setup

**Immediate Action Items**:
1. Follow [CloudFlare Tunnel Configuration Guide](./cloudflare-tunnel-setup.md)
2. Setup minikube with GPU support
3. Deploy KServe v0.14.1 to minikube
4. Deploy InferenceServices (vLLM, BGE-M3)
5. Test end-to-end connectivity (GKE → CloudFlare → Local)

**Detailed Checklist**: See [Post-GKE Deployment Checklist](../deployment/post-gke-deployment-checklist.md) *(to be created)*

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Maintainer**: IntelliRAG Team
**Status**: ✅ Active Architecture
