# Phase 3: Integration Testing with Real Services

**Date:** 2025-10-17
**Project:** IntelliRAG - Production-Ready RAG System
**Feature:** Integration Testing for EmbeddingService and VectorDBService
**Methodology:** Test-Driven Development (TDD)
**Coverage Target:** >70% (Integration Tests)
**Priority:** HIGH (Validate Foundation Before Building Pipeline)

**Version:** 1.0
**Prerequisites:** ✅ Phase 1 (EmbeddingService Unit Tests) Complete, ✅ Phase 2 (VectorDBService Unit Tests) Complete

---

## 1. EXECUTIVE SUMMARY

### What We've Completed

**Phase 1: EmbeddingService Unit Tests** ✅
- 24 unit tests passing
- Mocked SentenceTransformer model
- CPU/GPU device management tested
- Async operations validated
- Coverage: >85%

**Phase 2: VectorDBService Unit Tests** ✅
- 13 unit tests passing
- Mocked AsyncQdrantClient
- CRUD operations tested
- Vector operations validated
- Coverage: >85%

### What's Next: Phase 3

**Phase 3: Integration Testing**
1. **Setup Real Services** - Qdrant Docker, real embedding model
2. **EmbeddingService Integration Tests** - Test with actual model
3. **VectorDBService Integration Tests** - Test with actual Qdrant
4. **End-to-End Integration Tests** - Test full workflow
5. **Performance Benchmarking** - Measure real-world performance

**Why This Phase Matters:**
- Unit tests use mocks - they don't catch real-world integration issues
- Need to validate actual Qdrant connection handling
- Need to test real embedding model loading and inference
- Need to verify 768-dimensional vectors work with Qdrant
- Need to measure actual performance metrics
- Catch compatibility issues early before building pipeline

---

## 2. ARCHITECTURE OVERVIEW

### Integration Test Scope

```
┌─────────────────────────────────────────────────────────┐
│                   Integration Tests                      │
│  ┌──────────────────────────────────────────────────┐   │
│  │   Test Real EmbeddingService                     │   │
│  │   ↓ (no mocks)                                   │   │
│  │   Actual SentenceTransformer Model               │   │
│  │   • Model download (~420MB)                      │   │
│  │   • CPU/GPU inference                            │   │
│  │   • Batch processing (128 vectors)               │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │   Test Real VectorDBService                      │   │
│  │   ↓ (no mocks)                                   │   │
│  │   Actual Qdrant Instance                         │   │
│  │   • Docker container (localhost:6333)            │   │
│  │   • Collection management                        │   │
│  │   • Vector upsert (768-d)                        │   │
│  │   • Similarity search                            │   │
│  └──────────────────────────────────────────────────┘   │
│                                                          │
│  ┌──────────────────────────────────────────────────┐   │
│  │   Test End-to-End Workflow                       │   │
│  │   • Text → Embedding (768-d)                     │   │
│  │   • Embedding → Storage (Qdrant)                 │   │
│  │   • Query → Retrieval (Similarity Search)        │   │
│  │   • Performance Benchmarking                     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 3. PREREQUISITES SETUP

### 3.1 Qdrant Docker Setup

```bash
# Pull Qdrant image
docker pull qdrant/qdrant:latest

# Run Qdrant container
docker run -d \
  --name qdrant-test \
  -p 6333:6333 \
  -p 6334:6334 \
  -v $(pwd)/qdrant_storage:/qdrant/storage \
  qdrant/qdrant:latest

# Verify Qdrant is running
curl http://localhost:6333/health

# Expected response: {"title":"qdrant - vector search engine","version":"1.15.1+"}
```

### 3.2 Test Data Preparation

```python
# tests/fixtures/integration_data.py

SAMPLE_TEXTS = [
    "Python is a high-level programming language.",
    "Machine learning enables computers to learn from data.",
    "Vector databases store high-dimensional embeddings.",
    "Natural language processing helps computers understand text.",
    "Deep learning uses neural networks with multiple layers.",
]

