# Unit vs Integration Test Patterns

**Date**: 2025-10-28  
**Purpose**: Define clear testing patterns to prevent performance issues and ensure proper test isolation

---

## 🎯 Overview

This guide establishes patterns for writing unit and integration tests in the IntelliRAG project. Following these patterns prevents:
- ❌ System crashes from loading large models (560MB+)
- ❌ Slow test execution (minutes instead of seconds)
- ❌ Excessive memory usage (10-15GB)
- ❌ Flaky tests due to real service dependencies

---

## 📊 Test Categories

### Unit Tests (`@pytest.mark.unit`)

**Purpose**: Test logic and behavior in isolation  
**Speed**: <0.1 seconds per test  
**Memory**: <100MB per test  
**Dependencies**: All external dependencies MOCKED

### Integration Tests (`@pytest.mark.integration`)

**Purpose**: Test real service interactions  
**Speed**: 1-30 seconds per test  
**Memory**: 2-5GB per test (acceptable)  
**Dependencies**: Real services (models, databases)

---

## 🔴 Unit Test Patterns

### Rule #1: ALWAYS Mock External Dependencies

**External dependencies include:**
- ✅ ML models (SentenceTransformer, BGEM3FlagModel)
- ✅ Databases (Qdrant, PostgreSQL)
- ✅ File systems (GCS, local storage)
- ✅ Network calls (HTTP, API clients)
- ✅ Third-party libraries (LangChain chunkers)

### Pattern 1: Testing Service Logic (Embedding Service)

**❌ WRONG - Loads Real Model:**
```python
def test_embedding_service_embed_single():
    """BAD: This loads 560MB model!"""
    from app.services.embedding import EmbeddingService
    
    service = EmbeddingService()  # ❌ Loads real BGE-M3
    vector = service.embed_single("test")
    
    assert len(vector) == 1024
```

**✅ CORRECT - Uses Mock:**
```python
@pytest.mark.unit
def test_embedding_service_embed_single(mocker, mock_sentence_transformer):
    """GOOD: Tests logic without loading model"""
    from app.services.embedding import EmbeddingService
    
    # Mock the model before instantiation
    mocker.patch('app.services.embedding.SentenceTransformer', 
                 return_value=mock_sentence_transformer)
    
    service = EmbeddingService()
    vector = service.embed_single("test")
    
    assert len(vector) == 1024
    assert isinstance(vector, list)
    mock_sentence_transformer.encode.assert_called_once()
```

**Why this works:**
- ✅ No model loading (instant execution)
- ✅ Tests the logic (vector processing, type conversion)
- ✅ Verifies correct method calls
- ✅ Predictable, deterministic results

---

### Pattern 2: Testing with Fixture-Based Mocks

**Create reusable mocks in `tests/conftest.py`:**

```python
# tests/conftest.py
import pytest
from unittest.mock import Mock, AsyncMock
import numpy as np

@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService for unit tests."""
    service = Mock()
    service.model_id = "BAAI/bge-m3"
    service.device = "cpu"
    service.get_embedding_dimension.return_value = 1024
    
    # Mock methods
    service.embed_single.return_value = [0.1] * 1024
    
    def mock_embed_batch(texts, **kwargs):
        return [[0.1 * (i + 1)] * 1024 for i in range(len(texts))]
    service.embed_batch.side_effect = mock_embed_batch
    
    # Async versions
    async def mock_async(text):
        return [0.1] * 1024
    service.embed_single_async = AsyncMock(side_effect=mock_async)
    
    return service
```

**Use in tests:**

```python
@pytest.mark.unit
def test_semantic_chunker_with_embeddings(mock_embedding_service):
    """Uses fixture-based mock - clean and simple"""
    from app.services.semantic_chunker import SemanticChunkerService
    
    chunker = SemanticChunkerService(embeddings=mock_embedding_service)
    
    assert chunker is not None
    assert hasattr(chunker, 'embeddings')
```

---

### Pattern 3: Testing Complex Interactions (Semantic Chunker)

