# Phase 2: Model Serving

**Duration**: 5-7 days
**Status**: Pending
**Dependencies**: Phase 0 (Infrastructure), Phase 1 (Application Deployment)

---

## 📋 Overview

This phase deploys KServe inference services for both the LLM (Qwen3-0.6B-Instruct) and embedding model (embeddinggemma-300m) on the local GPU server using minikube. Models will be served via vLLM for high-performance inference with OpenAI-compatible APIs.

**Key Components**:
- **vLLM Runtime**: High-throughput LLM serving with PagedAttention
- **KServe InferenceServices**: Kubernetes-native model deployment and management
- **Model Storage**: GCS buckets for model artifacts
- **API Gateway**: Istio/KServe Gateway for model endpoint access
- **CloudFlare Tunnel**: Secure connectivity from GKE to local GPU

---

## 🎯 Objectives

### Primary Goals
1. Install KServe on local minikube cluster
2. Upload model artifacts to GCS
3. Deploy vLLM InferenceService for Qwen3-0.6B
4. Deploy embedding InferenceService for embeddinggemma-300m
5. Expose models via OpenAI-compatible API
6. Integrate application services with model endpoints
7. Benchmark and optimize inference performance

### Success Criteria
- ✅ KServe successfully installed on minikube
- ✅ Models loaded from GCS and cached locally
- ✅ vLLM serving Qwen3-0.6B with <100ms P95 latency
- ✅ Embedding service processing 100+ docs/sec
- ✅ GPU utilization >90% under load
- ✅ CloudFlare Tunnel routing GKE → Local GPU traffic
- ✅ Application successfully queries both models
- ✅ Prometheus metrics exported for all inference services

---

## 🛠️ Prerequisites

- Phase 0 completed (Minikube with GPU, CloudFlare Tunnel)
- Minikube running with NVIDIA GPU device plugin
- GCS buckets created for model storage
- Sufficient local storage (100GB+) for model cache
- CloudFlare Tunnel configured and running

---

## 📦 Task 1: Install KServe on Minikube

### 1.1 Install KServe Dependencies

```bash
# Switch to minikube context
kubectl config use-context minikube

# Install cert-manager (required by KServe)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=Available --timeout=300s deployment/cert-manager -n cert-manager
kubectl wait --for=condition=Available --timeout=300s deployment/cert-manager-webhook -n cert-manager
```

### 1.2 Install KServe

```bash
# Install KServe CRDs and runtime
curl -s "https://raw.githubusercontent.com/kserve/kserve/release-0.12/hack/quick_install.sh" | bash

# This installs:
# - KServe CRDs (InferenceService, etc.)
# - KServe controller
# - KNative Serving (serverless runtime)
# - Istio (service mesh for routing)

# Verify installation
kubectl get pods -n kserve
kubectl get pods -n knative-serving
kubectl get pods -n istio-system
```

### 1.3 Configure KServe for GPU

**File**: `kubernetes/kserve/configmap-inferenceservice.yaml`
```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: inferenceservice-config
  namespace: kserve
data:
  predictors: |
    {
      "vllm": {
        "image": "vllm/vllm-openai",
        "defaultImageVersion": "v0.5.4",
        "defaultGpuImageVersion": "v0.5.4-cuda12.1.0",
        "supportedFrameworks": [
          "vllm"
        ],
        "multiModelServer": false
      }
    }
```

```bash
# Apply configuration
kubectl apply -f kubernetes/kserve/configmap-inferenceservice.yaml
```

### 1.4 Create Service Account for Model Access

**File**: `kubernetes/kserve/service-account.yaml`
```yaml
---
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kserve-sa
  namespace: kserve
  annotations:
    iam.gke.io/gcp-service-account: intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
---
apiVersion: v1
kind: Secret
metadata:
  name: gcs-credentials
  namespace: kserve
  annotations:
    serving.kserve.io/gcs-secret: "true"
type: Opaque
stringData:
  gcs_credentials.json: |
    {
      "type": "service_account",
      "project_id": "YOUR_PROJECT_ID",
      "private_key_id": "...",
      "private_key": "...",
      "client_email": "intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com",
      "client_id": "...",
      "auth_uri": "https://accounts.google.com/o/oauth2/auth",
      "token_uri": "https://oauth2.googleapis.com/token",
      "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
    }
```

