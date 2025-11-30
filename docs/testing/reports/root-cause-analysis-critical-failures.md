# Root Cause Analysis: Critical Test Failures

**Date**: 2025-11-30
**Investigator**: System Debugging Agent
**Scope**: 70+ failing unit tests after Phase 5 Day 1 CI/CD setup
**Status**: Investigation Complete - No Fixes Implemented

---

## Executive Summary

After analyzing the test suite, I've identified **4 critical root causes** affecting 70+ tests:

1. **BLOCKER 1**: Pydantic Settings Validation - **16 failures** (100% config tests)
2. **BLOCKER 2**: Service Dependency Mocking - **35+ failures** (orchestrator, vectordb, upload)
3. **HIGH PRIORITY 3**: Authentication Middleware - **10+ failures** (upload endpoint)
4. **HIGH PRIORITY 4**: Mock Configuration - **8+ failures** (LLM client, metrics)

**Critical Finding**: All failures are **test infrastructure issues**, NOT production code bugs. The production code is functional but tests are not properly isolated from external dependencies.

---

## BLOCKER 1: Pydantic Settings Validation (16 Failures)

### Root Cause Analysis

**File**: `app/config.py:79`
**Error**: `ValidationError: Extra inputs are not permitted`
**Affected Fields**: `api_key`, `device`, `max_batch_size`, `hf_token`

#### Current Implementation vs Expected Behavior

**Current `.env` file contains:**
```bash
API_KEY=xxx...xxx
DEVICE=cuda
MAX_BATCH_SIZE=16
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

**Settings class definition** (`app/config.py:9-76`):
```python
class Settings(BaseSettings):
    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")

    # Missing fields:
    # - api_key (only used in auth middleware via os.getenv)
    # - device (was EMBEDDING_DEVICE, not used in Settings)
    # - max_batch_size (was EMBEDDING_BATCH_SIZE, not used)
    # - hf_token (never used anywhere)
```

**Why the failure occurs:**
1. Pydantic v2 defaults to `extra='forbid'` (rejects unknown fields)
2. `.env` file is loaded at module import time (line 79: `settings = Settings()`)
3. Settings class only defines 25 fields but `.env` has 4 extra fields
4. Tests use `patch.dict(os.environ, ..., clear=True)` which doesn't prevent Settings singleton initialization

#### Design Mismatch

**Architecture conflict:**
```
Authentication Middleware (app/api/middleware/auth.py:25)
  ↓
  Uses: os.getenv("API_KEY")  ← Direct env access

Settings Class (app/config.py:9-76)
  ↓
  Does NOT have: api_key field  ← Not managed by Pydantic
```

**Why `API_KEY` is not in Settings:**
- Auth middleware was designed to work independently
- Dev mode detection: `if not api_key: return "dev-mode"` (line 49)
- Settings would require `Optional[str]` which complicates validation logic

**Similar issue with `DEVICE`, `MAX_BATCH_SIZE`, `HF_TOKEN`:**
- These were added to `.env` for standalone embedding service (`deploy/embedding-service/`)
- Not used by main application Settings class
- Create noise in environment but don't break production code

### Side Effects of Potential Fixes

#### Approach 1: Add fields to Settings class
```python
class Settings(BaseSettings):
    api_key: Optional[str] = None
    device: str = "cpu"
    max_batch_size: int = 16
    hf_token: Optional[str] = None
```

**Trade-offs:**
- ✅ Fixes validation errors
- ✅ Centralizes configuration
- ❌ Breaks auth middleware's dev mode detection (needs refactoring)
- ❌ Adds unused fields to main app (only embedding service uses them)
- ❌ Requires updating 10+ locations where Settings is used

#### Approach 2: Change to `extra='ignore'`
```python
class Settings(BaseSettings):
    model_config = ConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra='ignore'  # ADD THIS
    )