**Mock both the embedding service AND LangChain components:**

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_chunk_documents_returns_chunks(mock_embedding_service, mocker):
    """Tests chunking logic without real models"""
    from app.services.semantic_chunker import SemanticChunkerService
    from langchain_core.documents import Document
    
    # Mock LangChain's SemanticChunker.split_text
    mock_langchain_chunker = mocker.Mock()
    mock_langchain_chunker.split_text.return_value = [
        "Chunk 1 content",
        "Chunk 2 content",
        "Chunk 3 content",
    ]
    mocker.patch('app.services.semantic_chunker.SemanticChunker', 
                 return_value=mock_langchain_chunker)
    
    chunker = SemanticChunkerService(embeddings=mock_embedding_service)
    
    documents = [Document(page_content="long text...", metadata={"source": "test"})]
    chunks = await chunker.chunk_documents(documents)
    
    assert len(chunks) == 3
    assert all(isinstance(chunk, Document) for chunk in chunks)
    mock_langchain_chunker.split_text.assert_called_once()
```

---

### Pattern 4: Testing Model-Dependent Services (BGE-M3)

**Direct model injection for services with lazy loading:**

```python
@pytest.mark.unit
def test_bge_m3_embed_single_dense(mocker):
    """Tests BGE-M3 without loading 560MB model"""
    from app.services.bge_m3_embedding import BGEM3EmbeddingService
    import numpy as np
    
    # Create service (model not loaded yet)
    service = BGEM3EmbeddingService()
    
    # Create mock model
    mock_model = mocker.Mock()
    mock_model.encode.return_value = {
        'dense_vecs': np.array([np.random.rand(1024)])
    }
    
    # Directly inject mock (bypasses lazy loading)
    service._model = mock_model
    
    # Test the logic
    embedding = service.embed_single("test")
    
    assert len(embedding) == 1024
    assert isinstance(embedding, list)
    mock_model.encode.assert_called_once()
```

**Key points:**
- ✅ Service instantiation doesn't load model (lazy loading)
- ✅ Direct `._model` injection bypasses import mocking
- ✅ Mock returns numpy arrays (matches real behavior)
- ✅ Tests actual logic (.tolist() conversion, error handling)

---

### Pattern 5: Testing Edge Cases (No Model Needed)

**Some tests don't need mocks at all:**

```python
@pytest.mark.unit
def test_embedding_service_handles_empty_text():
    """Tests edge case - no model loading"""
    from app.services.embedding import EmbeddingService
    
    service = EmbeddingService()
    vector = service.embed_single("")  # Empty text
    
    assert len(vector) == 1024
    assert all(v == 0.0 for v in vector)
    assert service._model is None  # Confirms no model loaded
```

**When to skip mocking:**
- Empty input handling
- Parameter validation
- Configuration tests
- Abstract class tests

---

### Pattern 6: Testing Async Operations

**Mock async methods properly:**

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_embedding(mocker, mock_sentence_transformer):
    """Tests async operations without real model"""
    from app.services.embedding import EmbeddingService
    
    mocker.patch('app.services.embedding.SentenceTransformer',
                 return_value=mock_sentence_transformer)
    
    service = EmbeddingService()
    
    # Test async single
    vector = await service.embed_single_async("test")
    assert len(vector) == 1024
    
    # Test concurrent calls
    import asyncio
    tasks = [
        service.embed_single_async(f"text {i}")
        for i in range(3)
    ]
    vectors = await asyncio.gather(*tasks)
    assert len(vectors) == 3
```

---

## 🟢 Integration Test Patterns

### Rule #1: Use Real Services, But Efficiently

**Integration tests SHOULD:**
- ✅ Load real models (to test actual behavior)
- ✅ Connect to real databases (test queries work)
- ✅ Test end-to-end workflows
- ✅ Run separately from unit tests

**Integration tests should NOT:**
- ❌ Run in CI on every commit (too slow)
- ❌ Load models multiple times (use fixtures)
- ❌ Test logic that unit tests cover

### Pattern 1: Session-Scoped Model Loading

**Load model ONCE for all integration tests:**

```python
# tests/integration/conftest.py
import pytest

@pytest.fixture(scope="session")
def real_embedding_service():
    """Load model once for entire test session."""
    from app.services.embedding import EmbeddingService
    
    service = EmbeddingService()
    # Force model load
    _ = service.model
    
    yield service
    
    # Cleanup (optional)
    del service._model
```

**Use in tests:**

