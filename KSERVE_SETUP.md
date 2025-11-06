# KServe Local Setup - Getting Started

This document provides a quick overview of setting up KServe locally for IntelliRAG model serving.

## 📚 Documentation Overview

| Document | Purpose | When to Use |
|----------|---------|-------------|
| **[Local KServe Setup Guide](docs/deployment/local-kserve-setup-guide.md)** | Complete step-by-step setup | First-time setup |
| **[KServe Quick Reference](docs/deployment/kserve-quick-reference.md)** | Command cheat sheet | Daily operations |
| **[kubernetes/kserve/README.md](kubernetes/kserve/README.md)** | Manifest documentation | Deploying/updating models |

## 🚀 Quick Start (TL;DR)

```bash
# 1. Run automated setup (installs everything)
./scripts/setup-kserve-local.sh

# 2. Build and load embedding service image
docker build -t intellirag-embedding:latest deploy/embedding-service/
minikube image load intellirag-embedding:latest

# 3. Deploy models
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml
kubectl apply -f kubernetes/kserve/embedding-bge-m3-inference.yaml

# 4. Wait for ready (5-10 minutes on first run)
kubectl get inferenceservice -n intellirag -w

# 5. Set up port forwarding
kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080 &
kubectl port-forward -n intellirag svc/embedding-bge-m3-predictor 8001:8001 &

# 6. Test endpoints
curl http://localhost:8000/health
curl http://localhost:8001/health

# 7. Run IntelliRAG with KServe
export VLLM_BASE_URL=http://localhost:8000/v1
export EMBEDDING_SERVICE_URL=http://localhost:8001
export EMBEDDING_USE_REMOTE=true
uvicorn app.main:app --reload
```

**Total time**: 30-60 minutes (including downloads)

## 📋 What You Get

After setup, you'll have:

✅ **Minikube cluster** with GPU support  
✅ **KServe** with Knative, Istio, cert-manager  
✅ **Two InferenceServices**:
- `vllm-qwen` - LLM inference (Qwen/Qwen3-0.6B)
- `embedding-bge-m3` - Embeddings (BAAI/bge-m3)

✅ **Production-like setup** matching GKE deployment

## 🎯 Why Use KServe Locally?

### Benefits

1. **Production Parity**: Same setup as GKE deployment
2. **Proper Resource Management**: K8s-based scaling and limits
3. **Service Mesh**: Istio for networking and observability
4. **Autoscaling**: KServe handles scaling (including scale-to-zero)
5. **Version Management**: Easy model updates via manifests
6. **Monitoring**: Ready for Prometheus integration

### vs Docker Compose

| Feature | Docker Compose | KServe |
|---------|----------------|--------|
| Setup Complexity | Simple | Moderate |
| Production Parity | Low | High |
| Autoscaling | Manual | Automatic |
| Resource Limits | Basic | Advanced |
| GPU Management | Basic | Advanced |
| Service Mesh | No | Yes (Istio) |
| Monitoring | Basic | Full stack |
| Learning Curve | Low | Moderate |

**Recommendation**: Use Docker Compose for initial development, KServe for production-like testing.

## 📦 Files Created

```
IntelliRAG/
├── docs/deployment/
│   ├── local-kserve-setup-guide.md    # Complete setup guide
│   ├── kserve-quick-reference.md      # Command reference
│   └── pre-deployment-action-plan.md  # GKE deployment plan
├── kubernetes/kserve/
│   ├── vllm-qwen-inference.yaml       # LLM InferenceService
│   ├── embedding-bge-m3-inference.yaml # Embedding InferenceService
│   ├── namespace.yaml                  # Namespace setup
│   └── README.md                       # Manifest docs
├── scripts/
│   └── setup-kserve-local.sh          # Automated setup script
└── KSERVE_SETUP.md                     # This file
```

## 🛠️ Prerequisites

Before starting, ensure you have:

- **Hardware**:
  - NVIDIA GPU (you have RTX 4070Ti ✅)
  - 16GB+ RAM
  - 50GB+ free disk space

- **Software**:
  - Docker (installed ✅)
  - NVIDIA drivers and Docker runtime (installed ✅)
  - kubectl (will be installed by script)
  - minikube (will be installed by script)

## 📖 Detailed Setup Instructions

### Option 1: Automated Setup (Recommended)

Run the setup script that installs everything:

```bash
./scripts/setup-kserve-local.sh
```

This installs:
1. kubectl and minikube
2. Starts minikube with GPU support
3. Installs NVIDIA device plugin
4. Installs cert-manager
5. Installs Istio
6. Installs Knative Serving
7. Installs KServe
8. Creates IntelliRAG namespace

**Time**: ~20-30 minutes

### Option 2: Manual Setup

Follow the step-by-step guide:

```bash
# Open the guide
cat docs/deployment/local-kserve-setup-guide.md

# Or view in browser
firefox docs/deployment/local-kserve-setup-guide.md
```

