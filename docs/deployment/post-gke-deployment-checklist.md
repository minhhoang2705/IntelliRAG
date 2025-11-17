# Post-GKE Deployment Checklist for IntelliRAG

**Status**: ✅ Active
**Created**: 2025-11-16
**Purpose**: Step-by-step guide for deploying IntelliRAG after GKE cluster provisioning
**Prerequisites**: Phase 0 complete (GKE cluster running)

---

## 📋 Overview

This checklist provides a comprehensive, step-by-step guide for deploying the complete IntelliRAG system after your GKE cluster has been provisioned. Follow the phases in order for a smooth deployment.

**Total Estimated Time**: 6-8 hours (can be spread over 2-3 days)

---

## ✅ Phase 0 Verification (5 minutes)

Before proceeding, verify Phase 0 is complete:

```bash
# 1. Verify kubectl is connected to GKE
kubectl cluster-info
# Expected: Kubernetes control plane is running at https://X.X.X.X

# 2. Verify namespaces exist
kubectl get namespaces | grep -E "(app|kserve|observability)"
# Expected: app, kserve, observability

# 3. Verify service accounts
kubectl get sa -n app intellirag-app
# Expected: intellirag-app exists with Workload Identity annotation

# 4. Verify GCS buckets
gsutil ls | grep intellirag
# Expected: gs://intellirag-data, gs://intellirag-models

# 5. Check node status
kubectl get nodes
# Expected: 1 node (e2-standard-2) in Ready state
```

**If any verification fails**: Review [Phase 0 Execution Guide](../plans/phase-0-execution-guide.md)

---

## 🎯 Phase 1: Local GPU Setup (2-3 hours)

### Step 1.1: Install Prerequisites on Local Server (30 min)

**On your local Ubuntu 22.04 server with RTX 4070Ti:**

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install NVIDIA drivers (if not already installed)
# Check current driver
nvidia-smi
# If not working, install drivers:
sudo ubuntu-drivers autoinstall
sudo reboot

# Verify GPU after reboot
nvidia-smi
# Expected: RTX 4070Ti listed with driver version 535+

# Install Docker (if not installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install nvidia-container-toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit

# Configure Docker with NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify Docker GPU access
docker run --rm --gpus all nvidia/cuda:12.0-base-ubuntu22.04 nvidia-smi
# Expected: nvidia-smi output inside container
```

**Checklist**:
- [ ] NVIDIA drivers installed (v535+)
- [ ] Docker installed and running
- [ ] nvidia-container-toolkit installed
- [ ] Docker can access GPU

---

### Step 1.2: Install Minikube with GPU Support (20 min)

```bash
# Download minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Verify installation
minikube version
# Expected: minikube version: v1.32.0+

# Start minikube with GPU support
minikube start \
  --driver=docker \
  --gpus=all \
  --cpus=8 \
  --memory=32g \
  --disk-size=100g \
  --kubernetes-version=v1.28.3

# Verify cluster is running
minikube status
# Expected: host, kubelet, apiserver all Running

# Verify GPU is available in minikube
minikube ssh
nvidia-smi
exit
# Expected: GPU visible inside minikube VM

# Install NVIDIA device plugin
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU resource
kubectl get nodes -o json | jq '.items[0].status.capacity."nvidia.com/gpu"'
# Expected: "1"
```

**Checklist**:
- [ ] Minikube installed and running
- [ ] GPU accessible in minikube
- [ ] NVIDIA device plugin deployed
- [ ] GPU resource available for scheduling

---

### Step 1.3: Install KServe v0.14.1 (30 min)

```bash
# Install cert-manager (prerequisite)
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager

# Install KServe CRDs via Helm
helm install kserve-crd oci://ghcr.io/kserve/charts/kserve-crd --version v0.14.1

# Apply KServe cluster resources
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.14.0/kserve-cluster-resources.yaml

# Wait for KServe controller to be ready
kubectl wait --for=condition=available --timeout=300s deployment/kserve-controller-manager -n kserve

# Verify KServe installation
kubectl get pods -n kserve
# Expected: kserve-controller-manager pod Running

# Check CRDs
kubectl get crd | grep serving.kserve.io
# Expected: inferenceservices.serving.kserve.io, etc.
```

**Checklist**:
- [ ] cert-manager installed and running
- [ ] KServe CRDs installed
- [ ] KServe controller-manager running
- [ ] InferenceService CRD available

---

### Step 1.4: Deploy vLLM InferenceService (Qwen3-0.6B) (30 min)

**Create InferenceService manifest**:

```bash
# Create kserve namespace (if not exists)
kubectl create namespace kserve --dry-run=client -o yaml | kubectl apply -f -

