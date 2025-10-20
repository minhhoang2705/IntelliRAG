# Phase 5: Document Ingestion & Storage - Implementation Plan

**Date:** 2025-10-20 (Updated with PostgreSQL integration)
**Status:** 🚧 IN PROGRESS
**Phase Objective:** Enable document upload, storage, and processing pipeline with PostgreSQL metadata management
**Timeline:** 13-16 hours development
**Methodology:** Test-Driven Development (TDD)

---

## Executive Summary

Phase 5 implements the critical missing piece in the IntelliRAG system: **document ingestion**. Currently, users can only query pre-loaded documents. This phase adds the ability to upload, store, process, and index user documents for RAG queries.

**Key Innovations:**
- **Dual-Storage Architecture**: PostgreSQL for ACID-compliant metadata management + MinIO for S3-compatible object storage
- **Transaction Safety**: Full rollback capability on processing failures with comprehensive error handling
- **Real-Time Observability**: Complete audit trail and processing status tracking at every pipeline step
- **Production-Grade Deduplication**: SHA-256 hash-based duplicate detection prevents reprocessing

---

## Current Project Status

### ✅ Completed Phases

#### Phase 3: Embedding & Vector Database (Complete)
- **Services:** EmbeddingService (88% coverage), VectorDBService (97% coverage)
- **Integration:** 12 integration tests passing with real Qdrant
- **Features:** 768-d multilingual embeddings, vector CRUD operations
- **Status:** ✅ Production-ready

#### Phase 4: RAG Pipeline Integration (Complete)
- **Services:** LLM Client (94%), RAG Pipeline (100%), Orchestrator (89%)
- **API:** FastAPI with `/health` and `/api/v1/query` endpoints
- **Tests:** 13 unit tests + 14 integration tests (all passing)
- **Features:** Full RAG query flow with vLLM integration
- **Status:** ✅ Production-ready

### 🔴 Current Limitations (Addressed in Phase 5)

1. **No Document Upload** - Users cannot add their own documents
2. **Fixed Collection** - Hardcoded to "default" collection
3. **No Document Storage** - No raw document retention
4. **No Processing Status** - Cannot track ingestion progress
5. **No Collection Management** - Cannot create/delete collections

---

## Phase 5 Architecture

### High-Level System Design

```
┌─────────────────────────────────────────────────────────────┐
│                    User Interactions                         │
└─────────────────────────────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                        │
│  ┌──────────────────┐  ┌────────────────────────────────┐  │
│  │  POST /ingest    │  │  POST /api/v1/query            │  │
│  │  GET /status     │  │  (existing)                    │  │
│  └──────────────────┘  └────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
                            │
                ┌───────────┴───────────┐
                │                       │
                ↓                       ↓
┌───────────────────────┐   ┌───────────────────────┐
│   Ingestion Service   │   │    RAG Pipeline      │
│   (NEW)               │   │    (existing)         │
└───────────────────────┘   └───────────────────────┘
                │
        ┌───────┼───────┬───────────┬──────────┐
        │       │       │           │          │
        ↓       ↓       ↓           ↓          ↓
    ┌──────┐ ┌────┐ ┌────────┐ ┌─────────┐ ┌──────────┐
    │MinIO │ │Doc │ │Embedding│ │Qdrant  │ │PostgreSQL│
    │      │ │Proc│ │Service  │ │        │ │ (NEW)    │
    │(NEW) │ │    │ │         │ │        │ │          │
    └──────┘ └────┘ └────────┘ └─────────┘ └──────────┘
       │                                          │
       │← Raw Documents                           │← Metadata
       │                                          │
```

**Key Components:**
- **MinIO**: S3-compatible object storage for raw documents, parsed content, and chunks
- **PostgreSQL**: Relational database for document metadata, processing status, and collection management
- **Qdrant**: Vector database for embeddings and semantic search
- **vLLM**: LLM inference for RAG responses

### MinIO Storage Architecture

```
MinIO Server
├── raw-documents/              # Bucket for uploaded files
│   ├── collection_1/
│   │   ├── doc_001/
│   │   │   └── original.pdf
│   │   └── doc_002/
│   │       └── research.docx
│   └── collection_2/
│       └── doc_003/
│           └── notes.txt
│
├── processed-documents/        # Bucket for parsed content
│   ├── collection_1/
│   │   ├── doc_001/
│   │   │   └── metadata.json
│   │   └── doc_002/
│   │       └── metadata.json
│   └── collection_2/
│       └── doc_003/
│           └── metadata.json
│
└── document-chunks/           # Bucket for chunked text
    ├── collection_1/
    │   ├── doc_001/
    │   │   └── chunks.json
    │   └── doc_002/
    │       └── chunks.json
    └── collection_2/
        └── doc_003/
            └── chunks.json
```

### PostgreSQL Database Schema

#### **Purpose**
PostgreSQL serves as the **metadata management layer**, enabling:
- Fast queries for document lookup and filtering
- ACID-compliant transaction tracking
- Processing job status management
- Collection metadata and statistics
- Audit trail for all operations

#### **Database Schema**

