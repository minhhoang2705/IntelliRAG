# KServe InferenceServices Deployment

This directory contains Kubernetes manifests for deploying KServe InferenceServices on Minikube with GPU support.

## Components

### InferenceServices
- **vllm-qwen-inference.yaml** - vLLM-based LLM inference (Qwen3-0.6B)
- **embedding-inference.yaml** - embedding service

### Networking
- **ingress.yaml** - NGINX Ingress for external access via CloudFlare Tunnel
- **virtual-services.yaml** - Istio VirtualServices (reserved for future use)
- **namespace.yaml** - Namespace definition

---

## Architecture

```
External Client
    ↓ HTTPS
CloudFlare Tunnel
    ├─> llm.blockchainradar.xyz
    └─> embed.blockchainradar.xyz
         ↓ HTTP
NGINX Ingress Controller (192.168.49.2:80)
    ↓ Host-based routing
         ├─> vllm-qwen-predictor-00001:80
         └─> embedding-service-predictor-00001:80
```

---

## Prerequisites

1. **Minikube** with GPU support
2. **NGINX Ingress** addon enabled
3. **KServe** v0.14.1 installed
4. **CloudFlare Tunnel** configured

---

## Deployment

### 1. Create Namespace
```bash
kubectl --context=minikube apply -f namespace.yaml
```

### 2. Deploy InferenceServices
```bash
# vLLM LLM Service
kubectl --context=minikube apply -f vllm-qwen-inference.yaml

# Embedding Service
kubectl --context=minikube apply -f embedding-inference.yaml
```

### 3. Setup Ingress
```bash
# Enable NGINX Ingress addon (if not already enabled)
minikube addons enable ingress

# Deploy Ingress resource
kubectl --context=minikube apply -f ingress.yaml
```

### 4. Verify Deployment
```bash
# Check InferenceServices
kubectl --context=minikube get inferenceservices -n kserve

# Check Ingress
kubectl --context=minikube get ingress -n kserve

# Check pods
kubectl --context=minikube get pods -n kserve
```

---

## Configuration Details

### vLLM InferenceService

- **Model:** Qwen/Qwen3-0.6B
- **GPU:** 1x NVIDIA GPU
- **Memory:** 8-10Gi
- **Features:** LoRA, prefix caching, bfloat16

**Key Arguments:**
```yaml
args:
  - --model=Qwen/Qwen3-0.6B
  - --dtype=bfloat16
  - --max-model-len=2048
  - --gpu-memory-utilization=0.5
  - --enable-lora
  - --enable-prefix-caching
```

### Embedding Service

- **Model:** google/embeddinggemma-300m
- **Device:** CPU
- **Dimensions:** 768
- **Batch Size:** 32

**Environment Variables:**
```yaml
env:
  - name: EMBEDDING_MODEL
    value: "google/embeddinggemma-300m"
  - name: DEVICE
    value: "cpu"
  - name: MAX_BATCH_SIZE
    value: "32"
```

### Ingress Configuration

**Key Annotations:**
```yaml
annotations:
  nginx.ingress.kubernetes.io/ssl-redirect: "false"
  nginx.ingress.kubernetes.io/upstream-vhost: "$service_name.$namespace.svc.cluster.local"
```

The `upstream-vhost` annotation is **critical** for Knative routing to work correctly through NGINX Ingress.

---

## Accessing Services

### Local Access (bypassing CloudFlare)

```bash
# vLLM Service
curl -H "Host: llm.blockchainradar.xyz" http://192.168.49.2/v1/models

# Embedding Service
curl -H "Host: embed.blockchainradar.xyz" http://192.168.49.2/health
```

### External Access (via CloudFlare Tunnel)

```bash
# vLLM Service
curl https://llm.blockchainradar.xyz/v1/models
curl https://llm.blockchainradar.xyz/health

# Embedding Service
curl https://embed.blockchainradar.xyz/health
curl -X POST https://embed.blockchainradar.xyz/embed \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello world"]}'
```

---

## Troubleshooting

### InferenceService not ready

```bash
# Check status
kubectl --context=minikube get inferenceservice <name> -n kserve -o yaml

# Check predictor pod logs
kubectl --context=minikube logs -n kserve <predictor-pod> -c kserve-container

# Check events
kubectl --context=minikube describe inferenceservice <name> -n kserve
```

### Ingress not routing

```bash
# Check Ingress status
kubectl --context=minikube describe ingress kserve-ingress -n kserve

# Check Ingress controller logs
kubectl --context=minikube logs -n ingress-nginx <ingress-controller-pod>

# Verify service endpoints
kubectl --context=minikube get endpoints -n kserve
```

### 502 Bad Gateway from CloudFlare

This typically means:
1. CloudFlare Tunnel not running
2. Ingress controller not accessible on 192.168.49.2:80
3. Wrong Host header configuration

**Resolution:**
```bash
# Check CloudFlare Tunnel status
ps aux | grep cloudflared

# Restart tunnel if needed
pkill cloudflared
/usr/local/bin/cloudflared tunnel \
  --config ~/.cloudflared/config.yml \
  --no-autoupdate run <tunnel-id> &

# Test local Ingress
curl -H "Host: llm.blockchainradar.xyz" http://192.168.49.2/health
```

---

## Performance Tuning

### vLLM Optimization

Adjust GPU memory utilization:
```yaml
args:
  - --gpu-memory-utilization=0.8  # Increase from 0.5
```

Adjust batch size:
```yaml
args:
  - --max-num-seqs=128  # Default: 256
```

### Embedding Service Optimization

Increase batch size:
```yaml
env:
  - name: MAX_BATCH_SIZE
    value: "64"  # Increase from 32
```

---

## Maintenance

### Updating InferenceServices

```bash
# Edit manifest
vim vllm-qwen-inference.yaml

# Apply changes
kubectl --context=minikube apply -f vllm-qwen-inference.yaml

# Watch rollout
kubectl --context=minikube get pods -n kserve -w
```

### Scaling

KServe automatically scales based on traffic (scale-to-zero enabled by default).

**Disable scale-to-zero:**
```yaml
metadata:
  annotations:
    autoscaling.knative.dev/min-scale: "1"
```

---

## Related Documentation

- [Ingress + CloudFlare Tunnel Setup](../../docs/architecture/ingress-cloudflare-tunnel-setup.md)
- [Migration Summary](../../docs/summaries/2025-11-23-ingress-migration-summary.md)
- [Phase 2 Model Serving](../../docs/plans/phase-2-model-serving.md)

---

## Important Notes

1. **Do NOT use port-forwards in production** - They are brittle and die when pods restart
2. **Always use the Ingress** - It provides self-healing, stable endpoints
3. **Host header is critical** - The `upstream-vhost` annotation must be set for Knative routing
4. **GPU resources** - Ensure GPU is available before deploying vLLM service
5. **CloudFlare Tunnel** - Must be restarted after config changes

---

## Success Criteria

- ✅ InferenceServices show `READY=True`
- ✅ Ingress has ADDRESS assigned (192.168.49.2)
- ✅ Local curls return 200 OK
- ✅ CloudFlare Tunnel endpoints return 200 OK
- ✅ No port-forward processes running