SAMPLE_DOCUMENTS = [
    {
        "id": "doc_1",
        "text": "Python is a versatile programming language used for web development, data science, and automation.",
        "metadata": {"category": "programming", "language": "en"}
    },
    {
        "id": "doc_2",
        "text": "Vector databases like Qdrant enable semantic search through similarity comparisons.",
        "metadata": {"category": "databases", "language": "en"}
    },
    {
        "id": "doc_3",
        "text": "Embedding models convert text into numerical vectors for machine learning.",
        "metadata": {"category": "ai", "language": "en"}
    },
]
```

---

## 4. TASK BREAKDOWN

### Phase 3.1: EmbeddingService Integration Tests (3 hours)

#### Task 3.1.1: Test Model Loading and Inference (1.5 hours)

**Purpose**: Verify real model downloads, loads, and generates embeddings

**Test Specifications**:
```python
# tests/integration/test_embedding_integration.py

import pytest
import numpy as np

@pytest.mark.integration
def test_embedding_service_loads_real_model():
    """Test EmbeddingService loads actual model from HuggingFace."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()

    # Verify model loads (may take ~20-30s on first run)
    assert service.model is not None
    assert service.get_embedding_dimension() == 768


@pytest.mark.integration
def test_embedding_service_generates_real_embeddings():
    """Test real embedding generation (not mocked)."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()

    text = "This is a test sentence for embedding."
    embedding = service.embed_single(text)

    # Verify embedding properties
    assert isinstance(embedding, list)
    assert len(embedding) == 768
    assert all(isinstance(x, float) for x in embedding)

    # Verify embeddings are not zero vectors
    assert not all(x == 0.0 for x in embedding)

    # Verify embeddings are normalized (L2 norm should be reasonable)
    norm = np.linalg.norm(embedding)
    assert 0.1 < norm < 10.0  # Reasonable range


@pytest.mark.integration
def test_embedding_service_batch_real_inference():
    """Test batch embedding with real model."""
    from app.services.embedding import EmbeddingService
    from tests.fixtures.integration_data import SAMPLE_TEXTS

    service = EmbeddingService()

    embeddings = service.embed_batch(SAMPLE_TEXTS)

    # Verify batch results
    assert len(embeddings) == len(SAMPLE_TEXTS)
    assert all(len(emb) == 768 for emb in embeddings)

    # Verify embeddings are different for different texts
    emb1 = np.array(embeddings[0])
    emb2 = np.array(embeddings[1])
    cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

    # Similar texts should have high similarity, but not identical
    assert 0.0 < cosine_sim < 1.0


@pytest.mark.integration
@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_embedding_service_gpu_acceleration():
    """Test GPU-accelerated batch embedding."""
    from app.services.embedding import EmbeddingService
    import time

    service = EmbeddingService(device="cpu")

    texts = [f"Test sentence number {i}" for i in range(100)]

    # Benchmark CPU
    start_cpu = time.time()
    cpu_embeddings = service.embed_batch(texts, use_gpu=False)
    cpu_duration = time.time() - start_cpu

    # Benchmark GPU
    start_gpu = time.time()
    gpu_embeddings = service.embed_batch(texts, use_gpu=True)
    gpu_duration = time.time() - start_gpu

    # Verify results are similar
    assert len(cpu_embeddings) == len(gpu_embeddings)

    # GPU should be faster (at least 1.5x for 100 vectors)
    assert gpu_duration < cpu_duration / 1.5

    print(f"CPU: {cpu_duration:.3f}s, GPU: {gpu_duration:.3f}s, Speedup: {cpu_duration/gpu_duration:.2f}x")


@pytest.mark.integration
def test_embedding_service_multilingual():
    """Test multilingual embedding support."""
    from app.services.embedding import EmbeddingService

    service = EmbeddingService()

    texts = {
        'en': "Hello world",
        'fr': "Bonjour le monde",
        'es': "Hola mundo",
        'vi': "Xin chào thế giới",
        'de': "Hallo Welt"
    }

    embeddings = {}
    for lang, text in texts.items():
        embeddings[lang] = service.embed_single(text)

    # All embeddings should be valid 768-d vectors
    assert all(len(emb) == 768 for emb in embeddings.values())

    # Similar meanings should have high similarity
    # "Hello world" variants should be similar to each other
    en_emb = np.array(embeddings['en'])
    fr_emb = np.array(embeddings['fr'])

    similarity = np.dot(en_emb, fr_emb) / (np.linalg.norm(en_emb) * np.linalg.norm(fr_emb))

    # Multilingual model should recognize semantic similarity
    assert similarity > 0.5  # Reasonable threshold for similar meanings