```sql
-- Collections Table
CREATE TABLE collections (
    collection_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    -- Statistics (denormalized for performance)
    document_count INTEGER DEFAULT 0,
    total_chunks INTEGER DEFAULT 0,

    -- Constraints
    CONSTRAINT collection_name_format CHECK (collection_name ~ '^[a-zA-Z0-9_-]+$')
);

CREATE INDEX idx_collections_name ON collections(collection_name);
CREATE INDEX idx_collections_created_at ON collections(created_at DESC);

-- Documents Table
CREATE TABLE documents (
    document_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    collection_id UUID NOT NULL REFERENCES collections(collection_id) ON DELETE CASCADE,

    -- File Information
    filename VARCHAR(500) NOT NULL,
    mime_type VARCHAR(100) NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    file_hash VARCHAR(64) NOT NULL,  -- SHA-256 hash for deduplication

    -- Storage Paths
    minio_bucket VARCHAR(100) NOT NULL,
    minio_raw_path VARCHAR(1000) NOT NULL,
    minio_processed_path VARCHAR(1000),
    minio_chunks_path VARCHAR(1000),

    -- Metadata
    custom_metadata JSONB DEFAULT '{}',

    -- Processing Information
    chunk_count INTEGER DEFAULT 0,
    processing_duration_seconds NUMERIC(10, 2),

    -- Timestamps
    uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP WITH TIME ZONE,

    -- User Information (for future multi-tenancy)
    uploaded_by VARCHAR(255),

    CONSTRAINT unique_file_in_collection UNIQUE(collection_id, file_hash)
);

CREATE INDEX idx_documents_collection ON documents(collection_id);
CREATE INDEX idx_documents_filename ON documents(filename);
CREATE INDEX idx_documents_uploaded_at ON documents(uploaded_at DESC);
CREATE INDEX idx_documents_file_hash ON documents(file_hash);
CREATE INDEX idx_documents_custom_metadata ON documents USING GIN(custom_metadata);

-- Processing Jobs Table
CREATE TABLE processing_jobs (
    job_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
    collection_id UUID NOT NULL REFERENCES collections(collection_id) ON DELETE CASCADE,

    -- Job Status
    status VARCHAR(50) NOT NULL DEFAULT 'pending',  -- pending, processing, completed, failed

    -- Pipeline Steps Status (JSONB for flexibility)
    progress JSONB DEFAULT '{
        "upload": "pending",
        "parsing": "pending",
        "chunking": "pending",
        "embedding": "pending",
        "indexing": "pending"
    }',

    -- Error Handling
    error_message TEXT,
    error_details JSONB,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,

    CONSTRAINT valid_status CHECK (status IN ('pending', 'processing', 'completed', 'failed', 'retrying'))
);

CREATE INDEX idx_jobs_document ON processing_jobs(document_id);
CREATE INDEX idx_jobs_status ON processing_jobs(status);
CREATE INDEX idx_jobs_created_at ON processing_jobs(created_at DESC);

-- Document Chunks Table (for tracking chunks metadata)
CREATE TABLE document_chunks (
    chunk_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,

    -- Chunk Information
    chunk_index INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_size INTEGER NOT NULL,

    -- Vector Information
    qdrant_point_id VARCHAR(100),  -- Reference to Qdrant vector ID
    embedding_model VARCHAR(100) NOT NULL,

    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_chunk_in_document UNIQUE(document_id, chunk_index)
);

CREATE INDEX idx_chunks_document ON document_chunks(document_id);
CREATE INDEX idx_chunks_qdrant_point ON document_chunks(qdrant_point_id);

-- Audit Log Table (optional, for compliance)
CREATE TABLE audit_logs (
    log_id BIGSERIAL PRIMARY KEY,
    entity_type VARCHAR(50) NOT NULL,  -- 'collection', 'document', 'job'
    entity_id UUID NOT NULL,
    action VARCHAR(50) NOT NULL,  -- 'create', 'update', 'delete'
    actor VARCHAR(255),  -- User who performed the action
    changes JSONB,  -- Before/after state
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_created_at ON audit_logs(created_at DESC);
```

#### **Key Design Decisions**

1. **UUIDs for Primary Keys**: Better for distributed systems and privacy
2. **JSONB for Flexible Data**: `custom_metadata`, `progress`, `error_details` allow schema evolution
3. **Denormalized Counters**: `document_count`, `total_chunks` for fast dashboard queries
4. **Cascade Deletes**: When collection deleted, all related data automatically removed
5. **File Hash Deduplication**: SHA-256 prevents duplicate uploads within same collection
6. **Audit Trail**: Complete history for compliance and debugging

### Document Ingestion Flow (with PostgreSQL)

This comprehensive flow shows the complete transaction lifecycle with database operations:

```
┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 1: UPLOAD & INITIALIZATION (Synchronous - API Response)       │
└─────────────────────────────────────────────────────────────────────┘

1. User uploads document via POST /api/v1/ingest
   - File: multipart/form-data
   - Metadata: collection_name, custom_metadata (optional)
        ↓
2. FastAPI receives file + validates
   - Check file size (<50MB)
   - Verify MIME type (PDF/DOCX/TXT/CSV)
   - Calculate SHA-256 hash
        ↓
3. PostgreSQL Transaction BEGIN
        ↓
4. Check if collection exists in PostgreSQL
   SELECT collection_id FROM collections WHERE collection_name = ?
   - If not exists: CREATE collection
        ↓
5. Check for duplicate file (by hash)
   SELECT document_id FROM documents
   WHERE collection_id = ? AND file_hash = ?
   - If exists: Return 409 Conflict
        ↓
6. Generate UUIDs
   - document_id = gen_random_uuid()
   - job_id = gen_random_uuid()
        ↓
7. Store raw document in MinIO
   - Bucket: raw-documents
   - Path: {collection_name}/{document_id}/original.{ext}
   - Get minio_raw_path
        ↓
8. INSERT into documents table
   INSERT INTO documents (
       document_id, collection_id, filename, mime_type,
       file_size_bytes, file_hash, minio_bucket, minio_raw_path,
       custom_metadata, uploaded_at
   ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ↓
9. INSERT into processing_jobs table
   INSERT INTO processing_jobs (
       job_id, document_id, collection_id, status, progress
   ) VALUES (?, ?, ?, 'pending', '{"upload": "completed", ...}')
        ↓
10. UPDATE collections statistics
    UPDATE collections
    SET document_count = document_count + 1,
        updated_at = CURRENT_TIMESTAMP
    WHERE collection_id = ?
        ↓
11. PostgreSQL Transaction COMMIT
        ↓
12. Return UploadResponse to user
    {
        "job_id": "...",
        "status": "processing",
        "filename": "document.pdf",
        "collection_name": "my_collection",
        "minio_path": "raw-documents/my_collection/uuid/original.pdf",
        "created_at": "2025-10-20T..."
    }
        ↓
13. Schedule background processing task
    background_tasks.add_task(process_document, job_id)

┌─────────────────────────────────────────────────────────────────────┐
│ PHASE 2: BACKGROUND PROCESSING (Asynchronous)                       │
└─────────────────────────────────────────────────────────────────────┘

14. Update job status to 'processing'
    UPDATE processing_jobs
    SET status = 'processing', started_at = CURRENT_TIMESTAMP
    WHERE job_id = ?
        ↓
15. Update progress: parsing = 'in_progress'
    UPDATE processing_jobs
    SET progress = jsonb_set(progress, '{parsing}', '"in_progress"')
    WHERE job_id = ?
        ↓
16. Download file from MinIO
    GET raw-documents/{collection_name}/{document_id}/original.{ext}
        ↓
17. Parse document using preprocessing handlers
    - PDFHandler / DocxHandler / TextHandler / CSVHandler
    - Extract text, tables, metadata
        ↓
18. Update progress: parsing = 'completed', chunking = 'in_progress'
        ↓
19. Store parsed content in MinIO
    - Bucket: processed-documents
    - Path: {collection_name}/{document_id}/metadata.json
    - Update minio_processed_path in documents table
        ↓
20. Chunk text using semantic chunker
    - Chunk size: 512 tokens
    - Overlap: 50 tokens
    - Result: List[str] chunks
        ↓
21. Update progress: chunking = 'completed', embedding = 'in_progress'
        ↓
22. Store chunks in MinIO
    - Bucket: document-chunks
    - Path: {collection_name}/{document_id}/chunks.json
    - Update minio_chunks_path in documents table
        ↓
23. Generate embeddings for all chunks
    - Model: all-MiniLM-L6-v2
    - Dimension: 768
    - Batch processing for efficiency
        ↓
24. Update progress: embedding = 'completed', indexing = 'in_progress'
        ↓
25. PostgreSQL Transaction BEGIN
        ↓
26. For each chunk, INSERT into document_chunks table
    INSERT INTO document_chunks (
        chunk_id, document_id, chunk_index, chunk_text,
        chunk_size, embedding_model, created_at
    ) VALUES (?, ?, ?, ?, ?, 'all-MiniLM-L6-v2', CURRENT_TIMESTAMP)
        ↓
27. Store vectors in Qdrant
    - Collection: {collection_name}
    - Points: [{id: chunk_id, vector: embedding, payload: metadata}]
        ↓
28. UPDATE document_chunks with qdrant_point_id
    UPDATE document_chunks
    SET qdrant_point_id = ?
    WHERE chunk_id = ?
        ↓
29. UPDATE documents table with final stats
    UPDATE documents
    SET chunk_count = ?,
        processed_at = CURRENT_TIMESTAMP,
        processing_duration_seconds = ?
    WHERE document_id = ?
        ↓
30. UPDATE collections statistics
    UPDATE collections
    SET total_chunks = total_chunks + ?,
        updated_at = CURRENT_TIMESTAMP
    WHERE collection_id = ?
        ↓
31. UPDATE processing_jobs to 'completed'
    UPDATE processing_jobs
    SET status = 'completed',
        completed_at = CURRENT_TIMESTAMP,
        progress = '{"upload": "completed", "parsing": "completed",
                     "chunking": "completed", "embedding": "completed",
                     "indexing": "completed"}'
    WHERE job_id = ?
        ↓
32. PostgreSQL Transaction COMMIT
        ↓
33. Log success
    INSERT INTO audit_logs (entity_type, entity_id, action, actor)
    VALUES ('document', document_id, 'processed', 'system')
        ↓
34. Document ready for RAG queries!

┌─────────────────────────────────────────────────────────────────────┐
│ ERROR HANDLING (On Any Failure)                                     │
└─────────────────────────────────────────────────────────────────────┘

On Error in Background Processing:
    ↓
1. PostgreSQL Transaction ROLLBACK (if in transaction)
        ↓
2. UPDATE processing_jobs
   UPDATE processing_jobs
   SET status = 'failed',
       error_message = ?,
       error_details = ?::jsonb,
       completed_at = CURRENT_TIMESTAMP
   WHERE job_id = ?
        ↓
3. Check retry_count < max_retries
   - If yes: Schedule retry with exponential backoff
   - If no: Mark as permanently failed
        ↓
4. Log error
   INSERT INTO audit_logs (entity_type, entity_id, action, changes)
   VALUES ('job', job_id, 'failed', '{"error": "..."}'::jsonb)
        ↓
5. Cleanup orphaned MinIO objects (optional)
        ↓
6. Notify monitoring system (Prometheus/Grafana)
```