# Create vLLM InferenceService manifest
cat <<EOF > vllm-qwen-inference.yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-qwen
  namespace: kserve
spec:
  predictor:
    containers:
      - name: kserve-container
        image: vllm/vllm-openai:latest
        args:
          - --model=Qwen/Qwen2.5-0.5B-Instruct
          - --dtype=float16
          - --max-model-len=4096
          - --gpu-memory-utilization=0.9
          - --tensor-parallel-size=1
        env:
          - name: HF_TOKEN
            value: ""  # Optional: Add if using gated models
        resources:
          limits:
            nvidia.com/gpu: "1"
            memory: 10Gi
          requests:
            nvidia.com/gpu: "1"
            memory: 8Gi
            cpu: 2000m
        ports:
          - containerPort: 8000
            protocol: TCP
EOF

# Apply InferenceService
kubectl apply -f vllm-qwen-inference.yaml

# Watch pod creation (may take 5-10 minutes to download model)
kubectl get pods -n kserve -w

# Wait for InferenceService to be ready
kubectl wait --for=condition=ready --timeout=600s inferenceservice/vllm-qwen -n kserve

# Check InferenceService status
kubectl get inferenceservices -n kserve vllm-qwen
# Expected: READY=True, URL=http://vllm-qwen.kserve.svc.cluster.local
```

**Test vLLM endpoint**:
```bash
# Port-forward to test
kubectl port-forward -n kserve svc/vllm-qwen-predictor 8000:8000 &

# Test chat completions
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen2.5-0.5B-Instruct",
    "messages": [{"role": "user", "content": "Hello, how are you?"}],
    "max_tokens": 50
  }'

# Expected: JSON response with generated text
```

**Checklist**:
- [ ] vLLM InferenceService deployed
- [ ] InferenceService status is READY
- [ ] Pod is running and healthy
- [ ] Test curl succeeds

---

### Step 1.5: Deploy BGE-M3 Embedding InferenceService (30 min)

**Create Embedding InferenceService manifest**:

```bash
cat <<EOF > bge-m3-inference.yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: bge-m3-embedding
  namespace: kserve
spec:
  predictor:
    containers:
      - name: kserve-container
        image: michaelf34/infinity:latest
        args:
          - --model-name-or-path=BAAI/bge-m3
          - --port=8000
        resources:
          limits:
            nvidia.com/gpu: "1"
            memory: 6Gi
          requests:
            nvidia.com/gpu: "1"
            memory: 4Gi
            cpu: 1000m
        ports:
          - containerPort: 8000
            protocol: TCP
EOF

# Apply InferenceService
kubectl apply -f bge-m3-inference.yaml

# Wait for ready
kubectl wait --for=condition=ready --timeout=600s inferenceservice/bge-m3-embedding -n kserve

# Check status
kubectl get inferenceservices -n kserve bge-m3-embedding
```

**Test embedding endpoint**:
```bash
# Port-forward
kubectl port-forward -n kserve svc/bge-m3-embedding-predictor 8001:8000 &

# Test embeddings
curl http://localhost:8001/v1/embeddings \
  -H "Content-Type: application/json" \
  -d '{
    "model": "BAAI/bge-m3",
    "input": "This is a test sentence for embedding generation"
  }'

# Expected: JSON response with 1024-dim vector
```

**Checklist**:
- [ ] BGE-M3 InferenceService deployed
- [ ] InferenceService status is READY
- [ ] Test curl succeeds
- [ ] Embedding vector has 1024 dimensions

---

### Step 1.6: Setup CloudFlare Tunnel (45 min)

**Follow the detailed guide**: [CloudFlare Tunnel Setup Guide](./cloudflare-tunnel-setup-guide.md)

**Quick Steps Summary**:

```bash
# 1. Install cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# 2. Authenticate
cloudflared tunnel login

# 3. Create tunnel
cloudflared tunnel create intellirag-gpu
# Save the tunnel ID

# 4. Configure tunnel (replace <TUNNEL_ID> with actual ID)
mkdir -p ~/.cloudflared
cat <<EOF > ~/.cloudflared/config.yml
tunnel: <TUNNEL_ID>
credentials-file: /home/$USER/.cloudflared/<TUNNEL_ID>.json

ingress:
  - hostname: gpu.intellirag.example.com
    service: http://localhost:8080
  - service: http_status:404
EOF

# 5. Route DNS
cloudflared tunnel route dns intellirag-gpu gpu.intellirag.example.com

# 6. Test tunnel
cloudflared tunnel --config ~/.cloudflared/config.yml run intellirag-gpu