```bash
# Create GCS credentials secret
# First, download service account key from GCP Console
gcloud iam service-accounts keys create gcs-key.json \
  --iam-account=intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Create secret from file
kubectl create secret generic gcs-credentials \
  --from-file=gcs_credentials.json=gcs-key.json \
  -n kserve

# Annotate secret for KServe
kubectl annotate secret gcs-credentials \
  serving.kserve.io/gcs-secret=true \
  -n kserve

# Cleanup local key file
rm gcs-key.json
```

---

## 📦 Task 2: Upload Models to GCS

### 2.1 Download and Prepare Models

```bash
# Create local model directory
mkdir -p ~/models/{Qwen3-0.6B,embeddinggemma-300m}

# Download Qwen3-0.6B-Instruct from Hugging Face
cd ~/models/Qwen3-0.6B
huggingface-cli download Qwen/Qwen3-0.6B --local-dir .

# Download embeddinggemma-300m from Hugging Face
cd ~/models/embeddinggemma-300m
huggingface-cli download google/embeddinggemma-300m --local-dir .
```

### 2.2 Upload Models to GCS

```bash
# Upload Qwen3-0.6B
gsutil -m rsync -r ~/models/Qwen3-0.6B/ gs://intellirag-models/Qwen3-0.6B/

# Upload embeddinggemma-300m
gsutil -m rsync -r ~/models/embeddinggemma-300m/ gs://intellirag-models/embeddinggemma-300m/

# Verify uploads
gsutil ls gs://intellirag-models/Qwen3-0.6B/
gsutil ls gs://intellirag-models/embeddinggemma-300m/

# Check total size
gsutil du -sh gs://intellirag-models/
```

---

## 📦 Task 3: Deploy vLLM InferenceService for LLM

### 3.1 Create vLLM InferenceService Manifest

**File**: `kubernetes/kserve/vllm-qwen-inference.yaml`
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-qwen
  namespace: kserve
  annotations:
    serving.kserve.io/enable-prometheus-scraping: "true"
spec:
  predictor:
    serviceAccountName: kserve-sa
    minReplicas: 1
    maxReplicas: 1
    containers:
    - name: kserve-container
      image: vllm/vllm-openai:v0.5.4
      command:
      - python3
      - -m
      - vllm.entrypoints.openai.api_server
      args:
      - --model
      - /mnt/models/Qwen3-0.6B
      - --dtype
      - auto
      - --max-model-len
      - "8192"
      - --gpu-memory-utilization
      - "0.95"
      - --trust-remote-code
      - --enable-prefix-caching
      - --port
      - "8080"
      env:
      - name: GOOGLE_APPLICATION_CREDENTIALS
        value: /var/secrets/gcs/gcs_credentials.json
      - name: HF_HOME
        value: /mnt/models/cache
      ports:
      - containerPort: 8080
        protocol: TCP
        name: http1
      resources:
        requests:
          cpu: "4"
          memory: 16Gi
          nvidia.com/gpu: "1"
        limits:
          cpu: "8"
          memory: 24Gi
          nvidia.com/gpu: "1"
      volumeMounts:
      - name: model-storage
        mountPath: /mnt/models
      - name: gcs-credentials
        mountPath: /var/secrets/gcs
        readOnly: true
      livenessProbe:
        httpGet:
          path: /health
          port: 8080
        initialDelaySeconds: 120
        periodSeconds: 30
        timeoutSeconds: 10
        failureThreshold: 3
      readinessProbe:
        httpGet:
          path: /health
          port: 8080
        initialDelaySeconds: 60
        periodSeconds: 10
        timeoutSeconds: 5
        failureThreshold: 3
    volumes:
    - name: model-storage
      persistentVolumeClaim:
        claimName: model-cache-pvc
    - name: gcs-credentials
      secret:
        secretName: gcs-credentials
  # Optional: Transformer for request/response processing
  # transformer:
  #   containers:
  #   - image: your-transformer-image:latest