```

**Trade-offs:**
- ✅ Quick fix, 1 line change
- ✅ No code changes needed elsewhere
- ✅ Backward compatible
- ❌ Silently ignores typos in `.env` (e.g., `QDRAT_URL` instead of `QDRANT_URL`)
- ❌ Loses Pydantic's strict validation benefits
- ❌ Can hide configuration errors

#### Approach 3: Remove extra fields from `.env`
```python
# Remove from .env:
# API_KEY  (use environment variable directly in K8s)
# DEVICE  (only for embedding service, not main app)
# MAX_BATCH_SIZE  (only for embedding service)
# HF_TOKEN  (never used)
```

**Trade-offs:**
- ✅ Keeps strict validation
- ✅ Clean separation of concerns
- ❌ Breaks local development workflow (API_KEY needed for testing)
- ❌ Need separate `.env.embedding` for embedding service
- ❌ More complex deployment documentation

### Recommended Fix Approach

**Hybrid approach (safest):**

1. **Short-term**: Add `extra='ignore'` to Settings (1 line, unblocks all tests)
2. **Medium-term**: Create separate `.env.app` and `.env.embedding`
3. **Long-term**: Centralize all config in Settings with proper Optional types

**Rationale:**
- Unblocks tests immediately
- Maintains production functionality
- Allows incremental refactoring without breaking changes

### Unresolved Questions

1. **Who added these extra fields to `.env`?** Check git history: `git log -p -- .env`
2. **Are they used in production?** Check K8s ConfigMap: `helm/intellirag-app/templates/configmap.yaml`
3. **Why wasn't this caught earlier?** Tests were passing before - what changed?

---

## BLOCKER 2: Service Dependency Mocking (35+ Failures)

### Root Cause Analysis

**File**: `app/services/orchestrator.py:59-63`
**Error**: `RuntimeError: Cannot connect to embedding service at http://localhost:8001`
**Stack Trace**:
```
tests/unit/test_orchestrator.py:165 → orchestrator.ingest()
app/services/orchestrator.py:263 → embedding_service.get_embedding_dimension()
app/services/embedding.py:146 → _fetch_model_info()
app/services/embedding.py:184 → client.get(f"{remote_url}/model-info")
httpx.ConnectError: [Errno 111] Connection refused
```

#### Current Implementation vs Expected Behavior

**Orchestrator initialization** (`app/services/orchestrator.py:56-63`):
```python
def __init__(self, embedding_service_url="http://localhost:8001", use_remote_embedding=True):
    # Service is initialized IMMEDIATELY at import time
    self.embedding_service = EmbeddingService(
        use_remote=use_remote_embedding,
        remote_url=embedding_service_url,
        device="cpu"
    )
```

**Embedding service initialization** (`app/services/embedding.py:89-106`):
```python
def __init__(self, use_remote=False, remote_url="http://localhost:8001"):
    self.use_remote = use_remote
    self.remote_url = remote_url
    # Model info fetched LAZILY on first use
```

**Why the failure occurs:**
1. Tests create `OrchestratorService()` without mocking
2. OrchestratorService creates real `EmbeddingService(use_remote=True)`
3. First call to `embedding_service.get_embedding_dimension()` triggers HTTP request
4. No mock HTTP server → `httpx.ConnectError`

#### Lazy Initialization Trap

**The problem:**
```python
# At initialization (line 62):
self.embedding_service = EmbeddingService(use_remote=True)  # OK, no network call

# Later in ingest() (line 263):
vector_size = self.embedding_service.get_embedding_dimension()  # BOOM! Network call
    ↓
def get_embedding_dimension(self):  # line 145
    model_info = self._fetch_model_info()  # First call triggers HTTP
        ↓
    response = client.get(f"{self.remote_url}/model-info")  # Connection refused
```

**Why mocks in conftest.py don't work:**
```python
# conftest.py has mock_embedding_service fixture (line 62)
@pytest.fixture
def mock_embedding_service():
    service = Mock()
    service.embed_single.return_value = [0.1] * 1024
    return service

# But tests don't USE it:
def test_ingest_accepts_file_path(orchestrator):  # No mock parameter!
    result = await orchestrator.ingest(...)  # Real embedding service used
```

#### Design Mismatch