#### **Transaction Flow Benefits**

1. **ACID Compliance**: All database operations are atomic
2. **Data Consistency**: MinIO and PostgreSQL always in sync
3. **Idempotency**: Duplicate detection prevents reprocessing
4. **Observability**: Complete audit trail of all operations
5. **Error Recovery**: Rollback on failure, retry with backoff
6. **Real-time Status**: User can query job status at any point

---

## Detailed Implementation Plan

### Task 1: MinIO Storage Service (Priority: HIGH)

**File:** `app/services/storage.py`

**Purpose:** Abstraction layer for MinIO operations

**Features:**
- Initialize MinIO client with configuration
- Create buckets with proper policies
- Upload/download operations
- Generate presigned URLs for direct uploads
- List objects in bucket
- Delete objects
- Get object metadata

**API Design:**
```python
class MinIOStorageService:
    def __init__(self, endpoint, access_key, secret_key, secure=False)
    async def ensure_buckets_exist(self, bucket_names: List[str]) -> None
    async def upload_file(self, bucket: str, object_path: str, file_data: BinaryIO, metadata: Dict) -> str
    async def download_file(self, bucket: str, object_path: str) -> bytes
    async def get_presigned_url(self, bucket: str, object_path: str, expires_hours: int = 24) -> str
    async def list_objects(self, bucket: str, prefix: str = "") -> List[ObjectInfo]
    async def delete_object(self, bucket: str, object_path: str) -> bool
    async def get_metadata(self, bucket: str, object_path: str) -> Dict
```

**Tests:** `tests/unit/test_storage.py` (6-8 tests)
- test_minio_client_initialization
- test_bucket_creation
- test_file_upload
- test_file_download
- test_presigned_url_generation
- test_list_objects
- test_delete_object
- test_error_handling

**Estimated Time:** 2 hours

---

### Task 2: PostgreSQL Database Service (Priority: HIGH)

**File:** `app/services/database.py`

**Purpose:** Async PostgreSQL operations for metadata management

**Features:**
- Initialize PostgreSQL connection pool (asyncpg)
- Database migrations (Alembic)
- CRUD operations for collections, documents, processing_jobs
- Transaction management
- Query builders for complex filters
- Connection health checks

**API Design:**
```python
class DatabaseService:
    def __init__(self, database_url: str)

    async def connect(self) -> None
    async def disconnect(self) -> None
    async def health_check(self) -> bool

    # Collection operations
    async def create_collection(
        self, name: str, description: Optional[str] = None
    ) -> UUID

    async def get_collection(self, name: str) -> Optional[Dict]
    async def list_collections(self) -> List[Dict]
    async def delete_collection(self, collection_id: UUID) -> bool
    async def update_collection_stats(
        self, collection_id: UUID, document_delta: int = 0, chunks_delta: int = 0
    ) -> None

    # Document operations
    async def create_document(
        self,
        collection_id: UUID,
        filename: str,
        mime_type: str,
        file_size: int,
        file_hash: str,
        minio_bucket: str,
        minio_raw_path: str,
        custom_metadata: Optional[Dict] = None
    ) -> UUID

    async def get_document(self, document_id: UUID) -> Optional[Dict]
    async def list_documents(
        self, collection_id: UUID, offset: int = 0, limit: int = 100
    ) -> List[Dict]

    async def update_document_paths(
        self,
        document_id: UUID,
        processed_path: Optional[str] = None,
        chunks_path: Optional[str] = None
    ) -> None

    async def update_document_processing_complete(
        self, document_id: UUID, chunk_count: int, duration: float
    ) -> None

    async def check_duplicate_document(
        self, collection_id: UUID, file_hash: str
    ) -> Optional[UUID]

    async def delete_document(self, document_id: UUID) -> bool

    # Processing job operations
    async def create_processing_job(
        self, document_id: UUID, collection_id: UUID
    ) -> UUID

    async def get_job_status(self, job_id: UUID) -> Optional[Dict]

    async def update_job_status(
        self, job_id: UUID, status: str, error_msg: Optional[str] = None
    ) -> None

    async def update_job_progress(
        self, job_id: UUID, step: str, step_status: str
    ) -> None

    # Chunk operations
    async def create_chunks(
        self,
        document_id: UUID,
        chunks: List[Dict]  # [{chunk_index, chunk_text, chunk_size, embedding_model}]
    ) -> List[UUID]

    async def update_chunk_qdrant_id(
        self, chunk_id: UUID, qdrant_point_id: str
    ) -> None

    async def get_document_chunks(self, document_id: UUID) -> List[Dict]

    # Audit log operations
    async def log_audit(
        self, entity_type: str, entity_id: UUID, action: str,
        actor: Optional[str] = None, changes: Optional[Dict] = None
    ) -> None
```