```

### 3.2 Deploy vLLM InferenceService

```bash
# Apply InferenceService
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml

# Watch deployment progress
kubectl get inferenceservice vllm-qwen -n kserve -w

# This will take 5-10 minutes as it:
# 1. Pulls vLLM image
# 2. Downloads model from GCS
# 3. Loads model into GPU memory
# 4. Starts OpenAI server

# Check pod logs
kubectl logs -n kserve -l serving.kserve.io/inferenceservice=vllm-qwen -f
```

### 3.3 Verify vLLM Deployment

```bash
# Check InferenceService status
kubectl get inferenceservice vllm-qwen -n kserve

# Expected output:
# NAME        URL                                      READY   PREV   LATEST   AGE
# vllm-qwen   http://vllm-qwen.kserve.svc.cluster...  True    100                5m

# Get service endpoint
ISVC_URL=$(kubectl get inferenceservice vllm-qwen -n kserve -o jsonpath='{.status.url}')
echo $ISVC_URL

# Port-forward to test locally
kubectl port-forward -n kserve svc/vllm-qwen-predictor-default 8080:80

# Test health endpoint
curl http://localhost:8080/health

# Test OpenAI-compatible API
curl http://localhost:8080/v1/models

# Test chat completion
curl http://localhost:8080/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "messages": [
      {"role": "user", "content": "What is RAG?"}
    ],
    "max_tokens": 100
  }'
```

---

## 📦 Task 4: Deploy Embedding InferenceService

> **Note**: Sections 4.1-4.3 cover verification and containerization of the **already implemented** embedding service. The actual KServe deployment tasks begin at section 4.4.

### 4.1 Verify Existing Embedding Server Implementation

✅ **Already Implemented**: The custom embedding service has been developed and is available at `deploy/embedding-service/`

**Existing Components**:
- **`main.py`**: FastAPI-based embedding server with the following features:
  - Configurable model support (default: `google/embeddinggemma-300m`)
  - Endpoints: `/health`, `/model-info`, `/vectorize`
  - Auto-detection of embedding dimensions
  - Batch processing with configurable batch sizes
  - CPU and GPU support
  - HuggingFace authentication for gated models

- **`Dockerfile`**: Production-ready containerization with health checks

- **`docker-compose.yaml`**: Local development and testing setup with:
  - NVIDIA GPU runtime support
  - Environment-based configuration
  - Model caching to avoid re-downloads
  - Resource limits and health checks

**Configuration Options** (via environment variables):
- `EMBEDDING_MODEL`: Model to load (default: `BAAI/bge-m3`)
- `DEVICE`: `cpu` or `cuda` (default: `cpu`)
- `MAX_BATCH_SIZE`: Maximum batch size (default: `128`)
- `HF_TOKEN`: HuggingFace token for gated models (optional)

### 4.2 Test Embedding Service Locally (Optional)

```bash
cd deploy/embedding-service

# Test with docker-compose (uses default model: BAAI/bge-m3)
docker-compose up -d

# Check health
curl http://localhost:8001/health

# Get model info
curl http://localhost:8001/model-info

# Test embedding generation
curl -X POST http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello world", "Test document"],
    "normalize": true
  }'

# Stop service
docker-compose down
```

### 4.3 Build and Push Embedding Image for KServe

```bash
cd deploy/embedding-service

# Build image for KServe deployment
docker build -t gcr.io/YOUR_PROJECT_ID/intellirag-embedding:v1.0.0 .

# Test locally
docker run --rm -p 8001:8001 gcr.io/YOUR_PROJECT_ID/intellirag-embedding:v1.0.0

# In another terminal, test
curl http://localhost:8001/health
curl -X POST http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello world"], "normalize": true}'

# Push to GCR
docker push gcr.io/YOUR_PROJECT_ID/intellirag-embedding:v1.0.0
```

### 4.4 Create Embedding InferenceService for KServe

**File**: `kubernetes/kserve/embedding-inference.yaml`
```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: intellirag-embedding
  namespace: kserve
  annotations:
    serving.kserve.io/enable-prometheus-scraping: "true"
