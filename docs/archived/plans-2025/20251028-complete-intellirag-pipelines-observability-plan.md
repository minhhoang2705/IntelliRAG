# IntelliRAG Complete Implementation Plan
# Ingestion Pipeline + Enhanced Observability

**Version**: 1.0
**Date**: 2025-10-28
**Timeline**: 5-7 days
**Approach**: TDD (Test-Driven Development)
**Coverage Target**: >80%

---

## Executive Summary

This plan completes the IntelliRAG system by implementing:
1. **Full Ingestion Pipeline** with 3-endpoint design (upload → ingest → status)
2. **Enhanced Observability** with OpenTelemetry + Jaeger distributed tracing
3. **Production-ready quality** with comprehensive testing

**Key Decisions:**
- Three endpoints for granular control and async processing
- Jaeger for distributed tracing (matching docs)
- Defer Evidently drift monitoring to Phase 2 (pragmatic)
- Balance speed and completeness (5-7 days)

---

## Table of Contents

1. [Current State Analysis](#1-current-state-analysis)
2. [Architecture Overview](#2-architecture-overview)
3. [Phase 1: Ingestion Pipeline (Days 1-3)](#3-phase-1-ingestion-pipeline-days-1-3)
4. [Phase 2: Enhanced Observability (Days 4-5)](#4-phase-2-enhanced-observability-days-4-5)
5. [Phase 3: Integration & Polish (Days 6-7)](#5-phase-3-integration--polish-days-6-7)
6. [Testing Strategy](#6-testing-strategy)
7. [Dependencies & Requirements](#7-dependencies--requirements)
8. [Risk Mitigation](#8-risk-mitigation)
9. [Success Criteria](#9-success-criteria)
10. [TODO Checklist](#10-todo-checklist)

---

## 1. Current State Analysis

### What EXISTS (✅):
- **Query/RAG Pipeline**: Complete with LangGraph routing
- **Document Loaders**: All 7 types (PDF, DOCX, CSV, Text, Markdown, URL, GCS)
- **Processing Services**: FileValidator, SemanticChunker, EmbeddingService
- **Storage**: GCSStorageService, VectorDBService (Qdrant)
- **Schemas**: IngestionRequest, IngestionResponse, all metadata models
- **Basic Observability**:
  - Structured JSON logging (app/core/logging.py)
  - Prometheus metrics middleware (basic)
  - Correlation ID middleware

### What's MISSING (❌):
- **Ingestion Pipeline**:
  - OrchestratorService.ingest() method
  - Upload endpoint (POST /api/v1/upload)
  - Ingest endpoint (POST /api/v1/ingest)
  - Status endpoint (GET /api/v1/ingest/status/{job_id})
  - Job state management (in-memory or Redis)
  - Integration tests for full flow

- **Enhanced Observability**:
  - OpenTelemetry instrumentation
  - Jaeger distributed tracing
  - Trace ID propagation to logs
  - Ingestion pipeline metrics
  - Document processing stage metrics
  - Enhanced RAG instrumentation

---

## 2. Architecture Overview

### 2.1 Ingestion Pipeline Flow

```
User → POST /api/v1/upload
    ↓ (Validate file, upload to GCS)
    ← Returns: {file_id, gcs_path}

User → POST /api/v1/ingest {file_id, collection_name}
    ↓ (Async processing starts)
    ← Returns: {job_id, status: "processing"}

Background Task:
    ├─> Load from GCS (GCSLoaderService)
    ├─> Parse content (Docling for PDF/images)
    ├─> Chunk (SemanticChunkerService)
    ├─> Embed (EmbeddingService - BGE-M3)
    ├─> Store (VectorDBService - Qdrant)
    └─> Update job status

User → GET /api/v1/ingest/status/{job_id}
    ← Returns: {job_id, status, progress, errors}
```

### 2.2 Observability Architecture

```
Every Request:
    ↓
OpenTelemetry Middleware
    ├─> Generate/Extract Trace ID
    ├─> Create Root Span
    ├─> Inject into Context
    └─> Propagate to all services
        ↓
Service Operations:
    ├─> Create Child Spans
    │   ├─ Embedding span (with dimensions)
    │   ├─ VectorDB span (with operation type)
    │   ├─ LLM span (with tokens)
    │   └─ File processing span (with file info)
    ├─> Record Metrics
    │   ├─ Prometheus counters/histograms
    │   └─ Custom business metrics
    └─> Structured Logs (with trace_id)
        ↓
Observability Backends:
    ├─> Jaeger (traces)
    ├─> Prometheus (metrics)
    └─> Loki (logs - future)
        ↓
Grafana Dashboards:
    ├─> System overview
    ├─> RAG performance
    ├─> Ingestion pipeline
    └─> Error tracking
```

---

## 3. Phase 1: Ingestion Pipeline (Days 1-3)

### Day 1: Job Management + Upload Endpoint

#### Task 1.1: Job State Management (TDD)

**Test First** (`tests/unit/test_job_manager.py`):
```python
"""Unit tests for JobManager service."""
import pytest
from app.services.job_manager import JobManager, JobStatus, IngestionJob


class TestJobManager:
    """Test job state management."""

    def test_create_job_returns_unique_id(self):
        """Creating a job should return a unique job ID."""
        manager = JobManager()
        job1 = manager.create_job(file_id="file_123", collection_name="test")
        job2 = manager.create_job(file_id="file_456", collection_name="test")

        assert job1.job_id != job2.job_id
        assert job1.status == JobStatus.PENDING

    def test_get_job_status_existing_job(self):
        """Getting status of existing job should return job details."""
        manager = JobManager()
        job = manager.create_job(file_id="file_123", collection_name="test")

        retrieved = manager.get_job(job.job_id)

        assert retrieved.job_id == job.job_id
        assert retrieved.status == JobStatus.PENDING

    def test_get_job_status_nonexistent_job(self):
        """Getting status of non-existent job should raise error."""
        manager = JobManager()

        with pytest.raises(ValueError, match="Job not found"):
            manager.get_job("invalid_job_id")

    def test_update_job_progress(self):
        """Updating job progress should modify state correctly."""
        manager = JobManager()
        job = manager.create_job(file_id="file_123", collection_name="test")

        manager.update_job(
            job.job_id,
            status=JobStatus.PROCESSING,
            progress=50,
            message="Processing chunks"
        )

        updated = manager.get_job(job.job_id)
        assert updated.status == JobStatus.PROCESSING
        assert updated.progress == 50
        assert updated.message == "Processing chunks"

    def test_complete_job_with_results(self):
        """Completing job should store results."""
        manager = JobManager()
        job = manager.create_job(file_id="file_123", collection_name="test")

        manager.complete_job(
            job.job_id,
            chunks_created=42,
            collection_name="docs"
        )

        completed = manager.get_job(job.job_id)
        assert completed.status == JobStatus.COMPLETED
        assert completed.progress == 100
        assert completed.chunks_created == 42

    def test_fail_job_with_error(self):
        """Failing job should record error details."""
        manager = JobManager()
        job = manager.create_job(file_id="file_123", collection_name="test")

        manager.fail_job(job.job_id, error="File parse failed")

        failed = manager.get_job(job.job_id)
        assert failed.status == JobStatus.FAILED
        assert "File parse failed" in failed.error

    def test_cleanup_old_jobs(self):
        """Old completed jobs should be removed after TTL."""
        manager = JobManager(job_ttl_seconds=1)
        job = manager.create_job(file_id="file_123", collection_name="test")
        manager.complete_job(job.job_id, chunks_created=10, collection_name="test")

        import time
        time.sleep(2)

        manager.cleanup_old_jobs()

        with pytest.raises(ValueError, match="Job not found"):
            manager.get_job(job.job_id)
```

**Implementation** (`app/services/job_manager.py`):
```python
"""Job state management for async ingestion pipeline."""
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional
import uuid
import logging
from threading import Lock


logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """Job status enum."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class IngestionJob:
    """Represents an ingestion job."""
    job_id: str
    file_id: str
    collection_name: str
    status: JobStatus
    progress: int = 0
    message: str = ""
    chunks_created: int = 0
    error: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)


class JobManager:
    """Manages ingestion job state."""

    def __init__(self, job_ttl_seconds: int = 3600):
        """Initialize job manager.

        Args:
            job_ttl_seconds: Time to keep completed jobs (default: 1 hour)
        """
        self._jobs: Dict[str, IngestionJob] = {}
        self._lock = Lock()
        self._ttl = timedelta(seconds=job_ttl_seconds)

    def create_job(self, file_id: str, collection_name: str) -> IngestionJob:
        """Create a new ingestion job.

        Args:
            file_id: ID of uploaded file
            collection_name: Target collection name

        Returns:
            Created job with unique ID
        """
        job_id = str(uuid.uuid4())
        job = IngestionJob(
            job_id=job_id,
            file_id=file_id,
            collection_name=collection_name,
            status=JobStatus.PENDING
        )

        with self._lock:
            self._jobs[job_id] = job

        logger.info(f"Created job {job_id} for file {file_id}")
        return job

    def get_job(self, job_id: str) -> IngestionJob:
        """Get job by ID.

        Args:
            job_id: Job ID

        Returns:
            Job details

        Raises:
            ValueError: If job not found
        """
        with self._lock:
            job = self._jobs.get(job_id)

        if not job:
            raise ValueError(f"Job not found: {job_id}")

        return job

    def update_job(
        self,
        job_id: str,
        status: Optional[JobStatus] = None,
        progress: Optional[int] = None,
        message: Optional[str] = None
    ) -> None:
        """Update job state.

        Args:
            job_id: Job ID
            status: New status
            progress: Progress percentage (0-100)
            message: Status message

        Raises:
            ValueError: If job not found
        """
        job = self.get_job(job_id)

        with self._lock:
            if status:
                job.status = status
            if progress is not None:
                job.progress = progress
            if message:
                job.message = message
            job.updated_at = datetime.utcnow()

        logger.info(f"Updated job {job_id}: status={status}, progress={progress}")

    def complete_job(
        self,
        job_id: str,
        chunks_created: int,
        collection_name: str
    ) -> None:
        """Mark job as completed.

        Args:
            job_id: Job ID
            chunks_created: Number of chunks created
            collection_name: Collection name
        """
        job = self.get_job(job_id)

        with self._lock:
            job.status = JobStatus.COMPLETED
            job.progress = 100
            job.chunks_created = chunks_created
            job.collection_name = collection_name
            job.message = f"Successfully ingested {chunks_created} chunks"
            job.updated_at = datetime.utcnow()

        logger.info(f"Completed job {job_id}: {chunks_created} chunks")

    def fail_job(self, job_id: str, error: str) -> None:
        """Mark job as failed.

        Args:
            job_id: Job ID
            error: Error message
        """
        job = self.get_job(job_id)

        with self._lock:
            job.status = JobStatus.FAILED
            job.error = error
            job.message = f"Failed: {error}"
            job.updated_at = datetime.utcnow()

        logger.error(f"Failed job {job_id}: {error}")

    def cleanup_old_jobs(self) -> int:
        """Remove old completed/failed jobs.

        Returns:
            Number of jobs cleaned up
        """
        cutoff = datetime.utcnow() - self._ttl
        cleaned = 0

        with self._lock:
            job_ids_to_remove = [
                job_id
                for job_id, job in self._jobs.items()
                if job.status in (JobStatus.COMPLETED, JobStatus.FAILED)
                and job.updated_at < cutoff
            ]

            for job_id in job_ids_to_remove:
                del self._jobs[job_id]
                cleaned += 1

        if cleaned > 0:
            logger.info(f"Cleaned up {cleaned} old jobs")

        return cleaned
```

**TDD Cycle**:
```bash
# 1. Write tests (RED)
pytest tests/unit/test_job_manager.py -v
# Expected: FAILED (module not found)

# 2. Implement minimal code (GREEN)
# Create app/services/job_manager.py with implementation above
pytest tests/unit/test_job_manager.py -v
# Expected: PASSED ✅

# 3. Check coverage
pytest tests/unit/test_job_manager.py --cov=app.services.job_manager --cov-report=term-missing
# Target: >80%
```

---

#### Task 1.2: Upload Endpoint (TDD)

**Schema First** (`app/models/schemas.py` - add to existing file):
```python
# Add to existing schemas.py

class UploadRequest(BaseModel):
    """Request model for file upload."""
    # File will come as multipart/form-data, not in JSON body
    collection_name: str = Field(
        ...,
        min_length=1,
        description="Target collection name"
    )


class UploadResponse(BaseModel):
    """Response model for file upload."""
    file_id: str = Field(..., description="Unique file identifier")
    filename: str = Field(..., description="Original filename")
    gcs_path: str = Field(..., description="GCS storage path")
    file_size: int = Field(..., ge=0, description="File size in bytes")
    mime_type: str = Field(..., description="MIME type of file")
    uploaded_at: str = Field(..., description="Upload timestamp (ISO format)")
```

**Test First** (`tests/unit/test_upload_endpoint.py`):
```python
"""Unit tests for upload endpoint."""
import pytest
from fastapi import UploadFile
from unittest.mock import AsyncMock, Mock, patch
from io import BytesIO


@pytest.mark.asyncio
async def test_upload_endpoint_valid_pdf():
    """Upload valid PDF should return file_id and GCS path."""
    from app.main import app
    from httpx import AsyncClient

    # Create mock file
    file_content = b"%PDF-1.4 test content"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    data = {"collection_name": "documents"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.services.gcs_storage.GCSStorageService.upload_file") as mock_upload:
            mock_upload.return_value = "gs://bucket/uploads/abc123.pdf"

            response = await client.post(
                "/api/v1/upload",
                files=files,
                data=data
            )

    assert response.status_code == 200
    body = response.json()
    assert "file_id" in body
    assert body["filename"] == "test.pdf"
    assert body["gcs_path"].startswith("gs://")
    assert body["mime_type"] == "application/pdf"


@pytest.mark.asyncio
async def test_upload_endpoint_invalid_file_type():
    """Upload unsupported file type should return 400."""
    from app.main import app
    from httpx import AsyncClient

    file_content = b"invalid content"
    files = {"file": ("malware.exe", BytesIO(file_content), "application/x-executable")}
    data = {"collection_name": "documents"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/upload",
            files=files,
            data=data
        )

    assert response.status_code == 400
    assert "unsupported file type" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_endpoint_file_too_large():
    """Upload file exceeding size limit should return 413."""
    from app.main import app
    from httpx import AsyncClient

    # Simulate large file (100MB)
    file_content = b"x" * (100 * 1024 * 1024)
    files = {"file": ("large.pdf", BytesIO(file_content), "application/pdf")}
    data = {"collection_name": "documents"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/upload",
            files=files,
            data=data
        )

    assert response.status_code == 413
    assert "file too large" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_upload_endpoint_gcs_failure():
    """GCS upload failure should return 500 with error."""
    from app.main import app
    from httpx import AsyncClient

    file_content = b"%PDF-1.4 test"
    files = {"file": ("test.pdf", BytesIO(file_content), "application/pdf")}
    data = {"collection_name": "documents"}

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.services.gcs_storage.GCSStorageService.upload_file") as mock_upload:
            mock_upload.side_effect = Exception("GCS connection failed")

            response = await client.post(
                "/api/v1/upload",
                files=files,
                data=data
            )

    assert response.status_code == 500
    assert "upload failed" in response.json()["detail"].lower()
```

**Implementation** (`app/main.py` - add endpoint):
```python
# Add to existing app/main.py

from fastapi import UploadFile, File, Form, HTTPException
from app.models.schemas import UploadResponse
from app.services.gcs_storage import GCSStorageService
from app.services.file_validator import FileValidatorService
import uuid
from datetime import datetime

# Initialize services (add to existing services)
gcs_storage = GCSStorageService()
file_validator = FileValidatorService()
job_manager = JobManager()


@app.post("/api/v1/upload", response_model=UploadResponse)
async def upload_endpoint(
    file: UploadFile = File(...),
    collection_name: str = Form(...)
):
    """Upload file to GCS for later ingestion.

    Args:
        file: File to upload
        collection_name: Target collection name

    Returns:
        Upload details with file_id and GCS path

    Raises:
        HTTPException: 400 for invalid file, 413 for too large, 500 for upload failure
    """
    try:
        # 1. Validate file
        content = await file.read()

        # Check size (max 50MB)
        max_size = 50 * 1024 * 1024
        if len(content) > max_size:
            raise HTTPException(status_code=413, detail="File too large (max 50MB)")

        # Validate file type
        is_valid, error = file_validator.validate_file_type(file.filename, content)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid file: {error}")

        # 2. Generate file ID
        file_id = str(uuid.uuid4())

        # 3. Upload to GCS
        gcs_path = await gcs_storage.upload_file(
            file_content=content,
            filename=file.filename,
            file_id=file_id
        )

        # 4. Return response
        return UploadResponse(
            file_id=file_id,
            filename=file.filename,
            gcs_path=gcs_path,
            file_size=len(content),
            mime_type=file.content_type or "application/octet-stream",
            uploaded_at=datetime.utcnow().isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")
```

**TDD Cycle**:
```bash
# 1. Write tests (RED)
pytest tests/unit/test_upload_endpoint.py -v
# Expected: FAILED

# 2. Implement (GREEN)
pytest tests/unit/test_upload_endpoint.py -v
# Expected: PASSED ✅

# 3. Coverage
pytest tests/unit/test_upload_endpoint.py --cov=app.main --cov-report=term-missing
```

---

### Day 2: Ingest Endpoint + Orchestrator.ingest()

#### Task 2.1: OrchestratorService.ingest() (TDD)

**Test First** (`tests/unit/test_orchestrator.py` - add to existing):
```python
# Add to existing test_orchestrator.py

@pytest.mark.asyncio
async def test_orchestrator_ingest_pdf_success():
    """Ingest PDF should load, chunk, embed, and store vectors."""
    orchestrator = OrchestratorService()

    with patch.object(orchestrator, 'gcs_loader') as mock_loader, \
         patch.object(orchestrator, 'semantic_chunker') as mock_chunker, \
         patch.object(orchestrator.embedding_service, 'embed_batch_async') as mock_embed, \
         patch.object(orchestrator.vectordb_service, 'upsert_vectors') as mock_upsert:

        # Mock GCS loader
        mock_loader.load_from_gcs.return_value = [
            {"text": "Document content", "page": 1}
        ]

        # Mock chunker
        mock_chunker.chunk_documents.return_value = [
            {"text": "Chunk 1", "chunk_id": 0},
            {"text": "Chunk 2", "chunk_id": 1}
        ]

        # Mock embeddings
        mock_embed.return_value = [[0.1] * 1024, [0.2] * 1024]

        # Mock vector store
        mock_upsert.return_value = None

        # Test ingest
        result = await orchestrator.ingest(
            file_id="file_123",
            gcs_path="gs://bucket/file.pdf",
            collection_name="documents"
        )

        assert result["status"] == "success"
        assert result["chunks_created"] == 2
        assert result["collection_name"] == "documents"
        mock_loader.load_from_gcs.assert_called_once()
        mock_chunker.chunk_documents.assert_called_once()
        mock_embed.assert_called_once()
        mock_upsert.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_ingest_handles_chunking_error():
    """Ingest should handle chunking errors gracefully."""
    orchestrator = OrchestratorService()

    with patch.object(orchestrator, 'gcs_loader') as mock_loader, \
         patch.object(orchestrator, 'semantic_chunker') as mock_chunker:

        mock_loader.load_from_gcs.return_value = [{"text": "content"}]
        mock_chunker.chunk_documents.side_effect = Exception("Chunking failed")

        with pytest.raises(Exception, match="Chunking failed"):
            await orchestrator.ingest(
                file_id="file_123",
                gcs_path="gs://bucket/file.pdf",
                collection_name="documents"
            )


@pytest.mark.asyncio
async def test_orchestrator_ingest_creates_collection_if_not_exists():
    """Ingest should create collection if it doesn't exist."""
    orchestrator = OrchestratorService()

    with patch.object(orchestrator.vectordb_service, 'collection_exists') as mock_exists, \
         patch.object(orchestrator.vectordb_service, 'create_collection') as mock_create, \
         patch.object(orchestrator, 'gcs_loader') as mock_loader, \
         patch.object(orchestrator, 'semantic_chunker') as mock_chunker, \
         patch.object(orchestrator.embedding_service, 'embed_batch_async') as mock_embed, \
         patch.object(orchestrator.vectordb_service, 'upsert_vectors') as mock_upsert:

        mock_exists.return_value = False
        mock_create.return_value = None
        mock_loader.load_from_gcs.return_value = [{"text": "content"}]
        mock_chunker.chunk_documents.return_value = [{"text": "Chunk 1"}]
        mock_embed.return_value = [[0.1] * 1024]
        mock_upsert.return_value = None

        result = await orchestrator.ingest(
            file_id="file_123",
            gcs_path="gs://bucket/file.pdf",
            collection_name="new_collection"
        )

        mock_exists.assert_called_once_with("new_collection")
        mock_create.assert_called_once()
        assert result["status"] == "success"
```

**Implementation** (`app/services/orchestrator.py` - add method):
```python
# Add to existing OrchestratorService class

from app.services.gcs_loader import GCSLoaderService
from app.services.semantic_chunker import SemanticChunkerService
from typing import Dict, Any

class OrchestratorService:
    def __init__(self, ...):
        # ... existing init code ...

        # Add loader and chunker services
        self.gcs_loader = GCSLoaderService()
        self.semantic_chunker = SemanticChunkerService()

    async def ingest(
        self,
        file_id: str,
        gcs_path: str,
        collection_name: str,
        chunk_size: int = 512,
        chunk_overlap: int = 50
    ) -> Dict[str, Any]:
        """Ingest document from GCS: load → chunk → embed → store.

        Args:
            file_id: Unique file identifier
            gcs_path: GCS path to file
            collection_name: Target collection name
            chunk_size: Size of text chunks
            chunk_overlap: Overlap between chunks

        Returns:
            Ingestion result with status and metrics

        Raises:
            Exception: If any step fails
        """
        logger.info(f"Starting ingestion for file {file_id} from {gcs_path}")

        try:
            # 1. Load document from GCS
            documents = await self.gcs_loader.load_from_gcs(gcs_path)
            logger.info(f"Loaded {len(documents)} document sections")

            # 2. Chunk documents
            chunks = await self.semantic_chunker.chunk_documents(
                documents=documents,
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap
            )
            logger.info(f"Created {len(chunks)} chunks")

            # 3. Embed chunks
            texts = [chunk["text"] for chunk in chunks]
            embeddings = await self.embedding_service.embed_batch_async(texts)
            logger.info(f"Generated {len(embeddings)} embeddings")

            # 4. Ensure collection exists
            exists = await self.vectordb_service.collection_exists(collection_name)
            if not exists:
                await self.vectordb_service.create_collection(
                    collection_name=collection_name,
                    vector_size=1024,  # BGE-M3 dimension
                    distance="cosine"
                )
                logger.info(f"Created collection: {collection_name}")

            # 5. Prepare payloads with metadata
            payloads = []
            for i, chunk in enumerate(chunks):
                payload = {
                    "text": chunk["text"],
                    "file_id": file_id,
                    "chunk_id": i,
                    "chunk_index": chunk.get("chunk_id", i),
                    "metadata": chunk.get("metadata", {})
                }
                payloads.append(payload)

            # 6. Store vectors in Qdrant
            ids = list(range(len(embeddings)))
            await self.vectordb_service.upsert_vectors(
                collection_name=collection_name,
                vectors=embeddings,
                payloads=payloads,
                ids=ids
            )
            logger.info(f"Stored {len(embeddings)} vectors in {collection_name}")

            return {
                "status": "success",
                "chunks_created": len(chunks),
                "collection_name": collection_name,
                "file_id": file_id
            }

        except Exception as e:
            logger.error(f"Ingestion failed for {file_id}: {e}", exc_info=True)
            raise
```

**TDD Cycle**:
```bash
# 1. Write tests (RED)
pytest tests/unit/test_orchestrator.py::test_orchestrator_ingest_pdf_success -v
# Expected: FAILED

# 2. Implement (GREEN)
pytest tests/unit/test_orchestrator.py::test_orchestrator_ingest_pdf_success -v
# Expected: PASSED ✅

# 3. Coverage
pytest tests/unit/test_orchestrator.py --cov=app.services.orchestrator --cov-report=term-missing
```

---

#### Task 2.2: Ingest Endpoint (TDD)

**Schema** (`app/models/schemas.py` - add):
```python
class IngestRequest(BaseModel):
    """Request model for async ingestion."""
    file_id: str = Field(..., description="File ID from upload")
    collection_name: str = Field(..., min_length=1, description="Target collection")
    chunk_size: int = Field(default=512, ge=100, le=2000, description="Chunk size")
    chunk_overlap: int = Field(default=50, ge=0, le=500, description="Chunk overlap")


class IngestStatusResponse(BaseModel):
    """Response model for ingestion status."""
    job_id: str = Field(..., description="Job identifier")
    file_id: str = Field(..., description="File identifier")
    status: str = Field(..., description="Job status: pending/processing/completed/failed")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage")
    message: str = Field(..., description="Status message")
    chunks_created: int = Field(default=0, description="Number of chunks created")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    created_at: str = Field(..., description="Job creation timestamp")
    updated_at: str = Field(..., description="Last update timestamp")
```

**Test First** (`tests/unit/test_ingest_endpoint.py`):
```python
"""Unit tests for ingest endpoint."""
import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock


@pytest.mark.asyncio
async def test_ingest_endpoint_starts_async_job():
    """POST /api/v1/ingest should create job and return job_id."""
    from app.main import app

    request_data = {
        "file_id": "file_123",
        "collection_name": "documents",
        "chunk_size": 512,
        "chunk_overlap": 50
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingest", json=request_data)

    assert response.status_code == 202  # Accepted
    body = response.json()
    assert "job_id" in body
    assert body["status"] == "processing"
    assert body["file_id"] == "file_123"


@pytest.mark.asyncio
async def test_ingest_endpoint_invalid_file_id():
    """Ingest with invalid file_id should return 404."""
    from app.main import app

    request_data = {
        "file_id": "invalid_file",
        "collection_name": "documents"
    }

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post("/api/v1/ingest", json=request_data)

    assert response.status_code == 404
    assert "file not found" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_status_endpoint_returns_job_details():
    """GET /api/v1/ingest/status/{job_id} should return job status."""
    from app.main import app

    # First create a job
    async with AsyncClient(app=app, base_url="http://test") as client:
        create_response = await client.post("/api/v1/ingest", json={
            "file_id": "file_123",
            "collection_name": "documents"
        })
        job_id = create_response.json()["job_id"]

        # Then check status
        status_response = await client.get(f"/api/v1/ingest/status/{job_id}")

    assert status_response.status_code == 200
    body = status_response.json()
    assert body["job_id"] == job_id
    assert "status" in body
    assert "progress" in body


@pytest.mark.asyncio
async def test_status_endpoint_nonexistent_job():
    """GET status for non-existent job should return 404."""
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.get("/api/v1/ingest/status/invalid_job_id")

    assert response.status_code == 404
    assert "job not found" in response.json()["detail"].lower()
```

**Implementation** (`app/main.py` - add endpoints):
```python
# Add to app/main.py

from fastapi import BackgroundTasks
from app.models.schemas import IngestRequest, IngestStatusResponse
from app.services.job_manager import JobManager, JobStatus

# Initialize job manager (add with other services)
job_manager = JobManager()


@app.post("/api/v1/ingest", response_model=IngestStatusResponse, status_code=202)
async def ingest_endpoint(
    request: IngestRequest,
    background_tasks: BackgroundTasks
):
    """Start async ingestion job.

    Args:
        request: Ingestion request with file_id and collection_name
        background_tasks: FastAPI background tasks

    Returns:
        Job details with job_id and initial status

    Raises:
        HTTPException: 404 if file not found
    """
    try:
        # 1. Validate file exists (check if we have GCS path)
        # For now, assume file_id is valid (can add DB check later)

        # 2. Create job
        job = job_manager.create_job(
            file_id=request.file_id,
            collection_name=request.collection_name
        )

        # 3. Start background task
        background_tasks.add_task(
            _process_ingestion,
            job.job_id,
            request.file_id,
            request.collection_name,
            request.chunk_size,
            request.chunk_overlap
        )

        # 4. Return job details
        return IngestStatusResponse(
            job_id=job.job_id,
            file_id=job.file_id,
            status=job.status.value,
            progress=job.progress,
            message="Ingestion started",
            chunks_created=0,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat()
        )

    except Exception as e:
        logger.error(f"Failed to start ingestion: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/v1/ingest/status/{job_id}", response_model=IngestStatusResponse)
async def get_ingest_status(job_id: str):
    """Get ingestion job status.

    Args:
        job_id: Job identifier

    Returns:
        Current job status and progress

    Raises:
        HTTPException: 404 if job not found
    """
    try:
        job = job_manager.get_job(job_id)

        return IngestStatusResponse(
            job_id=job.job_id,
            file_id=job.file_id,
            status=job.status.value,
            progress=job.progress,
            message=job.message,
            chunks_created=job.chunks_created,
            error=job.error,
            created_at=job.created_at.isoformat(),
            updated_at=job.updated_at.isoformat()
        )

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


async def _process_ingestion(
    job_id: str,
    file_id: str,
    collection_name: str,
    chunk_size: int,
    chunk_overlap: int
):
    """Background task to process ingestion.

    Args:
        job_id: Job identifier
        file_id: File identifier
        collection_name: Target collection
        chunk_size: Chunk size
        chunk_overlap: Chunk overlap
    """
    try:
        # Update to processing
        job_manager.update_job(
            job_id,
            status=JobStatus.PROCESSING,
            progress=10,
            message="Loading document from GCS"
        )

        # Get GCS path (you'll need to store this in upload response)
        # For now, construct it
        gcs_path = f"gs://intellirag-uploads/{file_id}"

        # Run ingestion through orchestrator
        result = await orchestrator.ingest(
            file_id=file_id,
            gcs_path=gcs_path,
            collection_name=collection_name,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        # Complete job
        job_manager.complete_job(
            job_id,
            chunks_created=result["chunks_created"],
            collection_name=collection_name
        )

    except Exception as e:
        logger.error(f"Ingestion job {job_id} failed: {e}", exc_info=True)
        job_manager.fail_job(job_id, error=str(e))
```

**TDD Cycle**:
```bash
# 1. Write tests (RED)
pytest tests/unit/test_ingest_endpoint.py -v
# Expected: FAILED

# 2. Implement (GREEN)
pytest tests/unit/test_ingest_endpoint.py -v
# Expected: PASSED ✅

# 3. Coverage
pytest tests/unit/test_ingest_endpoint.py --cov=app.main --cov-report=term-missing
```

---

### Day 3: Integration Tests

#### Task 3.1: E2E Ingestion Flow Test

**Integration Test** (`tests/integration/test_ingestion_flow.py`):
```python
"""Integration tests for complete ingestion pipeline."""
import pytest
import asyncio
import uuid
from pathlib import Path


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_ingestion_pipeline_pdf():
    """Test complete flow: Upload → Ingest → Query.

    Integration Test: Verifies full ingestion pipeline works end-to-end.
    Expected: Document is uploaded, processed, and queryable.
    """
    from httpx import AsyncClient
    from app.main import app

    collection_name = f"test_ingest_{uuid.uuid4()}"

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Step 1: Upload file
        test_pdf = Path("tests/fixtures/test-sample-1.pdf")
        with open(test_pdf, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            data = {"collection_name": collection_name}

            upload_response = await client.post(
                "/api/v1/upload",
                files=files,
                data=data
            )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]

        # Step 2: Start ingestion
        ingest_request = {
            "file_id": file_id,
            "collection_name": collection_name,
            "chunk_size": 512,
            "chunk_overlap": 50
        }

        ingest_response = await client.post(
            "/api/v1/ingest",
            json=ingest_request
        )

        assert ingest_response.status_code == 202
        ingest_data = ingest_response.json()
        job_id = ingest_data["job_id"]

        # Step 3: Poll for completion
        max_attempts = 30
        for attempt in range(max_attempts):
            status_response = await client.get(
                f"/api/v1/ingest/status/{job_id}"
            )

            assert status_response.status_code == 200
            status_data = status_response.json()

            if status_data["status"] == "completed":
                assert status_data["chunks_created"] > 0
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Ingestion failed: {status_data['error']}")

            await asyncio.sleep(1)
        else:
            pytest.fail("Ingestion did not complete within timeout")

        # Step 4: Query the ingested document
        query_request = {
            "query": "What is this document about?",
            "collection_name": collection_name,
            "top_k": 3
        }

        query_response = await client.post(
            "/api/v1/query",
            json=query_request
        )

        assert query_response.status_code == 200
        query_data = query_response.json()

        # Verify we got results
        assert len(query_data["sources"]) > 0
        assert query_data["answer"] is not None

        # Cleanup
        from app.services.vectordb import VectorDBService
        vectordb = VectorDBService(url="http://localhost:6333")
        await vectordb.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_ingestion_handles_unsupported_format():
    """Test ingestion rejects unsupported file formats."""
    from httpx import AsyncClient
    from app.main import app
    from io import BytesIO

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Try to upload unsupported file
        files = {"file": ("test.exe", BytesIO(b"fake exe content"), "application/x-executable")}
        data = {"collection_name": "test"}

        response = await client.post(
            "/api/v1/upload",
            files=files,
            data=data
        )

        assert response.status_code == 400
        assert "unsupported" in response.json()["detail"].lower()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_concurrent_ingestions():
    """Test multiple concurrent ingestion jobs."""
    from httpx import AsyncClient
    from app.main import app
    from pathlib import Path
    import asyncio

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Upload 3 files concurrently
        jobs = []

        for i in range(3):
            collection_name = f"test_concurrent_{uuid.uuid4()}"

            # Upload
            test_pdf = Path("tests/fixtures/test-sample-1.pdf")
            with open(test_pdf, "rb") as f:
                files = {"file": (f"test_{i}.pdf", f, "application/pdf")}
                data = {"collection_name": collection_name}

                upload_response = await client.post(
                    "/api/v1/upload",
                    files=files,
                    data=data
                )

            file_id = upload_response.json()["file_id"]

            # Start ingestion
            ingest_response = await client.post(
                "/api/v1/ingest",
                json={
                    "file_id": file_id,
                    "collection_name": collection_name
                }
            )

            job_id = ingest_response.json()["job_id"]
            jobs.append((job_id, collection_name))

        # Wait for all to complete
        for job_id, collection_name in jobs:
            max_attempts = 30
            completed = False

            for _ in range(max_attempts):
                status_response = await client.get(
                    f"/api/v1/ingest/status/{job_id}"
                )
                status_data = status_response.json()

                if status_data["status"] == "completed":
                    completed = True
                    break
                elif status_data["status"] == "failed":
                    pytest.fail(f"Job {job_id} failed: {status_data['error']}")

                await asyncio.sleep(1)

            assert completed, f"Job {job_id} did not complete"

            # Cleanup
            from app.services.vectordb import VectorDBService
            vectordb = VectorDBService(url="http://localhost:6333")
            await vectordb.delete_collection(collection_name)
```

**Run Integration Tests**:
```bash
# Ensure services are running
docker-compose up -d qdrant

# Run integration tests
pytest tests/integration/test_ingestion_flow.py -v --timeout=60

# Expected: All tests PASS ✅
```

---

## 4. Phase 2: Enhanced Observability (Days 4-5)

### Day 4: OpenTelemetry + Jaeger Tracing

#### Task 4.1: OpenTelemetry Setup (TDD)

**Dependencies** (add to `pyproject.toml`):
```toml
[project]
dependencies = [
    # ... existing dependencies ...
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-instrumentation-fastapi>=0.41b0",
    "opentelemetry-instrumentation-httpx>=0.41b0",
    "opentelemetry-exporter-jaeger>=1.20.0",
]
```

**Test First** (`tests/unit/test_tracing_middleware.py`):
```python
"""Unit tests for OpenTelemetry tracing middleware."""
import pytest
from unittest.mock import Mock, patch
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


def test_tracing_middleware_creates_span():
    """Tracing middleware should create span for each request."""
    from app.api.middleware.tracing import setup_tracing
    from fastapi import FastAPI

    app = FastAPI()
    tracer = setup_tracing(app, service_name="test-service")

    # Create in-memory exporter for testing
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))

    # Simulate request
    with tracer.start_as_current_span("test_span") as span:
        span.set_attribute("test.key", "test.value")

    # Verify span was created
    spans = exporter.get_finished_spans()
    assert len(spans) == 1
    assert spans[0].name == "test_span"
    assert spans[0].attributes["test.key"] == "test.value"


def test_trace_context_propagation():
    """Trace context should propagate across async calls."""
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider

    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)

    # Create parent span
    with tracer.start_as_current_span("parent") as parent:
        parent_ctx = parent.get_span_context()

        # Create child span
        with tracer.start_as_current_span("child") as child:
            child_ctx = child.get_span_context()

            # Verify trace ID matches (context propagated)
            assert child_ctx.trace_id == parent_ctx.trace_id
            assert child_ctx.span_id != parent_ctx.span_id


def test_logging_includes_trace_id():
    """Logs should include trace_id from span context."""
    from app.core.logging import get_logger
    from opentelemetry import trace
    import logging

    logger = get_logger(__name__)
    tracer = trace.get_tracer(__name__)

    # Create span
    with tracer.start_as_current_span("test") as span:
        span_ctx = span.get_span_context()
        trace_id = format(span_ctx.trace_id, '032x')

        # Log with trace context
        with patch.object(logger, 'info') as mock_log:
            logger.info("test message", extra={'trace_id': trace_id})

            # Verify trace_id in log
            mock_log.assert_called_once()
            call_args = mock_log.call_args
            assert 'trace_id' in call_args[1].get('extra', {})
```

**Implementation** (`app/api/middleware/tracing.py`):
```python
"""OpenTelemetry distributed tracing middleware."""
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
from fastapi import FastAPI
import os
import logging


logger = logging.getLogger(__name__)


def setup_tracing(app: FastAPI, service_name: str = "intellirag") -> trace.Tracer:
    """Configure OpenTelemetry tracing with Jaeger exporter.

    Args:
        app: FastAPI application instance
        service_name: Service name for tracing

    Returns:
        Tracer instance
    """
    # Create resource with service name
    resource = Resource.create({SERVICE_NAME: service_name})

    # Set up tracer provider
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # Configure Jaeger exporter
    jaeger_host = os.getenv("JAEGER_AGENT_HOST", "localhost")
    jaeger_port = int(os.getenv("JAEGER_AGENT_PORT", "6831"))

    jaeger_exporter = JaegerExporter(
        agent_host_name=jaeger_host,
        agent_port=jaeger_port,
    )

    # Add span processor
    provider.add_span_processor(BatchSpanProcessor(jaeger_exporter))

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Instrument HTTP client (for outgoing requests)
    HTTPXClientInstrumentor().instrument()

    logger.info(f"Tracing configured: service={service_name}, jaeger={jaeger_host}:{jaeger_port}")

    return trace.get_tracer(__name__)


def get_current_trace_id() -> str:
    """Get current trace ID from span context.

    Returns:
        Trace ID as hex string, or empty string if no active span
    """
    span = trace.get_current_span()
    if span and span.is_recording():
        span_ctx = span.get_span_context()
        return format(span_ctx.trace_id, '032x')
    return ""
```

**Update Logging** (`app/core/logging.py` - enhance existing):
```python
# Add to existing logging.py

from app.api.middleware.tracing import get_current_trace_id


class StructuredJSONFormatter(logging.Formatter):
    """Custom formatter that outputs structured JSON logs with trace_id."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with trace context."""
        log_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'trace_id': get_current_trace_id(),  # Add trace ID
        }

        # Add extra fields if present
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)

        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        return json.dumps(log_data)
```

**TDD Cycle**:
```bash
# 1. Install dependencies
uv pip install opentelemetry-api opentelemetry-sdk opentelemetry-instrumentation-fastapi opentelemetry-exporter-jaeger

# 2. Write tests (RED)
pytest tests/unit/test_tracing_middleware.py -v
# Expected: FAILED

# 3. Implement (GREEN)
pytest tests/unit/test_tracing_middleware.py -v
# Expected: PASSED ✅

# 4. Coverage
pytest tests/unit/test_tracing_middleware.py --cov=app.api.middleware.tracing --cov-report=term-missing
```

---

#### Task 4.2: Instrument Services with Tracing

**Test First** (`tests/unit/test_orchestrator_tracing.py`):
```python
"""Unit tests for orchestrator tracing instrumentation."""
import pytest
from unittest.mock import patch, AsyncMock
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter


@pytest.mark.asyncio
async def test_orchestrator_query_creates_spans():
    """Query should create spans for each stage."""
    from app.services.orchestrator import OrchestratorService

    # Setup tracing
    trace.set_tracer_provider(TracerProvider())
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))

    orchestrator = OrchestratorService()

    with patch.object(orchestrator.query_router_service, 'classify_and_route') as mock_route, \
         patch.object(orchestrator.rag_pipeline, 'process_query') as mock_rag:

        mock_route.return_value = {
            "needs_rag": True,
            "query_type": "rag"
        }
        mock_rag.return_value = {
            "answer": "Test answer",
            "sources": []
        }

        # Execute query
        await orchestrator.query(query="test query", collection_name="docs")

        # Verify spans were created
        spans = exporter.get_finished_spans()
        span_names = [span.name for span in spans]

        assert "orchestrator.query" in span_names
        assert "query_router.classify" in span_names
        assert "rag_pipeline.process" in span_names


@pytest.mark.asyncio
async def test_ingest_creates_detailed_spans():
    """Ingest should create spans with detailed attributes."""
    from app.services.orchestrator import OrchestratorService

    trace.set_tracer_provider(TracerProvider())
    exporter = InMemorySpanExporter()
    trace.get_tracer_provider().add_span_processor(SimpleSpanProcessor(exporter))

    orchestrator = OrchestratorService()

    with patch.object(orchestrator.gcs_loader, 'load_from_gcs') as mock_load, \
         patch.object(orchestrator.semantic_chunker, 'chunk_documents') as mock_chunk, \
         patch.object(orchestrator.embedding_service, 'embed_batch_async') as mock_embed, \
         patch.object(orchestrator.vectordb_service, 'upsert_vectors') as mock_upsert, \
         patch.object(orchestrator.vectordb_service, 'collection_exists') as mock_exists:

        mock_load.return_value = [{"text": "content"}]
        mock_chunk.return_value = [{"text": "chunk1"}, {"text": "chunk2"}]
        mock_embed.return_value = [[0.1] * 1024, [0.2] * 1024]
        mock_upsert.return_value = None
        mock_exists.return_value = True

        await orchestrator.ingest(
            file_id="file_123",
            gcs_path="gs://bucket/file.pdf",
            collection_name="docs"
        )

        # Verify spans
        spans = exporter.get_finished_spans()
        span_names = [span.name for span in spans]

        assert "orchestrator.ingest" in span_names
        assert "gcs_loader.load" in span_names
        assert "semantic_chunker.chunk" in span_names
        assert "embedding.embed_batch" in span_names
        assert "vectordb.upsert" in span_names

        # Verify attributes
        ingest_span = next(s for s in spans if s.name == "orchestrator.ingest")
        assert ingest_span.attributes["file_id"] == "file_123"
        assert ingest_span.attributes["collection_name"] == "docs"
```

**Implementation** (`app/services/orchestrator.py` - enhance with tracing):
```python
# Update existing orchestrator.py

from opentelemetry import trace
from app.api.middleware.tracing import get_current_trace_id

# Get tracer
tracer = trace.get_tracer(__name__)


class OrchestratorService:
    # ... existing init ...

    async def query(self, query: str, collection_name: str, top_k: int = 5):
        """Process query with distributed tracing."""
        with tracer.start_as_current_span("orchestrator.query") as span:
            span.set_attribute("query.length", len(query))
            span.set_attribute("collection", collection_name)
            span.set_attribute("top_k", top_k)

            logger.info(
                f"Processing query",
                extra={'trace_id': get_current_trace_id(), 'query_length': len(query)}
            )

            try:
                # Classification
                with tracer.start_as_current_span("query_router.classify") as classify_span:
                    routing_decision = await self.query_router_service.classify_and_route(
                        query=query,
                        collection_name=collection_name
                    )
                    classify_span.set_attribute("needs_rag", routing_decision["needs_rag"])
                    classify_span.set_attribute("query_type", routing_decision["query_type"])

                # RAG processing if needed
                if routing_decision["needs_rag"]:
                    with tracer.start_as_current_span("rag_pipeline.process") as rag_span:
                        result = await self.rag_pipeline.process_query(
                            query=query,
                            collection_name=collection_name,
                            top_k=top_k
                        )
                        rag_span.set_attribute("sources_count", len(result.get("sources", [])))
                        span.set_attribute("used_rag", True)
                else:
                    # Direct answer
                    result = await self._direct_answer(query)
                    span.set_attribute("used_rag", False)

                span.set_attribute("answer_length", len(result.get("answer", "")))
                return result

            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                raise

    async def ingest(self, file_id: str, gcs_path: str, collection_name: str, ...):
        """Ingest with distributed tracing."""
        with tracer.start_as_current_span("orchestrator.ingest") as span:
            span.set_attribute("file_id", file_id)
            span.set_attribute("gcs_path", gcs_path)
            span.set_attribute("collection_name", collection_name)

            logger.info(
                f"Starting ingestion",
                extra={'trace_id': get_current_trace_id(), 'file_id': file_id}
            )

            try:
                # Load
                with tracer.start_as_current_span("gcs_loader.load") as load_span:
                    documents = await self.gcs_loader.load_from_gcs(gcs_path)
                    load_span.set_attribute("documents_count", len(documents))

                # Chunk
                with tracer.start_as_current_span("semantic_chunker.chunk") as chunk_span:
                    chunks = await self.semantic_chunker.chunk_documents(documents, ...)
                    chunk_span.set_attribute("chunks_count", len(chunks))

                # Embed
                with tracer.start_as_current_span("embedding.embed_batch") as embed_span:
                    texts = [chunk["text"] for chunk in chunks]
                    embeddings = await self.embedding_service.embed_batch_async(texts)
                    embed_span.set_attribute("embeddings_count", len(embeddings))
                    embed_span.set_attribute("embedding_dimension", len(embeddings[0]))

                # Store
                with tracer.start_as_current_span("vectordb.upsert") as upsert_span:
                    # ... existing upsert code ...
                    upsert_span.set_attribute("vectors_count", len(embeddings))
                    upsert_span.set_attribute("collection", collection_name)

                span.set_attribute("status", "success")
                return {"status": "success", "chunks_created": len(chunks), ...}

            except Exception as e:
                span.record_exception(e)
                span.set_status(trace.StatusCode.ERROR, str(e))
                raise
```

**Similarly instrument other services** (`app/services/embedding.py`, `app/services/vectordb.py`, etc.):
```python
# Add tracing to critical operations in each service

from opentelemetry import trace
tracer = trace.get_tracer(__name__)

class EmbeddingService:
    async def embed_batch_async(self, texts: List[str]):
        with tracer.start_as_current_span("embedding.encode") as span:
            span.set_attribute("batch_size", len(texts))
            span.set_attribute("avg_text_length", sum(len(t) for t in texts) / len(texts))

            # ... existing code ...

            span.set_attribute("embedding_dimension", len(embeddings[0]))
            return embeddings
```

**TDD Cycle**:
```bash
# 1. Write tests (RED)
pytest tests/unit/test_orchestrator_tracing.py -v
# Expected: FAILED

# 2. Implement (GREEN)
pytest tests/unit/test_orchestrator_tracing.py -v
# Expected: PASSED ✅

# 3. Coverage
pytest tests/unit/test_orchestrator_tracing.py --cov=app.services.orchestrator --cov-report=term-missing
```

---

### Day 5: Enhanced Metrics + Integration

#### Task 5.1: Ingestion Pipeline Metrics

**Test First** (`tests/unit/test_ingestion_metrics.py`):
```python
"""Unit tests for ingestion pipeline metrics."""
import pytest
from prometheus_client import REGISTRY


def test_ingestion_metrics_registered():
    """Ingestion metrics should be registered in Prometheus."""
    from app.api.middleware.metrics import (
        ingestion_jobs_total,
        ingestion_job_duration_seconds,
        ingestion_chunks_created,
        ingestion_file_size_bytes,
        document_processing_duration_seconds
    )

    # Verify metrics exist
    assert ingestion_jobs_total is not None
    assert ingestion_job_duration_seconds is not None
    assert ingestion_chunks_created is not None


@pytest.mark.asyncio
async def test_ingestion_records_metrics():
    """Ingest endpoint should record metrics."""
    from app.main import app
    from httpx import AsyncClient
    from unittest.mock import patch

    initial_count = ingestion_jobs_total._value.get()

    async with AsyncClient(app=app, base_url="http://test") as client:
        with patch("app.services.orchestrator.OrchestratorService.ingest") as mock_ingest:
            mock_ingest.return_value = {"status": "success", "chunks_created": 10}

            response = await client.post("/api/v1/ingest", json={
                "file_id": "file_123",
                "collection_name": "docs"
            })

    # Verify metric increased
    final_count = ingestion_jobs_total._value.get()
    assert final_count > initial_count
```

**Implementation** (`app/api/middleware/metrics.py` - add to existing):
```python
# Add to existing metrics.py

# Ingestion Pipeline Metrics
ingestion_jobs_total = Counter(
    'ingestion_jobs_total',
    'Total number of ingestion jobs',
    ['status', 'file_type']  # status: started, completed, failed
)

ingestion_job_duration_seconds = Histogram(
    'ingestion_job_duration_seconds',
    'Ingestion job processing time',
    ['file_type'],
    buckets=[1, 5, 10, 30, 60, 120, 300, 600]
)

ingestion_chunks_created = Histogram(
    'ingestion_chunks_created',
    'Number of chunks created per document',
    ['file_type'],
    buckets=[1, 10, 50, 100, 500, 1000, 5000]
)

ingestion_file_size_bytes = Histogram(
    'ingestion_file_size_bytes',
    'Size of ingested files',
    ['file_type'],
    buckets=[1024, 10*1024, 100*1024, 1024*1024, 10*1024*1024, 50*1024*1024]
)

document_processing_duration_seconds = Histogram(
    'document_processing_duration_seconds',
    'Time spent in each processing stage',
    ['stage'],  # load, chunk, embed, store
    buckets=[0.1, 0.5, 1.0, 5.0, 10.0, 30.0, 60.0]
)
```

**Update endpoints to record metrics** (`app/main.py`):
```python
# In upload_endpoint
from app.api.middleware.metrics import ingestion_jobs_total, ingestion_file_size_bytes
import time

@app.post("/api/v1/upload", ...)
async def upload_endpoint(...):
    start_time = time.time()

    try:
        # ... existing upload code ...

        # Record metrics
        file_ext = file.filename.split('.')[-1].lower()
        ingestion_file_size_bytes.labels(file_type=file_ext).observe(len(content))
        ingestion_jobs_total.labels(status='uploaded', file_type=file_ext).inc()

        return UploadResponse(...)

    except Exception as e:
        ingestion_jobs_total.labels(status='upload_failed', file_type='unknown').inc()
        raise


# In _process_ingestion background task
async def _process_ingestion(...):
    start_time = time.time()
    file_ext = file_id.split('.')[-1] if '.' in file_id else 'unknown'

    try:
        # ... existing ingestion code ...

        # Record success metrics
        duration = time.time() - start_time
        ingestion_job_duration_seconds.labels(file_type=file_ext).observe(duration)
        ingestion_chunks_created.labels(file_type=file_ext).observe(result["chunks_created"])
        ingestion_jobs_total.labels(status='completed', file_type=file_ext).inc()

    except Exception as e:
        ingestion_jobs_total.labels(status='failed', file_type=file_ext).inc()
        raise
```

---

#### Task 5.2: Integration Test for Observability

**Test** (`tests/integration/test_observability_integration.py`):
```python
"""Integration tests for observability stack."""
import pytest
from httpx import AsyncClient
import time


@pytest.mark.integration
@pytest.mark.asyncio
async def test_tracing_propagates_through_pipeline():
    """Trace context should propagate through full pipeline."""
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make query request with trace header
        response = await client.post(
            "/api/v1/query",
            json={"query": "test", "collection_name": "docs"},
            headers={"traceparent": "00-0123456789abcdef0123456789abcdef-0123456789abcdef-01"}
        )

        # Verify response includes trace headers
        assert response.status_code == 200
        # Trace ID should be in logs (check manually or with log aggregation)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_metrics_exported_correctly():
    """Metrics endpoint should expose all custom metrics."""
    from app.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        # Make some requests to generate metrics
        await client.post("/api/v1/query", json={"query": "test", "collection_name": "docs"})

        # Fetch metrics
        metrics_response = await client.get("/metrics")

        assert metrics_response.status_code == 200
        metrics_text = metrics_response.text

        # Verify key metrics exist
        assert "http_requests_total" in metrics_text
        assert "http_request_duration_seconds" in metrics_text
        assert "query_classification_total" in metrics_text
        assert "rag_query_duration_seconds" in metrics_text
        assert "ingestion_jobs_total" in metrics_text


@pytest.mark.integration
@pytest.mark.asyncio
async def test_logs_include_trace_id():
    """Logs should include trace_id for correlation."""
    from app.main import app
    import logging
    from io import StringIO

    # Capture logs
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logging.getLogger().addHandler(handler)

    async with AsyncClient(app=app, base_url="http://test") as client:
        await client.post("/api/v1/query", json={"query": "test", "collection_name": "docs"})

    # Check logs contain trace_id
    log_output = log_stream.getvalue()
    assert "trace_id" in log_output
```

---

## 5. Phase 3: Integration & Polish (Days 6-7)

### Day 6: E2E Testing & Documentation

#### Task 6.1: Comprehensive E2E Test

**Test** (`tests/integration/test_complete_system.py`):
```python
"""End-to-end test of complete IntelliRAG system."""
import pytest
import asyncio
import uuid
from pathlib import Path


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_complete_intellirag_system():
    """Test complete system: Upload → Ingest → Monitor → Query → Observe.

    This test verifies:
    1. File upload works
    2. Async ingestion processes correctly
    3. Metrics are recorded
    4. Tracing is active
    5. Query retrieves ingested content
    6. All observability data is accessible
    """
    from httpx import AsyncClient
    from app.main import app

    collection_name = f"test_complete_{uuid.uuid4()}"

    async with AsyncClient(app=app, base_url="http://test", timeout=120.0) as client:
        # STEP 1: Upload document
        print("\n[1/6] Uploading document...")
        test_pdf = Path("tests/fixtures/test-sample-1.pdf")
        with open(test_pdf, "rb") as f:
            files = {"file": ("test.pdf", f, "application/pdf")}
            data = {"collection_name": collection_name}

            upload_response = await client.post(
                "/api/v1/upload",
                files=files,
                data=data
            )

        assert upload_response.status_code == 200
        upload_data = upload_response.json()
        file_id = upload_data["file_id"]
        print(f"✅ Uploaded: file_id={file_id}")

        # STEP 2: Start ingestion
        print("\n[2/6] Starting ingestion...")
        ingest_response = await client.post(
            "/api/v1/ingest",
            json={
                "file_id": file_id,
                "collection_name": collection_name,
                "chunk_size": 512,
                "chunk_overlap": 50
            }
        )

        assert ingest_response.status_code == 202
        job_id = ingest_response.json()["job_id"]
        print(f"✅ Ingestion started: job_id={job_id}")

        # STEP 3: Monitor ingestion progress
        print("\n[3/6] Monitoring ingestion progress...")
        max_attempts = 60
        for attempt in range(max_attempts):
            status_response = await client.get(
                f"/api/v1/ingest/status/{job_id}"
            )

            assert status_response.status_code == 200
            status_data = status_response.json()

            print(f"  Progress: {status_data['progress']}% - {status_data['message']}")

            if status_data["status"] == "completed":
                print(f"✅ Ingestion completed: {status_data['chunks_created']} chunks")
                chunks_created = status_data["chunks_created"]
                break
            elif status_data["status"] == "failed":
                pytest.fail(f"Ingestion failed: {status_data['error']}")

            await asyncio.sleep(2)
        else:
            pytest.fail("Ingestion timeout")

        # STEP 4: Check metrics
        print("\n[4/6] Checking metrics...")
        metrics_response = await client.get("/metrics")
        assert metrics_response.status_code == 200
        metrics_text = metrics_response.text

        # Verify ingestion metrics
        assert "ingestion_jobs_total" in metrics_text
        assert "ingestion_chunks_created" in metrics_text
        print("✅ Metrics recorded")

        # STEP 5: Query ingested content
        print("\n[5/6] Querying ingested content...")
        query_response = await client.post(
            "/api/v1/query",
            json={
                "query": "What is this document about?",
                "collection_name": collection_name,
                "top_k": 3
            }
        )

        assert query_response.status_code == 200
        query_data = query_response.json()

        assert len(query_data["sources"]) > 0
        assert query_data["answer"] is not None
        print(f"✅ Query successful: {len(query_data['sources'])} sources retrieved")
        print(f"   Answer: {query_data['answer'][:100]}...")

        # STEP 6: Verify observability
        print("\n[6/6] Verifying observability...")

        # Check metrics again for query
        metrics_response = await client.get("/metrics")
        metrics_text = metrics_response.text
        assert "query_classification_total" in metrics_text
        assert "rag_query_duration_seconds" in metrics_text
        print("✅ Query metrics recorded")

        # Cleanup
        print("\n[Cleanup] Removing test collection...")
        from app.services.vectordb import VectorDBService
        vectordb = VectorDBService(url="http://localhost:6333")
        await vectordb.delete_collection(collection_name)
        print("✅ Test completed successfully!")
```

Run:
```bash
pytest tests/integration/test_complete_system.py -v -s --timeout=180
```

---

#### Task 6.2: Update Documentation

**Create/Update Files**:

1. `docs/api/ingestion-api.md` - Document all 3 endpoints
2. `docs/observability/tracing-guide.md` - How to use Jaeger
3. `docs/observability/metrics-guide.md` - All available metrics
4. Update `README.md` - Add observability section

---

### Day 7: Performance Testing & Final Integration

#### Task 7.1: Performance/Load Testing

**Test** (`tests/integration/test_performance.py`):
```python
"""Performance and load tests."""
import pytest
import asyncio
import time
from httpx import AsyncClient


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_concurrent_queries_performance():
    """Test system handles concurrent queries efficiently."""
    from app.main import app

    async def make_query(client, query_num):
        start = time.time()
        response = await client.post(
            "/api/v1/query",
            json={
                "query": f"test query {query_num}",
                "collection_name": "docs"
            }
        )
        duration = time.time() - start
        return response.status_code, duration

    async with AsyncClient(app=app, base_url="http://test", timeout=30.0) as client:
        # Run 20 concurrent queries
        tasks = [make_query(client, i) for i in range(20)]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        successful = sum(1 for r in results if isinstance(r, tuple) and r[0] == 200)
        avg_duration = sum(r[1] for r in results if isinstance(r, tuple)) / len(results)

        print(f"\nConcurrent queries: {successful}/{len(results)} successful")
        print(f"Average duration: {avg_duration:.2f}s")

        assert successful >= 18  # Allow some failures
        assert avg_duration < 5.0  # Average under 5s


@pytest.mark.integration
@pytest.mark.slow
@pytest.mark.asyncio
async def test_ingestion_throughput():
    """Test ingestion can handle multiple files."""
    from app.main import app
    from pathlib import Path

    async with AsyncClient(app=app, base_url="http://test", timeout=120.0) as client:
        # Upload 5 files
        job_ids = []
        test_pdf = Path("tests/fixtures/test-sample-1.pdf")

        for i in range(5):
            # Upload
            with open(test_pdf, "rb") as f:
                files = {"file": (f"test_{i}.pdf", f, "application/pdf")}
                data = {"collection_name": f"perf_test_{i}"}

                upload_response = await client.post(
                    "/api/v1/upload",
                    files=files,
                    data=data
                )

            file_id = upload_response.json()["file_id"]

            # Start ingestion
            ingest_response = await client.post(
                "/api/v1/ingest",
                json={"file_id": file_id, "collection_name": f"perf_test_{i}"}
            )

            job_ids.append(ingest_response.json()["job_id"])

        # Wait for all to complete
        completed = 0
        max_wait = 180  # 3 minutes
        start = time.time()

        while completed < len(job_ids) and (time.time() - start) < max_wait:
            for job_id in job_ids:
                status_response = await client.get(f"/api/v1/ingest/status/{job_id}")
                if status_response.json()["status"] == "completed":
                    completed += 1

            await asyncio.sleep(2)

        print(f"\nIngestion throughput: {completed}/{len(job_ids)} completed in {time.time()-start:.1f}s")
        assert completed == len(job_ids)
```

---

#### Task 7.2: Final Integration & Cleanup

**Tasks**:
1. Run full test suite
2. Check coverage
3. Update environment variables
4. Create `.env.example`
5. Update deployment docs
6. Create troubleshooting guide

**Commands**:
```bash
# Full test suite
pytest tests/ -v --cov=app --cov-report=html --cov-report=term

# Coverage report
open htmlcov/index.html

# Check observability
docker-compose up -d jaeger
# Open Jaeger UI: http://localhost:16686
```

---

## 6. Testing Strategy

### Unit Tests (>80% coverage required)
- All services individually tested
- Mocked dependencies
- Fast execution (<1s each)
- TDD: Write test first, see it fail, implement, see it pass

### Integration Tests
- Real services (Qdrant, embeddings)
- Test service interactions
- Moderate execution time (5-30s)

### E2E Tests
- Complete workflows
- All components working together
- Slower execution (30s-2min)

### Performance Tests
- Concurrency handling
- Throughput measurement
- Load testing

---

## 7. Dependencies & Requirements

### Python Packages (add to pyproject.toml):
```toml
dependencies = [
    # ... existing ...
    "opentelemetry-api>=1.20.0",
    "opentelemetry-sdk>=1.20.0",
    "opentelemetry-instrumentation-fastapi>=0.41b0",
    "opentelemetry-instrumentation-httpx>=0.41b0",
    "opentelemetry-exporter-jaeger>=1.20.0",
]
```

### External Services:
- **Qdrant**: Vector database (already configured)
- **Jaeger**: Distributed tracing
  ```bash
  docker run -d --name jaeger \
    -p 16686:16686 \
    -p 6831:6831/udp \
    jaegertracing/all-in-one:latest
  ```
- **Prometheus**: Metrics (for production)
- **Grafana**: Visualization (for production)

### Environment Variables:
```bash
# .env
JAEGER_AGENT_HOST=localhost
JAEGER_AGENT_PORT=6831
GCS_BUCKET_NAME=intellirag-uploads
GCS_PROJECT_ID=your-project-id
QDRANT_URL=http://localhost:6333
VLLM_BASE_URL=http://localhost:8000/v1
LOG_LEVEL=INFO
```

---

## 8. Risk Mitigation

### Technical Risks:

1. **Risk**: Background task failures not visible
   - **Mitigation**: Comprehensive job state tracking, error logging, monitoring

2. **Risk**: Trace context loss across async boundaries
   - **Mitigation**: Proper OpenTelemetry instrumentation, context propagation testing

3. **Risk**: Performance degradation with tracing overhead
   - **Mitigation**: Sampling configuration, async span export, benchmarking

4. **Risk**: GCS upload failures
   - **Mitigation**: Retry logic, exponential backoff, clear error messages

5. **Risk**: Concurrent ingestion conflicts
   - **Mitigation**: Job queue management, collection existence checks

### Process Risks:

1. **Risk**: Test coverage below 80%
   - **Mitigation**: TDD enforcement, coverage checks in CI, incremental testing

2. **Risk**: Breaking existing query pipeline
   - **Mitigation**: Comprehensive regression tests, backward compatibility checks

---

## 9. Success Criteria

### Functional Requirements:
- [ ] Upload endpoint accepts files, validates, uploads to GCS
- [ ] Ingest endpoint creates jobs, processes async
- [ ] Status endpoint shows real-time progress
- [ ] Documents are chunked, embedded, stored in Qdrant
- [ ] Query endpoint retrieves ingested documents
- [ ] Error handling for all failure scenarios

### Observability Requirements:
- [ ] OpenTelemetry tracing configured with Jaeger
- [ ] Trace ID propagates through entire request
- [ ] Logs include trace_id for correlation
- [ ] All metrics exported to /metrics endpoint
- [ ] Ingestion metrics (jobs, duration, chunks, file size)
- [ ] Query metrics (classification, retrieval, LLM)
- [ ] Service-level tracing (spans for each operation)

### Quality Requirements:
- [ ] Test coverage >80%
- [ ] All unit tests pass
- [ ] All integration tests pass
- [ ] E2E test completes successfully
- [ ] Performance tests meet targets (20 concurrent queries)
- [ ] Documentation complete and accurate

---

## 10. TODO Checklist

### Phase 1: Ingestion Pipeline (Days 1-3)

**Day 1: Job Management + Upload**
- [ ] Write tests for JobManager (TDD RED)
- [ ] Implement JobManager service (TDD GREEN)
- [ ] Verify tests pass, check coverage (TDD REFACTOR)
- [ ] Add UploadRequest/UploadResponse schemas
- [ ] Write tests for upload endpoint (TDD RED)
- [ ] Implement upload endpoint (TDD GREEN)
- [ ] Test file validation, size limits, GCS upload
- [ ] Coverage check (>80%)

**Day 2: Ingest Endpoint + Orchestrator**
- [ ] Write tests for orchestrator.ingest() (TDD RED)
- [ ] Implement orchestrator.ingest() method (TDD GREEN)
- [ ] Test load, chunk, embed, store flow
- [ ] Add IngestRequest/IngestStatusResponse schemas
- [ ] Write tests for ingest endpoint (TDD RED)
- [ ] Implement ingest endpoint with background task (TDD GREEN)
- [ ] Implement status endpoint
- [ ] Test async job processing
- [ ] Coverage check (>80%)

**Day 3: Integration Tests**
- [ ] Write E2E ingestion test (upload → ingest → query)
- [ ] Test concurrent ingestions
- [ ] Test error handling (invalid files, parsing errors)
- [ ] Verify all integration tests pass
- [ ] Fix any issues found
- [ ] Coverage report for entire ingestion pipeline

### Phase 2: Enhanced Observability (Days 4-5)

**Day 4: OpenTelemetry + Tracing**
- [ ] Add OpenTelemetry dependencies
- [ ] Write tests for tracing middleware (TDD RED)
- [ ] Implement tracing middleware (TDD GREEN)
- [ ] Configure Jaeger exporter
- [ ] Update logging to include trace_id
- [ ] Write tests for orchestrator tracing (TDD RED)
- [ ] Instrument orchestrator.query() with spans (TDD GREEN)
- [ ] Instrument orchestrator.ingest() with spans (TDD GREEN)
- [ ] Add span attributes (file_id, collection, etc.)
- [ ] Test trace context propagation
- [ ] Coverage check

**Day 5: Enhanced Metrics + Integration**
- [ ] Add ingestion metrics definitions
- [ ] Write tests for metrics recording (TDD RED)
- [ ] Instrument upload endpoint with metrics (TDD GREEN)
- [ ] Instrument ingest background task with metrics (TDD GREEN)
- [ ] Instrument document processing stages (TDD GREEN)
- [ ] Write observability integration test
- [ ] Test metrics export at /metrics
- [ ] Test trace ID in logs
- [ ] Verify Jaeger UI shows traces
- [ ] Coverage check

### Phase 3: Integration & Polish (Days 6-7)

**Day 6: E2E Testing + Documentation**
- [ ] Write comprehensive E2E system test
- [ ] Run full test suite, ensure all pass
- [ ] Generate coverage report (verify >80%)
- [ ] Create `docs/api/ingestion-api.md`
- [ ] Create `docs/observability/tracing-guide.md`
- [ ] Create `docs/observability/metrics-guide.md`
- [ ] Update README.md with observability section
- [ ] Create troubleshooting guide

**Day 7: Performance + Final Integration**
- [ ] Write performance tests (concurrent queries)
- [ ] Write load test (multiple ingestions)
- [ ] Run performance tests, document results
- [ ] Create `.env.example` with all variables
- [ ] Test with Jaeger running locally
- [ ] Final integration: Upload → Ingest → Monitor → Query
- [ ] Verify all metrics in Prometheus format
- [ ] Verify all traces in Jaeger
- [ ] Final test suite run
- [ ] Generate final coverage report
- [ ] Code review and cleanup
- [ ] **READY FOR PRODUCTION** 🎉

---

## Implementation Notes

### TDD Workflow (MANDATORY for every task):
```bash
# 1. RED: Write failing test
pytest tests/unit/test_<component>.py::<test_name> -v
# Expected: FAILED ❌

# 2. GREEN: Implement minimal solution
vim app/services/<component>.py
pytest tests/unit/test_<component>.py::<test_name> -v
# Expected: PASSED ✅

# 3. REFACTOR: Improve code quality
pytest tests/unit/test_<component>.py -v --cov=app.services.<component>
# Target: >80% coverage

# 4. Commit only when tests pass
git add tests/unit/test_<component>.py app/services/<component>.py
git commit -m "feat(component): add functionality with tests"
```

### Key Design Decisions:

1. **Three-endpoint design**: Separates upload, processing, and monitoring for better async handling
2. **In-memory job state**: Simple, fast, no Redis dependency (can upgrade later)
3. **Background tasks**: FastAPI's built-in BackgroundTasks (good for moderate load)
4. **Jaeger for tracing**: Mature, easy local dev, matches documentation
5. **Defer Evidently**: Focus on core pipelines first, add drift monitoring in Phase 2
6. **OpenTelemetry**: Industry standard, supports multiple backends

### Performance Considerations:

- Background task processing allows API to return quickly
- Job TTL prevents memory growth (1 hour default)
- Batch embedding for efficiency
- Async operations throughout pipeline
- Trace sampling for production (configure later)

### Security Considerations:

- File type validation before upload
- File size limits (50MB default)
- GCS path validation
- Collection name sanitization
- No secrets in logs or traces

---

## Next Steps After Completion

Once this plan is complete, the system will have:
- ✅ Full ingestion pipeline with 3-endpoint async design
- ✅ Complete query/RAG pipeline with LangGraph routing
- ✅ Distributed tracing with OpenTelemetry + Jaeger
- ✅ Comprehensive metrics for Prometheus
- ✅ Structured logging with trace correlation
- ✅ >80% test coverage
- ✅ Production-ready quality

**Future enhancements** (Phase 2+):
- Evidently data drift monitoring
- Persistent job queue (Redis/Celery)
- Grafana dashboards
- Alert rules
- RAGAS continuous evaluation
- Multi-modal ingestion (images, tables)
- Kubernetes deployment

---

**Document Status**: ✅ Ready for Implementation
**Created**: 2025-10-28
**Timeline**: 5-7 days
**Approach**: Test-Driven Development (TDD)
**Coverage Target**: >80%