```

---

### Phase 3.2: VectorDBService Integration Tests (4 hours)

#### Task 3.2.1: Test Qdrant Connection and Collection Management (1.5 hours)

**Test Specifications**:
```python
# tests/integration/test_vectordb_integration.py

import pytest
import uuid

@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_connects_to_real_qdrant():
    """Test connection to actual Qdrant instance."""
    from app.services.vectordb import VectorDBService

    service = VectorDBService(url="http://localhost:6333")

    # Verify client is initialized
    assert service.client is not None

    # Test connection by checking health (via collection_exists)
    # This should not raise an exception
    exists = await service.collection_exists("nonexistent_collection")
    assert exists is False


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_create_collection_real():
    """Test creating actual collection in Qdrant."""
    from app.services.vectordb import VectorDBService

    service = VectorDBService(url="http://localhost:6333")

    collection_name = f"test_collection_{uuid.uuid4()}"

    try:
        # Create collection
        success = await service.create_collection(
            collection_name=collection_name,
            vector_size=768,
            distance="cosine"
        )

        assert success is True

        # Verify collection exists
        exists = await service.collection_exists(collection_name)
        assert exists is True

        # Get collection info
        info = await service.get_collection_info(collection_name)
        assert info is not None

    finally:
        # Cleanup
        await service.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_collection_lifecycle():
    """Test full collection lifecycle."""
    from app.services.vectordb import VectorDBService

    service = VectorDBService(url="http://localhost:6333")
    collection_name = f"test_lifecycle_{uuid.uuid4()}"

    # 1. Create
    await service.create_collection(collection_name, 768, "cosine")
    assert await service.collection_exists(collection_name) is True

    # 2. Get info
    info = await service.get_collection_info(collection_name)
    assert info is not None

    # 3. Delete
    success = await service.delete_collection(collection_name)
    assert success is True

    # 4. Verify deleted
    exists = await service.collection_exists(collection_name)
    assert exists is False
