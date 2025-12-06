# Phase 2: LangChain Integration with BGE-M3 - Implementation Plan

**Version**: 1.0  
**Date**: 2025-10-24  
**Status**: 🟡 **IN PROGRESS** - Core embedding working, loaders pending

---

## 🎯 Phase 2 Objectives

Implement LangChain document loaders, upgrade to BGE-M3 embedding model (1024 dims), and create a multi-class query router using LangGraph.

### User Choices
- ✅ **Retrieval Mode**: Dense + Sparse (hybrid)
- ✅ **Migration**: Replace existing 768-dim collection with 1024-dim
- ✅ **Loaders**: GCS, DOCX, URL, Markdown
- ✅ **Router**: Multi-class (RAG, Direct, Clarification, Multi-hop)

---

## ✅ Completed Work (2025-10-24)

### 1. BGE-M3 Core Embedding Service
**Status**: ✅ DONE

**Files Created**:
- `app/services/bge_m3_embedding.py` - Core service implementation
- `tests/unit/test_bge_m3_embedding.py` - Unit tests

**Functionality Implemented**:
- ✅ Service initialization with configurable device and FP16
- ✅ Lazy model loading (2GB BGE-M3 model)
- ✅ Dense embedding generation (`embed_single()`)
- ✅ 1024-dimensional vector output
- ✅ Empty text handling (zero vector)

**Test Results**:
```
tests/unit/test_bge_m3_embedding.py::TestBGEM3EmbeddingServiceInit::test_init_with_defaults PASSED
tests/unit/test_bge_m3_embedding.py::TestBGEM3EmbeddingServiceInit::test_get_embedding_dimension PASSED
tests/unit/test_bge_m3_embedding.py::TestBGEM3EmbeddingServiceInit::test_embed_single_dense PASSED
```

**Model Info**:
- Model ID: `BAAI/bge-m3`
- Size: ~2GB (30 files downloaded)
- Dimensions: 1024
- Load time: ~50 seconds (first run)
- Embedding time: ~5 seconds per call

---

## 🚧 Remaining Work

### Priority 1: Complete BGE-M3 Service (Week 1, Day 1-2)

#### A. Batch Dense Embedding
**File**: `app/services/bge_m3_embedding.py`

**Add Methods**:
```python
def embed_batch(
    self, 
    texts: List[str],
    batch_size: Optional[int] = None,
    show_progress: bool = False
) -> List[List[float]]:
    """Generate dense embeddings for batch of texts."""
    # Use model.encode() with batch processing
    # Return list of 1024-dim vectors
```

**Tests to Add** (one at a time per TDD):
```python
def test_embed_batch_dense(self):
    """Test batch dense embedding generation."""

def test_embed_batch_empty_list(self):
    """Test batch embedding with empty list."""

def test_embed_batch_multilingual(self):
    """Test batch embedding with multilingual texts."""
```

#### B. Sparse Embedding Support
**Add Methods**:
```python
def embed_single_sparse(self, text: str) -> Dict[str, List]:
    """Generate sparse embedding (vocabulary-based)."""
    result = self.model.encode(
        [text],
        return_dense=False,
        return_sparse=True,
        return_colbert_vecs=False
    )
    # Extract sparse vectors (indices + values)
    sparse_emb = result['lexical_weights'][0]
    return {
        "indices": list(sparse_emb.keys()),
        "values": list(sparse_emb.values())
    }

def embed_batch_sparse(self, texts: List[str]) -> List[Dict[str, List]]:
    """Generate sparse embeddings for batch."""
```

**Tests to Add**:
```python
def test_embed_single_sparse(self):
def test_embed_batch_sparse(self):
```

#### C. Hybrid Embedding (Dense + Sparse)
**Add Methods**:
```python
def embed_single_hybrid(self, text: str) -> Dict[str, Any]:
    """Generate both dense and sparse embeddings."""
    result = self.model.encode(
        [text],
        return_dense=True,
        return_sparse=True,
        return_colbert_vecs=False
    )
    return {
        "dense": result['dense_vecs'][0].tolist(),
        "sparse": {
            "indices": list(result['lexical_weights'][0].keys()),
            "values": list(result['lexical_weights'][0].values())
        }
    }

def embed_batch_hybrid(self, texts: List[str]) -> List[Dict[str, Any]]:
    """Generate hybrid embeddings for batch."""
```

