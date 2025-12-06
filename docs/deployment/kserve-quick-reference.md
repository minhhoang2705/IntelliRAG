# KServe Quick Reference

**Quick commands for working with KServe locally**

---

## Setup

```bash
# One-time setup (runs all installation steps)
./scripts/setup-kserve-local.sh

# Or follow the detailed guide
docs/deployment/local-kserve-setup-guide.md
```

---

## Deploy Models

```bash
# 1. Build embedding service image
docker build -t intellirag-embedding:latest deploy/embedding-service/
minikube image load intellirag-embedding:latest

# 2. Deploy both models
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml
kubectl apply -f kubernetes/kserve/embedding-bge-m3-inference.yaml

# 3. Wait for ready (takes 5-10 minutes first time)
kubectl get inferenceservice -n intellirag -w
```

---

## Access Services

```bash
# Port forward (run in background)
kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080 &
kubectl port-forward -n intellirag svc/embedding-bge-m3-predictor 8001:8001 &

# Test endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health
```

---

## Common Commands

### Check Status

```bash
# InferenceServices status
kubectl get inferenceservice -n intellirag

# Pods status
kubectl get pods -n intellirag

# Full details
kubectl describe inferenceservice vllm-qwen -n intellirag
```

### View Logs

```bash
# vLLM logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen -f

# Embedding service logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=embedding-bge-m3 -f

# All logs in namespace
kubectl logs -n intellirag --all-containers=true -f
```

### Monitor Resources

```bash
# Node resources
kubectl top node

# Pod resources
kubectl top pods -n intellirag

# GPU usage (inside pod)
kubectl exec -n intellirag <pod-name> -- nvidia-smi
```

### Update Models

```bash
# Edit InferenceService
kubectl edit inferenceservice vllm-qwen -n intellirag

# Or apply updated manifest
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml

# Watch rollout
kubectl get pods -n intellirag -w
```

### Restart Services

```bash
# Delete pod (will auto-recreate)
kubectl delete pod -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen

# Or delete and recreate InferenceService
kubectl delete inferenceservice vllm-qwen -n intellirag
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml
```

### Clean Up

```bash
# Delete InferenceServices
kubectl delete inferenceservice --all -n intellirag

# Delete namespace
kubectl delete namespace intellirag

# Stop port forwards
pkill -f "port-forward.*intellirag"

# Stop minikube
minikube stop

# Delete cluster (removes all data)
minikube delete
```

---

## Cluster Management

### Start/Stop

```bash
# Stop cluster (preserves state)
minikube stop

# Start cluster
minikube start

# Check status
minikube status

# SSH into node
minikube ssh
```

### GPU Management

```bash
# Check GPU availability
kubectl get nodes -o jsonpath='{.items[*].status.allocatable.nvidia\.com/gpu}'

# Restart NVIDIA plugin
kubectl delete daemonset nvidia-device-plugin-daemonset -n kube-system
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml

# View GPU from pod
kubectl exec -n intellirag <pod-name> -- nvidia-smi
```

---

## Troubleshooting

### InferenceService Stuck

```bash
# Check pod events
kubectl get events -n intellirag --sort-by='.lastTimestamp'

# Check pod status
kubectl describe pod <pod-name> -n intellirag

# Check KServe controller logs
kubectl logs -n kserve -l control-plane=kserve-controller-manager -f
```

### Port Forward Issues

```bash
# Kill existing port forwards
pkill -f "port-forward.*8000"
pkill -f "port-forward.*8001"

# Restart with verbose logging
kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080 -v=9
```

### Out of Memory

```bash
# Increase minikube resources
minikube stop
minikube start --memory=16384 --cpus=6

# Or reduce InferenceService resource requests
kubectl edit inferenceservice vllm-qwen -n intellirag
```

### Model Download Timeout