```

#### Task 3.2.2: Test Vector Operations (2 hours)

**Test Specifications**:
```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_upsert_real_vectors():
    """Test upserting vectors to real Qdrant."""
    from app.services.vectordb import VectorDBService
    import numpy as np

    service = VectorDBService(url="http://localhost:6333")
    collection_name = f"test_upsert_{uuid.uuid4()}"

    try:
        # Create collection
        await service.create_collection(collection_name, 768, "cosine")

        # Generate test vectors
        vectors = [np.random.rand(768).tolist() for _ in range(10)]
        payloads = [{"text": f"Document {i}", "index": i} for i in range(10)]
        ids = [f"doc_{i}" for i in range(10)]

        # Upsert vectors
        success = await service.upsert_vectors(
            collection_name=collection_name,
            vectors=vectors,
            payloads=payloads,
            ids=ids
        )

        assert success is True

        # Verify vectors were stored
        info = await service.get_collection_info(collection_name)
        # Note: Qdrant info structure may vary, adjust accordingly

    finally:
        await service.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_search_real():
    """Test similarity search with real Qdrant."""
    from app.services.vectordb import VectorDBService
    import numpy as np

    service = VectorDBService(url="http://localhost:6333")
    collection_name = f"test_search_{uuid.uuid4()}"

    try:
        # Create collection
        await service.create_collection(collection_name, 768, "cosine")

        # Create and upsert test vectors
        base_vector = np.random.rand(768)
        vectors = [
            base_vector.tolist(),  # Exact match
            (base_vector + np.random.rand(768) * 0.1).tolist(),  # Very similar
            np.random.rand(768).tolist(),  # Random (dissimilar)
        ]

        payloads = [
            {"text": "Exact match", "similarity": "exact"},
            {"text": "Very similar", "similarity": "high"},
            {"text": "Random", "similarity": "low"},
        ]

        ids = ["exact", "similar", "random"]

        await service.upsert_vectors(collection_name, vectors, payloads, ids)

        # Wait for indexing (Qdrant may need a moment)
        import asyncio
        await asyncio.sleep(1)

        # Search with base vector
        results = await service.search_vectors(
            collection_name=collection_name,
            query_vector=base_vector.tolist(),
            limit=3
        )

        # Verify results
        assert len(results) == 3

        # First result should be exact match with high score
        assert results[0]['id'] == "exact"
        assert results[0]['score'] > 0.99

        # Second should be similar with good score
        assert results[1]['id'] == "similar"
        assert results[1]['score'] > 0.8

        # Results should be sorted by score (descending)
        scores = [r['score'] for r in results]
        assert scores == sorted(scores, reverse=True)

    finally:
        await service.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_vectordb_batch_upsert_performance():
    """Test batch upsert performance with real Qdrant."""
    from app.services.vectordb import VectorDBService
    import numpy as np
    import time

    service = VectorDBService(url="http://localhost:6333")
    collection_name = f"test_perf_{uuid.uuid4()}"

    try:
        await service.create_collection(collection_name, 768, "cosine")

        # Generate 1000 vectors
        n_vectors = 1000
        vectors = [np.random.rand(768).tolist() for _ in range(n_vectors)]
        payloads = [{"index": i} for i in range(n_vectors)]
        ids = [f"vec_{i}" for i in range(n_vectors)]

        # Benchmark upsert
        start_time = time.time()
        success = await service.upsert_vectors(
            collection_name=collection_name,
            vectors=vectors,
            payloads=payloads,
            ids=ids
        )
        duration = time.time() - start_time

        assert success is True

        # Calculate throughput
        throughput = n_vectors / duration

        print(f"Upserted {n_vectors} vectors in {duration:.2f}s ({throughput:.1f} vectors/sec)")

        # Should be at least 100 vectors/sec
        assert throughput > 100

    finally:
        await service.delete_collection(collection_name)
```

---

### Phase 3.3: End-to-End Integration Tests (3 hours)

#### Task 3.3.1: Test Complete Embedding → Storage → Retrieval Workflow (2 hours)

**Test Specifications**:
```python
# tests/integration/test_e2e_integration.py