```python
@pytest.mark.integration
def test_real_embedding_produces_expected_results(real_embedding_service):
    """Tests with REAL model - run separately"""
    
    embedding = real_embedding_service.embed_single("Hello world")
    
    # Test real properties
    assert len(embedding) == 1024
    assert all(isinstance(v, float) for v in embedding)
    # Test embedding quality
    assert abs(sum(embedding)) > 0.1  # Non-zero
```

---

### Pattern 2: Testing Real Model Behavior

**Integration tests validate actual ML behavior:**

```python
@pytest.mark.integration
def test_embedding_semantic_similarity(real_embedding_service):
    """Tests that similar texts have similar embeddings"""
    
    text1 = "Machine learning is fascinating"
    text2 = "AI and ML are interesting"
    text3 = "I like pizza"
    
    emb1 = real_embedding_service.embed_single(text1)
    emb2 = real_embedding_service.embed_single(text2)
    emb3 = real_embedding_service.embed_single(text3)
    
    # Calculate cosine similarity
    def cosine_sim(a, b):
        import numpy as np
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    sim_1_2 = cosine_sim(emb1, emb2)
    sim_1_3 = cosine_sim(emb1, emb3)
    
    # Related texts should be more similar
    assert sim_1_2 > sim_1_3
```

---

### Pattern 3: End-to-End Integration Tests

**Test complete workflows:**

```python
@pytest.mark.integration
@pytest.mark.asyncio
async def test_document_ingestion_pipeline(
    real_embedding_service,
    test_qdrant_client,
    tmp_path
):
    """Tests full pipeline: Load → Chunk → Embed → Store"""
    from app.services.semantic_chunker import SemanticChunkerService
    from app.services.vectordb import QdrantService
    from langchain_core.documents import Document
    
    # Setup
    chunker = SemanticChunkerService(embeddings=real_embedding_service)
    vector_db = QdrantService(client=test_qdrant_client)
    
    # Create test document
    doc = Document(
        page_content="Long document about AI and ML...",
        metadata={"source": "test.pdf"}
    )
    
    # Execute pipeline
    chunks = await chunker.chunk_documents([doc])
    embeddings = [real_embedding_service.embed_single(c.page_content) 
                  for c in chunks]
    await vector_db.insert_vectors(embeddings, chunks)
    
    # Verify
    assert len(chunks) > 1
    results = await vector_db.search("AI", limit=5)
    assert len(results) > 0
```

---

## 📋 Test Organization

### Directory Structure

```
tests/
├── conftest.py              # Shared mock fixtures
├── unit/                    # Fast, isolated tests
│   ├── conftest.py         # Unit-specific fixtures
│   ├── test_embedding.py
│   ├── test_semantic_chunker_service.py
│   └── test_bge_m3_embedding.py
├── integration/             # Slow, real service tests
│   ├── conftest.py         # Integration-specific fixtures
│   ├── test_embedding_integration.py
│   ├── test_qdrant_integration.py
│   └── test_rag_pipeline.py
└── fixtures/                # Test data files
    ├── sample.pdf
    └── sample.txt
```

---

## 🏃 Running Tests

### Run Only Unit Tests (Fast)

```bash
# All unit tests (~5 seconds)
pytest tests/unit/ -m unit -v

# Specific file
pytest tests/unit/test_embedding.py -m unit -v

# Parallel execution (even faster)
pytest tests/unit/ -m unit -n auto
```

### Run Only Integration Tests (Slow)

```bash
# All integration tests (~2-5 minutes)
pytest tests/integration/ -m integration -v

# Skip integration in CI
pytest tests/ -m "not integration" -v
```

### Run All Tests

```bash
# Everything
pytest tests/ -v

# With coverage
pytest tests/ --cov=app --cov-report=html
```

---

## ✅ Checklist: Writing New Tests

### For Unit Tests:

- [ ] Add `@pytest.mark.unit` marker
- [ ] Mock ALL external dependencies
- [ ] Use fixtures from `conftest.py`
- [ ] Test runs in <0.1 seconds
- [ ] Uses <100MB memory
- [ ] Test passes without network/database/models
- [ ] Tests logic, not real behavior

### For Integration Tests:

- [ ] Add `@pytest.mark.integration` marker
- [ ] Use session-scoped fixtures for expensive resources
- [ ] Test real model/service behavior
- [ ] Can run independently
- [ ] Clean up resources (databases, files)
- [ ] Document expected runtime
- [ ] Tests actual behavior, not just logic

---

## 🎓 Examples from Codebase

### Unit Test Example

```python
# tests/unit/test_embedding.py
@pytest.mark.unit
def test_embedding_service_embed_batch_respects_max_batch_size(
    mocker, 
    mock_sentence_transformer
):
    """Unit test: Tests batching logic without loading model"""
    from app.services.embedding import EmbeddingService
    
    mocker.patch('app.services.embedding.SentenceTransformer',
                 return_value=mock_sentence_transformer)
    service = EmbeddingService(max_batch_size=32)
    
    # Create large batch
    texts = [f"Sentence {i}" for i in range(100)]
    vectors = service.embed_batch(texts)
    
    # Verify logic
    assert len(vectors) == 100
    assert all(len(v) == 1024 for v in vectors)
    # Model should be called (implementation detail tested)
```

### Integration Test Example

```python
# tests/integration/test_embedding_integration.py
@pytest.mark.integration
def test_embedding_service_multilingual_quality(real_embedding_service):
    """Integration test: Tests REAL multilingual model quality"""
    
    texts = {
        "en": "Hello, how are you?",
        "fr": "Bonjour, comment allez-vous?",
        "es": "Hola, ¿cómo estás?",
        "vi": "Xin chào, bạn khỏe không?",
    }
    
    embeddings = {
        lang: real_embedding_service.embed_single(text)
        for lang, text in texts.items()
    }
    
    # All should produce valid embeddings
    for lang, emb in embeddings.items():
        assert len(emb) == 1024
        assert any(v != 0.0 for v in emb), f"{lang} embedding is all zeros"
    
    # Similar meanings should have similar embeddings
    import numpy as np
    def cosine_sim(a, b):
        return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))
    
    # English and French should be similar (same meaning)
    sim = cosine_sim(embeddings["en"], embeddings["fr"])
    assert sim > 0.7, "Translations should have high similarity"
```

---

## 🚫 Common Mistakes

### Mistake 1: Loading Real Models in Unit Tests

```python
# ❌ WRONG
@pytest.mark.unit
def test_embedding():
    service = EmbeddingService()  # Loads 560MB model!
    ...
```

**Fix**: Always mock external dependencies.

### Mistake 2: Over-Mocking Integration Tests

```python
# ❌ WRONG - This defeats the purpose
@pytest.mark.integration
def test_real_model_quality(mocker):
    mock_model = mocker.Mock()  # Not testing real model!
    ...
```

**Fix**: Use real services in integration tests.

### Mistake 3: No Test Markers

```python
# ❌ WRONG - No marker
def test_embedding():
    ...
```

**Fix**: Always add `@pytest.mark.unit` or `@pytest.mark.integration`.

### Mistake 4: Mixing Unit and Integration

```python
# ❌ WRONG - Real model in unit test
@pytest.mark.unit
def test_with_real_model():
    service = EmbeddingService()  # Real model
    ...
```

**Fix**: Separate unit (mocked) from integration (real).

---

## 📚 Additional Resources

### Related Documentation

- `docs/testing/tdd-workflow.md` - TDD methodology
- `CLAUDE.md` - Testing guidelines
- `tests/conftest.py` - Available mock fixtures

### External References

- [pytest documentation](https://docs.pytest.org/)
- [pytest-mock](https://pytest-mock.readthedocs.io/)
- [Python unittest.mock](https://docs.python.org/3/library/unittest.mock.html)

---

## 🎯 Success Metrics

**Good unit test suite:**
- ✅ All tests run in <10 seconds
- ✅ Uses <500MB memory
- ✅ No network/database/model dependencies
- ✅ 100% pass rate (deterministic)
- ✅ Can run offline

**Good integration test suite:**
- ✅ Tests real behavior
- ✅ Uses session-scoped fixtures
- ✅ Runs independently
- ✅ Clear failure messages
- ✅ Documented runtime expectations

---

**Last Updated**: 2025-10-28  
**Maintained By**: IntelliRAG Development Team