```bash
# Pre-download models
python3 -c "
from transformers import AutoTokenizer, AutoModel
AutoTokenizer.from_pretrained('Qwen/Qwen3-0.6B')
AutoModel.from_pretrained('BAAI/bge-m3')
"

# Check cache
ls -lh ~/.cache/huggingface/hub/
```

---

## Testing

### Test vLLM Directly

```bash
# Health check
curl http://localhost:8000/health

# Generate text
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "prompt": "What is machine learning?",
    "max_tokens": 100
  }'
```

### Test Embedding Service

```bash
# Health check
curl http://localhost:8001/health

# Model info
curl http://localhost:8001/model-info

# Generate embeddings
curl -X POST http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello world"],
    "normalize": false
  }'
```

### Test IntelliRAG Integration

```bash
# Set environment
export VLLM_BASE_URL=http://localhost:8000/v1
export EMBEDDING_SERVICE_URL=http://localhost:8001
export EMBEDDING_USE_REMOTE=true

# Run IntelliRAG
uvicorn app.main:app --reload

# Test query endpoint
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is IntelliRAG?", "collection_name": "default"}'
```

---

## Configuration Files

- **InferenceService Manifests**: `kubernetes/kserve/`
- **Setup Script**: `scripts/setup-kserve-local.sh`
- **Detailed Guide**: `docs/deployment/local-kserve-setup-guide.md`
- **Docker Compose** (alternative): `docker-compose.yml`

---

## Environment Variables for IntelliRAG

```bash
# KServe endpoints
export VLLM_BASE_URL=http://localhost:8000/v1
export VLLM_MODEL=Qwen/Qwen3-0.6B
export EMBEDDING_SERVICE_URL=http://localhost:8001
export EMBEDDING_USE_REMOTE=true

# Other services
export QDRANT_URL=http://localhost:6333
export GCP_PROJECT_ID=intellirag-project
export GCS_BUCKET_NAME=intellirag-raw-documents
```

Or use `.env.kserve` file:

```bash
# Create config
cat > .env.kserve <<EOF
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen3-0.6B
EMBEDDING_SERVICE_URL=http://localhost:8001
EMBEDDING_USE_REMOTE=true
QDRANT_URL=http://localhost:6333
EOF

# Use it
source .env.kserve
uvicorn app.main:app --reload
```

---

## Useful kubectl Shortcuts

```bash
# Create aliases
alias k='kubectl'
alias kgi='kubectl get inferenceservice -n intellirag'
alias kgp='kubectl get pods -n intellirag'
alias kl='kubectl logs -n intellirag'
alias kd='kubectl describe -n intellirag'

# Use them
kgi              # Get InferenceServices
kgp              # Get pods
kl <pod-name>    # View logs
kd pod <name>    # Describe pod
```

---

## Performance Tuning

### Increase GPU Utilization

```yaml
# In vllm-qwen-inference.yaml
command:
  - --gpu-memory-utilization
  - "0.95"  # Use 95% of GPU memory
```

### Increase Context Length

```yaml
# In vllm-qwen-inference.yaml
command:
  - --max-model-len
  - "4096"  # Increase from 2048
```

### Enable Multi-GPU (if you have multiple GPUs)

```yaml
# In vllm-qwen-inference.yaml
command:
  - --tensor-parallel-size
  - "2"  # Use 2 GPUs
resources:
  limits:
    nvidia.com/gpu: "2"  # Request 2 GPUs
```

---

## Next Steps

1. ✅ Complete setup: `./scripts/setup-kserve-local.sh`
2. ✅ Deploy models: `kubectl apply -f kubernetes/kserve/`
3. ✅ Set up port forwarding
4. ✅ Test endpoints
5. ✅ Integrate with IntelliRAG
6. 📊 Monitor performance
7. 🚀 Prepare for GKE deployment

---

**Need Help?**
- Full guide: `docs/deployment/local-kserve-setup-guide.md`
- KServe docs: https://kserve.github.io/website/
- vLLM docs: https://docs.vllm.ai/