**Database Migrations:**
```python
# migrations/versions/001_initial_schema.py
"""Initial schema for IntelliRAG Phase 5

Revision ID: 001
Create Date: 2025-10-20
"""

def upgrade():
    # Create all tables as shown in schema section

def downgrade():
    # Drop all tables in reverse order
```

**Tests:** `tests/unit/test_database.py` (10-12 tests)
- test_database_connection
- test_create_collection
- test_get_collection
- test_create_document
- test_check_duplicate_document
- test_create_processing_job
- test_update_job_progress
- test_create_chunks
- test_transaction_rollback
- test_concurrent_operations
- test_cascade_delete

**Estimated Time:** 3 hours

---

### Task 3: Enhanced Pydantic Schemas (Priority: HIGH)

**File:** `app/models/schemas.py` (update existing)

**New Models:**

```python
class UploadRequest(BaseModel):
    """Document upload request (multipart form)."""
    collection_name: str = Field(..., min_length=1, description="Collection to store document")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="Custom metadata")
    # File will be handled separately as UploadFile

class UploadResponse(BaseModel):
    """Document upload response."""
    job_id: str = Field(..., description="Unique job identifier (UUID)")
    status: str = Field(..., description="Processing status")
    filename: str = Field(..., description="Uploaded filename")
    collection_name: str = Field(..., description="Target collection")
    minio_path: str = Field(..., description="Path in MinIO storage")
    created_at: datetime = Field(..., description="Upload timestamp")

class ProcessingStep(str, Enum):
    """Processing pipeline steps."""
    UPLOAD = "upload"
    PARSING = "parsing"
    CHUNKING = "chunking"
    EMBEDDING = "embedding"
    INDEXING = "indexing"

class StepStatus(str, Enum):
    """Status of individual steps."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingProgress(BaseModel):
    """Progress of document processing."""
    upload: StepStatus = StepStatus.PENDING
    parsing: StepStatus = StepStatus.PENDING
    chunking: StepStatus = StepStatus.PENDING
    embedding: StepStatus = StepStatus.PENDING
    indexing: StepStatus = StepStatus.PENDING

class ProcessingStatus(BaseModel):
    """Document processing status."""
    job_id: str
    status: str  # "processing" | "completed" | "failed"
    progress: ProcessingProgress
    chunks_created: Optional[int] = None
    error: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None

class CollectionInfo(BaseModel):
    """Collection metadata."""
    collection_name: str
    document_count: int
    vector_count: int
    created_at: datetime
    last_modified: datetime

class CollectionCreateRequest(BaseModel):
    """Create new collection."""
    collection_name: str = Field(..., min_length=1, pattern="^[a-zA-Z0-9_-]+$")
    description: Optional[str] = None

class CollectionListResponse(BaseModel):
    """List of collections."""
    collections: List[CollectionInfo]
    total_count: int
```

**Tests:** Update `tests/unit/test_schemas.py` (+4-5 tests)

**Estimated Time:** 1 hour

---

### Task 3: Document Ingestion Service (Priority: HIGH)

**File:** `app/services/ingestion.py`

**Purpose:** Orchestrate document upload and processing

**Features:**
- Accept uploaded file
- Generate unique job_id
- Store raw file in MinIO
- Trigger async processing pipeline
- Track processing status
- Handle errors and retries

**API Design:**
```python
class IngestionService:
    def __init__(
        self,
        storage_service: MinIOStorageService,
        embedding_service: EmbeddingService,
        vectordb_service: VectorDBService,
        preprocessing_pipeline: PreprocessingPipeline
    )

    async def ingest_document(
        self,
        file: UploadFile,
        collection_name: str,
        metadata: Optional[Dict] = None
    ) -> UploadResponse

    async def process_document(self, job_id: str) -> None

    async def get_status(self, job_id: str) -> ProcessingStatus

    async def _update_progress(
        self,
        job_id: str,
        step: ProcessingStep,
        status: StepStatus
    ) -> None
```

**Processing Pipeline:**
1. Store file in MinIO (raw-documents bucket)
2. Parse document using existing preprocessing handlers
3. Store parsed content in MinIO (processed-documents bucket)
4. Chunk text using existing chunker
5. Store chunks in MinIO (document-chunks bucket)
6. Generate embeddings
7. Store vectors in Qdrant
8. Update status to completed

**Tests:** `tests/unit/test_ingestion.py` (5-6 tests)
- test_ingest_document_creates_job
- test_document_stored_in_minio
- test_processing_pipeline_execution
- test_status_tracking
- test_error_handling
- test_concurrent_ingestions

**Estimated Time:** 2 hours

---