spec:
  predictor:
    serviceAccountName: kserve-sa
    minReplicas: 1
    maxReplicas: 1
    containers:
    - name: kserve-container
      image: gcr.io/YOUR_PROJECT_ID/intellirag-embedding:v1.0.0
      env:
      # Configure which embedding model to use
      - name: EMBEDDING_MODEL
        value: "google/embeddinggemma-300m"
      # Use CPU for embedding inference (less GPU memory pressure)
      - name: DEVICE
        value: "cpu"
      - name: MAX_BATCH_SIZE
        value: "32"
      # Optional: HuggingFace token for gated models
      - name: HF_TOKEN
        valueFrom:
          secretKeyRef:
            name: hf-token
            key: token
            optional: true
      # Model cache directory
      - name: TRANSFORMERS_CACHE
        value: /mnt/models/cache
      ports:
      - containerPort: 8001
        protocol: TCP
        name: http1
      resources:
        requests:
          cpu: "2"
          memory: 4Gi
        limits:
          cpu: "4"
          memory: 8Gi
      volumeMounts:
      - name: model-storage
        mountPath: /mnt/models
      livenessProbe:
        httpGet:
          path: /health
          port: 8001
        initialDelaySeconds: 90
        periodSeconds: 30
        timeoutSeconds: 5
        failureThreshold: 3
      readinessProbe:
        httpGet:
          path: /health
          port: 8001
        initialDelaySeconds: 60
        periodSeconds: 10
        timeoutSeconds: 3
        failureThreshold: 3
    volumes:
    - name: model-storage
      persistentVolumeClaim:
        claimName: model-cache-pvc
```

**Note**: The service uses port 8001 and has the following endpoints:
- `/health` - Health check
- `/model-info` - Get model metadata including embedding dimension
- `/vectorize` - Generate embeddings (POST with `{"texts": [...], "normalize": bool}`)
- `/docs` - OpenAPI documentation

### 4.5 Deploy Embedding InferenceService

```bash
# Apply InferenceService
kubectl apply -f kubernetes/kserve/embedding-inference.yaml

# Watch deployment
kubectl get inferenceservice intellirag-embedding -n kserve -w

# Expected output when ready:
# NAME                  URL                                      READY   PREV   LATEST   AGE
# intellirag-embedding  http://intellirag-embedding.kserve...   True    100              5m

# Check logs
kubectl logs -n kserve -l serving.kserve.io/inferenceservice=intellirag-embedding -f

# Port-forward and test
kubectl port-forward -n kserve svc/intellirag-embedding-predictor-default 8001:80

# Test health endpoint
curl http://localhost:8001/health

# Get model information (including embedding dimension)
curl http://localhost:8001/model-info

# Test embedding generation
curl -X POST http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{
    "texts": [
      "This is a test document for embedding generation",
      "Another test sentence"
    ],
    "normalize": true
  }'
```

---

## 📦 Task 5: Configure CloudFlare Tunnel Gateway

### 5.1 Update CloudFlare Tunnel Config

**File**: `~/.cloudflared/config.yml`
```yaml
tunnel: intellirag-gpu
credentials-file: /home/YOUR_USERNAME/.cloudflared/TUNNEL_ID.json

ingress:
  # Route LLM traffic
  - hostname: llm.intellirag.example.com
    service: http://vllm-qwen-predictor-default.kserve.svc.cluster.local:80
    originRequest:
      connectTimeout: 60s
      noTLSVerify: true

  # Route embedding traffic (updated service name)
  - hostname: embeddings.intellirag.example.com
    service: http://intellirag-embedding-predictor-default.kserve.svc.cluster.local:80
    originRequest:
      connectTimeout: 30s
      noTLSVerify: true

  # Catch-all
  - service: http_status:404

loglevel: info
```

### 5.2 Update DNS Records

```bash
# Add DNS records for model endpoints
cloudflared tunnel route dns intellirag-gpu llm.intellirag.example.com
cloudflared tunnel route dns intellirag-gpu embeddings.intellirag.example.com