**Architectural issue:**
```
Unit Test Expectation:
  ↓
  "orchestrator" fixture should be isolated, no network calls

Reality:
  ↓
  orchestrator → EmbeddingService(use_remote=True)
               → get_embedding_dimension()
               → HTTP GET http://localhost:8001/model-info
               → Connection refused ❌
```

**Why dependency injection isn't used:**
- OrchestratorService creates its own dependencies (line 59-95)
- No constructor parameter for `embedding_service`
- Hard-coded instantiation prevents mocking

### Side Effects of Potential Fixes

#### Approach 1: Add embedding_service parameter to OrchestratorService
```python
def __init__(
    self,
    vectordb_url="http://localhost:6333",
    llm_base_url="http://localhost:8000/v1",
    embedding_service=None  # ADD THIS
):
    if embedding_service:
        self.embedding_service = embedding_service
    else:
        self.embedding_service = EmbeddingService(use_remote=True)
```

**Trade-offs:**
- ✅ Proper dependency injection
- ✅ Easy to mock in tests
- ✅ Follows SOLID principles
- ❌ Breaks existing code that creates OrchestratorService()
- ❌ Need to update app/main.py initialization
- ❌ More complex initialization in production

#### Approach 2: Mock at import level with pytest-mock
```python
@pytest.fixture
def orchestrator(mocker):
    # Mock EmbeddingService before import
    mock_embedding = mocker.patch('app.services.orchestrator.EmbeddingService')
    mock_embedding.return_value.get_embedding_dimension.return_value = 1024

    from app.services.orchestrator import OrchestratorService
    return OrchestratorService()
```

**Trade-offs:**
- ✅ No production code changes
- ✅ Tests remain isolated
- ❌ Fragile (import order matters)
- ❌ Need to mock in every test file
- ❌ Harder to debug when mocks fail

#### Approach 3: Add test mode to EmbeddingService
```python
class EmbeddingService:
    def __init__(self, use_remote=False, test_mode=False):
        if test_mode:
            self.use_remote = False
            self._model_info_cache = {
                "model_name": "BAAI/bge-m3",
                "embedding_dimension": 1024
            }
```

**Trade-offs:**
- ✅ Simple test setup
- ✅ No network calls in test mode
- ❌ Production code has test-specific logic (code smell)
- ❌ Can accidentally enable in production
- ❌ Violates separation of concerns

### Recommended Fix Approach

**Dependency injection + backward compatibility:**

```python
# app/services/orchestrator.py
def __init__(
    self,
    vectordb_url="http://localhost:6333",
    llm_base_url="http://localhost:8000/v1",
    embedding_service=None,  # NEW: Optional injection
    vectordb_service=None,   # NEW: Inject all services
    llm_client=None          # NEW: Full DI support
):
    # Use injected or create default
    self.embedding_service = embedding_service or EmbeddingService(use_remote=True)
    self.vectordb_service = vectordb_service or VectorDBService(url=vectordb_url)
    self.llm_client = llm_client or LLMClientService(base_url=llm_base_url)
```

**Rationale:**
- Backward compatible (existing code works)
- Proper DI for tests
- Production code unchanged
- Gradual migration path

### Unresolved Questions

1. **Why use_remote=True by default?** Should tests use local mode instead?
2. **Is there a test embedding service?** Check docker-compose.test.yml
3. **Should we use FastAPI dependency_overrides?** Check app/main.py for DI patterns

---

## HIGH PRIORITY 3: Authentication Middleware (10+ Failures)

### Root Cause Analysis

**File**: `tests/unit/test_upload_endpoint.py:40`
**Error**: `AssertionError: Expected 200, got 401 Unauthorized`
**Affected Endpoint**: `POST /api/v1/upload`

#### Current Implementation vs Expected Behavior

**Upload endpoint** (`app/api/v1/upload.py:42-47`):
```python
@router.post("/api/v1/upload", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    collection_name: str = Form(...),
    api_key: str = Depends(verify_api_key)  # ← Auth required
):
```