### Task 4: Ingestion API Endpoints (Priority: HIGH)

**File:** `app/api/v1/ingest.py`

**Endpoints:**

#### POST /api/v1/ingest
```python
@router.post("/ingest", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    metadata: Optional[str] = Form(None),  # JSON string
    background_tasks: BackgroundTasks,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> UploadResponse:
    """
    Upload and process a document.

    Accepts: PDF, DOCX, TXT, CSV files
    Max size: 50MB
    """
```

#### GET /api/v1/ingest/status/{job_id}
```python
@router.get("/ingest/status/{job_id}", response_model=ProcessingStatus)
async def get_processing_status(
    job_id: str,
    ingestion_service: IngestionService = Depends(get_ingestion_service)
) -> ProcessingStatus:
    """Get processing status for uploaded document."""
```

#### GET /api/v1/collections
```python
@router.get("/collections", response_model=CollectionListResponse)
async def list_collections(
    collection_manager: CollectionManager = Depends(get_collection_manager)
) -> CollectionListResponse:
    """List all available collections."""
```

#### POST /api/v1/collections
```python
@router.post("/collections", response_model=CollectionInfo)
async def create_collection(
    request: CollectionCreateRequest,
    collection_manager: CollectionManager = Depends(get_collection_manager)
) -> CollectionInfo:
    """Create a new collection."""
```

#### DELETE /api/v1/collections/{collection_name}
```python
@router.delete("/collections/{collection_name}", status_code=204)
async def delete_collection(
    collection_name: str,
    collection_manager: CollectionManager = Depends(get_collection_manager)
) -> None:
    """Delete a collection and all its documents."""
```

**Tests:** `tests/unit/test_ingest_api.py` (4-5 tests)
- test_upload_document_endpoint
- test_get_status_endpoint
- test_file_validation
- test_error_responses

**Estimated Time:** 1.5 hours

---

### Task 5: Collection Management Service (Priority: MEDIUM)

**File:** `app/services/collection_manager.py`

**Purpose:** Manage collections and their metadata

**Features:**
- Create new collections in Qdrant
- Delete collections and associated MinIO objects
- List all collections
- Get collection statistics
- Track collection metadata

**API Design:**
```python
class CollectionManager:
    def __init__(
        self,
        vectordb_service: VectorDBService,
        storage_service: MinIOStorageService
    )

    async def create_collection(
        self,
        name: str,
        description: Optional[str] = None
    ) -> CollectionInfo

    async def delete_collection(self, name: str) -> bool

    async def list_collections(self) -> List[CollectionInfo]

    async def get_collection_info(self, name: str) -> CollectionInfo

    async def collection_exists(self, name: str) -> bool
```

**Tests:** `tests/unit/test_collection_manager.py` (4-5 tests)

**Estimated Time:** 1.5 hours

---

### Task 6: Environment Configuration (Priority: MEDIUM)

**Files:** `.env.example`, `app/config.py`

**`.env.example` Content:**
```env
# Application
APP_NAME=IntelliRAG
APP_VERSION=0.2.0
DEBUG=true

# PostgreSQL Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=intellirag
POSTGRES_USER=intellirag_user
POSTGRES_PASSWORD=change_me_in_production
DATABASE_URL=postgresql+asyncpg://intellirag_user:change_me_in_production@localhost:5432/intellirag

# Database Pool Settings
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
DB_POOL_TIMEOUT=30

# MinIO Configuration
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_SECURE=false
MINIO_REGION=us-east-1

# MinIO Buckets
RAW_DOCUMENTS_BUCKET=raw-documents
PROCESSED_DOCUMENTS_BUCKET=processed-documents
DOCUMENT_CHUNKS_BUCKET=document-chunks

# Qdrant Configuration
QDRANT_URL=http://localhost:6333

# vLLM Configuration
VLLM_BASE_URL=http://localhost:8000/v1
VLLM_MODEL=Qwen/Qwen3-0.6B

# Processing Configuration
MAX_FILE_SIZE_MB=50
ALLOWED_FILE_TYPES=pdf,docx,txt,csv
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

**`app/config.py` Content:**
```python
from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    # Application
    app_name: str = "IntelliRAG"
    app_version: str = "0.2.0"
    debug: bool = False

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "intellirag"
    postgres_user: str = "intellirag_user"
    postgres_password: str
    database_url: str  # Full connection string

    # Database Pool
    db_pool_min_size: int = 5
    db_pool_max_size: int = 20
    db_pool_timeout: int = 30

    # MinIO
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    minio_secure: bool = False
    minio_region: str = "us-east-1"

    # Buckets
    raw_documents_bucket: str = "raw-documents"
    processed_documents_bucket: str = "processed-documents"
    document_chunks_bucket: str = "document-chunks"

    # Qdrant
    qdrant_url: str = "http://localhost:6333"

    # vLLM
    vllm_base_url: str = "http://localhost:8000/v1"
    vllm_model: str = "Qwen/Qwen3-0.6B"

    # Processing
    max_file_size_mb: int = 50
    allowed_file_types: List[str] = ["pdf", "docx", "txt", "csv"]
    chunk_size: int = 512
    chunk_overlap: int = 50

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