@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_text_to_storage_to_retrieval():
    """Test complete workflow: text → embedding → storage → retrieval."""
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    from tests.fixtures.integration_data import SAMPLE_DOCUMENTS
    import uuid

    # Initialize services
    embedding_svc = EmbeddingService()
    vectordb_svc = VectorDBService(url="http://localhost:6333")

    collection_name = f"test_e2e_{uuid.uuid4()}"

    try:
        # 1. Create collection
        await vectordb_svc.create_collection(collection_name, 768, "cosine")

        # 2. Generate embeddings for documents
        texts = [doc['text'] for doc in SAMPLE_DOCUMENTS]
        embeddings = await embedding_svc.embed_batch_async(texts)

        # 3. Store in Qdrant
        ids = [doc['id'] for doc in SAMPLE_DOCUMENTS]
        payloads = [doc for doc in SAMPLE_DOCUMENTS]

        await vectordb_svc.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=payloads,
            ids=ids
        )

        # Wait for indexing
        import asyncio
        await asyncio.sleep(1)

        # 4. Query with semantic search
        query = "Tell me about programming languages"
        query_embedding = await embedding_svc.embed_single_async(query)

        results = await vectordb_svc.search_vectors(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=3
        )

        # 5. Verify results
        assert len(results) > 0

        # Top result should be about Python (doc_1)
        assert results[0]['payload']['id'] == 'doc_1'
        assert 'Python' in results[0]['payload']['text']

        # All results should have reasonable scores
        assert all(r['score'] > 0.3 for r in results)

        print(f"Query: {query}")
        for i, result in enumerate(results):
            print(f"Result {i+1}: score={result['score']:.3f}, text={result['payload']['text'][:50]}...")

    finally:
        await vectordb_svc.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_multilingual_semantic_search():
    """Test multilingual semantic search."""
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    import uuid

    embedding_svc = EmbeddingService()
    vectordb_svc = VectorDBService(url="http://localhost:6333")

    collection_name = f"test_multilingual_{uuid.uuid4()}"

    try:
        await vectordb_svc.create_collection(collection_name, 768, "cosine")

        # Documents in different languages
        docs = [
            {"id": "en", "text": "Python is a programming language", "lang": "en"},
            {"id": "fr", "text": "Python est un langage de programmation", "lang": "fr"},
            {"id": "es", "text": "Python es un lenguaje de programación", "lang": "es"},
            {"id": "de", "text": "Python ist eine Programmiersprache", "lang": "de"},
        ]

        texts = [doc['text'] for doc in docs]
        embeddings = await embedding_svc.embed_batch_async(texts)

        await vectordb_svc.upsert_vectors(
            collection_name=collection_name,
            vectors=embeddings,
            payloads=docs,
            ids=[doc['id'] for doc in docs]
        )

        await asyncio.sleep(1)

        # Query in English
        query = "What programming language is being discussed?"
        query_embedding = await embedding_svc.embed_single_async(query)

        results = await vectordb_svc.search_vectors(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=4
        )

        # All documents should be retrieved (they all talk about Python)
        assert len(results) == 4

        # All should have good similarity scores (multilingual model)
        assert all(r['score'] > 0.6 for r in results)

        print("Multilingual search results:")
        for result in results:
            print(f"  {result['payload']['lang']}: {result['score']:.3f}")

    finally:
        await vectordb_svc.delete_collection(collection_name)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_e2e_concurrent_operations():
    """Test concurrent embedding and storage operations."""
    from app.services.embedding import EmbeddingService
    from app.services.vectordb import VectorDBService
    import uuid
    import asyncio

    embedding_svc = EmbeddingService()
    vectordb_svc = VectorDBService(url="http://localhost:6333")

    collection_name = f"test_concurrent_{uuid.uuid4()}"

    try:
        await vectordb_svc.create_collection(collection_name, 768, "cosine")

        # Create multiple concurrent tasks
        async def process_batch(batch_id: int, texts: list):
            embeddings = await embedding_svc.embed_batch_async(texts)
            ids = [f"batch{batch_id}_doc{i}" for i in range(len(texts))]
            payloads = [{"batch": batch_id, "text": t} for t in texts]

            await vectordb_svc.upsert_vectors(
                collection_name=collection_name,
                vectors=embeddings,
                payloads=payloads,
                ids=ids
            )

            return len(embeddings)

        # Run 5 concurrent batches of 20 texts each
        batches = [
            [f"Batch {i} document {j}" for j in range(20)]
            for i in range(5)
        ]

        tasks = [process_batch(i, batch) for i, batch in enumerate(batches)]
        results = await asyncio.gather(*tasks)

        # Verify all batches processed
        assert all(r == 20 for r in results)

        # Total 100 vectors stored
        total_stored = sum(results)
        assert total_stored == 100

        print(f"Successfully processed {total_stored} vectors concurrently")

    finally:
        await vectordb_svc.delete_collection(collection_name)
```

---

### Phase 3.4: Performance Benchmarking (2 hours)

**Test Specifications**:
```python
# tests/integration/test_performance.py

@pytest.mark.integration
@pytest.mark.benchmark
def test_embedding_throughput_cpu():
    """Benchmark embedding throughput on CPU."""
    from app.services.embedding import EmbeddingService
    import time

    service = EmbeddingService(device="cpu")

    # Warm up
    service.embed_single("warmup")

    # Benchmark single embedding
    start = time.time()
    for _ in range(100):
        service.embed_single("test sentence")
    single_duration = time.time() - start

    single_throughput = 100 / single_duration

    # Benchmark batch embedding
    texts = [f"Test sentence {i}" for i in range(100)]

    start = time.time()
    service.embed_batch(texts)
    batch_duration = time.time() - start

    batch_throughput = 100 / batch_duration

    print(f"\nEmbedding Performance (CPU):")
    print(f"  Single: {single_throughput:.1f} embeddings/sec")
    print(f"  Batch:  {batch_throughput:.1f} embeddings/sec")
    print(f"  Batch speedup: {batch_throughput/single_throughput:.1f}x")

    # Assert minimum performance (mpnet-base-v2 on CPU)
    assert single_throughput > 10  # At least 10/sec for single
    assert batch_throughput > 30   # At least 30/sec for batch


