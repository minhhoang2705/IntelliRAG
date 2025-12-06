# Embedding Service Deployment Guide

**Last Updated**: November 4, 2025  
**Version**: 1.0.0

---

## Overview

This guide covers deploying the standalone embedding service for IntelliRAG, which serves BAAI/bge-m3 embeddings via FastAPI with automatic dimension detection and zero cold-start delay.

---

## Architecture

```
┌─────────────────────┐
│  FastAPI Main App   │
│  (Orchestrator)     │
└──────────┬──────────┘
           │
           ├──> http://localhost:6333  (Qdrant)
           ├──> http://localhost:8000  (vLLM - Qwen)
           └──> http://localhost:8001  (Embedding Service) ← NEW
```

---

## Prerequisites

- Docker & Docker Compose
- 4GB RAM minimum (8GB recommended)
- Python 3.11+ (for local development)
- Network access to HuggingFace (for model download)

---

## Quick Start

### 1. Deploy with Docker Compose

```bash
# Clone repository
cd /path/to/IntelliRAG

# Start all services (Qdrant + Embedding)
docker-compose up -d

# Verify embedding service is running
curl http://localhost:8001/health
```

Expected response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "BAAI/bge-m3",
  "device": "cpu",
  "embedding_dimension": 1024
}
```

### 2. Verify Integration

```bash
# Get model info
curl http://localhost:8001/model-info

# Generate test embeddings
curl -X POST http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{
    "texts": ["Hello world", "Test embedding"],
    "normalize": false
  }'
```

---

## Configuration

### Environment Variables

Create `.env` file in project root:

```bash
# Embedding Service
EMBEDDING_MODEL=BAAI/bge-m3           # Model to use
DEVICE=cpu                             # cpu or cuda
MAX_BATCH_SIZE=128                     # Max batch size

# Main App (to use remote embedding)
EMBEDDING_SERVICE_URL=http://embedding-service:8001  # In Docker network
EMBEDDING_USE_REMOTE=true             # Use remote service
```

### Switching Embedding Models

1. **Stop services**:
   ```bash
   docker-compose down
   ```

2. **Update .env**:
   ```bash
   echo "EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2" > .env
   ```

3. **Rebuild and restart**:
   ```bash
   docker-compose up -d --build
   ```

4. **Verify new dimension**:
   ```bash
   curl http://localhost:8001/model-info
   # {"embedding_dimension": 384, ...}
   ```

**Supported Models**:
- `BAAI/bge-m3` (1024 dims) - Default, multilingual
- `sentence-transformers/all-MiniLM-L6-v2` (384 dims) - Fast, English
- `BAAI/bge-large-en-v1.5` (1024 dims) - High quality, English
- `intfloat/e5-large-v2` (1024 dims) - General purpose
- `sentence-transformers/all-mpnet-base-v2` (768 dims) - Balanced

---

## Deployment Modes

### Local Development

```bash
# Standalone embedding service
cd deploy/embedding-service
docker-compose up -d

# Main app uses remote service
export EMBEDDING_USE_REMOTE=true
export EMBEDDING_SERVICE_URL=http://localhost:8001
uvicorn app.main:app --reload
```

### Docker Compose (Recommended)

```bash
# All services together
docker-compose up -d

# Services communicate via Docker network
# embedding-service: http://embedding-service:8001
```

### Kubernetes (Production)

See `/kubernetes/helm/embedding-service/` for Helm charts (pending).

---

## Integration with Main App

### Automatic (Recommended)

The main app automatically uses remote embedding service when `EMBEDDING_USE_REMOTE=true`:

```python
# app/main.py initializes orchestrator with remote embedding
orchestrator = OrchestratorService(
    embedding_service_url=os.getenv("EMBEDDING_SERVICE_URL", "http://localhost:8001"),
    use_remote_embedding=os.getenv("EMBEDDING_USE_REMOTE", "true").lower() == "true"
)
```

### Manual

```python
from app.services.embedding import EmbeddingService

# Remote mode
embedding_service = EmbeddingService(
    use_remote=True,
    remote_url="http://localhost:8001"
)

# Auto-discover dimension
dim = embedding_service.get_embedding_dimension()  # 1024

# Generate embeddings
embeddings = embedding_service.embed_batch(["text1", "text2"])
```

---

## Monitoring & Troubleshooting

### Check Service Health

```bash
# Health endpoint
curl http://localhost:8001/health

# Model info
curl http://localhost:8001/model-info

# Logs
docker logs -f intellirag-embedding
```

### Common Issues

#### 1. Service Not Starting

**Symptoms**: Container exits immediately or restarts repeatedly

**Solutions**:
```bash
# Check logs
docker logs intellirag-embedding

# Common causes:
# - Insufficient memory: Increase in docker-compose.yaml
# - Model download failed: Check network/HuggingFace access
# - Port conflict: Change port in docker-compose.yaml
```

#### 2. Connection Refused

**Symptoms**: Main app can't connect to embedding service

**Solutions**:
```bash
# Wait for model loading (60s)
curl http://localhost:8001/health