# Global settings instance
settings = Settings()
```

**Estimated Time:** 0.5 hours

---

### Task 7: Integration Tests (Priority: HIGH)

**File:** `tests/integration/test_ingestion_integration.py`

**Test Scenarios:**
1. End-to-end document upload and processing
2. MinIO storage operations
3. Collection management
4. Error handling and recovery
5. Concurrent uploads
6. Large file handling

**Sample Tests:**
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_document_ingestion():
    """Test complete document ingestion flow."""
    # Upload document
    # Verify stored in MinIO
    # Wait for processing
    # Verify embeddings in Qdrant
    # Query document content

@pytest.mark.integration
@pytest.mark.asyncio
async def test_minio_storage_operations():
    """Test MinIO upload, download, delete."""

@pytest.mark.integration
@pytest.mark.asyncio
async def test_collection_management():
    """Test create, list, delete collections."""

@pytest.mark.integration
@pytest.mark.asyncio
async def test_processing_status_tracking():
    """Test status updates throughout pipeline."""
```

**Estimated Time:** 1.5 hours

---

## Deliverables

### Core Features
- ✅ Document upload endpoint (`POST /api/v1/ingest`)
- ✅ MinIO storage integration for raw documents
- ✅ Asynchronous processing pipeline
- ✅ Processing status tracking (`GET /api/v1/ingest/status/{job_id}`)
- ✅ Collection management (create/list/delete)
- ✅ Environment configuration (.env support)
- ✅ Error handling and logging

### Documentation
- ✅ Phase 5 implementation plan (this document)
- ✅ API documentation (OpenAPI/Swagger auto-generated)
- ✅ MinIO setup guide
- ✅ Document ingestion user guide
- ✅ Architecture diagrams

### Tests
- ✅ Unit tests: ~25 new tests
- ✅ Integration tests: 6-8 tests
- ✅ Test coverage: >80% on all new code
- ✅ All existing tests still passing

### Infrastructure
- ✅ MinIO Docker Compose configuration
- ✅ Environment variables template
- ✅ Configuration management system

---

## Success Metrics

### Functional Metrics
- [ ] Documents successfully uploaded to MinIO
- [ ] Processing pipeline completes without errors
- [ ] Uploaded documents searchable via RAG queries
- [ ] Collections properly isolated (no cross-contamination)
- [ ] Status tracking accurate throughout pipeline
- [ ] Error handling prevents data loss

### Performance Metrics
- [ ] Document upload: <2 seconds for 10MB file
- [ ] Processing pipeline: <30 seconds for typical PDF
- [ ] Status check: <100ms response time
- [ ] Concurrent uploads: Support 5+ simultaneous users

### Quality Metrics
- [ ] Test coverage: >80% on new code
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] No critical bugs or security issues
- [ ] Proper logging throughout pipeline
- [ ] Error messages clear and actionable

### User Experience Metrics
- [ ] Clear upload feedback
- [ ] Real-time status updates
- [ ] Helpful error messages
- [ ] Intuitive collection management

---

## Risk Assessment & Mitigation

### Technical Risks

#### 1. Large File Handling
**Risk:** Memory overflow with large PDF files
**Mitigation:**
- Implement streaming file uploads
- Process documents in chunks
- Set maximum file size limit (50MB initially)
- Add file size validation

#### 2. Processing Failures
**Risk:** Pipeline failures leave orphaned data
**Mitigation:**
- Implement retry logic with exponential backoff
- Store processing state in database
- Add cleanup tasks for failed jobs
- Comprehensive error logging

#### 3. MinIO Availability
**Risk:** MinIO service downtime blocks uploads
**Mitigation:**
- Health checks before operations
- Graceful degradation
- Clear error messages to user
- Retry logic for transient failures

#### 4. Concurrent Processing
**Risk:** Race conditions with parallel uploads
**Mitigation:**
- Use unique job IDs (UUID)
- Atomic operations where possible
- Proper locking for shared resources
- Thorough concurrent testing

### Dependencies

**External Services:**
- PostgreSQL (metadata database)
- MinIO (object storage)
- Qdrant (vector database)
- vLLM (LLM inference)

**Infrastructure:**
- Sufficient disk space for documents
- Network bandwidth for file uploads
- GPU for embedding generation

**Python Packages:**
- `minio` - MinIO Python SDK
- `asyncpg` - Async PostgreSQL driver
- `sqlalchemy[asyncio]` - ORM and query builder (optional, for complex queries)
- `alembic` - Database migrations
- `python-multipart` - File upload handling
- `pydantic-settings` - Configuration management

---

## Future Enhancements (Phase 6+)

### Immediate Next Steps (Phase 6)
1. **Query Router with LangGraph**
   - Intelligent query classification
   - Conditional RAG routing
   - Multi-step reasoning

2. **API Authentication**
   - JWT token authentication
   - API key management
   - Role-based access control

3. **Rate Limiting**
   - Per-user request limits
   - Fair usage policies
   - DDoS protection

### Medium-Term (Phase 7-8)
1. **Batch Processing**
   - Upload multiple documents at once
   - Bulk import from S3/cloud storage
   - Scheduled reprocessing

2. **Document Versioning**
   - Track document changes
   - Reprocess on updates
   - Version history