# Restart tunnel
sudo systemctl restart cloudflared
```

### 5.3 Test External Access

```bash
# Test LLM endpoint from external network (or GKE pod)
curl https://llm.intellirag.example.com/v1/models

# Test embedding endpoint - health check
curl https://embeddings.intellirag.example.com/health

# Test embedding endpoint - get model info
curl https://embeddings.intellirag.example.com/model-info

# Test embedding generation
curl -X POST https://embeddings.intellirag.example.com/vectorize \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["test document", "another test"],
    "normalize": true
  }'
```

---

## 📦 Task 6: Update Application to Use KServe Endpoints

### 6.1 Update FastAPI Configuration

**File**: `app/config.py` (update)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # LLM Configuration
    LLM_ENDPOINT: str = "https://llm.intellirag.example.com/v1"
    LLM_MODEL: str = "Qwen/Qwen3-0.6B-Instruct"
    LLM_TIMEOUT: int = 60

    # Embedding Configuration
    EMBEDDING_ENDPOINT: str = "https://embeddings.intellirag.example.com/v1"
    EMBEDDING_MODEL: str = "google/embeddinggemma-300m"
    EMBEDDING_TIMEOUT: int = 30
    EMBEDDING_BATCH_SIZE: int = 32

    class Config:
        env_file = ".env"

settings = Settings()
```

### 6.2 Update LLM Client

**File**: `app/services/llm_client.py` (update)
```python
import httpx
from openai import AsyncOpenAI
from app.config import settings

class LLMClient:
    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=settings.LLM_ENDPOINT,
            api_key="EMPTY",  # vLLM doesn't require API key
            timeout=settings.LLM_TIMEOUT
        )

    async def generate(self, prompt: str, max_tokens: int = 512) -> str:
        response = await self.client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens,
            temperature=0.7
        )
        return response.choices[0].message.content
```

### 6.3 Update Embedding Service

**File**: `app/services/embedding.py` (update)
```python
import httpx
from typing import List
import numpy as np
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=settings.EMBEDDING_TIMEOUT)
        self.endpoint = f"{settings.EMBEDDING_ENDPOINT}/vectorize"
        self.model_info_endpoint = f"{settings.EMBEDDING_ENDPOINT}/model-info"
        self._embedding_dimension = None

    async def get_embedding_dimension(self) -> int:
        """Get embedding dimension from the model service."""
        if self._embedding_dimension is None:
            response = await self.client.get(self.model_info_endpoint)
            response.raise_for_status()
            data = response.json()
            self._embedding_dimension = data["embedding_dimension"]
            logger.info(f"Embedding dimension: {self._embedding_dimension}")
        return self._embedding_dimension

    async def embed_texts(self, texts: List[str], normalize: bool = True) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        response = await self.client.post(
            self.endpoint,
            json={
                "texts": texts,
                "normalize": normalize
            }
        )
        response.raise_for_status()
        data = response.json()
        return data["embeddings"]

    async def embed_query(self, query: str, normalize: bool = True) -> List[float]:
        """Generate embedding for a single query."""
        embeddings = await self.embed_texts([query], normalize=normalize)
        return embeddings[0]
```

### 6.4 Update Helm ConfigMap

**File**: `helm/intellirag-app/values-prod.yaml` (update)
```yaml
config:
  llmEndpoint: "https://llm.intellirag.example.com/v1"
  llmModel: "Qwen/Qwen3-0.6B-Instruct"
  # Note: No /v1 suffix - API uses /vectorize, /health, /model-info directly
  embeddingEndpoint: "https://embeddings.intellirag.example.com"
  embeddingModel: "google/embeddinggemma-300m"
```

### 6.5 Redeploy Application

```bash
# Upgrade Helm release with new config
helm upgrade intellirag ./helm/intellirag-app \
  --namespace app \
  --values helm/intellirag-app/values-prod.yaml \
  --wait

# Watch rollout
kubectl rollout status deployment/intellirag-app -n app

# Test query endpoint
kubectl port-forward -n app svc/intellirag-app 8000:8000

curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is retrieval-augmented generation?"
  }'
```