**Tests to Add**:
```python
def test_embed_single_hybrid(self):
def test_embed_batch_hybrid(self):
```

#### D. Async Methods
**Add Methods**:
```python
async def embed_single_async(self, text: str) -> List[float]:
    """Async version of embed_single."""
    import asyncio
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self.embed_single, text)

async def embed_batch_async(self, texts: List[str]) -> List[List[float]]:
    """Async version of embed_batch."""

async def embed_batch_hybrid_async(self, texts: List[str]) -> List[Dict[str, Any]]:
    """Async version of embed_batch_hybrid."""
```

**Tests to Add**:
```python
@pytest.mark.asyncio
async def test_embed_single_async(self):

@pytest.mark.asyncio
async def test_embed_batch_async(self):

@pytest.mark.asyncio
async def test_embed_batch_hybrid_async(self):
```

---

### Priority 2: Update VectorDB for Hybrid Retrieval (Week 1, Day 2-3)

#### A. Modify Qdrant Collection Schema
**File**: `app/services/vectordb.py`

**Changes Needed**:
1. Update `create_collection()` for 1024-dim vectors
2. Add sparse vector support in payload
3. Implement hybrid search method

**New Methods**:
```python
async def upsert_vectors_hybrid(
    self,
    collection_name: str,
    dense_vectors: List[List[float]],
    sparse_vectors: List[Dict[str, List]],
    payloads: List[Dict[str, Any]],
    ids: List[str]
) -> bool:
    """Upsert both dense and sparse vectors."""
    points = [
        PointStruct(
            id=point_id,
            vector=dense_vec,
            payload={
                **payload,
                "sparse_embedding": sparse_vec  # Store sparse in payload
            }
        )
        for point_id, dense_vec, sparse_vec, payload 
        in zip(ids, dense_vectors, sparse_vectors, payloads)
    ]
    await self.client.upsert(collection_name=collection_name, points=points)
    return True

async def search_vectors_hybrid(
    self,
    collection_name: str,
    query_dense: List[float],
    query_sparse: Dict[str, List],
    limit: int = 10,
    alpha: float = 0.7  # Dense weight
) -> List:
    """Hybrid search combining dense and sparse."""
    # Perform dense search
    dense_results = await self.search_vectors(
        collection_name, query_dense, limit=limit*2
    )
    
    # Implement sparse matching using payload filter
    # Combine scores: final_score = alpha * dense_score + (1-alpha) * sparse_score
    # Return top K results
```

**Tests to Add**:
```python
@pytest.mark.asyncio
async def test_upsert_vectors_hybrid(self):

@pytest.mark.asyncio
async def test_search_vectors_hybrid(self):
```

#### B. Migration Script
**File**: `scripts/migrate_to_bge_m3.py`

**Functionality**:
1. Backup existing 768-dim collection
2. Create new 1024-dim collection
3. Re-embed all documents with BGE-M3
4. Validate retrieval quality

---

### Priority 3: LangChain Document Loaders (Week 1, Day 3-5)

#### A. Directory Structure
```
app/services/loaders/
├── __init__.py
├── base.py              # Abstract base loader
├── gcs_loader.py        # GCS integration
├── docx_loader.py       # DOCX handler
├── url_loader.py        # Web page loader
├── markdown_loader.py   # Markdown files
└── loader_factory.py    # Factory pattern
```

#### B. Base Loader Interface
**File**: `app/services/loaders/base.py`

```python
from abc import ABC, abstractmethod
from typing import List, Dict, Any
from langchain.schema import Document

class BaseDocumentLoader(ABC):
    """Abstract base class for document loaders."""
    
    @abstractmethod
    async def load(self, source: str) -> List[Document]:
        """Load documents from source."""
        pass
    
    @abstractmethod
    def get_loader_type(self) -> str:
        """Return loader type identifier."""
        pass
```

#### C. GCS Loader
**File**: `app/services/loaders/gcs_loader.py`

