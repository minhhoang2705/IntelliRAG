# KServe InferenceService Manifests

This directory contains Kubernetes manifests for deploying IntelliRAG models with KServe.

## Files

- `vllm-qwen-inference.yaml` - LLM inference service (Qwen/Qwen3-0.6B via vLLM)
- `embedding-bge-m3-inference.yaml` - Embedding service (BAAI/bge-m3)
- `namespace.yaml` - Namespace and basic setup

## Prerequisites

Before applying these manifests, ensure you have:

1. ✅ Minikube running with GPU support
2. ✅ KServe and dependencies installed (Knative, Istio, cert-manager)
3. ✅ NVIDIA device plugin running
4. ✅ Namespace created and labeled

See [local-kserve-setup-guide.md](../../docs/deployment/local-kserve-setup-guide.md) for full setup instructions.

## Quick Start

### 1. Create Namespace

```bash
kubectl create namespace intellirag
kubectl label namespace intellirag istio-injection=enabled
```

### 2. Deploy vLLM Service

```bash
kubectl apply -f vllm-qwen-inference.yaml

# Wait for ready
kubectl wait --for=condition=Ready inferenceservice/vllm-qwen -n intellirag --timeout=10m

# Check status
kubectl get inferenceservice vllm-qwen -n intellirag
```

### 3. Deploy Embedding Service

First, build and load the embedding service image:

```bash
# Build image
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG
docker build -t intellirag-embedding:latest deploy/embedding-service/

# Load into minikube
minikube image load intellirag-embedding:latest

# Deploy
kubectl apply -f embedding-bge-m3-inference.yaml

# Wait for ready
kubectl wait --for=condition=Ready inferenceservice/embedding-bge-m3 -n intellirag --timeout=10m
```

### 4. Access Services

```bash
# Port forward vLLM
kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080 &

# Port forward embedding
kubectl port-forward -n intellirag svc/embedding-bge-m3-predictor 8001:8001 &

# Test vLLM
curl http://localhost:8000/health

# Test embedding
curl http://localhost:8001/health
```

## Configuration

### Adjust GPU Memory

Edit `vllm-qwen-inference.yaml`:

```yaml
command:
  - --gpu-memory-utilization
  - "0.5"  # Change to 0.95 for maximum GPU usage
```

### Change Models

Edit the `--model` parameter in `vllm-qwen-inference.yaml`:

```yaml
command:
  - --model
  - Qwen/Qwen3-0.6B # Larger model
```

Or edit `EMBEDDING_MODEL` in `embedding-bge-m3-inference.yaml`:

```yaml
env:
  - name: EMBEDDING_MODEL
    value: sentence-transformers/all-MiniLM-L6-v2  # Smaller, faster model
```

### Enable Autoscaling

Add autoscaling configuration:

```yaml
spec:
  predictor:
    minReplicas: 0  # Scale to zero when idle
    maxReplicas: 2
    scaleTarget: 10
    scaleMetric: concurrency
```

## Troubleshooting

### InferenceService Not Ready

```bash
# Check pod status
kubectl get pods -n intellirag

# Check logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen

# Check events
kubectl describe inferenceservice vllm-qwen -n intellirag
```

### GPU Not Available

```bash
# Check GPU allocation
kubectl describe node minikube | grep nvidia.com/gpu

# Restart NVIDIA device plugin if needed
kubectl delete daemonset nvidia-device-plugin-daemonset -n kube-system
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml
```

### Out of Memory

```bash
# Reduce resource requests
# Edit InferenceService and lower memory limits

# Or increase minikube memory
minikube stop
minikube start --memory=16384
```

## Monitoring

### Check Resource Usage

```bash
# Node resources
kubectl top node

# Pod resources
kubectl top pods -n intellirag

# GPU usage (from pod)
kubectl exec -n intellirag <pod-name> -- nvidia-smi
```

### View Logs

```bash
# vLLM logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen -f

# Embedding logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=embedding-bge-m3 -f
```

## Integration with IntelliRAG

Update your IntelliRAG configuration to use KServe endpoints:

```bash
# Set environment variables
export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_MODEL=Qwen/Qwen3-0.6B
export EMBEDDING_SERVICE_URL=http://localhost:8001
export EMBEDDING_USE_REMOTE=true

# Run IntelliRAG
uvicorn app.main:app --reload
```

Or create `.env.kserve`:

```bash
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen3-0.6B
EMBEDDING_SERVICE_URL=http://localhost:8001
EMBEDDING_USE_REMOTE=true
QDRANT_URL=http://localhost:6333
```

## Cleanup

```bash
# Delete InferenceServices
kubectl delete -f .

# Or delete entire namespace
kubectl delete namespace intellirag
```

## Next Steps

- Set up monitoring with Prometheus
- Configure proper ingress for production
- Test autoscaling behavior
- Benchmark performance vs Docker Compose
- Prepare for GKE deployment

## References

- [Full Setup Guide](../../docs/deployment/local-kserve-setup-guide.md)
- [KServe Documentation](https://kserve.github.io/website/)
- [vLLM Documentation](https://docs.vllm.ai/)