**Auth middleware** (`app/api/middleware/auth.py:28-66`):
```python
async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    api_key = get_api_key()  # os.getenv("API_KEY")

    # Dev mode: no key = allow all
    if not api_key:
        return "dev-mode"

    # Auth enabled: require Bearer token
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing API key")

    if credentials.credentials != api_key:
        raise HTTPException(status_code=401, detail="Invalid API key")
```

**Test implementation** (`tests/unit/test_upload_endpoint.py:19-40`):
```python
async def test_upload_valid_pdf_success(self):
    from app.main import app

    # NO AUTH HEADER PROVIDED
    files = {"file": ("test.pdf", BytesIO(pdf_content), "application/pdf")}
    data = {"collection_name": "documents"}

    async with AsyncClient(...) as client:
        response = await client.post("/api/v1/upload", files=files, data=data)

    assert response.status_code == 200  # FAILS: Got 401
```

**Why the failure occurs:**
1. Test environment has `.env` file loaded
2. `.env` contains `API_KEY=b9b864c03c693b7a62c656c1...` (not empty)
3. Auth middleware sees `api_key` is set → Auth enabled
4. Test doesn't provide `Authorization: Bearer` header
5. Middleware returns 401 Unauthorized

#### Environment Leakage

**The problem:**
```
Test Expectation:           Reality:
   ↓                          ↓
.env NOT loaded           .env IS loaded (app/config.py:12)
API_KEY = None            API_KEY = "b9b864c..."
Auth = Dev mode           Auth = Enabled ✅
Test passes               Test fails with 401 ❌
```

**Root cause chain:**
```
1. app/config.py:12 → model_config = ConfigDict(env_file=".env")
2. app/config.py:79 → settings = Settings()  # Loads .env at import
3. Any test that imports app.main → Triggers Settings() → .env loaded
4. os.getenv("API_KEY") → Returns value from .env
5. Auth middleware enabled → Tests need Bearer token
```

#### Design Mismatch

**Architectural conflict:**
```
Production:
  ↓
  API_KEY from K8s Secret → Auth enabled ✅

Development:
  ↓
  No API_KEY in .env → Auth disabled (dev mode) ✅

Tests:
  ↓
  .env loaded with API_KEY → Auth enabled unexpectedly ❌
```

### Side Effects of Potential Fixes

#### Approach 1: Mock API_KEY environment variable in tests
```python
@pytest.fixture(autouse=True)
def disable_auth():
    with patch.dict(os.environ, {"API_KEY": ""}, clear=False):
        yield
```

**Trade-offs:**
- ✅ Simple fixture
- ✅ No code changes
- ❌ Every test file needs fixture
- ❌ Can't test auth logic
- ❌ Masks real auth behavior

#### Approach 2: Add auth headers to test requests
```python
async def test_upload_valid_pdf_success(self):
    headers = {"Authorization": "Bearer test-api-key-123"}

    with patch("os.getenv", return_value="test-api-key-123"):
        response = await client.post(
            "/api/v1/upload",
            files=files,
            data=data,
            headers=headers  # ADD THIS
        )
```

**Trade-offs:**
- ✅ Tests real auth flow
- ✅ More realistic tests
- ❌ Need to update 10+ test files
- ❌ Mock coordination (patch must match header)
- ❌ More boilerplate

#### Approach 3: Use FastAPI dependency_overrides
```python
@pytest.fixture
def test_app():
    from app.main import app

    # Override auth dependency
    async def mock_verify_api_key():
        return "test-mode"

    app.dependency_overrides[verify_api_key] = mock_verify_api_key
    yield app
    app.dependency_overrides.clear()
```

**Trade-offs:**
- ✅ Clean separation (test infra vs prod code)
- ✅ Centralized in conftest.py
- ✅ Can override per-test if needed
- ❌ Need to import verify_api_key correctly
- ❌ Requires understanding FastAPI DI

### Recommended Fix Approach

**FastAPI dependency_overrides (most Pythonic):**

```python
# tests/conftest.py
@pytest.fixture
def test_app():
    from app.main import app
    from app.api.middleware.auth import verify_api_key

    async def mock_auth():
        return "test-mode"

    app.dependency_overrides[verify_api_key] = mock_auth
    yield app
    app.dependency_overrides.clear()

# tests/unit/test_upload_endpoint.py
async def test_upload_valid_pdf_success(test_app):  # Use fixture
    async with AsyncClient(transport=ASGITransport(app=test_app)) as client:
        response = await client.post("/api/v1/upload", ...)
```