@pytest.mark.integration
@pytest.mark.benchmark
@pytest.mark.asyncio
async def test_search_latency():
    """Benchmark search latency."""
    from app.services.vectordb import VectorDBService
    import numpy as np
    import time
    import uuid

    service = VectorDBService(url="http://localhost:6333")
    collection_name = f"test_latency_{uuid.uuid4()}"

    try:
        await service.create_collection(collection_name, 768, "cosine")

        # Insert 10,000 vectors
        n_vectors = 10000
        batch_size = 1000

        for i in range(0, n_vectors, batch_size):
            vectors = [np.random.rand(768).tolist() for _ in range(batch_size)]
            payloads = [{"index": i + j} for j in range(batch_size)]
            ids = [f"vec_{i + j}" for j in range(batch_size)]

            await service.upsert_vectors(collection_name, vectors, payloads, ids)

        # Wait for indexing
        await asyncio.sleep(2)

        # Benchmark search latency
        query_vector = np.random.rand(768).tolist()

        latencies = []
        for _ in range(50):  # 50 queries
            start = time.time()
            await service.search_vectors(collection_name, query_vector, limit=10)
            latency = (time.time() - start) * 1000  # Convert to ms
            latencies.append(latency)

        avg_latency = np.mean(latencies)
        p95_latency = np.percentile(latencies, 95)
        p99_latency = np.percentile(latencies, 99)

        print(f"\nSearch Latency (10k vectors):")
        print(f"  Average: {avg_latency:.1f}ms")
        print(f"  P95: {p95_latency:.1f}ms")
        print(f"  P99: {p99_latency:.1f}ms")

        # Assert latency requirements
        assert avg_latency < 100  # Average < 100ms
        assert p99_latency < 200   # P99 < 200ms

    finally:
        await service.delete_collection(collection_name)
```

---

## 5. PYTEST CONFIGURATION

### pytest.ini Configuration

```ini
# pytest.ini

[pytest]
markers =
    unit: Unit tests with mocked dependencies
    integration: Integration tests with real services (Qdrant, model)
    benchmark: Performance benchmarking tests
    slow: Tests that take >10 seconds

# Default: run only unit tests
addopts = -v --strict-markers

# Integration test specific settings
integration_timeout = 300  # 5 minutes timeout for integration tests
```

### conftest.py Fixtures

```python
# tests/integration/conftest.py

import pytest
import asyncio
import requests
import time

def qdrant_available():
    """Check if Qdrant is running."""
    try:
        response = requests.get("http://localhost:6333/health", timeout=2)
        return response.status_code == 200
    except:
        return False


@pytest.fixture(scope="session")
def check_qdrant():
    """Verify Qdrant is available before running tests."""
    if not qdrant_available():
        pytest.skip("Qdrant not running. Start with: docker run -p 6333:6333 qdrant/qdrant")


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def clean_qdrant_collections():
    """Clean up test collections after each test."""
    from app.services.vectordb import VectorDBService

    service = VectorDBService(url="http://localhost:6333")

    yield

    # Cleanup: delete all test collections
    # Implementation depends on Qdrant API for listing collections
```

---

## 6. RUNNING INTEGRATION TESTS

### Command Reference

```bash
# Run only integration tests (requires Qdrant running)
pytest tests/integration/ -v -m integration

# Run specific integration test file
pytest tests/integration/test_embedding_integration.py -v

# Run with coverage
pytest tests/integration/ -v --cov=app.services --cov-report=term-missing

# Run performance benchmarks
pytest tests/integration/test_performance.py -v -m benchmark

# Skip slow tests
pytest tests/integration/ -v -m "integration and not slow"

