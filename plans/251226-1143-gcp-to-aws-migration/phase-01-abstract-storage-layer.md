# Phase 1: Abstract Storage Layer

## Context Links
- [GCS Storage Service](../../app/services/gcs_storage.py)
- [GCS Loader Service](../../app/services/gcs_loader.py)
- [Orchestrator](../../app/services/orchestrator.py)
- [Upload Endpoint](../../app/api/v1/upload.py)

## Overview

**Priority**: P1 (Critical Path)
**Status**: Implementation Complete - Code Review Completed
**Effort**: 6 hours
**Review**: [Code Review Report](../reports/code-reviewer-251231-0336-gcp-aws-migration-phase1.md)
**Quality Score**: 8.5/10

Create provider-agnostic storage interface enabling seamless swap between GCS and S3 without application code changes. This is the foundation for all subsequent migration phases.

## Key Insights

- Current `GCSStorageService` has tight coupling to `gcloud-aio-storage`
- `GCSLoaderService` uses LangChain's GCS-specific loaders
- Both services share similar interface: `upload_file()`, `download_file()`, `load_file()`
- LangChain has equivalent S3 loaders: `S3FileLoader`, `S3DirectoryLoader`

## Requirements

### Functional
- Abstract interface for object storage operations
- S3 implementation using `aioboto3`
- GCS implementation (preserve existing, refactor)
- Factory pattern for provider selection via environment variable
- URI scheme normalization (`gs://` <-> `s3://`)

### Non-Functional
- Zero breaking changes to existing tests
- Maintain async operations
- Support dependency injection for testing

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     Application Layer                            │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │  Upload API │  │ Orchestrator│  │  Ingest API │              │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘              │
│         │                │                │                      │
│         └────────────────┼────────────────┘                      │
│                          │                                       │
│                          ▼                                       │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              ObjectStorageService (Protocol)                 │ │
│  │  - upload_file(data, path, content_type) -> uri             │ │
│  │  - download_file(path) -> bytes                             │ │
│  │  - delete_file(path) -> bool                                │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                          │                                       │
│         ┌────────────────┼────────────────┐                      │
│         ▼                ▼                ▼                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐              │
│  │GCSStorage   │  │ S3Storage   │  │ LocalStorage│              │
│  │Service      │  │ Service     │  │ Service     │              │
│  └─────────────┘  └─────────────┘  └─────────────┘              │
└─────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Files to Create
| File | Purpose |
|------|---------|
| `app/services/storage/base.py` | Abstract protocol definition |
| `app/services/storage/s3_storage.py` | S3 implementation |
| `app/services/storage/factory.py` | Provider factory |
| `app/services/storage/__init__.py` | Module exports |
| `app/services/loader/base.py` | Abstract loader protocol |
| `app/services/loader/s3_loader.py` | S3 loader implementation |
| `app/services/loader/factory.py` | Loader factory |
| `app/services/loader/__init__.py` | Module exports |
| `tests/unit/test_s3_storage.py` | S3 storage tests |
| `tests/unit/test_s3_loader.py` | S3 loader tests |
| `tests/unit/test_storage_factory.py` | Factory tests |

### Files to Modify
| File | Changes |
|------|---------|
| `app/services/gcs_storage.py` | Move to `storage/gcs_storage.py`, implement protocol |
| `app/services/gcs_loader.py` | Move to `loader/gcs_loader.py`, implement protocol |
| `app/services/orchestrator.py` | Use factory instead of direct GCS imports |
| `app/api/v1/upload.py` | Use factory instead of direct GCS imports |
| `app/config.py` | Add `STORAGE_PROVIDER` and S3 config vars |
| `app/models/schemas.py` | Generalize `GCSStorageInfo` to `CloudStorageInfo` |
| `pyproject.toml` | Add `aioboto3`, `boto3` dependencies |

### Files to Delete (After Migration Complete)
| File | Reason |
|------|--------|
| `app/services/gcs_storage.py` | Moved to storage module |
| `app/services/gcs_loader.py` | Moved to loader module |

## Implementation Steps

### Step 1: Create Abstract Storage Protocol (TDD - Write Test First)