**Rationale:**
- FastAPI's official testing approach
- Clean test/prod separation
- Can test auth separately
- One-time fixture setup

### Unresolved Questions

1. **Should tests verify auth logic?** Separate test suite for auth middleware?
2. **How does staging/prod handle API_KEY?** Check K8s deployment manifests
3. **Is dev mode safe?** Should it log warnings in production?

---

## HIGH PRIORITY 4: Mock Configuration (8+ Failures)

### Root Cause Analysis

**File**: `app/services/llm_client.py:80`
**Error**: `TypeError: '<' not supported between instances of 'MagicMock' and 'int'`
**Affected Code**:
```python
# Line 76-86
if hasattr(response, 'usage') and response.usage:
    llm_token_count.labels(
        model=self.model,
        type='input'
    ).inc(response.usage.prompt_tokens)  # ← Line 80: BOOM!

    llm_token_count.labels(
        model=self.model,
        type='output'
    ).inc(response.usage.completion_tokens)
```

#### Current Implementation vs Expected Behavior

**Test mock** (`tests/unit/test_llm_client.py:38-41`):
```python
# Mock the OpenAI client response
mock_response = MagicMock()
mock_response.choices = [MagicMock()]
mock_response.choices[0].message.content = "Python is a programming language"
# ❌ Missing: mock_response.usage.prompt_tokens
```

**Prometheus Counter.inc()** (from prometheus_client library):
```python
def inc(self, amount=1):
    if amount < 0:  # ← Line that fails
        raise ValueError("Counter cannot decrease")
    self._value += amount
```

**Why the failure occurs:**
1. Mock doesn't specify `response.usage.prompt_tokens`
2. Accessing undefined attribute returns `MagicMock()` object
3. `llm_token_count.inc(MagicMock())` calls `MagicMock() < 0`
4. Python can't compare MagicMock with int → TypeError

#### Mock Attribute Access Chain

**The problem:**
```python
# Test mock:
mock_response = MagicMock()

# Code accesses:
response.usage.prompt_tokens
    ↓
mock_response.usage          # Returns MagicMock() (auto-generated)
    ↓
mock_response.usage.prompt_tokens  # Returns MagicMock() (auto-generated)
    ↓
llm_token_count.inc(MagicMock())  # Passes MagicMock to Prometheus
    ↓
if MagicMock() < 0:  # TypeError ❌
```

**Why this happens:**
- MagicMock auto-generates attributes on access
- Test didn't explicitly set numeric values
- Production code assumes real OpenAI response object
- Prometheus library does type checking

#### Design Mismatch

**Architectural issue:**
```
Unit Test Assumption:
  ↓
  "Mock only what's tested (response.choices[0].message.content)"

Production Code Reality:
  ↓
  "Uses response.usage.prompt_tokens for metrics"

Result:
  ↓
  Incomplete mock causes TypeError in metrics code
```

### Side Effects of Potential Fixes

#### Approach 1: Add numeric attributes to mock
```python
mock_response = MagicMock()
mock_response.choices[0].message.content = "Python is a programming language"
mock_response.usage.prompt_tokens = 10      # ADD
mock_response.usage.completion_tokens = 15  # ADD
mock_response.usage.total_tokens = 25       # ADD
```

**Trade-offs:**
- ✅ Simple, 3 lines
- ✅ Matches OpenAI API structure
- ✅ Tests metrics code
- ❌ Need to update multiple test files
- ❌ Can forget to update when new fields added

#### Approach 2: Patch Prometheus metrics
```python
@patch('app.services.llm_client.llm_token_count')
async def test_llm_client_generate(mock_metrics, mocker):
    mock_metrics.labels.return_value.inc.return_value = None
    # Test only LLM logic, ignore metrics
```