---

## 📦 Task 7: Performance Benchmarking

### 7.1 Install Benchmarking Tools

```bash
# Install hey for load testing
go install github.com/rakyll/hey@latest

# Install locust for complex scenarios
pip install locust
```

### 7.2 Benchmark LLM Inference

```bash
# Simple load test
hey -n 100 -c 10 -m POST \
  -H "Content-Type: application/json" \
  -d '{"model":"Qwen/Qwen3-0.6B-Instruct","messages":[{"role":"user","content":"Hello"}],"max_tokens":50}' \
  https://llm.intellirag.example.com/v1/chat/completions

# Expected metrics:
# - Throughput: 500-800 tokens/sec
# - P95 latency: <100ms
# - GPU utilization: >90%
```

### 7.3 Benchmark Embedding Generation

```bash
# Batch embedding test
hey -n 1000 -c 50 -m POST \
  -H "Content-Type: application/json" \
  -d '{"texts":["test document 1","test document 2"],"normalize":true}' \
  https://embeddings.intellirag.example.com/vectorize

# Expected metrics:
# - Throughput: 100-200 docs/sec
# - P95 latency: <200ms
# - CPU utilization: 80-90% (CPU inference)
```

### 7.4 Monitor GPU Performance

```bash
# SSH into minikube node
minikube ssh

# Monitor GPU in real-time
watch -n 1 nvidia-smi

# Expected during load:
# - GPU Utilization: 90-100%
# - Memory Usage: 10-11GB / 12GB
# - Temperature: 60-80°C
```

---

## 🧪 Verification and Testing

### Test 1: End-to-End RAG Query

```bash
# Upload test document
curl -X POST http://localhost:8000/api/v1/upload \
  -F "file=@tests/fixtures/sample.pdf"

# Trigger ingestion
curl -X POST http://localhost:8000/api/v1/ingest \
  -H "Content-Type: application/json" \
  -d '{"file_path":"sample.pdf"}'

# Query with RAG
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the key points from the document"
  }'

# Verify response includes:
# - Retrieved context from Qdrant
# - Generated answer from vLLM
# - Low latency (<2s total)
```

### Test 2: Concurrent Requests

```bash
# Run 100 concurrent queries
seq 1 100 | xargs -P 10 -I {} curl -s -X POST \
  http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"Test query {}"}' \
  -w "Request {}: %{time_total}s\n"

# Verify all requests succeed
# Check P95 latency stays <5s
```

### Test 3: Model Failover

```bash
# Scale vLLM InferenceService to 0
kubectl scale inferenceservice vllm-qwen -n kserve --replicas=0

# Verify application handles gracefully
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}'

# Expected: 503 Service Unavailable with clear error message

# Scale back up
kubectl scale inferenceservice vllm-qwen -n kserve --replicas=1
```

---

## 🚨 Troubleshooting

### Issue 1: Model Download Timeout

**Symptom**: InferenceService pods stuck in Init or CrashLoopBackOff

**Debug Steps**:
```bash
# Check pod events
kubectl describe inferenceservice vllm-qwen -n kserve

# Check pod logs
kubectl logs -n kserve -l serving.kserve.io/inferenceservice=vllm-qwen --all-containers

# Increase timeout in InferenceService spec:
# readinessProbe.initialDelaySeconds: 300
```

### Issue 2: GPU Out of Memory

**Symptom**: vLLM crashes with CUDA OOM error

**Solutions**:
```bash
# Reduce max-model-len
# args: ["--max-model-len", "4096"]

# Enable quantization (INT8)
# args: ["--quantization", "awq"]

# Reduce gpu-memory-utilization
# args: ["--gpu-memory-utilization", "0.85"]
```

### Issue 3: CloudFlare Tunnel Not Routing

**Symptom**: 502 Bad Gateway from GKE to local GPU