# 7. Setup as systemd service (follow detailed guide)
```

**Test CloudFlare Tunnel**:
```bash
# From local server
curl https://gpu.intellirag.example.com/health

# From GKE (in another terminal)
kubectl run -n app -it --rm debug \
  --image=curlimages/curl \
  --restart=Never \
  -- curl -v https://gpu.intellirag.example.com/health
```

**Checklist**:
- [ ] cloudflared installed
- [ ] Tunnel created and configured
- [ ] DNS route created
- [ ] Systemd service running
- [ ] Test from GKE succeeds

---

## 🚀 Phase 2: GKE Application Deployment (2-3 hours)

### Step 2.1: Build FastAPI Docker Image (30 min)

**On your development machine**:

```bash
# Navigate to project root
cd /path/to/IntelliRAG

# Create Dockerfile (if not exists)
cat <<'EOF' > Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY pyproject.toml .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

# Build image
docker build -t gcr.io/intellirag-aide1/intellirag-api:latest .

# Test image locally (optional)
docker run --rm -p 8000:8000 \
  -e QDRANT_HOST=localhost \
  -e GCS_BUCKET=intellirag-data \
  gcr.io/intellirag-aide1/intellirag-api:latest

# Push to Google Container Registry
gcloud auth configure-docker
docker push gcr.io/intellirag-aide1/intellirag-api:latest
```

**Checklist**:
- [ ] Dockerfile created
- [ ] Image built successfully
- [ ] Image pushed to GCR
- [ ] Image URI: `gcr.io/intellirag-aide1/intellirag-api:latest`

---

### Step 2.2: Deploy Qdrant to GKE (20 min)

```bash
# Create Qdrant manifest
cat <<EOF > qdrant-deployment.yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: qdrant-storage
  namespace: app
spec:
  storageClassName: fast-ssd
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: qdrant
  namespace: app
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
          image: qdrant/qdrant:v1.7.4
          ports:
            - containerPort: 6333
              name: http
            - containerPort: 6334
              name: grpc
          resources:
            requests:
              cpu: 1000m
              memory: 4Gi
            limits:
              cpu: 4000m
              memory: 8Gi
          volumeMounts:
            - name: qdrant-storage
              mountPath: /qdrant/storage
  volumeClaimTemplates:
    - metadata:
        name: qdrant-storage
      spec:
        storageClassName: fast-ssd
        accessModes:
          - ReadWriteOnce
        resources:
          requests:
            storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: qdrant
  namespace: app
spec:
  selector:
    app: qdrant
  ports:
    - name: http
      port: 6333
      targetPort: 6333
    - name: grpc
      port: 6334
      targetPort: 6334
  type: ClusterIP
EOF

# Apply manifest
kubectl apply -f qdrant-deployment.yaml

# Wait for Qdrant to be ready
kubectl wait --for=condition=ready --timeout=300s pod/qdrant-0 -n app

# Verify Qdrant
kubectl exec -n app qdrant-0 -- curl http://localhost:6333
# Expected: JSON response with Qdrant version
```

**Checklist**:
- [ ] PVC created
- [ ] StatefulSet deployed
- [ ] Pod is running and ready
- [ ] Service is accessible

---

### Step 2.3: Deploy FastAPI to GKE (30 min)

**Create ConfigMap and Secret**:

```bash
# Create ConfigMap
cat <<EOF > intellirag-configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: intellirag-config
  namespace: app
data:
  LLM_ENDPOINT: "https://gpu.intellirag.example.com/v1/chat/completions"
  EMBEDDING_ENDPOINT: "https://gpu.intellirag.example.com/v1/embeddings"
  QDRANT_HOST: "qdrant.app.svc.cluster.local"
  QDRANT_PORT: "6333"
  GCS_BUCKET: "intellirag-data"
  GCS_PROJECT_ID: "intellirag-aide1"
  JAEGER_AGENT_HOST: "jaeger-agent.observability.svc.cluster.local"
  JAEGER_AGENT_PORT: "6831"
EOF

kubectl apply -f intellirag-configmap.yaml

# Create Secret (if needed)
kubectl create secret generic intellirag-secrets \
  -n app \
  --from-literal=MODEL_API_KEY=""  # Add if using CloudFlare Access
```

**Create Deployment**:

```bash
cat <<EOF > intellirag-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: intellirag-api
  namespace: app
