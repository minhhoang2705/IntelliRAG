# Local KServe Setup Guide with Minikube

**Last Updated**: November 5, 2025  
**Version**: 1.0.0  
**Target**: Local development with KServe model serving

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Part 1: Minikube Setup with GPU](#part-1-minikube-setup-with-gpu)
4. [Part 2: Install KServe Dependencies](#part-2-install-kserve-dependencies)
5. [Part 3: Install KServe](#part-3-install-kserve)
6. [Part 4: Deploy Models with KServe](#part-4-deploy-models-with-kserve)
7. [Part 5: Integrate with IntelliRAG](#part-5-integrate-with-intellirag)
8. [Part 6: Testing and Validation](#part-6-testing-and-validation)
9. [Troubleshooting](#troubleshooting)
10. [Monitoring and Debugging](#monitoring-and-debugging)

---

## Overview

This guide will help you set up a local Kubernetes cluster using **Minikube** with **KServe** for serving your LLM and embedding models. By the end, you'll have:

- ✅ Minikube cluster with GPU support
- ✅ KServe with all dependencies (Knative, Istio)
- ✅ Two InferenceServices:
  - `vllm-qwen` - LLM inference (Qwen/Qwen3-0.6B)
  - `embedding-bge-m3` - Embedding generation (BAAI/bge-m3)
- ✅ IntelliRAG integrated with KServe endpoints

**Architecture**:
```
┌─────────────────────────────────────────────────────────┐
│                   Minikube Cluster                      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │   FastAPI    │──│   KServe     │──│  vLLM Pod    │   │
│  │ (IntelliRAG) │  │  Controller  │  │  (Qwen3)     │   │
│  └──────────────┘  └──────────────┘  │  + GPU       │   │ 
│         │                            └──────────────┘   │
│         │          ┌──────────────┐                     │
│         └──────────│  Embedding   │                     │
│                    │  Service Pod │                     │
│                    │  + GPU       │                     │
│                    └──────────────┘                     │
│                                                         │
│  Knative Serving + Istio (Networking & Autoscaling)     │
└─────────────────────────────────────────────────────────┘
```

---

## Prerequisites

### System Requirements

- **OS**: Ubuntu 20.04+ / Linux with NVIDIA GPU
- **GPU**: NVIDIA GPU (you have RTX 4070Ti 12GB - perfect!)
- **RAM**: 16GB minimum (32GB recommended)
- **Disk**: 50GB free space
- **CPU**: 4 cores minimum

### Software Prerequisites

1. **Docker** (installed)
2. **NVIDIA Docker Runtime** (for GPU support)
3. **kubectl** (Kubernetes CLI)
4. **minikube** (to be installed)
5. **helm** (for package management)

### Verify Prerequisites

```bash
# Check Docker
docker --version
# Expected: Docker version 20.10+

# Check NVIDIA drivers
nvidia-smi
# Should show your RTX 4070Ti

# Check NVIDIA Docker runtime
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
# Should show GPU info inside container

# Check kubectl
kubectl version --client
# If not installed, we'll install it

# Check helm
helm version
# If not installed, we'll install it
```

---

## Part 1: Minikube Setup with GPU

### Step 1.1: Install kubectl

```bash
# Download kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

# Make executable
chmod +x kubectl

# Move to PATH
sudo mv kubectl /usr/local/bin/

# Verify
kubectl version --client
```

### Step 1.2: Install Minikube

```bash
# Download minikube
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

# Install
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Verify
minikube version
```

### Step 1.3: Start Minikube with GPU Support

**Important**: Minikube needs to use the Docker driver with GPU passthrough.

```bash
# Start minikube with GPU support
minikube start \
  --driver=docker \
  --container-runtime=docker \
  --gpus=all \
  --memory=12288 \
  --cpus=4 \
  --disk-size=50g \
  --kubernetes-version=v1.28.0

# This will take 5-10 minutes on first run
```

**Expected output**:
```
😄  minikube v1.32.0 on Ubuntu 22.04
✨  Using the docker driver based on user configuration
👍  Starting control plane node minikube in cluster minikube
🚜  Pulling base image ...
🔥  Creating docker container (CPUs=4, Memory=12288MB) ...
🐳  Preparing Kubernetes v1.28.0 on Docker 24.0.7 ...
🔗  Configuring bridge CNI (Container Networking Interface) ...
🔎  Verifying Kubernetes components...
🌟  Enabled addons: storage-provisioner, default-storageclass
🏄  Done! kubectl is now configured to use "minikube" cluster
```

### Step 1.4: Verify Cluster

```bash
# Check cluster status
minikube status

# Check nodes
kubectl get nodes

# Expected:
# NAME       STATUS   ROLES           AGE   VERSION
# minikube   Ready    control-plane   2m    v1.28.0

# Check kubectl context
kubectl config current-context
# Should show: minikube
```

### Step 1.5: Install NVIDIA Device Plugin

This enables Kubernetes to schedule GPU workloads.

```bash
# Install NVIDIA device plugin
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml

# Wait for daemonset to be ready
kubectl rollout status daemonset nvidia-device-plugin-daemonset -n kube-system

# Verify GPU is available to Kubernetes
kubectl get nodes -o jsonpath='{.items[*].status.allocatable}' | jq .
```

**Expected output should include**:
```json
{
  "nvidia.com/gpu": "1"
}
```

### Step 1.6: Test GPU Access

```bash
# Create a test pod with GPU
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  restartPolicy: Never
  containers:
  - name: cuda-test
    image: nvidia/cuda:11.8.0-base-ubuntu22.04
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
EOF

# Wait for pod to complete
kubectl wait --for=condition=completed pod/gpu-test --timeout=60s

# Check logs - should show your GPU info
kubectl logs gpu-test

# Clean up
kubectl delete pod gpu-test
```

✅ **Checkpoint**: If you see your RTX 4070Ti info in the logs, GPU support is working!

---

## Part 2: Install KServe Dependencies

KServe requires:
1. **cert-manager** (SSL certificate management)
2. **Knative Serving** (serverless platform)
3. **Istio** (service mesh for networking)

### Step 2.1: Install cert-manager

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.2/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager -n cert-manager
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-webhook -n cert-manager
kubectl wait --for=condition=available --timeout=300s deployment/cert-manager-cainjector -n cert-manager

# Verify
kubectl get pods -n cert-manager
```

**Expected**:
```
NAME                                      READY   STATUS    RESTARTS   AGE
cert-manager-xxxxx-xxxxx                  1/1     Running   0          1m
cert-manager-cainjector-xxxxx-xxxxx       1/1     Running   0          1m
cert-manager-webhook-xxxxx-xxxxx          1/1     Running   0          1m
```

### Step 2.2: Install Istio

```bash
# Download Istio
curl -L https://istio.io/downloadIstio | ISTIO_VERSION=1.20.0 sh -

# Move to PATH
cd istio-1.20.0
export PATH=$PWD/bin:$PATH

# Install Istio with minimal profile (good for local dev)
istioctl install --set profile=default -y

# Enable Istio sidecar injection in default namespace
kubectl label namespace default istio-injection=enabled

# Verify
kubectl get pods -n istio-system
```

**Expected**:
```
NAME                                    READY   STATUS    RESTARTS   AGE
istiod-xxxxx-xxxxx                      1/1     Running   0          2m
istio-ingressgateway-xxxxx-xxxxx        1/1     Running   0          2m
```

### Step 2.3: Install Knative Serving

```bash
# Install Knative Serving CRDs
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-crds.yaml

# Install Knative Serving core
kubectl apply -f https://github.com/knative/serving/releases/download/knative-v1.12.0/serving-core.yaml

# Wait for Knative to be ready
kubectl wait --for=condition=available --timeout=300s deployment/controller -n knative-serving
kubectl wait --for=condition=available --timeout=300s deployment/webhook -n knative-serving

# Install Knative Istio controller
kubectl apply -f https://github.com/knative/net-istio/releases/download/knative-v1.12.0/net-istio.yaml

# Configure Knative to use Istio
kubectl patch configmap/config-features \
  -n knative-serving \
  --type merge \
  -p '{"data":{"kubernetes.podspec-affinity":"enabled", "kubernetes.podspec-nodeselector":"enabled", "kubernetes.podspec-tolerations":"enabled"}}'

# Verify
kubectl get pods -n knative-serving
```

**Expected**:
```
NAME                                     READY   STATUS    RESTARTS   AGE
activator-xxxxx-xxxxx                    1/1     Running   0          2m
autoscaler-xxxxx-xxxxx                   1/1     Running   0          2m
controller-xxxxx-xxxxx                   1/1     Running   0          2m
webhook-xxxxx-xxxxx                      1/1     Running   0          2m
net-istio-controller-xxxxx-xxxxx         1/1     Running   0          2m
net-istio-webhook-xxxxx-xxxxx            1/1     Running   0          2m
```

✅ **Checkpoint**: All three components (cert-manager, Istio, Knative) should be running!

---

## Part 3: Install KServe

### Step 3.1: Install KServe CRDs and Runtime

```bash
# Install KServe CRDs
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.12.0/kserve.yaml

# Install KServe built-in ClusterServingRuntimes
kubectl apply -f https://github.com/kserve/kserve/releases/download/v0.12.0/kserve-cluster-resources.yaml

# Wait for KServe to be ready
kubectl wait --for=condition=available --timeout=300s deployment/kserve-controller-manager -n kserve
kubectl wait --for=condition=available --timeout=300s deployment/kserve-webhook-server-deployment -n kserve

# Verify
kubectl get pods -n kserve
```

**Expected**:
```
NAME                                         READY   STATUS    RESTARTS   AGE
kserve-controller-manager-xxxxx-xxxxx        2/2     Running   0          2m
kserve-webhook-server-deployment-xx-xx       1/1     Running   0          2m
```

### Step 3.2: Configure KServe for Local Development

```bash
# Configure ingress gateway for local access
kubectl patch configmap/config-domain \
  -n knative-serving \
  --type merge \
  -p '{"data":{"example.com":""}}'

# Disable Istio mTLS (simplifies local dev)
kubectl apply -f - <<EOF
apiVersion: security.istio.io/v1beta1
kind: PeerAuthentication
metadata:
  name: default
  namespace: istio-system
spec:
  mtls:
    mode: PERMISSIVE
EOF

# Configure KServe to use raw deployment (not serverless) for GPU workloads
kubectl patch configmap/inferenceservice-config \
  -n kserve \
  --type merge \
  -p '{"data":{"deploy":"{\"defaultDeploymentMode\":\"RawDeployment\"}"}}'
```

### Step 3.3: Verify KServe Installation

```bash
# Check all KServe components
kubectl get crd | grep kserve

# Expected output should include:
# inferenceservices.serving.kserve.io
# trainedmodels.serving.kserve.io
# clusterservingruntimes.serving.kserve.io
# servingruntimes.serving.kserve.io

# Check available serving runtimes
kubectl get clusterservingruntimes
```

✅ **Checkpoint**: KServe is installed and ready!

---

## Part 4: Deploy Models with KServe

Now we'll create InferenceServices for your two models.

### Step 4.1: Create Namespace

```bash
# Create namespace for IntelliRAG
kubectl create namespace intellirag

# Label for Istio injection
kubectl label namespace intellirag istio-injection=enabled

# Verify
kubectl get namespace intellirag --show-labels
```

### Step 4.2: Deploy vLLM InferenceService (LLM)

Create the InferenceService manifest for Qwen3-0.6B:

```bash
cat > /tmp/vllm-qwen-inference.yaml <<'EOF'
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-qwen
  namespace: intellirag
spec:
  predictor:
    minReplicas: 1
    maxReplicas: 1
    containers:
    - name: kserve-container
      image: vllm/vllm-openai:latest
      command:
        - python3
        - -m
        - vllm.entrypoints.openai.api_server
        - --model
        - Qwen/Qwen3-0.6B
        - --gpu-memory-utilization
        - "0.5"
        - --max-model-len
        - "2048"
        - --dtype
        - bfloat16
        - --enable-prefix-caching
        - --port
        - "8080"
      env:
        - name: HF_HOME
          value: /root/.cache/huggingface
      ports:
        - containerPort: 8080
          protocol: TCP
      resources:
        limits:
          cpu: "4"
          memory: 8Gi
          nvidia.com/gpu: "1"
        requests:
          cpu: "2"
          memory: 4Gi
          nvidia.com/gpu: "1"
      volumeMounts:
        - name: huggingface-cache
          mountPath: /root/.cache/huggingface
    volumes:
      - name: huggingface-cache
        hostPath:
          path: /home/minh-ubs-k8s/.cache/huggingface
          type: DirectoryOrCreate
EOF

# Apply the InferenceService
kubectl apply -f /tmp/vllm-qwen-inference.yaml

# Monitor deployment (this will take 5-10 minutes on first run due to model download)
kubectl get inferenceservice -n intellirag -w
```

**Expected progression**:
```
NAME         URL   READY   PREV   LATEST   AGE
vllm-qwen          False                    10s
vllm-qwen          False                    30s
vllm-qwen          True                     5m
```

Press `Ctrl+C` to stop watching once READY becomes True.

```bash
# Check the pods
kubectl get pods -n intellirag

# Check logs (useful for debugging)
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen -f
```

### Step 4.3: Deploy Embedding InferenceService

Create the InferenceService for BGE-M3 embeddings:

```bash
cat > /tmp/embedding-bge-m3-inference.yaml <<'EOF'
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: embedding-bge-m3
  namespace: intellirag
spec:
  predictor:
    minReplicas: 1
    maxReplicas: 1
    containers:
    - name: kserve-container
      image: intellirag-embedding:latest
      imagePullPolicy: Never  # Use local image
      env:
        - name: EMBEDDING_MODEL
          value: BAAI/bge-m3
        - name: DEVICE
          value: cuda
        - name: MAX_BATCH_SIZE
          value: "128"
      ports:
        - containerPort: 8001
          protocol: TCP
      resources:
        limits:
          cpu: "2"
          memory: 4Gi
          nvidia.com/gpu: "1"
        requests:
          cpu: "1"
          memory: 2Gi
          nvidia.com/gpu: "1"
      volumeMounts:
        - name: huggingface-cache
          mountPath: /root/.cache/huggingface
    volumes:
      - name: huggingface-cache
        hostPath:
          path: /home/minh-ubs-k8s/.cache/huggingface
          type: DirectoryOrCreate
EOF

# First, build and load the embedding service image into minikube
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG
minikube image load intellirag-embedding:latest

# Apply the InferenceService
kubectl apply -f /tmp/embedding-bge-m3-inference.yaml

# Monitor
kubectl get inferenceservice -n intellirag
```

### Step 4.4: Get Service Endpoints

```bash
# Get all InferenceServices
kubectl get inferenceservice -n intellirag

# Get the service URLs
kubectl get ksvc -n intellirag

# For local access, get the cluster IP
kubectl get svc -n intellirag
```

**Note**: In RawDeployment mode, you'll access services via ClusterIP. We'll set up port forwarding in the next section.

---

## Part 5: Integrate with IntelliRAG

### Step 5.1: Set Up Port Forwarding

To access KServe services from your local machine:

```bash
# Port forward vLLM service (LLM)
kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080 &

# Port forward embedding service
kubectl port-forward -n intellirag svc/embedding-bge-m3-predictor 8001:8001 &

# Verify connections
curl http://localhost:8000/health
curl http://localhost:8001/health
```

### Step 5.2: Update IntelliRAG Configuration

You'll need to update your application configuration to point to KServe endpoints:

**Option A: Environment Variables**

```bash
# Create .env.kserve file
cat > .env.kserve <<'EOF'
# KServe Model Endpoints
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen3-0.6B

EMBEDDING_SERVICE_URL=http://localhost:8001
EMBEDDING_USE_REMOTE=true

# Qdrant (still local)
QDRANT_URL=http://localhost:6333

# GCS (for production)
GCP_PROJECT_ID=intellirag-project
GCS_BUCKET_NAME=intellirag-raw-documents
EOF

# Use this when running IntelliRAG
source .env.kserve
uvicorn app.main:app --reload
```

**Option B: Update docker-compose.yml**

If you want to mix KServe with docker-compose for other services:

```yaml
# Update docker-compose.yml
services:
  # Keep Qdrant
  qdrant:
    # ... existing config ...
  
  # Remove qwen3-llm and embedding-service
  # They're now served by KServe
  
  # Add IntelliRAG FastAPI app
  intellirag-api:
    build: .
    ports:
      - "8080:8000"
    environment:
      - VLLM_BASE_URL=http://host.docker.internal:8000/v1
      - EMBEDDING_SERVICE_URL=http://host.docker.internal:8001
      - QDRANT_URL=http://qdrant:6333
    depends_on:
      - qdrant
    network_mode: bridge
    extra_hosts:
      - "host.docker.internal:host-gateway"
```

### Step 5.3: Verify Integration

Create a test script to verify everything works:

```bash
cat > /tmp/test_kserve_integration.py <<'EOF'
#!/usr/bin/env python3
"""Test KServe integration with IntelliRAG."""
import asyncio
import httpx

async def test_vllm():
    """Test vLLM inference."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8000/v1/completions",
            json={
                "model": "Qwen/Qwen3-0.6B",
                "prompt": "Hello, how are you?",
                "max_tokens": 50
            }
        )
        print("✅ vLLM Response:", response.json())

async def test_embedding():
    """Test embedding service."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(
            "http://localhost:8001/vectorize",
            json={
                "texts": ["Hello world", "Test embedding"],
                "normalize": False
            }
        )
        print("✅ Embedding Response:", response.json())

async def main():
    print("Testing KServe Integration...")
    await test_vllm()
    await test_embedding()
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    asyncio.run(main())
EOF

# Run test
python3 /tmp/test_kserve_integration.py
```

---

## Part 6: Testing and Validation

### Step 6.1: Test InferenceServices Directly

```bash
# Test vLLM health
curl http://localhost:8000/health

# Test vLLM inference
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "prompt": "What is machine learning?",
    "max_tokens": 100,
    "temperature": 0.7
  }'

# Test embedding service
curl -X POST http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Machine learning is a subset of AI"],
    "normalize": false
  }'
```

### Step 6.2: Test Full IntelliRAG Pipeline

```bash
# Start IntelliRAG with KServe endpoints
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG
export VLLM_BASE_URL=http://localhost:8000/v1
export EMBEDDING_SERVICE_URL=http://localhost:8001
export EMBEDDING_USE_REMOTE=true

uvicorn app.main:app --reload --port 8080

# In another terminal, test the query endpoint
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What is IntelliRAG?",
    "collection_name": "default"
  }'
```

### Step 6.3: Run Integration Tests

```bash
# Update test configuration
export VLLM_BASE_URL=http://localhost:8000/v1
export EMBEDDING_SERVICE_URL=http://localhost:8001

# Run integration tests
pytest tests/integration/ -v
```

---

## Troubleshooting

### Issue 1: GPU Not Detected

**Symptom**: Pods stuck in Pending state with "insufficient nvidia.com/gpu"

**Solution**:
```bash
# Check GPU allocatable
kubectl describe node minikube | grep -A5 Allocatable

# If GPU not showing, restart NVIDIA device plugin
kubectl delete daemonset nvidia-device-plugin-daemonset -n kube-system
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml

# Verify
kubectl get nodes -o yaml | grep nvidia.com/gpu
```

### Issue 2: InferenceService Stuck in Not Ready

**Symptom**: InferenceService shows READY=False for >10 minutes

**Solution**:
```bash
# Check pod status
kubectl get pods -n intellirag

# Check pod logs
kubectl logs -n intellirag <pod-name>

# Check events
kubectl describe inferenceservice <name> -n intellirag

# Common causes:
# 1. Image pull issues (check imagePullPolicy)
# 2. Resource constraints (reduce memory/CPU requests)
# 3. Model download timeout (check HuggingFace access)
```

### Issue 3: Port Forwarding Dies

**Symptom**: Port forward connection drops

**Solution**:
```bash
# Create persistent port forwards with systemd or screen
screen -dmS vllm-forward kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080
screen -dmS embed-forward kubectl port-forward -n intellirag svc/embedding-bge-m3-predictor 8001:8001

# Or use kubectl proxy
kubectl proxy --port=8001 &
# Then access via: http://localhost:8001/api/v1/namespaces/intellirag/services/vllm-qwen-predictor:8080/proxy/
```

### Issue 4: Out of Memory

**Symptom**: Pods killed with OOMKilled status

**Solution**:
```bash
# Increase minikube memory
minikube stop
minikube start --memory=16384 --cpus=6

# Or reduce model resource requests in InferenceService manifests
```

### Issue 5: Model Download Timeout

**Symptom**: Pod logs show "Connection timeout" when downloading models

**Solution**:
```bash
# Pre-download models to your cache
python3 -c "
from transformers import AutoTokenizer, AutoModel
AutoTokenizer.from_pretrained('Qwen/Qwen3-0.6B')
AutoModel.from_pretrained('BAAI/bge-m3')
"

# Verify cache exists
ls -lh ~/.cache/huggingface/hub/

# Ensure volume mount is correct in InferenceService
```

---

## Monitoring and Debugging

### Monitor KServe Resources

```bash
# Watch InferenceServices
kubectl get inferenceservice -n intellirag -w

# Watch pods
kubectl get pods -n intellirag -w

# Watch events
kubectl get events -n intellirag --sort-by='.lastTimestamp'
```

### View Logs

```bash
# vLLM logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen -f

# Embedding service logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=embedding-bge-m3 -f

# KServe controller logs
kubectl logs -n kserve -l control-plane=kserve-controller-manager -f
```

### Check Resource Usage

```bash
# Node resource usage
kubectl top node

# Pod resource usage
kubectl top pods -n intellirag

# GPU usage (from within pod)
kubectl exec -n intellirag <pod-name> -- nvidia-smi
```

### Useful kubectl Commands

```bash
# Get all KServe resources
kubectl get inferenceservice,revision,configuration,route -n intellirag

# Describe InferenceService
kubectl describe inferenceservice vllm-qwen -n intellirag

# Get service endpoints
kubectl get ksvc -n intellirag

# Port forward to pod directly
kubectl port-forward -n intellirag <pod-name> 8000:8080
```

---

## Performance Tuning

### Optimize vLLM Settings

Edit the InferenceService to tune vLLM parameters:

```yaml
command:
  - --gpu-memory-utilization
  - "0.95"  # Use 95% of GPU memory (adjust based on your needs)
  - --max-model-len
  - "4096"  # Increase max sequence length
  - --swap-space
  - "8"     # GB of CPU memory for swapping
  - --enable-prefix-caching
  - --tensor-parallel-size
  - "1"     # Multi-GPU support (if you have multiple GPUs)
```

### Enable Autoscaling

For production-like behavior with scale-to-zero:

```yaml
spec:
  predictor:
    minReplicas: 0  # Scale to zero when idle
    maxReplicas: 2
    scaleTarget: 10  # Target 10 concurrent requests per replica
    scaleMetric: concurrency
```

---

## Managing Your Local Cluster

### Start/Stop Cluster

```bash
# Stop cluster (preserves state)
minikube stop

# Start cluster
minikube start

# Restart port forwards after cluster start
kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080 &
kubectl port-forward -n intellirag svc/embedding-bge-m3-predictor 8001:8001 &
```

### Clean Up

```bash
# Delete InferenceServices
kubectl delete inferenceservice --all -n intellirag

# Delete namespace
kubectl delete namespace intellirag

# Stop minikube
minikube stop

# Delete cluster (removes all data)
minikube delete
```

### Update InferenceServices

```bash
# Edit existing InferenceService
kubectl edit inferenceservice vllm-qwen -n intellirag

# Or apply updated manifest
kubectl apply -f vllm-qwen-inference.yaml

# Rollout will happen automatically
kubectl get pods -n intellirag -w
```

---

## Next Steps

Now that you have KServe running locally:

1. **Test thoroughly**: Run your integration tests with KServe endpoints
2. **Benchmark**: Compare performance vs Docker Compose setup
3. **Monitor**: Set up Prometheus/Grafana for KServe metrics
4. **Document findings**: Note any issues or optimizations
5. **Plan cloud migration**: Your local KServe setup closely mirrors GKE deployment

### Differences from GKE Deployment

| Aspect | Local (Minikube) | GKE Production |
|--------|------------------|----------------|
| **Autoscaling** | Manual minReplicas/maxReplicas | HPA with cluster autoscaler |
| **GPU** | Single RTX 4070Ti | T4 GPUs in node pools |
| **Networking** | Port forwarding | Ingress with SSL/TLS |
| **Storage** | HostPath volumes | Persistent Disks |
| **Monitoring** | kubectl logs | Prometheus + Grafana + Loki |
| **Cost** | $0 | ~$300/month |

---

## Useful Resources

- [KServe Documentation](https://kserve.github.io/website/)
- [vLLM Documentation](https://docs.vllm.ai/)
- [Knative Documentation](https://knative.dev/docs/)
- [Minikube GPU Support](https://minikube.sigs.k8s.io/docs/tutorials/nvidia/)
- [Troubleshooting KServe](https://kserve.github.io/website/latest/admin/debug/)

---

## Summary Checklist

After completing this guide, you should have:

- ✅ Minikube cluster running with GPU support
- ✅ cert-manager, Istio, and Knative Serving installed
- ✅ KServe installed and configured
- ✅ vLLM InferenceService serving Qwen3-0.6B
- ✅ Embedding InferenceService serving BGE-M3
- ✅ IntelliRAG integrated with KServe endpoints
- ✅ Port forwarding set up for local access
- ✅ Tests passing with KServe backend

**Total Setup Time**: 1-2 hours (plus model download time)

---

**Questions or Issues?**

If you encounter problems:
1. Check the Troubleshooting section
2. Review pod logs: `kubectl logs -n intellirag <pod-name>`
3. Check KServe controller logs: `kubectl logs -n kserve -l control-plane=kserve-controller-manager`
4. Verify GPU access: `kubectl exec -n intellirag <pod-name> -- nvidia-smi`

Good luck with your KServe setup! 🚀

