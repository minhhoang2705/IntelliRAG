# Phase 4 RAG Pipeline - Integration Testing Quick Start

**Date:** 2025-10-18  
**Tests:** 14 integration tests ready to execute  
**Time Required:** ~2-3 minutes (after services start)

---

## 🚀 Quick Start (3 Steps)

### Step 1: Start Services (One-Time Setup)

```bash
# Terminal 1: Start Qdrant (Vector Database)
docker run -d --name qdrant-test -p 6333:6333 qdrant/qdrant:latest

# Terminal 2: Start vLLM (LLM Inference Server - Requires NVIDIA GPU)
docker run -d --gpus all \
  -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  vllm/vllm-openai:latest \
  --model Qwen/Qwen3-0.6B\
  --gpu-memory-utilization 0.95

# Wait 30-60 seconds for vLLM to load model, then verify:
curl http://localhost:8000/v1/models
# Expected: {"object":"list","data":[{"id":"Qwen/Qwen3-0.6B-Instruct",...}]}
```

### Step 2: Run Integration Tests

```bash
# Run all Phase 4 integration tests
uv run pytest tests/integration/test_llm_integration.py \
           tests/integration/test_rag_pipeline_integration.py \
           tests/integration/test_fastapi_integration.py \
           -v -m integration

# Expected: 14 passed in ~60-90 seconds
```

### Step 3: Review Results

```bash
# Generate coverage report
uv run pytest tests/integration/ -v -m integration \
           --cov=app.services.llm_client \
           --cov=app.services.rag_pipeline \
           --cov=app.services.orchestrator \
           --cov=app.main \
           --cov-report=html

# View report: open htmlcov/index.html
```

---

## 📊 Test Breakdown

### LLM Client Tests (6 tests)
**File:** `tests/integration/test_llm_integration.py`

| Test | What It Validates |
|------|-------------------|
| test_vllm_service_availability | vLLM server is accessible |
| test_llm_client_real_generation | Basic text generation works |
| test_llm_client_with_system_message | System prompts influence output |
| test_llm_client_temperature_variations | Temperature parameter works (0.0, 0.7, 1.5) |
| test_llm_client_max_tokens_limit | Token limiting works correctly |
| test_llm_client_concurrent_requests | Handles 5 concurrent requests |

### RAG Pipeline Tests (3 tests)
**File:** `tests/integration/test_rag_pipeline_integration.py`

| Test | What It Validates |
|------|-------------------|
| test_rag_pipeline_with_real_services | Full RAG flow (embed → retrieve → generate) |
| test_rag_pipeline_different_top_k_values | Retrieval with k=1, 3, 5 works |
| test_rag_pipeline_source_attribution | Sources sorted by score correctly |

### FastAPI Endpoint Tests (5 tests)
**File:** `tests/integration/test_fastapi_integration.py`

| Test | What It Validates |
|------|-------------------|
| test_health_endpoint | GET /health returns 200 |
| test_api_startup_initialization | Services initialize on startup |
| test_query_endpoint_without_rag | Direct LLM mode (use_rag=false) |
| test_query_endpoint_with_rag | RAG mode (use_rag=true) with retrieval |
| test_query_endpoint_validation | Request validation (422 errors) |

---

## ⚡ Expected Performance

| Test Category | Expected Time |
|---------------|---------------|
| LLM Tests (6) | ~15-20 seconds |
| RAG Tests (3) | ~30-40 seconds |
| API Tests (5) | ~20-30 seconds |
| **Total** | **~60-90 seconds** |

---

## 🔧 Troubleshooting

### Tests Skip with "vLLM not running"

**Cause:** vLLM server not accessible  
**Fix:**
```bash
# Check vLLM is running
docker ps | grep vllm

# Check vLLM endpoint
curl http://localhost:8000/v1/models

# If not running, start it (see Step 1 above)
```

### Tests Fail with "Connection refused" (Qdrant)

**Cause:** Qdrant not running  
**Fix:**
```bash
# Check Qdrant is running
docker ps | grep qdrant

# Start if needed
docker run -d --name qdrant-test -p 6333:6333 qdrant/qdrant:latest
```

### GPU Out of Memory

**Cause:** Insufficient VRAM for Qwen3-0.6B  
**Fix:**
```bash
# Option 1: Lower GPU utilization
docker run -d --gpus all -p 8000:8000 \
  vllm/vllm-openai --model Qwen/Qwen3-0.6B\
  --gpu-memory-utilization 0.7

# Option 2: Use smaller model (3B)
docker run -d --gpus all -p 8000:8000 \
  vllm/vllm-openai --model Qwen/Qwen2.5-3B-Instruct
```

---

## 📝 Test Examples

### Example 1: Run Single Test
```bash
uv run pytest tests/integration/test_llm_integration.py::test_vllm_service_availability -v
```

### Example 2: Run with Detailed Output
```bash
uv run pytest tests/integration/ -v -s -m integration
```

### Example 3: Run Without vLLM (Will Skip Most Tests)
```bash
uv run pytest tests/integration/ -v -m integration
# Expected: 2 passed, 12 skipped
```

---

## 🎯 Success Criteria

✅ **All 14 tests should PASS when:**
- Qdrant running on localhost:6333
- vLLM running on localhost:8000 with Qwen3-0.6B-Instruct
- NVIDIA GPU available with sufficient VRAM (>8GB)

✅ **Partial Success (2 tests) when:**
- Only health check and validation tests run (no vLLM)
- 12 tests gracefully skip with clear message

---

## 📂 Files Created

### Test Files
- `tests/integration/test_llm_integration.py` (6 tests)
- `tests/integration/test_rag_pipeline_integration.py` (3 tests)
- `tests/integration/test_fastapi_integration.py` (5 tests)

### Updated Files
- `tests/integration/conftest.py` (added vLLM fixtures)
- `tests/fixtures/integration_data.py` (added RAG test data)

### Documentation
- `docs/phase4-integration-test-summary.md` (comprehensive)
- `docs/INTEGRATION_TESTING_GUIDE.md` (this file)

---

## 🔗 Related Documentation

- [Phase 4 Implementation Summary](./phase4-rag-pipeline-summary.md)
- [Phase 4 Integration Test Summary](./phase4-integration-test-summary.md)
- [Phase 3 Integration Test Summary](./integration-test-summary-20251017.md)

---

**Ready to test? Start services and run:** `uv run pytest tests/integration/ -v -m integration`
