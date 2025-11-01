# Phase 5: Critical Improvements & Recommendations

**Document Version:** 1.0  
**Date:** 2025-10-20  
**Purpose:** Production-ready enhancements for Phase 5 Implementation Plan  
**Status:** 🔴 REQUIRED BEFORE IMPLEMENTATION

---

## Table of Contents

1. [Critical Issues](#critical-issues)
2. [Additional Recommendations](#additional-recommendations)
3. [Implementation Checklist](#implementation-checklist)

---

## Critical Issues

### 1. Database Schema Enhancements

#### Missing Indexes for Performance

Add these indexes to support common query patterns:

```sql
-- Optimize queries for processed documents
CREATE INDEX idx_documents_processed_at ON documents(processed_at DESC) 
  WHERE processed_at IS NOT NULL;

-- Optimize collection + status queries
CREATE INDEX idx_jobs_collection_status ON processing_jobs(collection_id, status);

-- Optimize chunk lookups
CREATE INDEX idx_chunks_document_index ON document_chunks(document_id, chunk_index);
```

#### Transaction Isolation Level

Specify isolation level to prevent race conditions:

```python
# Add to DatabaseService
async def create_document(self, ...):
    async with self.pool.acquire() as conn:
        async with conn.transaction(isolation='serializable'):
            # Prevents race conditions on duplicate checks
            # ... document creation logic
```

#### Missing Composite Unique Constraint

Prevent duplicate filenames with different cases:

```sql
-- Current: UNIQUE(collection_id, file_hash)
-- Problem: Same file can be uploaded with different names

-- Add this constraint:
CREATE UNIQUE INDEX idx_unique_filename_collection 
ON documents(collection_id, LOWER(filename));

-- This prevents "report.pdf" and "Report.PDF" duplicates
```

---

### 2. Async Connection Pool Configuration

**Critical:** asyncpg pool management needs explicit configuration.

```python
# Add to DatabaseService.__init__
class DatabaseService:
    async def connect(self) -> None:
        self.pool = await asyncpg.create_pool(
            dsn=self.database_url,
            min_size=self.settings.db_pool_min_size,
            max_size=self.settings.db_pool_max_size,
            max_inactive_connection_lifetime=300,  # 5 minutes
            command_timeout=60,  # Query timeout
            server_settings={
                'application_name': 'intellirag',
                'jit': 'off'  # Disable JIT for connection pool stability
            }
        )

    async def disconnect(self) -> None:
        """Graceful shutdown with timeout."""
        if self.pool:
            await self.pool.close()
            await asyncio.wait_for(self.pool.wait_closed(), timeout=10)
```

---

### 3. MinIO Async Client Compatibility

**Issue:** The `minio` Python SDK is **synchronous**, but the plan assumes async operations.

#### Solution A: Use Async Wrapper (Quick Fix)

```python
from concurrent.futures import ThreadPoolExecutor
import asyncio

class MinIOStorageService:
    def __init__(self, endpoint, access_key, secret_key, secure=False):
        self.client = Minio(
            endpoint=endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure
        )
        self.executor = ThreadPoolExecutor(max_workers=4)
    
    async def upload_file(self, bucket: str, path: str, data: BinaryIO, metadata: Dict) -> str:
        """Async wrapper for sync MinIO client."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor,
            self._sync_upload,
            bucket, path, data, metadata
        )
    
    def _sync_upload(self, bucket: str, path: str, data: BinaryIO, metadata: Dict) -> str:
        """Synchronous upload operation."""
        return self.client.put_object(
            bucket_name=bucket,
            object_name=path,
            data=data,
            length=-1,  # Unknown size, read until EOF
            metadata=metadata,
            part_size=10*1024*1024  # 10MB parts
        )
```

#### Solution B: Use aioboto3 (Recommended for Production)

```python
import aioboto3
from botocore.config import Config

class MinIOStorageService:
    def __init__(self, endpoint, access_key, secret_key, secure=False):
        self.endpoint = endpoint
        self.session = aioboto3.Session(
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key
        )
        self.config = Config(
            signature_version='s3v4',
            s3={'addressing_style': 'path'}
        )
    
    async def upload_file(
        self, 
        bucket: str, 
        path: str, 
        data: BinaryIO, 
        metadata: Dict
    ) -> str:
        """Native async upload with S3-compatible API."""
        async with self.session.client(
            's3',
            endpoint_url=f'http://{self.endpoint}',
            config=self.config
        ) as s3:
            await s3.put_object(
                Bucket=bucket,
                Key=path,
                Body=data,
                Metadata=metadata
            )
            return path
    
    async def download_file(self, bucket: str, path: str) -> bytes:
        """Native async download."""
        async with self.session.client(
            's3',
            endpoint_url=f'http://{self.endpoint}',
            config=self.config
        ) as s3:
            response = await s3.get_object(Bucket=bucket, Key=path)
            async with response['Body'] as stream:
                return await stream.read()
```

**Update dependencies:**

```bash
# Remove minio, add aioboto3
uv remove minio
uv add aioboto3
```

---

### 4. File Upload Security - Critical Gap

**Missing:** File content validation, virus scanning, MIME type verification.

```python
# Add to app/services/file_validator.py
import magic
import hashlib
import re
from typing import BinaryIO, Tuple
from fastapi import UploadFile, HTTPException

ALLOWED_MIME_TYPES = {
    'application/pdf',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/csv',
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
}

class FileValidatorService:
    def __init__(self, max_size_mb: int = 50):
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    async def validate_file(self, file: UploadFile) -> Tuple[bytes, str, str]:
        """
        Validate uploaded file for security and compatibility.
        
        Returns:
            Tuple[bytes, str, str]: (file_data, safe_filename, file_hash)
        
        Raises:
            HTTPException: If validation fails
        """
        # 1. Read file data
        file_data = await file.read()
        await file.seek(0)  # Reset for potential re-reading
        
        # 2. Size check
        if len(file_data) > self.max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large: {len(file_data)} bytes (max: {self.max_size_bytes})"
            )
        
        # 3. MIME type verification (don't trust client headers)
        detected_mime = magic.from_buffer(file_data, mime=True)
        if detected_mime not in ALLOWED_MIME_TYPES:
            raise HTTPException(
                status_code=415,
                detail=f"Unsupported file type: {detected_mime}"
            )
        
        # 4. Filename sanitization (prevent path traversal)
        safe_filename = self._sanitize_filename(file.filename)
        
        # 5. Calculate SHA-256 hash for deduplication
        file_hash = hashlib.sha256(file_data).hexdigest()
        
        # 6. Optional: Malware scanning
        # await self._scan_for_malware(file_data)
        
        return file_data, safe_filename, file_hash
    
    def _sanitize_filename(self, filename: str) -> str:
        """
        Sanitize filename to prevent security issues.
        
        - Remove path separators (/, \)
        - Remove dangerous characters
        - Limit length to 255 characters
        - Preserve extension
        """
        # Remove path components
        filename = filename.split('/')[-1].split('\\')[-1]
        
        # Split name and extension
        name_parts = filename.rsplit('.', 1)
        if len(name_parts) == 2:
            name, ext = name_parts
        else:
            name, ext = filename, ''
        
        # Sanitize name: keep only alphanumeric, dash, underscore, space
        safe_name = re.sub(r'[^a-zA-Z0-9._\s-]', '_', name)
        safe_name = safe_name.strip()[:200]  # Limit length
        
        # Sanitize extension
        safe_ext = re.sub(r'[^a-zA-Z0-9]', '', ext)[:10]
        
        # Combine
        if safe_ext:
            return f"{safe_name}.{safe_ext}"
        return safe_name
    
    async def _scan_for_malware(self, file_data: bytes) -> None:
        """
        Optional: Integrate with ClamAV or cloud malware scanning service.
        
        Example with ClamAV:
        - Install: apt-get install clamav clamav-daemon
        - Python client: pip install clamd
        """
        # import clamd
        # cd = clamd.ClamdUnixSocket()
        # result = cd.scan_stream(file_data)
        # if result['stream'][0] == 'FOUND':
        #     raise HTTPException(status_code=400, detail="Malware detected")
        pass
```

**Update IngestionService to use validator:**

```python
class IngestionService:
    def __init__(self, ...):
        self.file_validator = FileValidatorService(max_size_mb=settings.max_file_size_mb)
    
    async def ingest_document(
        self,
        file: UploadFile,
        collection_name: str,
        metadata: Optional[Dict] = None
    ) -> UploadResponse:
        # Validate file first
        file_data, safe_filename, file_hash = await self.file_validator.validate_file(file)
        
        # Continue with ingestion...
```

**Add dependency:**

```bash
uv add python-magic-bin  # Cross-platform MIME detection
```

---

### 5. Error Handling & Rollback Implementation

**Issue:** Transaction rollback for MinIO uploads not fully detailed.

```python
# app/services/ingestion.py
class IngestionService:
    async def process_document(self, job_id: str) -> None:
        """
        Process document with comprehensive error handling and rollback.
        """
        minio_objects_created = []  # Track MinIO objects for cleanup
        qdrant_points_created = []  # Track Qdrant points for cleanup
        
        try:
            # Start database transaction
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    # Get job details
                    job = await self.db.get_job_status(job_id)
                    document = await self.db.get_document(job['document_id'])
                    
                    # Update status: processing
                    await self.db.update_job_status(job_id, 'processing')
                    
                    # Step 1: Download from MinIO
                    await self.db.update_job_progress(job_id, 'parsing', 'in_progress')
                    raw_data = await self.storage.download_file(
                        document['minio_bucket'],
                        document['minio_raw_path']
                    )
                    
                    # Step 2: Parse document
                    parsed_content = await self.parser.parse(raw_data, document['mime_type'])
                    
                    # Store parsed content
                    processed_path = f"{document['collection_name']}/{document['document_id']}/metadata.json"
                    await self.storage.upload_file(
                        self.settings.processed_documents_bucket,
                        processed_path,
                        json.dumps(parsed_content).encode(),
                        {}
                    )
                    minio_objects_created.append((self.settings.processed_documents_bucket, processed_path))
                    
                    await self.db.update_document_paths(
                        document['document_id'],
                        processed_path=processed_path
                    )
                    
                    # Step 3: Chunk text
                    await self.db.update_job_progress(job_id, 'chunking', 'in_progress')
                    chunks = await self.chunker.chunk_text(
                        parsed_content['text'],
                        chunk_size=self.settings.chunk_size,
                        overlap=self.settings.chunk_overlap
                    )
                    
                    # Store chunks
                    chunks_path = f"{document['collection_name']}/{document['document_id']}/chunks.json"
                    await self.storage.upload_file(
                        self.settings.document_chunks_bucket,
                        chunks_path,
                        json.dumps(chunks).encode(),
                        {}
                    )
                    minio_objects_created.append((self.settings.document_chunks_bucket, chunks_path))
                    
                    await self.db.update_document_paths(
                        document['document_id'],
                        chunks_path=chunks_path
                    )
                    
                    # Step 4: Generate embeddings
                    await self.db.update_job_progress(job_id, 'embedding', 'in_progress')
                    embeddings = await self.embedding_service.embed_batch([c['text'] for c in chunks])
                    
                    # Step 5: Store in Qdrant
                    await self.db.update_job_progress(job_id, 'indexing', 'in_progress')
                    
                    # Create chunk records in database
                    chunk_records = [
                        {
                            'chunk_index': i,
                            'chunk_text': chunk['text'],
                            'chunk_size': len(chunk['text']),
                            'embedding_model': 'all-MiniLM-L6-v2'
                        }
                        for i, chunk in enumerate(chunks)
                    ]
                    chunk_ids = await self.db.create_chunks(document['document_id'], chunk_records)
                    
                    # Store vectors in Qdrant
                    points = [
                        {
                            'id': str(chunk_id),
                            'vector': embedding,
                            'payload': {
                                'document_id': str(document['document_id']),
                                'collection_name': document['collection_name'],
                                'chunk_index': i,
                                'text': chunk['text']
                            }
                        }
                        for i, (chunk_id, embedding, chunk) in enumerate(zip(chunk_ids, embeddings, chunks))
                    ]
                    
                    await self.vectordb.upsert_vectors(
                        collection_name=document['collection_name'],
                        points=points
                    )
                    qdrant_points_created.extend([p['id'] for p in points])
                    
                    # Update chunk records with Qdrant IDs
                    for chunk_id in chunk_ids:
                        await self.db.update_chunk_qdrant_id(chunk_id, str(chunk_id))
                    
                    # Update document processing complete
                    duration = (datetime.utcnow() - job['created_at']).total_seconds()
                    await self.db.update_document_processing_complete(
                        document['document_id'],
                        chunk_count=len(chunks),
                        duration=duration
                    )
                    
                    # Update collection statistics
                    await self.db.update_collection_stats(
                        document['collection_id'],
                        chunks_delta=len(chunks)
                    )
                    
                    # Mark job as completed
                    await self.db.update_job_status(job_id, 'completed')
                    
                    # PostgreSQL transaction commits here automatically
                    
        except Exception as e:
            logger.error(f"Document processing failed for job {job_id}: {e}", exc_info=True)
            
            # PostgreSQL transaction automatically rolled back
            
            # Manual cleanup: MinIO objects
            for bucket, path in minio_objects_created:
                try:
                    await self.storage.delete_object(bucket, path)
                    logger.info(f"Cleaned up MinIO object: {bucket}/{path}")
                except Exception as cleanup_error:
                    logger.error(f"MinIO cleanup failed: {cleanup_error}")
            
            # Manual cleanup: Qdrant points
            if qdrant_points_created:
                try:
                    await self.vectordb.delete_vectors(
                        collection_name=document['collection_name'],
                        point_ids=qdrant_points_created
                    )
                    logger.info(f"Cleaned up {len(qdrant_points_created)} Qdrant points")
                except Exception as cleanup_error:
                    logger.error(f"Qdrant cleanup failed: {cleanup_error}")
            
            # Update job status to failed
            await self.db.update_job_status(
                job_id,
                status='failed',
                error_msg=str(e)
            )
            
            # Implement retry logic
            retry_count = await self.db.get_job_retry_count(job_id)
            if retry_count < self.settings.max_retries:
                await self._schedule_retry(job_id, retry_count)
            
            raise
    
    async def _schedule_retry(self, job_id: str, retry_count: int) -> None:
        """Schedule retry with exponential backoff."""
        delay = 2 ** retry_count  # 1s, 2s, 4s, 8s...
        await asyncio.sleep(delay)
        
        await self.db.increment_job_retry_count(job_id)
        await self.process_document(job_id)
```

**Add retry tracking to database:**

```sql
-- Add to processing_jobs table
ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;
ALTER TABLE processing_jobs ADD COLUMN IF NOT EXISTS max_retries INTEGER DEFAULT 3;
```

---

### 6. Idempotency & Duplicate Detection

**Issue:** Hash-based deduplication exists, but what if the same request is retried?

#### Database Schema Addition

```sql
-- Idempotency table
CREATE TABLE idempotency_keys (
    idempotency_key VARCHAR(100) PRIMARY KEY,
    job_id UUID NOT NULL,
    response_data JSONB NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX idx_idempotency_expires ON idempotency_keys(expires_at);

-- Cleanup expired keys (run via cron or background task)
DELETE FROM idempotency_keys WHERE expires_at < CURRENT_TIMESTAMP;
```

#### Schema Update

```python
# app/models/schemas.py
class UploadRequest(BaseModel):
    collection_name: str = Field(..., min_length=1)
    metadata: Optional[Dict[str, Any]] = None
    idempotency_key: Optional[str] = Field(
        None,
        description="Client-provided UUID for idempotent uploads"
    )
```

#### Service Implementation

```python
# app/services/ingestion.py
class IngestionService:
    async def ingest_document(
        self,
        file: UploadFile,
        collection_name: str,
        metadata: Optional[Dict] = None,
        idempotency_key: Optional[str] = None
    ) -> UploadResponse:
        """Idempotent document ingestion."""
        
        # Check idempotency key
        if idempotency_key:
            cached_response = await self.db.get_by_idempotency_key(idempotency_key)
            if cached_response:
                logger.info(f"Returning cached response for idempotency key: {idempotency_key}")
                return UploadResponse(**cached_response['response_data'])
        
        # Validate file
        file_data, safe_filename, file_hash = await self.file_validator.validate_file(file)
        
        # Check for duplicate file
        existing_doc = await self.db.check_duplicate_document(collection_id, file_hash)
        if existing_doc:
            raise HTTPException(
                status_code=409,
                detail=f"Document already exists: {existing_doc}"
            )
        
        # ... proceed with ingestion ...
        
        # Store idempotency key
        if idempotency_key:
            await self.db.store_idempotency_key(
                idempotency_key,
                job_id,
                response.dict(),
                expires_hours=24
            )
        
        return response
```

#### Database Service Methods

```python
# app/services/database.py
class DatabaseService:
    async def get_by_idempotency_key(self, key: str) -> Optional[Dict]:
        """Get cached response by idempotency key."""
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT job_id, response_data
                FROM idempotency_keys
                WHERE idempotency_key = $1 AND expires_at > CURRENT_TIMESTAMP
                """,
                key
            )
            return dict(row) if row else None
    
    async def store_idempotency_key(
        self,
        key: str,
        job_id: UUID,
        response_data: Dict,
        expires_hours: int = 24
    ) -> None:
        """Store idempotency key with response."""
        async with self.pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO idempotency_keys (idempotency_key, job_id, response_data, expires_at)
                VALUES ($1, $2, $3, CURRENT_TIMESTAMP + INTERVAL '%s hours')
                ON CONFLICT (idempotency_key) DO NOTHING
                """,
                key, job_id, json.dumps(response_data), expires_hours
            )
```

---

### 7. Streaming Large Files

**Issue:** Current design loads entire file into memory.

```python
# app/services/storage.py
from botocore.config import Config
from botocore.exceptions import ClientError

class MinIOStorageService:
    def __init__(self, ...):
        self.transfer_config = Config(
            signature_version='s3v4',
            s3={
                'addressing_style': 'path',
                'payload_signing_enabled': True
            }
        )
    
    async def upload_file_streaming(
        self,
        bucket: str,
        path: str,
        file: UploadFile,
        metadata: Optional[Dict] = None,
        chunk_size: int = 8 * 1024 * 1024  # 8MB chunks
    ) -> str:
        """
        Stream large file to MinIO without loading into memory.
        
        Uses multipart upload for files > 10MB.
        """
        async with self.session.client(
            's3',
            endpoint_url=f'http://{self.endpoint}',
            config=self.transfer_config
        ) as s3:
            try:
                # For small files, use simple upload
                file_size = 0
                if hasattr(file, 'size') and file.size:
                    file_size = file.size
                
                if file_size < 10 * 1024 * 1024:  # < 10MB
                    # Simple upload
                    await s3.put_object(
                        Bucket=bucket,
                        Key=path,
                        Body=file.file,
                        Metadata=metadata or {}
                    )
                else:
                    # Multipart upload for large files
                    upload = await s3.create_multipart_upload(
                        Bucket=bucket,
                        Key=path,
                        Metadata=metadata or {}
                    )
                    upload_id = upload['UploadId']
                    
                    parts = []
                    part_number = 1
                    
                    try:
                        while True:
                            chunk = await file.read(chunk_size)
                            if not chunk:
                                break
                            
                            part = await s3.upload_part(
                                Bucket=bucket,
                                Key=path,
                                PartNumber=part_number,
                                UploadId=upload_id,
                                Body=chunk
                            )
                            
                            parts.append({
                                'PartNumber': part_number,
                                'ETag': part['ETag']
                            })
                            
                            part_number += 1
                        
                        # Complete multipart upload
                        await s3.complete_multipart_upload(
                            Bucket=bucket,
                            Key=path,
                            UploadId=upload_id,
                            MultipartUpload={'Parts': parts}
                        )
                        
                    except Exception as e:
                        # Abort multipart upload on error
                        await s3.abort_multipart_upload(
                            Bucket=bucket,
                            Key=path,
                            UploadId=upload_id
                        )
                        raise
                
                return path
                
            except ClientError as e:
                logger.error(f"S3 upload failed: {e}")
                raise
    
    async def download_file_streaming(
        self,
        bucket: str,
        path: str,
        chunk_size: int = 8 * 1024 * 1024
    ) -> AsyncGenerator[bytes, None]:
        """
        Stream file download to avoid memory overload.
        
        Usage:
            async for chunk in storage.download_file_streaming(bucket, path):
                process(chunk)
        """
        async with self.session.client(
            's3',
            endpoint_url=f'http://{self.endpoint}',
            config=self.transfer_config
        ) as s3:
            response = await s3.get_object(Bucket=bucket, Key=path)
            
            async with response['Body'] as stream:
                while True:
                    chunk = await stream.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
```

**Update IngestionService:**

```python
class IngestionService:
    async def ingest_document(self, file: UploadFile, ...):
        # Use streaming upload
        minio_path = await self.storage.upload_file_streaming(
            bucket=self.settings.raw_documents_bucket,
            path=f"{collection_name}/{document_id}/original.{file_extension}",
            file=file,
            metadata={'filename': safe_filename, 'mime_type': detected_mime}
        )
```

---

### 8. Observability & Metrics

Add Prometheus metrics for production monitoring.

```python
# app/utils/metrics.py
from prometheus_client import Counter, Histogram, Gauge, Summary

# Document ingestion metrics
documents_uploaded_total = Counter(
    'documents_uploaded_total',
    'Total number of documents uploaded',
    ['collection', 'mime_type', 'status']
)

document_upload_size_bytes = Histogram(
    'document_upload_size_bytes',
    'Size of uploaded documents in bytes',
    ['collection', 'mime_type'],
    buckets=[1024, 10240, 102400, 1048576, 10485760, 52428800]  # 1KB to 50MB
)

document_processing_duration_seconds = Histogram(
    'document_processing_duration_seconds',
    'Time taken to process document',
    ['collection', 'step'],
    buckets=[1, 5, 10, 30, 60, 120, 300]  # 1s to 5min
)

active_processing_jobs = Gauge(
    'active_processing_jobs',
    'Number of documents currently being processed',
    ['collection']
)

processing_errors_total = Counter(
    'processing_errors_total',
    'Total processing errors',
    ['collection', 'error_type']
)

# Database metrics
db_connection_pool_size = Gauge(
    'db_connection_pool_size',
    'Current database connection pool size'
)

db_query_duration_seconds = Summary(
    'db_query_duration_seconds',
    'Database query execution time',
    ['operation']
)

# Storage metrics
minio_operations_total = Counter(
    'minio_operations_total',
    'Total MinIO operations',
    ['operation', 'bucket', 'status']
)

# Vector database metrics
qdrant_upsert_duration_seconds = Histogram(
    'qdrant_upsert_duration_seconds',
    'Time taken to upsert vectors to Qdrant',
    ['collection'],
    buckets=[0.1, 0.5, 1, 2, 5, 10]
)
```

**Instrument Services:**

```python
# app/services/ingestion.py
class IngestionService:
    async def ingest_document(self, file: UploadFile, collection_name: str, ...):
        # Record upload
        documents_uploaded_total.labels(
            collection=collection_name,
            mime_type=file.content_type,
            status='success'
        ).inc()
        
        document_upload_size_bytes.labels(
            collection=collection_name,
            mime_type=file.content_type
        ).observe(file.size)
        
        # ... ingestion logic ...
    
    async def process_document(self, job_id: str):
        # Track active jobs
        collection_name = document['collection_name']
        active_processing_jobs.labels(collection=collection_name).inc()
        
        try:
            # Track processing time per step
            with document_processing_duration_seconds.labels(
                collection=collection_name,
                step='parsing'
            ).time():
                parsed_content = await self.parser.parse(...)
            
            with document_processing_duration_seconds.labels(
                collection=collection_name,
                step='chunking'
            ).time():
                chunks = await self.chunker.chunk_text(...)
            
            # ... rest of processing ...
            
        except Exception as e:
            processing_errors_total.labels(
                collection=collection_name,
                error_type=type(e).__name__
            ).inc()
            raise
        
        finally:
            active_processing_jobs.labels(collection=collection_name).dec()
```

**Expose metrics endpoint:**

```python
# app/api/v1/metrics.py
from fastapi import APIRouter
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from starlette.responses import Response

router = APIRouter()

@router.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type=CONTENT_TYPE_LATEST
    )
```

**Add to main app:**

```python
# app/main.py
from app.api.v1 import metrics

app.include_router(metrics.router, tags=["Metrics"])
```

**Install dependency:**

```bash
uv add prometheus-client
```

---

### 9. Configuration - Secrets Management

**Issue:** Storing secrets in `.env` is insecure for production.

```python
# app/config.py
from pydantic import SecretStr, Field
from pydantic_settings import BaseSettings
from typing import Optional
import hvac  # HashiCorp Vault client

class Settings(BaseSettings):
    # Application
    app_name: str = "IntelliRAG"
    app_version: str = "0.2.0"
    environment: str = Field("development", regex="^(development|staging|production)$")
    
    # Secrets - use SecretStr to prevent accidental logging
    postgres_password: SecretStr
    minio_secret_key: SecretStr
    
    # Vault integration (optional)
    use_vault: bool = False
    vault_url: Optional[str] = None
    vault_token: Optional[SecretStr] = None
    vault_mount_point: str = "secret"
    vault_secret_path: str = "intellirag"
    
    # ... other settings ...
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
    
    @classmethod
    def from_vault(cls, vault_url: str, vault_token: str) -> "Settings":
        """
        Load secrets from HashiCorp Vault.
        
        Example:
            settings = Settings.from_vault(
                vault_url="http://localhost:8200",
                vault_token="hvs.xxx"
            )
        """
        client = hvac.Client(url=vault_url, token=vault_token)
        
        # Read secrets from Vault
        secret_response = client.secrets.kv.v2.read_secret_version(
            path='intellirag/production',
            mount_point='secret'
        )
        
        vault_secrets = secret_response['data']['data']
        
        # Merge with environment variables
        return cls(**vault_secrets)
    
    def get_database_url(self) -> str:
        """Get database URL with secrets revealed."""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:"
            f"{self.postgres_password.get_secret_value()}@"
            f"{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    def get_minio_client_config(self) -> dict:
        """Get MinIO config with secrets revealed."""
        return {
            'endpoint': self.minio_endpoint,
            'access_key': self.minio_access_key,
            'secret_key': self.minio_secret_key.get_secret_value(),
            'secure': self.minio_secure
        }

# Initialize settings
settings = Settings()

# For production with Vault
if settings.use_vault and settings.vault_url and settings.vault_token:
    settings = Settings.from_vault(
        vault_url=settings.vault_url,
        vault_token=settings.vault_token.get_secret_value()
    )
```

**Environment-specific configs:**

```bash
# .env.development
ENVIRONMENT=development
USE_VAULT=false
POSTGRES_PASSWORD=dev_password
MINIO_SECRET_KEY=minioadmin

# .env.production
ENVIRONMENT=production
USE_VAULT=true
VAULT_URL=https://vault.company.com
VAULT_TOKEN=hvs.xxxxx
VAULT_SECRET_PATH=intellirag/production
```

**Add dependency:**

```bash
uv add hvac  # HashiCorp Vault client
```

---

## Additional Recommendations

### 1. Health Checks for All Services

```python
# app/api/v1/health.py
from fastapi import APIRouter, Depends, HTTPException
from app.services.database import DatabaseService
from app.services.storage import MinIOStorageService
from app.services.vector_db import VectorDBService
from app.dependencies import get_db, get_storage, get_vectordb

router = APIRouter()

@router.get("/health")
async def basic_health():
    """Basic health check."""
    return {"status": "healthy"}

@router.get("/health/detailed")
async def detailed_health(
    db: DatabaseService = Depends(get_db),
    storage: MinIOStorageService = Depends(get_storage),
    vectordb: VectorDBService = Depends(get_vectordb)
):
    """
    Comprehensive health check for all services.
    
    Returns 200 if all services healthy, 503 if any service down.
    """
    health_status = {
        "status": "healthy",
        "services": {}
    }
    
    # PostgreSQL check
    try:
        pg_healthy = await db.health_check()
        health_status["services"]["postgresql"] = {
            "status": "healthy" if pg_healthy else "unhealthy",
            "pool_size": db.pool.get_size(),
            "free_connections": db.pool.get_idle_size()
        }
    except Exception as e:
        health_status["services"]["postgresql"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # MinIO check
    try:
        minio_healthy = await storage.health_check()
        health_status["services"]["minio"] = {
            "status": "healthy" if minio_healthy else "unhealthy"
        }
    except Exception as e:
        health_status["services"]["minio"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Qdrant check
    try:
        qdrant_healthy = await vectordb.health_check()
        health_status["services"]["qdrant"] = {
            "status": "healthy" if qdrant_healthy else "unhealthy"
        }
    except Exception as e:
        health_status["services"]["qdrant"] = {
            "status": "unhealthy",
            "error": str(e)
        }
        health_status["status"] = "unhealthy"
    
    # Disk space check
    try:
        disk_info = await check_disk_space()
        health_status["services"]["disk"] = disk_info
        
        if disk_info["percent_used"] > 90:
            health_status["status"] = "degraded"
    except Exception as e:
        health_status["services"]["disk"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # Return 503 if unhealthy
    if health_status["status"] == "unhealthy":
        raise HTTPException(status_code=503, detail=health_status)
    
    return health_status

async def check_disk_space() -> dict:
    """Check available disk space."""
    import shutil
    
    total, used, free = shutil.disk_usage("/")
    
    return {
        "status": "healthy",
        "total_gb": round(total / (1024**3), 2),
        "used_gb": round(used / (1024**3), 2),
        "free_gb": round(free / (1024**3), 2),
        "percent_used": round((used / total) * 100, 2)
    }
```

**Implement health check methods:**

```python
# app/services/database.py
class DatabaseService:
    async def health_check(self) -> bool:
        """Check PostgreSQL connectivity."""
        try:
            async with self.pool.acquire() as conn:
                await conn.fetchval('SELECT 1')
            return True
        except Exception as e:
            logger.error(f"PostgreSQL health check failed: {e}")
            return False

# app/services/storage.py
class MinIOStorageService:
    async def health_check(self) -> bool:
        """Check MinIO connectivity."""
        try:
            async with self.session.client('s3', ...) as s3:
                await s3.list_buckets()
            return True
        except Exception as e:
            logger.error(f"MinIO health check failed: {e}")
            return False

# app/services/vector_db.py
class VectorDBService:
    async def health_check(self) -> bool:
        """Check Qdrant connectivity."""
        try:
            collections = await self.client.get_collections()
            return True
        except Exception as e:
            logger.error(f"Qdrant health check failed: {e}")
            return False
```

---

### 2. Pagination for List Endpoints

```python
# app/models/schemas.py
from typing import Generic, TypeVar, List
from pydantic import BaseModel, Field

T = TypeVar('T')

class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int

class DocumentFilter(BaseModel):
    """Query parameters for filtering documents."""
    collection_name: Optional[str] = None
    mime_type: Optional[str] = None
    uploaded_after: Optional[datetime] = None
    uploaded_before: Optional[datetime] = None
    min_size: Optional[int] = None
    max_size: Optional[int] = None

# app/api/v1/documents.py
@router.get("/collections/{collection_name}/documents", response_model=PaginatedResponse[DocumentInfo])
async def list_documents(
    collection_name: str,
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    page_size: int = Query(50, ge=1, le=1000, description="Items per page"),
    sort_by: str = Query("uploaded_at", regex="^(filename|uploaded_at|file_size|processed_at)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    filters: DocumentFilter = Depends(),
    db: DatabaseService = Depends(get_db)
):
    """
    List documents in a collection with pagination and filtering.
    
    - **page**: Page number (1-indexed)
    - **page_size**: Number of items per page (max 1000)
    - **sort_by**: Field to sort by
    - **order**: Sort order (asc/desc)
    """
    offset = (page - 1) * page_size
    
    documents, total = await db.list_documents_paginated(
        collection_name=collection_name,
        offset=offset,
        limit=page_size,
        sort_by=sort_by,
        order=order,
        filters=filters
    )
    
    return PaginatedResponse(
        items=documents,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=(total + page_size - 1) // page_size
    )
```

**Database implementation:**

```python
# app/services/database.py
class DatabaseService:
    async def list_documents_paginated(
        self,
        collection_name: str,
        offset: int = 0,
        limit: int = 50,
        sort_by: str = "uploaded_at",
        order: str = "desc",
        filters: Optional[DocumentFilter] = None
    ) -> Tuple[List[Dict], int]:
        """
        List documents with pagination and filtering.
        
        Returns:
            Tuple[List[Dict], int]: (documents, total_count)
        """
        # Build WHERE clause
        where_clauses = ["c.collection_name = $1"]
        params = [collection_name]
        param_idx = 2
        
        if filters:
            if filters.mime_type:
                where_clauses.append(f"d.mime_type = ${param_idx}")
                params.append(filters.mime_type)
                param_idx += 1
            
            if filters.uploaded_after:
                where_clauses.append(f"d.uploaded_at >= ${param_idx}")
                params.append(filters.uploaded_after)
                param_idx += 1
            
            if filters.uploaded_before:
                where_clauses.append(f"d.uploaded_at <= ${param_idx}")
                params.append(filters.uploaded_before)
                param_idx += 1
            
            if filters.min_size:
                where_clauses.append(f"d.file_size_bytes >= ${param_idx}")
                params.append(filters.min_size)
                param_idx += 1
            
            if filters.max_size:
                where_clauses.append(f"d.file_size_bytes <= ${param_idx}")
                params.append(filters.max_size)
                param_idx += 1
        
        where_clause = " AND ".join(where_clauses)
        
        # Validate sort field
        allowed_sort_fields = {
            'filename': 'd.filename',
            'uploaded_at': 'd.uploaded_at',
            'file_size': 'd.file_size_bytes',
            'processed_at': 'd.processed_at'
        }
        sort_field = allowed_sort_fields.get(sort_by, 'd.uploaded_at')
        order_clause = "ASC" if order.lower() == "asc" else "DESC"
        
        async with self.pool.acquire() as conn:
            # Get total count
            count_query = f"""
                SELECT COUNT(*)
                FROM documents d
                JOIN collections c ON d.collection_id = c.collection_id
                WHERE {where_clause}
            """
            total = await conn.fetchval(count_query, *params)
            
            # Get paginated results
            query = f"""
                SELECT
                    d.document_id,
                    d.filename,
                    d.mime_type,
                    d.file_size_bytes,
                    d.chunk_count,
                    d.uploaded_at,
                    d.processed_at,
                    d.custom_metadata
                FROM documents d
                JOIN collections c ON d.collection_id = c.collection_id
                WHERE {where_clause}
                ORDER BY {sort_field} {order_clause}
                LIMIT ${param_idx} OFFSET ${param_idx + 1}
            """
            params.extend([limit, offset])
            
            rows = await conn.fetch(query, *params)
            documents = [dict(row) for row in rows]
            
            return documents, total
```

---

### 3. Document Deletion Endpoint

```python
# app/api/v1/documents.py
@router.delete("/documents/{document_id}", status_code=204)
async def delete_document(
    document_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """
    Delete a document and all associated data.
    
    This will:
    - Remove document from PostgreSQL
    - Delete vectors from Qdrant
    - Delete files from MinIO
    - Delete all chunks
    """
    await ingestion_service.delete_document(document_id)

# app/services/ingestion.py
class IngestionService:
    async def delete_document(self, document_id: str) -> None:
        """
        Delete document and all associated data.
        
        Ensures cleanup across all systems:
        - PostgreSQL (cascading deletes)
        - Qdrant (vector deletion)
        - MinIO (file deletion)
        """
        # Get document info
        document = await self.db.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail="Document not found")
        
        try:
            async with self.db.pool.acquire() as conn:
                async with conn.transaction():
                    # Get chunk IDs for Qdrant deletion
                    chunks = await self.db.get_document_chunks(document_id)
                    chunk_ids = [chunk['qdrant_point_id'] for chunk in chunks if chunk['qdrant_point_id']]
                    
                    # Delete from Qdrant
                    if chunk_ids:
                        await self.vectordb.delete_vectors(
                            collection_name=document['collection_name'],
                            point_ids=chunk_ids
                        )
                    
                    # Delete from PostgreSQL (cascades to chunks, jobs)
                    deleted = await self.db.delete_document(document_id)
                    if not deleted:
                        raise HTTPException(status_code=404, detail="Document not found")
                    
                    # Update collection stats
                    await self.db.update_collection_stats(
                        document['collection_id'],
                        document_delta=-1,
                        chunks_delta=-document['chunk_count']
                    )
            
            # Delete from MinIO (outside transaction)
            await self._cleanup_minio_files(document)
            
            logger.info(f"Successfully deleted document {document_id}")
            
        except Exception as e:
            logger.error(f"Failed to delete document {document_id}: {e}")
            raise HTTPException(status_code=500, detail=f"Failed to delete document: {e}")
    
    async def _cleanup_minio_files(self, document: Dict) -> None:
        """Delete all MinIO files for a document."""
        paths_to_delete = [
            (document['minio_bucket'], document['minio_raw_path'])
        ]
        
        if document.get('minio_processed_path'):
            paths_to_delete.append((
                self.settings.processed_documents_bucket,
                document['minio_processed_path']
            ))
        
        if document.get('minio_chunks_path'):
            paths_to_delete.append((
                self.settings.document_chunks_bucket,
                document['minio_chunks_path']
            ))
        
        for bucket, path in paths_to_delete:
            try:
                await self.storage.delete_object(bucket, path)
            except Exception as e:
                logger.warning(f"Failed to delete MinIO object {bucket}/{path}: {e}")
```

---

### 4. Batch Upload Endpoint

```python
# app/models/schemas.py
class BatchUploadResponse(BaseModel):
    """Response for batch document upload."""
    job_ids: List[str]
    total_files: int
    successful: int
    failed: int
    errors: List[Dict[str, str]] = []  # [{"filename": "...", "error": "..."}]

# app/api/v1/ingest.py
@router.post("/ingest/batch", response_model=BatchUploadResponse)
async def upload_documents_batch(
    files: List[UploadFile] = File(..., description="Multiple files to upload"),
    collection_name: str = Form(...),
    metadata: Optional[str] = Form(None),  # JSON string
    background_tasks: BackgroundTasks,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
):
    """
    Upload multiple documents at once.
    
    - **files**: List of files to upload
    - **collection_name**: Target collection
    - **metadata**: Optional JSON metadata applied to all files
    
    Returns job IDs for tracking each upload.
    """
    if len(files) > 100:
        raise HTTPException(status_code=400, detail="Maximum 100 files per batch")
    
    job_ids = []
    successful = 0
    failed = 0
    errors = []
    
    # Parse metadata once
    custom_metadata = None
    if metadata:
        try:
            custom_metadata = json.loads(metadata)
        except json.JSONDecodeError:
            raise HTTPException(status_code=400, detail="Invalid metadata JSON")
    
    # Process each file
    for file in files:
        try:
            response = await ingestion_service.ingest_document(
                file=file,
                collection_name=collection_name,
                metadata=custom_metadata
            )
            job_ids.append(response.job_id)
            successful += 1
            
            # Schedule background processing
            background_tasks.add_task(
                ingestion_service.process_document,
                response.job_id
            )
            
        except HTTPException as e:
            failed += 1
            errors.append({
                "filename": file.filename,
                "error": e.detail
            })
        except Exception as e:
            failed += 1
            errors.append({
                "filename": file.filename,
                "error": str(e)
            })
    
    return BatchUploadResponse(
        job_ids=job_ids,
        total_files=len(files),
        successful=successful,
        failed=failed,
        errors=errors
    )
```

---

### 5. Request ID Tracing

Add request ID for distributed tracing:

```python
# app/middleware/request_id.py
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
import contextvars

# Context variable for request ID
request_id_context: contextvars.ContextVar[str] = contextvars.ContextVar('request_id', default=None)

class RequestIDMiddleware(BaseHTTPMiddleware):
    """Add unique request ID to all requests."""
    
    async def dispatch(self, request: Request, call_next):
        # Generate or extract request ID
        request_id = request.headers.get('X-Request-ID') or str(uuid.uuid4())
        request_id_context.set(request_id)
        
        # Add to request state
        request.state.request_id = request_id
        
        # Process request
        response = await call_next(request)
        
        # Add to response headers
        response.headers['X-Request-ID'] = request_id
        
        return response

# app/utils/logging.py
import logging
from app.middleware.request_id import request_id_context

class RequestIDFilter(logging.Filter):
    """Add request ID to log records."""
    
    def filter(self, record):
        record.request_id = request_id_context.get() or 'no-request-id'
        return True

# Configure logging
def setup_logging():
    handler = logging.StreamHandler()
    handler.addFilter(RequestIDFilter())
    
    formatter = logging.Formatter(
        '[%(asctime)s] [%(request_id)s] [%(levelname)s] %(name)s: %(message)s'
    )
    handler.setFormatter(formatter)
    
    logging.basicConfig(level=logging.INFO, handlers=[handler])

# app/main.py
from app.middleware.request_id import RequestIDMiddleware
from app.utils.logging import setup_logging

app = FastAPI()

# Add middleware
app.add_middleware(RequestIDMiddleware)

# Setup logging
setup_logging()
```

---

### 6. Rate Limiting

Simple in-memory rate limiter:

```python
# app/middleware/rate_limit.py
from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio

class RateLimiter:
    """Simple in-memory rate limiter."""
    
    def __init__(self, max_requests: int = 100, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = timedelta(seconds=window_seconds)
        self.requests = defaultdict(list)
        self.lock = asyncio.Lock()
    
    async def is_allowed(self, identifier: str) -> bool:
        """Check if request is allowed."""
        now = datetime.utcnow()
        
        async with self.lock:
            # Clean old requests
            self.requests[identifier] = [
                req_time for req_time in self.requests[identifier]
                if now - req_time < self.window
            ]
            
            # Check limit
            if len(self.requests[identifier]) >= self.max_requests:
                return False
            
            # Add current request
            self.requests[identifier].append(now)
            return True

class RateLimitMiddleware(BaseHTTPMiddleware):
    """Rate limiting middleware."""
    
    def __init__(self, app, max_requests: int = 100, window_seconds: int = 60):
        super().__init__(app)
        self.limiter = RateLimiter(max_requests, window_seconds)
    
    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in ['/health', '/metrics']:
            return await call_next(request)
        
        # Use IP as identifier (or user ID in production)
        identifier = request.client.host
        
        if not await self.limiter.is_allowed(identifier):
            raise HTTPException(
                status_code=429,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": "60"}
            )
        
        return await call_next(request)

# app/main.py
from app.middleware.rate_limit import RateLimitMiddleware

app.add_middleware(
    RateLimitMiddleware,
    max_requests=100,  # 100 requests
    window_seconds=60   # per minute
)
```

---

### 7. CORS Configuration

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:8080",  # Vue dev server
        "https://intellirag.company.com"  # Production frontend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"]
)
```

---

### 8. OpenAPI Documentation Improvements

```python
# app/main.py
app = FastAPI(
    title="IntelliRAG API",
    description="""
    IntelliRAG is an intelligent document ingestion and retrieval system.
    
    ## Features
    
    * **Document Upload**: Upload PDF, DOCX, TXT, CSV files
    * **Semantic Search**: Query documents using natural language
    * **Collection Management**: Organize documents into collections
    * **Processing Status**: Track document processing in real-time
    
    ## Authentication
    
    API requires authentication via API keys (coming in Phase 6).
    """,
    version="0.2.0",
    contact={
        "name": "IntelliRAG Team",
        "url": "https://github.com/yourusername/intellirag",
        "email": "support@intellirag.com"
    },
    license_info={
        "name": "MIT",
        "url": "https://opensource.org/licenses/MIT"
    },
    openapi_tags=[
        {
            "name": "health",
            "description": "Health check and system status endpoints"
        },
        {
            "name": "ingestion",
            "description": "Document upload and processing"
        },
        {
            "name": "query",
            "description": "RAG query endpoints"
        },
        {
            "name": "collections",
            "description": "Collection management"
        },
        {
            "name": "documents",
            "description": "Document management"
        },
        {
            "name": "metrics",
            "description": "Prometheus metrics"
        }
    ]
)

# Tag endpoints
@router.post("/ingest", tags=["ingestion"])
@router.get("/collections", tags=["collections"])
@router.get("/health/detailed", tags=["health"])
```

---

## Implementation Checklist

### Phase 5A: Core Infrastructure ✅

- [ ] **Database Schema**
  - [ ] Add missing indexes
  - [ ] Add idempotency_keys table
  - [ ] Add composite unique constraints
  - [ ] Create Alembic migration

- [ ] **DatabaseService**
  - [ ] Implement connection pool with proper config
  - [ ] Add transaction isolation levels
  - [ ] Implement all CRUD operations
  - [ ] Add health check method
  - [ ] Add graceful shutdown

- [ ] **MinIO Storage**
  - [ ] Switch to aioboto3 for async support
  - [ ] Implement streaming upload/download
  - [ ] Add multipart upload for large files
  - [ ] Implement health check
  - [ ] Add comprehensive error handling

- [ ] **File Validation**
  - [ ] Create FileValidatorService class
  - [ ] Implement MIME type verification (python-magic)
  - [ ] Add filename sanitization
  - [ ] Implement size validation
  - [ ] Add optional malware scanning

### Phase 5B: Business Logic ✅

- [ ] **IngestionService**
  - [ ] Implement comprehensive error handling
  - [ ] Add full rollback logic (PostgreSQL + MinIO + Qdrant)
  - [ ] Implement retry with exponential backoff
  - [ ] Add idempotency key support
  - [ ] Implement document deletion
  - [ ] Add Prometheus metrics

- [ ] **Configuration**
  - [ ] Use SecretStr for sensitive data
  - [ ] Add Vault integration (optional)
  - [ ] Add environment-specific configs

### Phase 5C: API & Middleware ✅

- [ ] **API Endpoints**
  - [ ] Add pagination to list endpoints
  - [ ] Add document deletion endpoint
  - [ ] Add batch upload endpoint
  - [ ] Improve OpenAPI documentation

- [ ] **Middleware**
  - [ ] Add RequestIDMiddleware
  - [ ] Add RateLimitMiddleware
  - [ ] Configure CORS
  - [ ] Add Prometheus metrics endpoint

- [ ] **Health Checks**
  - [ ] Implement detailed health endpoint
  - [ ] Add service-specific health checks
  - [ ] Add disk space monitoring

### Phase 5D: Testing ✅

- [ ] **Unit Tests**
  - [ ] DatabaseService tests
  - [ ] MinIOStorageService tests
  - [ ] FileValidatorService tests
  - [ ] IngestionService tests

- [ ] **Integration Tests**
  - [ ] End-to-end upload flow
  - [ ] Error handling and rollback
  - [ ] Concurrent uploads
  - [ ] Large file handling

---

## Dependencies to Add

```bash
# Async PostgreSQL
uv add asyncpg "sqlalchemy[asyncio]" alembic

# Async S3-compatible storage (instead of minio)
uv add aioboto3

# File validation
uv add python-magic-bin

# Monitoring
uv add prometheus-client

# Secrets management (optional)
uv add hvac

# Testing
uv add --dev pytest-asyncio pytest-timeout
```

---

## Migration Path

1. **Immediate (Before Phase 5 Implementation):**
   - Switch to aioboto3
   - Add FileValidatorService
   - Update database schema with missing indexes

2. **During Phase 5 Implementation:**
   - Implement all improvements incrementally
   - Test each component thoroughly
   - Add metrics as you go

3. **Post-Phase 5 (Polish):**
   - Add comprehensive monitoring dashboards
   - Implement Vault integration
   - Add advanced rate limiting
   - Chaos testing

---

**Document Status:** ✅ Ready for Implementation  
**Last Updated:** 2025-10-20  
**Version:** 1.0