spec:
  replicas: 2
  selector:
    matchLabels:
      app: intellirag-api
  template:
    metadata:
      labels:
        app: intellirag-api
    spec:
      serviceAccountName: intellirag-app
      containers:
        - name: api
          image: gcr.io/intellirag-aide1/intellirag-api:latest
          ports:
            - containerPort: 8000
              name: http
          envFrom:
            - configMapRef:
                name: intellirag-config
          env:
            - name: MODEL_API_KEY
              valueFrom:
                secretKeyRef:
                  name: intellirag-secrets
                  key: MODEL_API_KEY
                  optional: true
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: 2000m
              memory: 2Gi
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 30
            periodSeconds: 10
          readinessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: intellirag-api
  namespace: app
spec:
  selector:
    app: intellirag-api
  ports:
    - port: 8000
      targetPort: 8000
      protocol: TCP
  type: ClusterIP
EOF

# Apply deployment
kubectl apply -f intellirag-deployment.yaml

# Wait for deployment
kubectl rollout status deployment/intellirag-api -n app

# Verify pods
kubectl get pods -n app -l app=intellirag-api
```

**Checklist**:
- [ ] ConfigMap created
- [ ] Secret created (if needed)
- [ ] Deployment created
- [ ] 2 pods running and ready
- [ ] Service created

---

### Step 2.4: Test End-to-End Flow (30 min)

```bash
# Port-forward to test locally
kubectl port-forward -n app svc/intellirag-api 8000:8000 &

# Test health endpoint
curl http://localhost:8000/health

# Test query endpoint (should call local GPU via CloudFlare Tunnel)
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is machine learning?"
  }'

# Test ingestion endpoint
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@/path/to/sample.pdf"
```

**Check logs for CloudFlare Tunnel calls**:
```bash
# FastAPI logs
kubectl logs -n app -l app=intellirag-api --tail=50

# Should see logs like:
# INFO:     Calling embedding endpoint: https://gpu.intellirag.example.com/v1/embeddings
# INFO:     Embedding latency: 45ms
```

**Checklist**:
- [ ] Health check succeeds
- [ ] Query endpoint works
- [ ] Ingestion endpoint works
- [ ] CloudFlare Tunnel calls succeed
- [ ] Qdrant stores vectors

---

## 📊 Phase 3: Observability Stack (1-2 hours)

### Step 3.1: Deploy Observability Stack with Helmfile (30 min)

```bash
# Navigate to observability directory
cd kubernetes/observability/

# Review helmfile.yaml
cat helmfile.yaml

# Create .env file for Grafana password
cat <<EOF > .env
GRAFANA_ADMIN_PASSWORD=your-secure-password-here
EOF

# Deploy all charts
helmfile apply

# Wait for all pods to be ready
kubectl get pods -n observability -w

# Verify all services are running
kubectl get pods -n observability
# Expected: prometheus, grafana, jaeger, loki pods all Running
```

**Checklist**:
- [ ] Helmfile executed successfully
- [ ] All pods in observability namespace running
- [ ] Prometheus server ready
- [ ] Grafana ready
- [ ] Jaeger query ready
- [ ] Loki ready

---

### Step 3.2: Import Grafana Dashboards (20 min)

```bash
# Port-forward to Grafana
kubectl port-forward -n observability svc/grafana 3000:80

# Open browser: http://localhost:3000
# Login: admin / <GRAFANA_ADMIN_PASSWORD from .env>

# Import dashboards from observability/grafana/provisioning/dashboards/json/
# 1. IntelliRAG Overview
# 2. Infrastructure
# 3. Ingestion Pipeline
# 4. Query Performance
# 5. LLM Metrics
```

**Checklist**:
- [ ] Grafana accessible
- [ ] 5 dashboards imported
- [ ] Prometheus datasource configured
- [ ] Metrics visible in dashboards

---

### Step 3.3: Validate Distributed Tracing (15 min)

```bash
# Port-forward to Jaeger
kubectl port-forward -n observability svc/jaeger-query 16686:80

# Open browser: http://localhost:16686

# Generate some traffic
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "test trace"}'

# In Jaeger UI:
# - Service: intellirag-api
# - Search for traces
# - Should see spans for: query_handler → embedding → qdrant → llm
```

**Checklist**:
- [ ] Jaeger UI accessible
- [ ] Traces visible
- [ ] Spans show CloudFlare Tunnel calls
- [ ] Latency breakdown visible

---

## 🎯 Final Verification (30 min)

### Comprehensive End-to-End Test

```bash
# 1. Upload a test document
curl -X POST http://localhost:8000/api/v1/ingest \
  -F "file=@tests/fixtures/sample.pdf" \
  -o /tmp/ingest-response.json

# Check response
cat /tmp/ingest-response.json
# Expected: {"job_id": "...", "status": "completed", "chunks_processed": 42}

# 2. Query the document
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Summarize the uploaded document"
  }' \
  -o /tmp/query-response.json