## 🧪 Testing Your Setup

### 1. Test vLLM Inference

```bash
curl -X POST http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "prompt": "What is machine learning?",
    "max_tokens": 100
  }'
```

### 2. Test Embedding Service

```bash
curl -X POST http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Machine learning is amazing"],
    "normalize": false
  }'
```

### 3. Test IntelliRAG Integration

```bash
# Start IntelliRAG
export VLLM_BASE_URL=http://localhost:8000/v1
export EMBEDDING_SERVICE_URL=http://localhost:8001
export EMBEDDING_USE_REMOTE=true
uvicorn app.main:app --reload --port 8080

# In another terminal, test query
curl -X POST http://localhost:8080/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query": "What is IntelliRAG?", "collection_name": "default"}'
```

## 🐛 Common Issues

### Issue: GPU not available

```bash
# Check GPU allocation
kubectl get nodes -o jsonpath='{.items[*].status.allocatable.nvidia\.com/gpu}'

# Restart NVIDIA plugin
kubectl delete daemonset nvidia-device-plugin-daemonset -n kube-system
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.3/nvidia-device-plugin.yml
```

### Issue: InferenceService stuck in "Not Ready"

```bash
# Check pod status
kubectl get pods -n intellirag

# Check logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen

# Check events
kubectl describe inferenceservice vllm-qwen -n intellirag
```

### Issue: Port forward disconnects

```bash
# Kill existing forwards
pkill -f "port-forward.*intellirag"

# Restart with verbose logging
kubectl port-forward -n intellirag svc/vllm-qwen-predictor 8000:8080 -v=9
```

More troubleshooting: See [local-kserve-setup-guide.md](docs/deployment/local-kserve-setup-guide.md#troubleshooting)

## 📊 Monitoring

### Check Resource Usage

```bash
# Node resources
kubectl top node

# Pod resources
kubectl top pods -n intellirag

# GPU usage (inside pod)
POD_NAME=$(kubectl get pod -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen -o jsonpath='{.items[0].metadata.name}')
kubectl exec -n intellirag $POD_NAME -- nvidia-smi
```

### View Logs

```bash
# vLLM logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=vllm-qwen -f

# Embedding logs
kubectl logs -n intellirag -l serving.kserve.io/inferenceservice=embedding-bge-m3 -f
```

## 🧹 Cleanup

### Stop Services (Keep Cluster)

```bash
# Delete InferenceServices
kubectl delete inferenceservice --all -n intellirag

# Stop port forwards
pkill -f "port-forward.*intellirag"
```

### Stop Cluster (Preserve State)

```bash
# Stop minikube
minikube stop

# Start again later
minikube start
```

### Delete Everything

```bash
# Delete cluster completely
minikube delete

# This removes all data, you'll need to run setup again
```

## 🚀 Next Steps

After getting KServe running:

1. **Run Tests**: `pytest tests/integration/ -v`
2. **Benchmark Performance**: Compare vs Docker Compose
3. **Monitor Metrics**: Set up Prometheus/Grafana (future)
4. **Document Issues**: Note any problems for GKE deployment
5. **Optimize Configuration**: Tune GPU memory, batch size, etc.

## 🔗 Additional Resources

- **KServe Documentation**: https://kserve.github.io/website/
- **vLLM Documentation**: https://docs.vllm.ai/
- **Knative Documentation**: https://knative.dev/docs/
- **Minikube GPU Guide**: https://minikube.sigs.k8s.io/docs/tutorials/nvidia/

## 💡 Tips

1. **Pre-download models**: Download models to `~/.cache/huggingface/` before deploying to speed up first start
2. **Increase minikube resources**: If running out of memory, increase with `minikube start --memory=16384`
3. **Use screen for port forwards**: Keep port forwards persistent with `screen` or `tmux`
4. **Monitor GPU usage**: Regularly check `nvidia-smi` to ensure GPU is being used efficiently
5. **Test before GKE**: Use local KServe to validate InferenceService manifests before cloud deployment

## 📞 Getting Help

If you encounter issues:

1. Check the [troubleshooting section](docs/deployment/local-kserve-setup-guide.md#troubleshooting)
2. Review pod logs: `kubectl logs -n intellirag <pod-name>`
3. Check KServe controller logs: `kubectl logs -n kserve -l control-plane=kserve-controller-manager`
4. Verify GPU access: `kubectl exec -n intellirag <pod-name> -- nvidia-smi`

---

**Ready to get started?**

Run this command to begin:

```bash
./scripts/setup-kserve-local.sh
```

Then follow the on-screen instructions!

---

**Last Updated**: November 5, 2025  
**Status**: Ready for use  
**Tested on**: Ubuntu 22.04, RTX 4070Ti, Minikube v1.32.0, KServe v0.12.0

