# Embedding Service

Standalone, always-on embedding service for IntelliRAG. Serves BAAI/bge-m3 embeddings via FastAPI with automatic dimension detection.

## Features

- **Always Available**: Model pre-loaded on startup (no cold start)
- **Configurable**: Swap models via environment variables
- **Auto-Discovery**: Embedding dimension detected automatically
- **Production-Ready**: Health checks, logging, resource limits

## Quick Start

### Local Development

```bash
# Build and start service
docker-compose up -d

# Check health
curl http://localhost:8001/health

# Get model info
curl http://localhost:8001/model-info

# Generate embeddings
curl -X POST http://localhost:8001/vectorize \
  -H "Content-Type: application/json" \
  -d '{"texts": ["Hello world", "This is a test"]}'
```

### Configuration

Create `.env` file:

```bash
# Default: BAAI/bge-m3 (1024 dimensions)
EMBEDDING_MODEL=BAAI/bge-m3

# Alternative models:
# EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2  # 384 dimensions
# EMBEDDING_MODEL=BAAI/bge-large-en-v1.5                  # 1024 dimensions
# EMBEDDING_MODEL=intfloat/e5-large-v2                    # 1024 dimensions

# Device
DEVICE=cpu  # or 'cuda'

# Batch size
MAX_BATCH_SIZE=128
```

Then restart:
```bash
docker-compose down
docker-compose up -d
```

## API Endpoints

### GET /health
Health check with model status

```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "BAAI/bge-m3",
  "device": "cpu",
  "embedding_dimension": 1024
}
```

### GET /model-info
Model metadata with dimension

```json
{
  "model_name": "BAAI/bge-m3",
  "embedding_dimension": 1024,
  "device": "cpu",
  "max_batch_size": 128,
  "model_loaded": true
}
```

### POST /vectorize
Generate embeddings

Request:
```json
{
  "texts": ["Text 1", "Text 2"],
  "normalize": false,
  "batch_size": 32
}
```

Response:
```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "model": "BAAI/bge-m3",
  "dimension": 1024,
  "count": 2,
  "processing_time_seconds": 0.045
}
```

## Switching Models

1. Stop service: `docker-compose down`
2. Update `.env`: `EMBEDDING_MODEL=new-model-name`
3. Rebuild and start: `docker-compose up -d --build`
4. Verify dimension: `curl http://localhost:8001/model-info`

## Integration with Main App

In `app/services/orchestrator.py`:

```python
self.embedding_service = EmbeddingService(
    use_remote=True,
    remote_url="http://localhost:8001"  # or http://embedding-service:8001 in Docker
)
```

The service automatically discovers the embedding dimension via `/model-info` endpoint.

## Resource Requirements

- **Memory**: 2-4GB (depends on model)
- **CPU**: 1-2 cores
- **Startup Time**: 30-60 seconds (model loading)

## Monitoring

View logs:
```bash
docker logs -f intellirag-embedding
```

Check metrics via Prometheus (if configured):
```
http://localhost:8001/metrics
```

## Troubleshooting

**Service not starting?**
- Check logs: `docker logs intellirag-embedding`
- Verify memory limits in docker-compose.yaml
- Ensure model can be downloaded from HuggingFace

**Connection refused?**
- Wait 60s for model loading (check `/health` endpoint)
- Verify port 8001 is not in use
- Check firewall settings

**Out of memory?**
- Increase memory limit in docker-compose.yaml
- Use smaller model (e.g., all-MiniLM-L6-v2)
- Reduce MAX_BATCH_SIZE

## Production Deployment

See Kubernetes/Helm deployment guide in `/kubernetes/helm/embedding-service/`.

