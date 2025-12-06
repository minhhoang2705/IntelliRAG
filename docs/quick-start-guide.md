# IntelliRAG Quick Start Guide

**Last Updated**: 2025-11-27
**Phase**: 3 (Completed) → 4 (Planning)

---

## System Status

✅ **ALL SYSTEMS OPERATIONAL**

| Component | Status | Endpoint/Access |
|-----------|--------|-----------------|
| GKE FastAPI | ✅ Running | https://api.intellirag.example.com |
| Qdrant (GKE) | ✅ Running | Internal: qdrant.database.svc.cluster.local:6333 |
| vLLM | ✅ Running | https://llm.blockchainradar.xyz/v1 |
| Embedding | ✅ Running | https://embed.blockchainradar.xyz |
| Grafana | ✅ Running | http://localhost:3000 (port-forward) |
| Prometheus | ✅ Running | http://localhost:9090 (port-forward) |

---

## Quick Access

### 1. Start Local Development Environment

```bash
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG

# Setup port-forwards
kubectl port-forward -n database svc/qdrant 6333:6333 &
kubectl port-forward -n observability svc/prometheus-grafana 3000:80 &

# Start FastAPI (loads .env automatically with uv)
export EMBEDDING_SERVICE_URL=https://embed.blockchainradar.xyz
export EMBEDDING_USE_REMOTE=true
export VLLM_BASE_URL=https://llm.blockchainradar.xyz/v1
export QDRANT_URL=http://localhost:6333
export API_KEY=b9b864c03c693b7a62c656c1b2fdc2cd8c126e58ce6ce4054aa3e07a5c55f0f9

uv run uvicorn app.main:app --host 0.0.0.0 --port 9000

# Check health
curl http://localhost:9000/ready
```

### 2. Access Grafana Dashboards

```bash
# URL: http://localhost:3000
# Username: admin
# Password: admin

# Dashboards available:
- Infrastructure Overview
- Ingestion Pipeline Metrics
- IntelliRAG System Overview
- LLM Performance Metrics
- Query Performance Dashboard
```

### 3. Test RAG Query

```bash
export API_KEY="b9b864c03c693b7a62c656c1b2fdc2cd8c126e58ce6ce4054aa3e07a5c55f0f9"

# Test query (will fail until documents ingested)
curl -X POST http://localhost:9000/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${API_KEY}" \
  -d '{"query": "What is RAG?"}'
```

### 4. Upload Document

```bash
curl -X POST http://localhost:9000/api/v1/upload \
  -H "Authorization: Bearer ${API_KEY}" \
  -F "file=@/path/to/document.pdf"
```

---

## Service Endpoints

### Production (GKE)

```bash
# FastAPI Application
https://api.intellirag.example.com

# Health check
https://api.intellirag.example.com/ready

# Metrics (Prometheus scraping)
https://api.intellirag.example.com/metrics

# API endpoints
POST https://api.intellirag.example.com/api/v1/upload
POST https://api.intellirag.example.com/api/v1/ingest
POST https://api.intellirag.example.com/api/v1/query
```

### Local GPU Services (via CloudFlare Tunnel)

```bash
# vLLM (Qwen3-0.6B)
https://llm.blockchainradar.xyz/v1/models
https://llm.blockchainradar.xyz/v1/chat/completions

# Embedding (EmbeddingGemma-300m)
https://embed.blockchainradar.xyz/health
https://embed.blockchainradar.xyz/vectorize
https://embed.blockchainradar.xyz/model-info
```

---

## Environment Configuration

### Local Development (.env)

```bash
# See .env file in project root
# Key variables:
EMBEDDING_SERVICE_URL=https://embed.blockchainradar.xyz
VLLM_BASE_URL=https://llm.blockchainradar.xyz/v1
QDRANT_URL=http://localhost:6333
API_KEY=b9b864c03c693b7a62c656c1b2fdc2cd8c126e58ce6ce4054aa3e07a5c55f0f9
```

### GKE Production

```bash
# Managed via Helm values.yaml
# See: helm/intellirag-app/values.yaml
embeddingServiceUrl: "https://embed.blockchainradar.xyz"
vllmBaseUrl: "https://llm.blockchainradar.xyz/v1"
qdrantUrl: "http://qdrant.database.svc.cluster.local:6333"
```

---

## Common Commands

### Kubernetes

```bash
# View GKE pods
kubectl get pods -n app
kubectl get pods -n database
kubectl get pods -n observability

# Check logs
kubectl logs -n app <pod-name> --tail=100 -f

# Port-forward services
kubectl port-forward -n database svc/qdrant 6333:6333
kubectl port-forward -n observability svc/prometheus-grafana 3000:80

# Check service endpoints
kubectl get svc -n app
kubectl get svc -n database
kubectl get svc -n observability
```

### Qdrant

```bash
# List collections
curl http://localhost:6333/collections

# Get collection info
curl http://localhost:6333/collections/default

# Count vectors
curl http://localhost:6333/collections/default/points/count
```

### Testing

```bash
# Run unit tests
pytest tests/unit/ -v

# Run integration tests
pytest tests/integration/ -v

# Check coverage
pytest --cov=app --cov-report=html
```

---

## Troubleshooting

### Issue: Embedding service connection failed

```bash
# Check if CloudFlare tunnel is active
curl https://embed.blockchainradar.xyz/health

# Verify environment variable
echo $EMBEDDING_SERVICE_URL

# Should be: https://embed.blockchainradar.xyz
```

### Issue: Qdrant connection failed

```bash
# Check if port-forward is running
ps aux | grep "port-forward.*qdrant"

# Restart port-forward
kubectl port-forward -n database svc/qdrant 6333:6333 &

# Test connection
curl http://localhost:6333/collections
```

### Issue: 401 Unauthorized

```bash
# Ensure API_KEY is set
echo $API_KEY

# Include Authorization header in all API requests
curl -H "Authorization: Bearer $API_KEY" ...
```

---

## Documentation

- **Phase 3 Verification**: `docs/summaries/phase-3-verification-report.md`
- **Migration Plan**: `docs/plans/embedding-dimension-migration-plan.md`
- **Phase 4 Plan**: `docs/plans/phase-4-mlops.md`
- **Architecture**: `images/high_level_architecture_v2.jpg`
- **CLAUDE.md**: Project instructions and guidelines

---

## Next Steps

1. ✅ Phase 3 verification complete
2. ⏳ Begin Phase 4 planning (MLOps)
3. 📋 Review Phase 4 plan and answer planning questions
4. 🚀 Implement MLFlow, RAGAS, Evidently monitoring

---

**Status**: Ready for Phase 4 Implementation
**Contact**: Engineering Team
