# Phase 2: Local Development Setup

## Context Links
- [Phase 1: Abstract Storage Layer](./phase-01-abstract-storage-layer.md)
- [Docker Compose Reference](https://docs.docker.com/compose/)
- [LocalStack Documentation](https://docs.localstack.cloud/)

## Overview

**Priority**: P1 (Critical Path)
**Status**: Pending
**Effort**: 4 hours
**Depends On**: Phase 1

Set up local AWS development environment using LocalStack to validate S3 implementation before deploying to actual AWS. Zero AWS cost during development.

## Key Insights

- LocalStack simulates AWS services locally (S3, Secrets Manager, IAM)
- Free tier sufficient for S3, Secrets Manager simulation
- Enables full integration testing without AWS credits
- Docker Compose orchestrates LocalStack + application services

## Requirements

### Functional
- LocalStack container running S3 service
- Application connects to LocalStack S3 in development mode
- Secrets Manager simulation for credential testing
- One-command setup: `docker compose up`

### Non-Functional
- Fast startup (<30 seconds)
- Reproducible environment
- Easy switch between LocalStack and real AWS

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                   Local Development Stack                        │
│                                                                  │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  FastAPI    │  │   Qdrant    │  │ LocalStack  │              │
│  │  (app)      │  │  (vector)   │  │ (S3, SM)    │              │
│  │  :8000      │  │  :6333      │  │  :4566      │              │
│  └──────┬──────┘  └─────────────┘  └──────┬──────┘              │
│         │                                  │                     │
│         └──────────────┬───────────────────┘                     │
│                        │                                         │
│              ┌─────────▼─────────┐                               │
│              │   Docker Network  │                               │
│              │   (intellirag)    │                               │
│              └───────────────────┘                               │
└─────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Files to Create
| File | Purpose |
|------|---------|
| `docker-compose.dev.yml` | Development stack with LocalStack |
| `scripts/localstack-init.sh` | Initialize S3 buckets in LocalStack |
| `.env.localstack` | LocalStack-specific environment vars |
| `tests/integration/test_s3_localstack.py` | LocalStack integration tests |

### Files to Modify
| File | Changes |
|------|---------|
| `docker-compose.yml` | Add LocalStack service option |
| `app/config.py` | Add LocalStack endpoint config |
| `.env.example` | Add AWS/LocalStack examples |

## Implementation Steps

### Step 1: Create Docker Compose for Development

```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  localstack:
    image: localstack/localstack:3.0
    ports:
      - "4566:4566"           # LocalStack gateway
      - "4510-4559:4510-4559" # External services port range
    environment:
      - SERVICES=s3,secretsmanager
      - DEBUG=1
      - DATA_DIR=/var/lib/localstack/data
      - DOCKER_HOST=unix:///var/run/docker.sock
    volumes:
      - localstack_data:/var/lib/localstack
      - /var/run/docker.sock:/var/run/docker.sock
      - ./scripts/localstack-init.sh:/etc/localstack/init/ready.d/init.sh
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:4566/_localstack/health"]
      interval: 10s
      timeout: 5s
      retries: 5

  qdrant:
    image: qdrant/qdrant:v1.7.4
    ports:
      - "6333:6333"
      - "6334:6334"
    volumes:
      - qdrant_data:/qdrant/storage
    environment:
      - QDRANT__SERVICE__GRPC_PORT=6334

  app:
    build:
      context: .
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      - STORAGE_PROVIDER=s3
      - S3_BUCKET_NAME=intellirag-documents
      - S3_REGION=us-east-1
      - AWS_ENDPOINT_URL=http://localstack:4566
      - AWS_ACCESS_KEY_ID=test
      - AWS_SECRET_ACCESS_KEY=test
      - QDRANT_URL=http://qdrant:6333
      - EMBEDDING_SERVICE_URL=${EMBEDDING_SERVICE_URL:-http://host.docker.internal:8001}
      - VLLM_BASE_URL=${VLLM_BASE_URL:-http://host.docker.internal:8000/v1}
    depends_on:
      localstack:
        condition: service_healthy
      qdrant:
        condition: service_started
    volumes:
      - ./app:/app/app:ro

networks:
  default:
    name: intellirag

volumes:
  localstack_data:
  qdrant_data:
```

### Step 2: Create LocalStack Initialization Script

```bash
#!/bin/bash
# scripts/localstack-init.sh
# Runs automatically when LocalStack starts

set -e

echo "Initializing LocalStack S3 buckets..."

# Create S3 buckets
awslocal s3 mb s3://intellirag-documents
awslocal s3 mb s3://intellirag-mlflow-artifacts

# Set bucket policies (optional)
awslocal s3api put-bucket-versioning \
    --bucket intellirag-documents \
    --versioning-configuration Status=Enabled

echo "LocalStack initialization complete!"

# List created resources
echo "Created buckets:"
awslocal s3 ls
```

### Step 3: Update S3 Storage Service for LocalStack

```python
# Update app/services/storage/s3_storage.py

class S3StorageService:
    def __init__(
        self,
        bucket_name: str,
        region: str = "us-east-1",
        endpoint_url: str = None  # For LocalStack
    ):
        self.bucket_name = bucket_name
        self.region = region
        self.endpoint_url = endpoint_url  # http://localstack:4566
        self._session = None
        self._client = None
        self._session_active = False

    async def connect(self) -> None:
        self._session = aioboto3.Session()
        client_kwargs = {'region_name': self.region}

        # Support LocalStack endpoint
        if self.endpoint_url:
            client_kwargs['endpoint_url'] = self.endpoint_url

        self._client = await self._session.client(
            's3', **client_kwargs
        ).__aenter__()
        self._session_active = True
```

### Step 4: Update Config for LocalStack

```python
# Add to app/config.py

# AWS Endpoint Override (for LocalStack)
aws_endpoint_url: str = Field(
    default="", description="AWS endpoint URL (set for LocalStack)")

# Factory uses this:
# if settings.aws_endpoint_url:
#     S3StorageService(..., endpoint_url=settings.aws_endpoint_url)
```

### Step 5: Create LocalStack Environment File

```bash
# .env.localstack
STORAGE_PROVIDER=s3
S3_BUCKET_NAME=intellirag-documents
S3_REGION=us-east-1
AWS_ENDPOINT_URL=http://localhost:4566
AWS_ACCESS_KEY_ID=test
AWS_SECRET_ACCESS_KEY=test
QDRANT_URL=http://localhost:6333
```

### Step 6: Create LocalStack Integration Test

```python
# tests/integration/test_s3_localstack.py
import pytest
import os

# Skip if not running with LocalStack
pytestmark = pytest.mark.skipif(
    os.getenv("AWS_ENDPOINT_URL") is None,
    reason="LocalStack not configured"
)

@pytest.fixture
async def s3_service():
    from app.services.storage.s3_storage import S3StorageService

    service = S3StorageService(
        bucket_name="intellirag-documents",
        region="us-east-1",
        endpoint_url=os.getenv("AWS_ENDPOINT_URL")
    )
    await service.connect()
    yield service
    await service.disconnect()

@pytest.mark.asyncio
async def test_upload_and_download(s3_service):
    # Upload
    test_data = b"Hello, LocalStack!"
    uri = await s3_service.upload_file(
        file_data=test_data,
        object_path="test/hello.txt",
        content_type="text/plain"
    )
    assert uri == "s3://intellirag-documents/test/hello.txt"

    # Download
    downloaded = await s3_service.download_file("test/hello.txt")
    assert downloaded == test_data

@pytest.mark.asyncio
async def test_upload_with_metadata(s3_service):
    uri = await s3_service.upload_file(
        file_data=b"test content",
        object_path="test/meta.txt",
        content_type="text/plain",
        metadata={"collection": "test", "source": "integration-test"}
    )
    assert "s3://" in uri
```

### Step 7: Add Development Scripts

```bash
# scripts/dev-start.sh
#!/bin/bash
# Start development environment with LocalStack

set -e

echo "Starting LocalStack development environment..."

# Build and start services
docker compose -f docker-compose.dev.yml up -d

# Wait for LocalStack to be ready
echo "Waiting for LocalStack..."
until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "running"'; do
    sleep 2
done

echo "LocalStack is ready!"
echo "S3 endpoint: http://localhost:4566"
echo "Qdrant endpoint: http://localhost:6333"
echo ""
echo "Run tests with: STORAGE_PROVIDER=s3 AWS_ENDPOINT_URL=http://localhost:4566 pytest"
```

```bash
# scripts/dev-stop.sh
#!/bin/bash
# Stop development environment

docker compose -f docker-compose.dev.yml down -v
echo "Development environment stopped."
```

## Todo List

- [ ] Create `docker-compose.dev.yml`
- [ ] Create `scripts/localstack-init.sh`
- [ ] Make init script executable: `chmod +x scripts/localstack-init.sh`
- [ ] Update S3StorageService for endpoint_url support
- [ ] Update app/config.py with aws_endpoint_url
- [ ] Create `.env.localstack`
- [ ] Update `.env.example` with AWS examples
- [ ] Create LocalStack integration tests
- [ ] Create dev-start.sh and dev-stop.sh scripts
- [ ] Test full flow: upload -> ingest -> query
- [ ] Document LocalStack usage in README

## Success Criteria

- [ ] `docker compose -f docker-compose.dev.yml up` starts all services
- [ ] LocalStack S3 buckets created automatically
- [ ] Application connects to LocalStack S3
- [ ] Upload/download operations work
- [ ] Integration tests pass with LocalStack
- [ ] No AWS credentials required for local development

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| LocalStack behavior differs from AWS | Use LocalStack Pro for closer parity (optional) |
| Port conflicts | Use non-standard ports if needed |
| Docker resource usage | Limit container resources in compose |

## Security Considerations

- LocalStack uses dummy credentials (`test`/`test`)
- Never use real AWS credentials with LocalStack
- LocalStack data is ephemeral (volumes can persist if needed)

## Next Steps

After completing this phase:
1. Validate all S3 operations work with LocalStack
2. Run full test suite against LocalStack
3. Proceed to Phase 3: AWS Foundation