```python
from langchain_community.document_loaders import GCSFileLoader
from app.services.gcs_storage import GCSStorageService

class GCSDocumentLoader(BaseDocumentLoader):
    """Load documents from Google Cloud Storage."""
    
    def __init__(self, gcs_service: GCSStorageService):
        self.gcs_service = gcs_service
    
    async def load(self, gcs_uri: str) -> List[Document]:
        """Load document from GCS URI (gs://bucket/path)."""
        # Parse GCS URI
        # Download file to temp location
        # Use appropriate LangChain loader based on file type
        # Return Document objects with metadata
```

**Tests**:
```python
@pytest.mark.asyncio
async def test_gcs_loader_pdf(self):
@pytest.mark.asyncio
async def test_gcs_loader_with_metadata(self):
```

#### D. DOCX Loader
**File**: `app/services/loaders/docx_loader.py`

```python
from langchain_community.document_loaders import UnstructuredWordDocumentLoader

class DOCXDocumentLoader(BaseDocumentLoader):
    """Load and parse DOCX files."""
    
    async def load(self, file_path: str) -> List[Document]:
        """Load DOCX with table/image extraction."""
        loader = UnstructuredWordDocumentLoader(file_path)
        documents = await loop.run_in_executor(None, loader.load)
        return documents
```

#### E. URL Loader
**File**: `app/services/loaders/url_loader.py`

```python
from langchain_community.document_loaders import WebBaseLoader

class URLDocumentLoader(BaseDocumentLoader):
    """Load web pages."""
    
    async def load(self, url: str) -> List[Document]:
        """Load web page content."""
        loader = WebBaseLoader(url)
        documents = await loop.run_in_executor(None, loader.load)
        return documents
```

#### F. Markdown Loader
**File**: `app/services/loaders/markdown_loader.py`

```python
from langchain_community.document_loaders import UnstructuredMarkdownLoader

class MarkdownDocumentLoader(BaseDocumentLoader):
    """Load markdown files with formatting preservation."""
    
    async def load(self, file_path: str) -> List[Document]:
        """Load markdown with code blocks and headers."""
        loader = UnstructuredMarkdownLoader(file_path)
        documents = await loop.run_in_executor(None, loader.load)
        return documents
```

---

### Priority 4: Multi-Class Query Router (Week 1, Day 5-6)

#### Directory Structure
```
app/services/query_router/
├── __init__.py
├── classifier.py        # Query classification
├── graph.py             # LangGraph state machine
├── router.py            # Main router service
└── prompts.py           # Classification prompts
```

#### A. Query Classifier
**File**: `app/services/query_router/classifier.py`

```python
from enum import Enum
from pydantic import BaseModel

class QueryType(Enum):
    RAG = "rag"                    # Requires document retrieval
    DIRECT = "direct"               # Can answer directly
    CLARIFICATION = "clarification" # Needs more info
    MULTI_HOP = "multi_hop"        # Requires multi-step reasoning

class QueryClassification(BaseModel):
    query_type: QueryType
    confidence: float
    reasoning: str

class QueryClassifier:
    """Classify queries using LLM."""
    
    def __init__(self, llm_client):
        self.llm = llm_client
    
    async def classify(self, query: str) -> QueryClassification:
        """Classify query into one of 4 categories."""
        # Use LLM with classification prompt
        # Return QueryClassification with confidence
```

#### B. LangGraph State Graph
**File**: `app/services/query_router/graph.py`

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

class QueryState(TypedDict):
    query: str
    classification: QueryClassification
    context: Optional[List[str]]
    response: Optional[str]
    error: Optional[str]

def build_router_graph() -> StateGraph:
    """Build LangGraph state machine for query routing."""
    graph = StateGraph(QueryState)
    
    # Add nodes
    graph.add_node("classify", classify_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)
    
    # Add edges with conditional routing
    graph.add_conditional_edges(
        "classify",
        route_based_on_type,
        {
            QueryType.RAG: "retrieve",
            QueryType.DIRECT: "generate",
            QueryType.CLARIFICATION: "generate",
            QueryType.MULTI_HOP: "retrieve"
        }
    )
    
    graph.set_entry_point("classify")
    return graph.compile()