```python
# tests/unit/test_storage_base.py
import pytest
from typing import Protocol, runtime_checkable

@runtime_checkable
class ObjectStorageProtocol(Protocol):
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...
    async def upload_file(self, file_data, object_path: str,
                          content_type: str, metadata: dict = None) -> str: ...
    async def download_file(self, object_path: str) -> bytes: ...

def test_gcs_implements_protocol():
    from app.services.storage.gcs_storage import GCSStorageService
    assert isinstance(GCSStorageService("proj", "bucket"), ObjectStorageProtocol)

def test_s3_implements_protocol():
    from app.services.storage.s3_storage import S3StorageService
    assert isinstance(S3StorageService("bucket", "us-east-1"), ObjectStorageProtocol)
```

### Step 2: Create Base Protocol

```python
# app/services/storage/base.py
from typing import Protocol, runtime_checkable, Optional

@runtime_checkable
class ObjectStorageProtocol(Protocol):
    """Protocol for object storage services (GCS, S3, etc.)."""

    bucket_name: str

    async def __aenter__(self) -> "ObjectStorageProtocol": ...
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None: ...
    async def connect(self) -> None: ...
    async def disconnect(self) -> None: ...

    async def upload_file(
        self,
        file_data,
        object_path: str,
        content_type: str,
        metadata: Optional[dict] = None
    ) -> str:
        """Upload file and return cloud URI (gs:// or s3://)."""
        ...

    async def download_file(self, object_path: str) -> bytes:
        """Download file and return bytes."""
        ...
```

### Step 3: Implement S3 Storage Service (TDD)

```python
# app/services/storage/s3_storage.py
import aioboto3
from app.services.storage.base import ObjectStorageProtocol
from app.exceptions import StorageError

class S3StorageService:
    """AWS S3 storage service implementing ObjectStorageProtocol."""

    def __init__(self, bucket_name: str, region: str = "us-east-1"):
        self.bucket_name = bucket_name
        self.region = region
        self._session = None
        self._client = None
        self._session_active = False

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self) -> None:
        self._session = aioboto3.Session()
        self._client = await self._session.client(
            's3', region_name=self.region
        ).__aenter__()
        self._session_active = True

    async def disconnect(self) -> None:
        if self._client and self._session_active:
            await self._client.__aexit__(None, None, None)
            self._session_active = False

    async def upload_file(
        self,
        file_data,
        object_path: str,
        content_type: str,
        metadata: dict = None
    ) -> str:
        if not self._session_active:
            raise StorageError("S3 client not connected")

        content = file_data.read() if hasattr(file_data, 'read') else file_data

        await self._client.put_object(
            Bucket=self.bucket_name,
            Key=object_path,
            Body=content,
            ContentType=content_type,
            Metadata=metadata or {}
        )

        return f"s3://{self.bucket_name}/{object_path}"

    async def download_file(self, object_path: str) -> bytes:
        if not self._session_active:
            raise StorageError("S3 client not connected")

        response = await self._client.get_object(
            Bucket=self.bucket_name,
            Key=object_path
        )
        return await response['Body'].read()
```

### Step 4: Create Storage Factory

```python
# app/services/storage/factory.py
from typing import Literal
from app.services.storage.base import ObjectStorageProtocol

StorageProvider = Literal["gcs", "s3", "local"]

def create_storage_service(
    provider: StorageProvider,
    bucket_name: str,
    **kwargs
) -> ObjectStorageProtocol:
    """Factory to create storage service based on provider."""

    if provider == "s3":
        from app.services.storage.s3_storage import S3StorageService
        return S3StorageService(
            bucket_name=bucket_name,
            region=kwargs.get("region", "us-east-1")
        )
    elif provider == "gcs":
        from app.services.storage.gcs_storage import GCSStorageService
        return GCSStorageService(
            project_id=kwargs.get("project_id", ""),
            bucket_name=bucket_name,
            credentials_path=kwargs.get("credentials_path")
        )
    else:
        raise ValueError(f"Unknown storage provider: {provider}")
```

### Step 5: Update Config

```python
# Add to app/config.py

# Storage Provider Configuration
storage_provider: str = Field(
    default="gcs", description="Storage provider: gcs, s3, local")

# AWS S3 Configuration (used when storage_provider=s3)
s3_bucket_name: str = Field(
    default="intellirag-documents", description="S3 bucket name")
s3_region: str = Field(
    default="us-east-1", description="AWS region")
s3_access_key_id: str = Field(
    default="", description="AWS access key (optional if using IAM role)")
s3_secret_access_key: str = Field(
    default="", description="AWS secret key (optional if using IAM role)")
```