**Trade-offs:**
- ✅ Isolates test from metrics code
- ✅ Clearer test intent
- ❌ Doesn't test metrics recording
- ❌ Can mask metrics bugs
- ❌ More mocking boilerplate

#### Approach 3: Use spec-based mocks
```python
from openai.types.chat import ChatCompletion

mock_response = MagicMock(spec=ChatCompletion)
mock_response.usage = MagicMock()
mock_response.usage.prompt_tokens = 10
mock_response.usage.completion_tokens = 15
```

**Trade-offs:**
- ✅ Type-safe mocking
- ✅ Catches attribute typos
- ❌ Requires knowing OpenAI types
- ❌ More verbose
- ❌ OpenAI SDK updates can break tests

### Recommended Fix Approach

**Complete mock with helper function:**

```python
# tests/conftest.py
def create_openai_response(content: str, prompt_tokens: int = 10, completion_tokens: int = 15):
    """Create a complete OpenAI response mock for testing."""
    mock = MagicMock()
    mock.choices = [MagicMock()]
    mock.choices[0].message.content = content
    mock.usage = MagicMock()
    mock.usage.prompt_tokens = prompt_tokens
    mock.usage.completion_tokens = completion_tokens
    mock.usage.total_tokens = prompt_tokens + completion_tokens
    return mock

# tests/unit/test_llm_client.py
async def test_llm_client_generate(mocker):
    mock_response = create_openai_response("Python is a programming language")
    mock_create = AsyncMock(return_value=mock_response)
    mocker.patch.object(client.client.chat.completions, 'create', mock_create)
```

**Rationale:**
- Reusable across tests
- Complete response structure
- Easy to customize per test
- Documents expected response shape

### Unresolved Questions

1. **Should metrics be tested separately?** Unit vs integration test boundary
2. **Are there other numeric comparisons?** Grep for `< 0`, `> 0` in codebase
3. **Why didn't AsyncMock handle this?** MagicMock vs spec differences

---

## Cross-Cutting Issues

### Issue 1: Test Isolation vs Reality

**Pattern observed across all failures:**
```
Unit tests expect: Isolated components, no external dependencies
Production code: Services tightly coupled, lazy initialization triggers network calls
Result: Tests fail when mocks incomplete
```

**Recommendation**: Refactor services to use dependency injection pattern consistently.

### Issue 2: Environment Configuration

**Pattern:**
```
.env file loaded at module import → Tests inherit production config
Tests use patch.dict(clear=True) → Still loads .env first
Result: Unpredictable test behavior based on .env contents
```

**Recommendation**: Use pytest-env plugin or separate test configuration.

### Issue 3: Fixture vs Dependency Override

**Pattern:**
```
conftest.py has fixtures → Tests don't use them
FastAPI has dependency_overrides → Tests don't use it
Result: Each test file implements own mocking strategy
```

**Recommendation**: Standardize on FastAPI dependency_overrides for API tests.

---

## Impact Assessment

### Test Categories by Fix Complexity

| Issue | Failures | Fix Time | Risk | Priority |
|-------|----------|----------|------|----------|
| BLOCKER 1: Pydantic Settings | 16 | 30min | Low | P0 |
| BLOCKER 2: Service Mocking | 35+ | 4-6hr | Medium | P0 |
| HIGH 3: Auth Middleware | 10+ | 2hr | Low | P1 |
| HIGH 4: Mock Configuration | 8+ | 1-2hr | Low | P1 |

### Recommended Fix Order

1. **BLOCKER 1** (quick win, unblocks config tests)
2. **HIGH 3** (single fixture, unblocks upload tests)
3. **HIGH 4** (helper function, unblocks LLM tests)
4. **BLOCKER 2** (largest effort, requires refactoring)

---

## Unresolved Questions (Overall)

1. **When did these tests last pass?** Git blame on test files
2. **Are integration tests affected?** Check `tests/integration/`
3. **Should we add pre-commit hooks?** Run subset of tests before commit
4. **Is coverage still >80%?** Some tests may be incorrectly marked as passing
5. **Who owns test infrastructure?** Clarify responsibilities for test maintenance

---

**Next Steps**: Review this analysis and approve fix approach before implementation.