```

---

### Priority 5: Document Ingestion Pipeline (Week 1, Day 6-7)

#### File Structure
```
app/services/ingestion/
├── __init__.py
├── pipeline.py          # Main orchestrator
└── batch.py             # Batch processor
```

#### Pipeline Orchestrator
**File**: `app/services/ingestion/pipeline.py`

```python
class IngestionPipeline:
    """Orchestrate document ingestion: Load → Parse → Chunk → Embed → Store."""
    
    def __init__(
        self,
        loader_factory,
        chunker,
        embedding_service: BGEM3EmbeddingService,
        vectordb_service
    ):
        self.loader_factory = loader_factory
        self.chunker = chunker
        self.embedding = embedding_service
        self.vectordb = vectordb_service
    
    async def ingest_document(
        self,
        source: str,
        source_type: str,
        collection_name: str
    ) -> Dict[str, Any]:
        """Ingest single document end-to-end."""
        # 1. Load document
        loader = self.loader_factory.get_loader(source_type)
        documents = await loader.load(source)
        
        # 2. Chunk documents
        chunks = self.chunker.chunk_documents(documents)
        
        # 3. Generate embeddings (hybrid)
        texts = [chunk.page_content for chunk in chunks]
        embeddings = await self.embedding.embed_batch_hybrid_async(texts)
        
        # 4. Prepare payloads
        payloads = [self._build_payload(chunk, emb) for chunk, emb in zip(chunks, embeddings)]
        
        # 5. Store in Qdrant
        await self.vectordb.upsert_vectors_hybrid(
            collection_name=collection_name,
            dense_vectors=[e["dense"] for e in embeddings],
            sparse_vectors=[e["sparse"] for e in embeddings],
            payloads=payloads,
            ids=[str(uuid.uuid4()) for _ in chunks]
        )
        
        return {
            "status": "success",
            "chunks_processed": len(chunks),
            "source": source
        }
```

---

### Priority 6: API Endpoints (Week 1, Day 7-8)

#### A. Upload Endpoint
**File**: `app/api/v1/upload.py`

```python
@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks
):
    """Upload document to GCS and trigger ingestion."""
    # 1. Validate file type
    # 2. Upload to GCS
    # 3. Trigger ingestion pipeline (background task)
    # 4. Return upload status + job ID
```

#### B. Ingest Endpoint
**File**: `app/api/v1/ingest.py`

```python
@router.post("/ingest")
async def ingest_document(
    request: IngestRequest,
    background_tasks: BackgroundTasks
):
    """Trigger document ingestion from GCS URI or URL."""
    # 1. Validate source
    # 2. Determine loader type
    # 3. Start ingestion pipeline
    # 4. Return job status
```

#### C. Query Endpoint Updates
**File**: `app/api/v1/query.py`

```python
@router.post("/query")
async def query_endpoint(request: QueryRequest):
    """Query with multi-class routing and hybrid search."""
    # 1. Classify query using QueryRouter
    # 2. Route based on classification
    # 3. If RAG: perform hybrid search
    # 4. Generate response
    # 5. Return with metadata (classification, confidence, sources)
```

---

## 📊 Success Criteria

### Performance Metrics
- [ ] BGE-M3 embedding latency < 100ms per query
- [ ] Hybrid retrieval nDCG@10 > 0.75
- [ ] Query routing accuracy > 90%
- [ ] Document ingestion throughput > 10 docs/sec

### Quality Metrics
- [ ] Test coverage > 80% (maintained)
- [ ] All unit tests passing
- [ ] All integration tests passing
- [ ] Zero critical bugs

### Functional Requirements
- [ ] All 4 document loaders working
- [ ] Hybrid search operational
- [ ] Multi-class routing functional
- [ ] API endpoints responding correctly

---

## 🎯 Next Immediate Steps

1. ✅ **DONE**: Core BGE-M3 embedding working
2. **CURRENT**: Complete remaining BGE-M3 methods (batch, sparse, hybrid, async)
3. **NEXT**: Update VectorDB for hybrid retrieval
4. **THEN**: Implement 4 document loaders
5. **AFTER**: Build multi-class query router
6. **FINALLY**: Create ingestion pipeline and API endpoints

---

## 📝 Notes

- BGE-M3 model is ~2GB - ensure sufficient disk space
- Model download happens on first use (auto-cached)
- FP16 can be enabled for faster inference on GPU
- Hybrid retrieval typically gives 10-15% accuracy improvement over dense-only
- Consider implementing caching for frequently used embeddings

---

**Last Updated**: 2025-10-24  
**Status**: Living document - will be updated as implementation progresses