3. **Advanced Features**
   - OCR for scanned documents
   - Table extraction
   - Image processing
   - Multi-modal embeddings

### Long-Term (Phase 9+)
1. **Observability**
   - Prometheus metrics
   - Grafana dashboards
   - Jaeger distributed tracing
   - Loki centralized logging

2. **Production Deployment**
   - Kubernetes manifests
   - Helm charts
   - CI/CD pipeline
   - Load testing

3. **Advanced RAG**
   - Document deduplication
   - Automatic summarization
   - Citation generation
   - Multi-hop reasoning

---

## Development Guidelines

### TDD Workflow
1. **RED**: Write failing test first
2. **GREEN**: Implement minimal code to pass
3. **REFACTOR**: Improve code while keeping tests green

### Code Quality Standards
- Type hints for all functions
- Docstrings for all public APIs
- Logging at appropriate levels
- Error handling with specific exceptions
- Input validation with Pydantic

### Testing Requirements
- Unit tests for all services
- Integration tests for API endpoints
- Mock external dependencies in unit tests
- Use real services for integration tests
- Maintain >80% coverage

### Commit Standards
- Conventional commit format: `type(scope): description`
- Clear, descriptive messages
- Atomic commits (one feature/fix per commit)
- No AI attribution in commits

---

## Timeline & Milestones

### Week 1: Core Infrastructure (6-7 hours)
- [x] Day 1: Project planning and documentation
- [ ] Day 2: PostgreSQL database service + migrations + tests (3h)
- [ ] Day 3: MinIO storage service + tests (2h)
- [ ] Day 4: Enhanced schemas + tests (1h)

### Week 2: Services & API (5-6 hours)
- [ ] Day 5: Ingestion service + tests (2h)
- [ ] Day 6: Ingestion API endpoints + tests (1.5h)
- [ ] Day 7: Collection management + tests (1.5h)
- [ ] Day 8: Environment configuration (0.5h)

### Week 3: Testing & Documentation (2-3 hours)
- [ ] Day 9: Integration tests (1.5h)
- [ ] Day 10: Bug fixes and optimizations (1h)
- [ ] Day 11: Final documentation and demo (0.5h)

**Total Estimated Time:** 13-16 hours (with PostgreSQL integration)

---

## Getting Started

### Prerequisites
```bash
# Install PostgreSQL via Docker
docker run -d \
  --name postgres \
  -p 5432:5432 \
  -e POSTGRES_DB=intellirag \
  -e POSTGRES_USER=intellirag_user \
  -e POSTGRES_PASSWORD=change_me_in_production \
  -v postgres_data:/var/lib/postgresql/data \
  postgres:16-alpine

# Verify PostgreSQL running
docker exec postgres pg_isready

# Install MinIO via Docker
docker run -d \
  --name minio \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  -v minio_data:/data \
  minio/minio server /data --console-address ":9001"

# Verify MinIO running
curl http://localhost:9000/minio/health/live

# Access MinIO console: http://localhost:9001
```

### Development Setup
```bash
# Add dependencies
uv add minio asyncpg "sqlalchemy[asyncio]" alembic

# Create .env file
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# Run database migrations
uv run alembic upgrade head

# Run existing services
docker run -d -p 6333:6333 qdrant/qdrant:latest
docker run -d --gpus all -p 8000:8000 vllm/vllm-openai --model Qwen/Qwen3-0.6B

# Start development server
uv run uvicorn app.main:app --reload
```

### Database Management
```bash
# Create new migration
uv run alembic revision -m "description"

# Apply migrations
uv run alembic upgrade head

# Rollback migration
uv run alembic downgrade -1

# Check current migration
uv run alembic current

# View migration history
uv run alembic history

# Access PostgreSQL CLI
docker exec -it postgres psql -U intellirag_user -d intellirag
```

---

## Summary

Phase 5 transforms IntelliRAG from a demo system with pre-loaded data into a **production-ready application** where users can upload their own documents and get intelligent answers.

**Key Achievements:**
- **Complete document lifecycle management**: upload → storage → processing → indexing → retrieval → generation
- **Dual-storage architecture**: PostgreSQL for metadata, MinIO for raw documents, Qdrant for vectors
- **ACID-compliant transactions**: Reliable processing with rollback on failure
- **Real-time status tracking**: Complete observability of document processing pipeline
- **Production-grade deduplication**: SHA-256 hash-based duplicate detection

**Next Phase Preview:** Phase 6 will add intelligent query routing with LangGraph and API authentication for production deployment.

---

**Document Version:** 2.0
**Last Updated:** 2025-10-20
**Author:** IntelliRAG Team
**Status:** Ready for Implementation 🚀

**Changelog:**
- **v2.0 (2025-10-20)**: Added PostgreSQL integration for metadata management
  - Added PostgreSQL database schema (collections, documents, processing_jobs, document_chunks, audit_logs)
  - Added detailed transaction flow for document uploads
  - Added DatabaseService implementation task
  - Updated environment configuration with PostgreSQL settings
  - Updated dependencies (asyncpg, sqlalchemy, alembic)
  - Updated timeline to 13-16 hours
- **v1.0 (2025-10-19)**: Initial plan with MinIO-only storage

---

**END OF PLAN**