### Step 6: Update Dependencies

```toml
# Add to pyproject.toml [project.dependencies]
aioboto3 = "^13.0.0"
boto3 = "^1.35.0"
```

### Step 7: Create S3 Loader Service

```python
# app/services/loader/s3_loader.py
from typing import List, Optional, Callable
from langchain_community.document_loaders import S3FileLoader, S3DirectoryLoader
from langchain_core.documents import Document
import asyncio
import logging

logger = logging.getLogger(__name__)

class S3LoaderService:
    """Service for loading documents from AWS S3."""

    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.region = region
        logger.info(f"Initialized S3LoaderService for bucket: {bucket}")

    async def load_file(self, key: str) -> List[Document]:
        """Load single file from S3."""
        logger.info(f"Loading file from S3: s3://{self.bucket}/{key}")

        loader = S3FileLoader(bucket=self.bucket, key=key)
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from {key}")
        return documents

    async def load_directory(
        self,
        prefix: str = "",
        continue_on_failure: bool = False
    ) -> List[Document]:
        """Load all files from S3 prefix."""
        logger.info(f"Loading directory from S3: s3://{self.bucket}/{prefix}")

        loader = S3DirectoryLoader(
            bucket=self.bucket,
            prefix=prefix
        )
        loop = asyncio.get_event_loop()
        documents = await loop.run_in_executor(None, loader.load)

        logger.info(f"Loaded {len(documents)} document(s) from prefix '{prefix}'")
        return documents
```

## Todo List

- [x] Write failing tests for ObjectStorageProtocol
- [x] Implement base protocol in `app/services/storage/base.py`
- [x] Write failing tests for S3StorageService
- [x] Implement S3StorageService
- [x] Write failing tests for storage factory
- [x] Implement storage factory
- [x] Refactor GCSStorageService to implement protocol
- [x] Write failing tests for S3LoaderService
- [x] Implement S3LoaderService
- [x] Update `app/config.py` with S3 settings
- [x] Update `pyproject.toml` dependencies
- [x] Update orchestrator to use factory
- [x] Update upload endpoint to use factory
- [x] Update schemas to be cloud-agnostic
- [ ] Run full test suite - verify >80% coverage (BLOCKED: `uv sync` needed)
- [ ] Test with LocalStack (Phase 2 validation)

## Critical Issues to Fix Before Tests

1. **Add Error Handling in S3LoaderService** (HIGH)
   - File: `app/services/loaders/s3_loader.py`
   - Add try/except blocks around LangChain loader operations

2. **Fix URI Parsing in Orchestrator** (MEDIUM)
   - File: `app/services/orchestrator.py`
   - Replace string replacement with urllib.parse.urlparse

3. **Fix Factory Type Annotation** (MEDIUM)
   - File: `app/services/storage/factory.py`
   - Change `provider: str` to `provider: StorageProvider`

## Pre-Production Requirements

4. **Add Retry Logic** (HIGH)
   - File: `app/services/storage/s3_storage.py`
   - Implement exponential backoff using tenacity

5. **Add Telemetry** (MEDIUM)
   - Add OpenTelemetry spans and Prometheus metrics

6. **Validate Bucket Names** (MEDIUM)
   - File: `app/config.py`
   - Add Field validators for S3 bucket names

## Success Criteria

- [ ] All existing GCS tests pass unchanged
- [ ] New S3 tests pass
- [ ] Factory correctly instantiates both providers
- [ ] Switching provider via env var works
- [ ] No hardcoded `gs://` references in application logic
- [ ] Test coverage >80%

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Breaking existing GCS functionality | Keep GCS impl, add S3 alongside |
| Async behavior differences | Use same patterns (aioboto3 mirrors gcloud-aio) |
| URI scheme confusion | Centralize URI generation in each implementation |

## Security Considerations

- S3 credentials via IAM role (IRSA) in production
- Never hardcode AWS credentials
- Use AWS Secrets Manager for sensitive config

## Next Steps

After completing this phase:
1. Proceed to Phase 2: Local Development Setup (LocalStack)
2. Validate S3 implementation with LocalStack before AWS deployment