# Run integration tests with detailed output
pytest tests/integration/ -v -s -m integration

# Run all tests (unit + integration)
pytest tests/ -v
```

### Pre-Test Checklist

```bash
# 1. Start Qdrant
docker run -d --name qdrant-test -p 6333:6333 qdrant/qdrant:latest

# 2. Verify Qdrant health
curl http://localhost:6333/health

# 3. Check CUDA availability (optional, for GPU tests)
python -c "import torch; print(f'CUDA available: {torch.cuda.is_available()}')"

# 4. Run integration tests
pytest tests/integration/ -v -m integration
```

---

## 7. ESTIMATED TIMELINE

| Phase | Task | Estimated Time |
|-------|------|----------------|
| **3.1** | EmbeddingService Integration | 3 hours |
| | Model loading tests | 1 hour |
| | Real inference tests | 1.5 hours |
| | Multilingual tests | 0.5 hours |
| **3.2** | VectorDBService Integration | 4 hours |
| | Connection tests | 1 hour |
| | Collection management | 1.5 hours |
| | Vector operations | 1.5 hours |
| **3.3** | End-to-End Integration | 3 hours |
| | Complete workflow | 2 hours |
| | Concurrent operations | 1 hour |
| **3.4** | Performance Benchmarking | 2 hours |
| | Embedding throughput | 1 hour |
| | Search latency | 1 hour |
| **3.5** | Documentation & Cleanup | 1 hour |
| **Total** | | **13 hours** |
| **Buffer (15%)** | | **2 hours** |
| **Grand Total** | | **15 hours** (~2 days) |

---

## 8. ACCEPTANCE CRITERIA

### Functional Requirements

- [ ] All integration tests pass with real Qdrant instance
- [ ] Real embedding model loads successfully (~20-30s first time)
- [ ] 768-dimensional embeddings generated correctly
- [ ] Multilingual embeddings work (tested with 5+ languages)
- [ ] Vector storage and retrieval work end-to-end
- [ ] Concurrent operations handle correctly
- [ ] Collection lifecycle tested (create, use, delete)

### Performance Requirements

- [ ] Embedding throughput: >30 vectors/sec on CPU (batch)
- [ ] Vector upsert: >100 vectors/sec
- [ ] Search latency: <100ms average for 10k vectors
- [ ] P99 search latency: <200ms
- [ ] GPU acceleration: >1.5x speedup vs CPU (if available)

### Quality Gates

- [ ] Integration test coverage: >70%
- [ ] No memory leaks (monitored during benchmarks)
- [ ] All cleanup code runs (no orphaned collections)
- [ ] Tests can run multiple times without conflicts
- [ ] Clear error messages when services unavailable

---

## 9. TROUBLESHOOTING GUIDE

### Common Issues

**Issue: Qdrant not available**
```bash
# Solution: Start Qdrant container
docker run -d --name qdrant-test -p 6333:6333 qdrant/qdrant:latest

# Verify
curl http://localhost:6333/health
```

**Issue: Model download fails**
```python
# Solution: Pre-download model
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('sentence-transformers/paraphrase-multilingual-mpnet-base-v2')
```

**Issue: Tests timeout**
```bash
# Solution: Increase timeout in pytest.ini
pytest tests/integration/ --timeout=600
```

**Issue: Port conflicts**
```bash
# Check if Qdrant port is already in use
lsof -i :6333

# Kill existing process or use different port
docker run -d -p 6334:6333 qdrant/qdrant:latest
# Update tests to use localhost:6334
```

---

## 10. NEXT STEPS AFTER COMPLETION

### Phase 4: RAG Pipeline Integration
1. Implement RAG orchestration service
2. Create Query Router with LangGraph
3. Integrate with vLLM for generation
4. Build REST API endpoints

### Phase 5: Production Readiness
1. Add monitoring and observability
2. Implement CI/CD pipeline
3. Deploy to GKE
4. Load testing and optimization

---

**Document Status:** Ready for Implementation
**Prerequisites:** ✅ Phase 1 Complete, ✅ Phase 2 Complete
**Target Completion:** 2 working days (~15 hours)

---

**END OF PLAN**