# Check response
cat /tmp/query-response.json
# Expected: {"answer": "...", "sources": [...], "latency": "180ms"}

# 3. Verify in Qdrant
kubectl exec -n app qdrant-0 -- curl -X GET \
  http://localhost:6333/collections/documents

# 4. Check Grafana dashboards
# - IntelliRAG Overview: Request rate, latency, error rate
# - LLM Metrics: TPS, GPU utilization (if exposed)
# - Query Performance: P50, P95, P99 latency

# 5. Check Jaeger trace
# - Find the query trace
# - Verify all spans: FastAPI → Embedding → Qdrant → LLM
```

**Final Checklist**:
- [ ] Document ingestion works end-to-end
- [ ] Query with RAG retrieval works
- [ ] Vectors stored in Qdrant
- [ ] CloudFlare Tunnel calls succeed
- [ ] Metrics visible in Grafana
- [ ] Traces visible in Jaeger
- [ ] Latency < 200ms (P95)
- [ ] No errors in logs

---

## 🎉 Success Criteria

Your IntelliRAG deployment is successful if:

✅ **Local GPU**:
- Minikube running with GPU access
- KServe deployed with 2 InferenceServices (vLLM, BGE-M3)
- CloudFlare Tunnel exposing endpoints securely

✅ **GKE Cloud**:
- FastAPI deployed with 2 replicas
- Qdrant running and storing vectors
- Observability stack operational (Prometheus, Grafana, Jaeger, Loki)

✅ **Connectivity**:
- GKE can reach local GPU via CloudFlare Tunnel
- End-to-end latency < 200ms (P95)
- No network errors or timeouts

✅ **Functionality**:
- Document ingestion works (PDF → chunks → embeddings → Qdrant)
- Query with RAG works (query → embedding → retrieve → generate)
- All metrics and traces visible in observability stack

---

## 📚 Next Steps

After successful deployment:

1. **Production Hardening** (Phase 4):
   - Setup NGINX Ingress Controller
   - Configure TLS certificates (Let's Encrypt)
   - Implement HPA autoscaling
   - Add network policies

2. **MLOps Integration** (Future):
   - Deploy MLFlow for model tracking
   - Setup model versioning workflow
   - Implement RAGAS evaluation

3. **CI/CD Pipeline** (Future):
   - Setup GitHub Actions
   - Automate image builds
   - Automated deployment to GKE

---

## 🔧 Troubleshooting Quick Reference

**Issue**: CloudFlare Tunnel not reachable from GKE
```bash
# Check tunnel status on local server
sudo systemctl status cloudflared
sudo journalctl -u cloudflared -f

# Test from GKE
kubectl run -n app -it --rm debug --image=curlimages/curl --restart=Never \
  -- curl -v https://gpu.intellirag.example.com/health
```

**Issue**: FastAPI pods crashing
```bash
# Check logs
kubectl logs -n app -l app=intellirag-api --tail=100

# Check ConfigMap
kubectl get configmap intellirag-config -n app -o yaml

# Verify Qdrant is reachable
kubectl exec -n app -it deployment/intellirag-api -- \
  curl http://qdrant.app.svc.cluster.local:6333
```

**Issue**: High latency (>500ms)
```bash
# Check Jaeger traces to identify bottleneck
kubectl port-forward -n observability svc/jaeger-query 16686:80

# Check Prometheus metrics
kubectl port-forward -n observability svc/prometheus-server 9090:80
# Query: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))
```

---

## 📋 Configuration Summary

**GKE Resources**:
- Cluster: intellirag-cluster (1-3 nodes, e2-standard-2)
- Namespaces: app, kserve, observability
- FastAPI: 2 replicas, 500m CPU, 1Gi RAM
- Qdrant: 1 replica, 1 CPU, 4Gi RAM

**Local GPU Resources**:
- Minikube: 8 CPUs, 32GB RAM, 100GB disk
- vLLM: 1 GPU, 8Gi RAM
- BGE-M3: 1 GPU, 4Gi RAM

**Network**:
- CloudFlare Tunnel: gpu.intellirag.example.com
- LLM Endpoint: https://gpu.intellirag.example.com/v1/chat/completions
- Embedding Endpoint: https://gpu.intellirag.example.com/v1/embeddings

**Cost**:
- GKE (1 node): ~$58/month
- GCS: ~$2/month
- Local GPU: ~$25/month (electricity)
- **Total**: ~$85/month ✅

---

**Document Version**: 1.0
**Last Updated**: 2025-11-16
**Maintainer**: IntelliRAG Team
**Status**: ✅ Production-Ready Checklist