# In Docker network, use service name:
EMBEDDING_SERVICE_URL=http://embedding-service:8001

# Check network
docker network ls
docker network inspect intellirag-network
```

#### 3. Out of Memory

**Symptoms**: Container killed by OOM

**Solutions**:
```yaml
# Increase memory in docker-compose.yaml
deploy:
  resources:
    limits:
      memory: 8G  # Increased from 4G
```

Or use smaller model:
```bash
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # Only ~100MB
```

#### 4. Slow Performance

**Symptoms**: Embeddings take >1s per request

**Solutions**:
```bash
# Enable GPU (if available)
DEVICE=cuda

# Reduce batch size
MAX_BATCH_SIZE=64

# Use smaller/faster model
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

---

## Performance Tuning

### CPU Optimization

```yaml
# docker-compose.yaml
deploy:
  resources:
    limits:
      cpus: '2.0'
      memory: 4G
```

### GPU Acceleration

```yaml
# docker-compose.yaml
services:
  embedding-service:
    runtime: nvidia
    environment:
      - DEVICE=cuda
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
```

### Batch Processing

```python
# For large ingestion jobs
embeddings = embedding_service.embed_batch(
    texts,
    batch_size=256,  # Larger batches for throughput
    normalize=False
)
```

---

## Scaling

### Horizontal Scaling (Multiple Replicas)

```yaml
# docker-compose.yaml
services:
  embedding-service:
    deploy:
      replicas: 3  # Multiple instances
```

Add load balancer (nginx):
```nginx
upstream embedding_backend {
    server embedding-service-1:8001;
    server embedding-service-2:8001;
    server embedding-service-3:8001;
}

server {
    location /vectorize {
        proxy_pass http://embedding_backend;
    }
}
```

---

## Migration Between Models

When switching embedding models with different dimensions:

1. **Backup existing data**:
   ```bash
   # Export Qdrant collection
   curl http://localhost:6333/collections/default/points/scroll
   ```

2. **Switch model**:
   ```bash
   docker-compose down
   echo "EMBEDDING_MODEL=new-model" > .env
   docker-compose up -d --build
   ```

3. **Re-embed documents**:
   ```bash
   # Use migration script (pending implementation)
   python scripts/migrate_embedding_model.py \
     --old-collection default \
     --new-collection default_v2 \
     --embedding-url http://localhost:8001
   ```

4. **Swap collections**:
   ```bash
   # Update app to use new collection
   ```

---

## Security Considerations

### API Authentication (Production)

Add API key protection:

```python
# deploy/embedding-service/main.py
from fastapi.security import APIKeyHeader

API_KEY = os.getenv("EMBEDDING_API_KEY")
api_key_header = APIKeyHeader(name="X-API-Key")

@app.post("/vectorize")
async def vectorize(request: EmbedRequest, api_key: str = Depends(api_key_header)):
    if api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    # ... rest of code
```

### Network Isolation

```yaml
# docker-compose.yaml
services:
  embedding-service:
    networks:
      - backend  # Internal network only
    # Don't expose port externally
```

---

## Maintenance

### Updates

```bash
# Update service
cd deploy/embedding-service
docker-compose pull
docker-compose up -d

# Update model
docker-compose down
docker-compose up -d --build --force-recreate
```

### Backups

```bash
# Backup Docker image
docker save intellirag-embedding:latest | gzip > embedding-service-backup.tar.gz

# Restore
docker load < embedding-service-backup.tar.gz
```

---

## Metrics & Observability

### Prometheus Metrics (Optional)

Add to `main.py`:

```python
from prometheus_client import Counter, Histogram, generate_latest

embedding_requests = Counter('embedding_requests_total', 'Total embedding requests')
embedding_duration = Histogram('embedding_duration_seconds', 'Embedding request duration')

@app.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type='text/plain')
```

Configure Prometheus:
```yaml
# prometheus.yml
scrape_configs:
  - job_name: 'embedding-service'
    static_configs:
      - targets: ['embedding-service:8001']
```

---

## Testing

### Unit Tests

```bash
# Test remote mode
pytest tests/unit/test_embedding_remote.py -v
```

### Integration Tests

```bash
# Requires service running
docker-compose up -d
pytest tests/integration/test_embedding_service_api.py -v
```

### Load Testing

```bash
# Using Apache Bench
ab -n 1000 -c 10 -p payload.json -T application/json \
   http://localhost:8001/vectorize
```

---

## Next Steps

1. **Deploy to Production**: See Kubernetes deployment guide (pending)
2. **Enable GPU**: For faster processing
3. **Add Monitoring**: Prometheus + Grafana dashboards
4. **Implement Caching**: Redis for frequently requested embeddings
5. **Rate Limiting**: Prevent abuse

---

## References

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [Qdrant Documentation](https://qdrant.tech/documentation/)
- [Docker Compose](https://docs.docker.com/compose/)

---

**Support**: Check logs with `docker logs intellirag-embedding`  
**Issues**: See troubleshooting section above