**Debug Steps**:
```bash
# Check tunnel status
cloudflared tunnel info intellirag-gpu

# Verify KServe service is accessible from tunnel host
kubectl port-forward -n kserve svc/vllm-qwen-predictor-default 8080:80
curl http://localhost:8080/health

# Test from minikube node
minikube ssh
curl http://vllm-qwen-predictor-default.kserve.svc.cluster.local/health
```

### Issue 4: High Latency

**Symptom**: Query latency >1s

**Investigation**:
```bash
# Check Jaeger traces to identify bottleneck
kubectl port-forward -n observability svc/jaeger-query 16686:80

# Check GPU utilization
minikube ssh
nvidia-smi

# Enable vLLM prefix caching
# args: ["--enable-prefix-caching"]

# Tune KV cache size
# args: ["--kv-cache-dtype", "fp8"]
```

### Issue 5: Embedding Service Not Loading Model

**Symptom**: Embedding service returns 503 "Model not loaded"

**Debug Steps**:
```bash
# Check pod logs
kubectl logs -n kserve -l serving.kserve.io/inferenceservice=intellirag-embedding -f

# Common issues:
# 1. Model download from HuggingFace taking too long
# 2. Insufficient memory
# 3. Missing HF_TOKEN for gated models

# Increase startup time
# readinessProbe.initialDelaySeconds: 120

# Check if model requires authentication
# Add HF_TOKEN secret if needed:
kubectl create secret generic hf-token \
  --from-literal=token=YOUR_HF_TOKEN \
  -n kserve
```

### Issue 6: Embedding API Response Format Error

**Symptom**: Application fails to parse embedding response

**Solution**:
```bash
# Verify API endpoint format
curl http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{"texts":["test"],"normalize":true}'

# Expected response format:
# {
#   "embeddings": [[0.1, 0.2, ...]],
#   "model": "google/embeddinggemma-300m",
#   "dimension": 300,
#   "count": 1,
#   "processing_time_seconds": 0.05
# }

# Ensure application code uses:
# - POST /vectorize (not /v1/embeddings)
# - Request: {"texts": [...], "normalize": bool}
# - Response: data["embeddings"]
```

---

## ✅ Deliverables Checklist

**Phase Prerequisites**:
- [x] Custom embedding service implemented (`deploy/embedding-service/`)
- [x] Embedding service Dockerfile created
- [x] Embedding service docker-compose for local testing

**KServe Installation**:
- [ ] KServe installed and configured on minikube
- [ ] cert-manager deployed
- [ ] KServe service account and GCS credentials configured

**Model Deployment**:
- [ ] Models uploaded to GCS (Qwen3-0.6B, embeddinggemma-300m)
- [ ] vLLM InferenceService deployed and healthy
- [ ] Embedding InferenceService deployed and healthy
- [ ] Both services passing health checks

**Networking & Integration**:
- [ ] CloudFlare Tunnel updated for model endpoints
- [ ] DNS records configured (llm.intellirag.example.com, embeddings.intellirag.example.com)
- [ ] External access verified from GKE
- [ ] Application configuration updated with KServe endpoints
- [ ] Application code updated to use embedding /vectorize API

**Testing & Validation**:
- [ ] LLM endpoint returns completions successfully
- [ ] Embedding endpoint generates vectors successfully
- [ ] End-to-end RAG query working (upload → ingest → query)
- [ ] Performance benchmarks completed and documented
- [ ] GPU utilization >90% under load (LLM)
- [ ] CPU utilization 80-90% under load (embeddings)
- [ ] P95 latency <100ms for LLM inference
- [ ] P95 latency <200ms for embedding generation

**Observability**:
- [ ] Prometheus metrics exported from both services
- [ ] Metrics visible in Grafana dashboards
- [ ] Load testing passed with 100+ concurrent users
- [ ] Documentation updated with all endpoint URLs and API specs

---

## 📝 Next Steps

After completing Phase 2, proceed to:
- **[Phase 3: Production Hardening](./phase-3-production-hardening.md)** - Implement security, scaling, and reliability features

---

**Phase Status**: Pending
**Last Updated**: 2025-11-13 (Updated embedding service sections to reflect existing implementation)
