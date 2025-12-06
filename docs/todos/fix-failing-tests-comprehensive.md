# Comprehensive Todo List: Fix 70+ Failing Tests

**Date**: 2025-11-29
**Status**: 🔴 In Progress
**Priority**: High
**Coverage**: 88.91% (above 80% threshold ✅)

---

## Executive Summary

After Phase 5 Day 1 CI/CD setup, we discovered 70+ failing tests. These failures are categorized into:
- ✅ **Drift Detector Tests (4)**: FIXED - Evidently v0.7.17 API compatibility
- 🔴 **API Response Schema Issues (11)**: Missing `used_rag` field
- 🔴 **Embedding Service Connection (7)**: Mock connection errors
- 🔴 **Query Logger Issues (4)**: AttributeError on mock objects
- 🔴 **Query Router Service (3)**: Missing embedding parameter
- 🔴 **Query Graph Tests (7)**: Assertion and error handling issues
- 🔴 **Readiness Endpoint (6)**: Health check logic issues
- 🔴 **Upload Endpoint (10)**: Context manager protocol errors
- 🔴 **Orchestrator Tests (7)**: Embedding service connection errors
- 🔴 **Orchestrator Metrics (2)**: Assertion failures
- 🔴 **Miscellaneous (9)**: Various mocking and assertion issues

---

## Phase 1: Critical API Response Schema Fixes (11 tests)

### Problem
`KeyError: 'used_rag'` - API endpoints expect `used_rag` field in response but orchestrator doesn't return it.

### Affected Tests
```
tests/unit/test_query_endpoint.py::test_query_endpoint_returns_classification
tests/unit/test_query_endpoint.py::test_query_endpoint_calls_orchestrator_without_use_rag
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_calls_orchestrator_with_request_data
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_includes_classification_when_present
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_includes_query_in_response
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_includes_sources_in_response
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_includes_used_rag_in_response
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_passes_all_parameters_to_orchestrator
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_passes_collection_name_to_orchestrator
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_response_validates_as_query_response_schema
tests/unit/test_query_router_api.py::TestQueryEndpointRouter::test_query_endpoint_returns_query_response
```

### Root Cause
`app/api/v1/query.py:52` expects `result["used_rag"]` but orchestrator returns classification instead.

### Fix Steps

#### Step 1.1: Update Orchestrator Response Schema
- **File**: `app/services/orchestrator.py`
- **Location**: `query()` method return statement
- **Change**: Add `used_rag` field to response dict
  ```python
  return {
      "answer": answer,
      "sources": sources,
      "classification": classification,
      "used_rag": classification.query_type == QueryType.RAG  # ADD THIS
  }
  ```

#### Step 1.2: Update Query Endpoint
- **File**: `app/api/v1/query.py`
- **Location**: Line 52
- **Verify**: `used_rag=result["used_rag"]` exists and works

#### Step 1.3: Update Test Mocks
- **Files**: All failing test files
- **Change**: Update mock return values to include `used_rag`
  ```python
  mock_result = {
      "answer": "...",
      "sources": [],
      "classification": QueryClassification(...),
      "used_rag": True  # ADD THIS
  }
  ```

#### Step 1.4: Run Tests
```bash
pytest tests/unit/test_query_endpoint.py tests/unit/test_query_router_api.py -v
```

**Estimated Time**: 1-2 hours
**Dependencies**: None
**Priority**: 🔴 Critical

---

## Phase 2: Embedding Service Connection Mocking (14 tests)

### Problem
`RuntimeError: Cannot connect to embedding service at http://localhost:8001`

### Affected Tests
```
tests/unit/test_orchestrator.py::test_ingest_accepts_file_path_and_collection
tests/unit/test_orchestrator.py::test_ingest_creates_job_and_returns_job_id
tests/unit/test_orchestrator.py::test_ingest_accepts_existing_job_id
tests/unit/test_orchestrator.py::test_ingest_updates_job_to_processing
tests/unit/test_orchestrator.py::test_ingest_loads_document_from_gcs
tests/unit/test_orchestrator.py::test_ingest_completes_full_pipeline_and_marks_completed
tests/unit/test_orchestrator_metrics.py::TestIngestionJobDurationMetric::test_records_total_job_duration_on_success
tests/unit/test_vectordb.py::TestVectorDBServiceSearchOperations::test_vectordb_service_search_vectors
```

### Root Cause
Tests are not properly mocking the embedding service initialization or health check.

### Fix Steps

#### Step 2.1: Create Embedding Service Mock Fixture
- **File**: `tests/conftest.py`
- **Add**:
  ```python
  @pytest.fixture
  def mock_embedding_service():
      """Mock embedding service to prevent connection attempts."""
      with patch('app.services.embedding.EmbeddingService') as mock:
          mock_instance = MagicMock()
          mock_instance.embed_single.return_value = [0.1] * 1024
          mock_instance.embed_batch.return_value = [[0.1] * 1024]
          mock_instance.get_embedding_dimension.return_value = 1024
          mock_instance.is_healthy.return_value = True
          mock.return_value = mock_instance
          yield mock_instance
  ```

#### Step 2.2: Add Fixture to Affected Tests
- **Files**: All failing orchestrator and vectordb tests
- **Change**: Add `mock_embedding_service` to test parameters
  ```python
  def test_ingest_accepts_file_path(
      orchestrator,
      mock_embedding_service  # ADD THIS
  ):
  ```

#### Step 2.3: Mock Embedding Service in Orchestrator Initialization
- **Alternative**: Patch at import level
  ```python
  @patch('app.dependencies.get_embedding_service')
  def test_ingest_accepts_file_path(mock_get_embedding):
      mock_get_embedding.return_value = mock_embedding_instance
  ```

#### Step 2.4: Run Tests
```bash
pytest tests/unit/test_orchestrator.py tests/unit/test_orchestrator_metrics.py tests/unit/test_vectordb.py -v
```

**Estimated Time**: 2-3 hours
**Dependencies**: None
**Priority**: 🔴 Critical

---

## Phase 3: Query Logger AttributeError Fixes (4 tests)

### Problem
`AttributeError: 'NoneType' object has no attribute 'kwargs'`

### Affected Tests
```
tests/unit/test_query_logger.py::TestQueryLoggerService::test_get_query_logs_success
tests/unit/test_query_logger.py::TestQueryLoggerService::test_log_query_metadata_structure
tests/unit/test_query_logger.py::TestQueryLoggerService::test_log_query_success
tests/unit/test_query_logger.py::TestQueryLoggerService::test_log_query_with_none_query_type
```

### Root Cause
Mock objects are not properly configured to return expected attributes.

### Fix Steps

#### Step 3.1: Investigate Query Logger Mock Setup
- **File**: `tests/unit/test_query_logger.py`
- **Check**: How Qdrant client is being mocked

#### Step 3.2: Fix Mock Configuration
- **Likely Issue**: `mock_qdrant.upsert.return_value` is None
- **Fix**:
  ```python
  mock_qdrant = MagicMock()
  mock_qdrant.upsert.return_value = MagicMock(status="completed")
  mock_qdrant.scroll.return_value = ([], None)  # For get_query_logs
  ```

#### Step 3.3: Ensure Async Mocks
- **Check**: If query_logger uses async operations
- **Use**: `AsyncMock()` instead of `MagicMock()` where needed

#### Step 3.4: Run Tests
```bash
pytest tests/unit/test_query_logger.py -v
```

**Estimated Time**: 1-2 hours
**Dependencies**: None
**Priority**: 🟡 Medium

---

## Phase 4: Query Router Service Initialization (3 tests)

### Problem
`TypeError: QueryRouterService.__init__() missing 1 required positional argument: 'embedding'`

### Affected Tests
```
tests/unit/test_query_router_service.py::TestQueryRouterServiceInit::test_init_with_all_services
tests/unit/test_query_router_service.py::TestQueryRouterServiceRouteQuery::test_route_query_error_handling
tests/unit/test_query_router_service.py::TestQueryRouterServiceRouteQuery::test_route_rag_query_success
```

### Root Cause
`QueryRouterService` API changed to require `embedding` parameter but tests weren't updated.

### Fix Steps

#### Step 4.1: Review QueryRouterService Constructor
- **File**: `app/services/query_router_service.py`
- **Check**: Current `__init__` signature

#### Step 4.2: Update Test Initialization
- **File**: `tests/unit/test_query_router_service.py`
- **Change**: Add embedding service to all instantiations
  ```python
  mock_embedding = MagicMock()
  router = QueryRouterService(
      llm_client=mock_llm,
      vectordb=mock_vectordb,
      embedding=mock_embedding  # ADD THIS
  )
  ```

#### Step 4.3: Run Tests
```bash
pytest tests/unit/test_query_router_service.py -v
```

**Estimated Time**: 30 minutes
**Dependencies**: None
**Priority**: 🟢 Low

---

## Phase 5: Query Graph Test Failures (7 tests)

### Problem
Multiple issues: assertion failures, error message mismatches, None values

### Affected Tests
```
tests/unit/test_query_graph.py::TestQueryGraphNodes::test_retrieve_node
tests/unit/test_query_graph.py::TestQueryGraphBuilding::test_graph_routes_rag_query_to_retrieve
tests/unit/test_query_graph.py::TestEndToEndGraphFlows::test_complete_rag_flow
tests/unit/test_query_graph.py::TestEndToEndGraphFlows::test_complete_multi_hop_flow
tests/unit/test_query_graph.py::TestEndToEndGraphFlows::test_edge_case_empty_retrieval_results
tests/unit/test_query_graph.py::TestEndToEndGraphFlows::test_error_handling_retrieval_failure
tests/unit/test_query_graph.py::TestEndToEndGraphFlows::test_error_handling_generation_failure
```

### Root Causes
- Embedding service not provided in config
- Assertions expecting specific error messages
- None values where data expected

### Fix Steps

#### Step 5.1: Add Embedding Service to Graph Config
- **File**: `tests/unit/test_query_graph.py`
- **Location**: Graph configuration setup
- **Add**: `embedding_service` to config dict

#### Step 5.2: Update Error Message Assertions
- **Tests**: error_handling_* tests
- **Change**: Match actual error messages from code
  ```python
  # Before
  assert 'Retrieval failed' in result["error"]
  # After
  assert 'Embedding service not provided' in result["error"]
  ```

#### Step 5.3: Fix None Assertions
- **Tests**: retrieve_node, complete_*_flow tests
- **Check**: What's actually being returned
- **Fix**: Mock return values or update assertions

#### Step 5.4: Run Tests
```bash
pytest tests/unit/test_query_graph.py -v
```

**Estimated Time**: 2-3 hours
**Dependencies**: Phase 4 (Query Router)
**Priority**: 🟡 Medium

---

## Phase 6: Readiness Endpoint Health Checks (6 tests)

### Problem
Expected 503 (unhealthy) but got 200 (healthy)

### Affected Tests
```
tests/unit/test_readiness_endpoint.py::TestReadinessEndpoint::test_embedding_unhealthy
tests/unit/test_readiness_endpoint.py::TestReadinessEndpoint::test_llm_unhealthy
tests/unit/test_readiness_endpoint.py::TestReadinessEndpoint::test_qdrant_unhealthy
tests/unit/test_readiness_endpoint.py::TestReadinessEndpoint::test_gcs_bucket_not_configured
tests/unit/test_readiness_endpoint.py::TestReadinessEndpoint::test_service_timeout
tests/unit/test_readiness_endpoint.py::TestReadinessEndpoint::test_failure_metrics_incremented
```

### Root Cause
Health check logic is not properly detecting unhealthy states or mocks are not configured correctly.

### Fix Steps

#### Step 6.1: Review Readiness Endpoint Logic
- **File**: `app/api/v1/ready.py` or `app/main.py`
- **Check**: How health checks are performed

#### Step 6.2: Update Health Check Mocks
- **File**: `tests/unit/test_readiness_endpoint.py`
- **Ensure**: Mocked services return unhealthy states
  ```python
  mock_embedding.is_healthy.return_value = False
  mock_llm.is_healthy.return_value = False
  mock_qdrant.get_collection.side_effect = Exception("Connection failed")
  ```

#### Step 6.3: Test Timeout Handling
- **Test**: test_service_timeout
- **Mock**: Slow response using `time.sleep` or async timeout

#### Step 6.4: Verify Metrics Increment
- **Test**: test_failure_metrics_incremented
- **Check**: Prometheus counter is actually incremented

#### Step 6.5: Run Tests
```bash
pytest tests/unit/test_readiness_endpoint.py -v
```

**Estimated Time**: 2 hours
**Dependencies**: Phase 2 (Embedding Service Mocking)
**Priority**: 🟡 Medium

---

## Phase 7: Upload Endpoint Context Manager Errors (10 tests)

### Problem
`TypeError: 'Mock' object does not support the context manager protocol`

### Affected Tests
```
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_valid_pdf_success
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_requires_collection_name
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_validates_allowed_mime_types
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_invalid_file_type_returns_400
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_empty_file_returns_400
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_file_too_large_returns_413
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_gcs_failure_returns_500
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_duration_is_positive
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_records_duration_metric
tests/unit/test_upload_endpoint.py::TestUploadEndpoint::test_upload_records_file_size_metric
```

### Root Cause
GCS client or file upload objects are mocked but don't support `with` statement (context manager protocol).

### Fix Steps

#### Step 7.1: Identify Context Manager Usage
- **File**: `app/api/v1/upload.py` or `app/services/gcs_storage.py`
- **Find**: `with` statements that need mocking

#### Step 7.2: Create Proper Context Manager Mocks
- **File**: `tests/unit/test_upload_endpoint.py`
- **Fix**:
  ```python
  # Before
  mock_gcs = MagicMock()

  # After
  mock_gcs = MagicMock()
  mock_gcs.__enter__ = MagicMock(return_value=mock_gcs)
  mock_gcs.__exit__ = MagicMock(return_value=False)
  ```

#### Step 7.3: Alternative - Use context manager decorator
```python
from unittest.mock import MagicMock, patch

@contextmanager
def mock_gcs_client():
    mock = MagicMock()
    yield mock

with patch('app.services.gcs_storage.storage.Client', side_effect=mock_gcs_client):
    # test code
```

#### Step 7.4: Run Tests
```bash
pytest tests/unit/test_upload_endpoint.py -v
```

**Estimated Time**: 2-3 hours
**Dependencies**: None
**Priority**: 🟡 Medium

---

## Phase 8: Miscellaneous Fixes (9 tests)

### Problem Group 1: Orchestrator Test Assertion
```
tests/unit/test_orchestrator.py::test_orchestrator_query_uses_router
  Error: AssertionError: expected call not found.
  Expected: mock(query='What is Python?', collection_name='docs')
  Actual: mock(query='What is Python?', collection_name='docs', force_rag=False)
```

**Fix**: Update test expectation to include `force_rag` parameter.

### Problem Group 2: LLM Client TypeError
```
tests/unit/test_llm_client.py::test_llm_client_generate
tests/unit/test_llm_client_tracing.py::TestLLMClientTracing::test_generate_creates_span
  Error: TypeError: '<' not supported between instances of 'MagicMock' and 'int'
```

**Fix**: Mock numeric values properly for comparison operations.

### Problem Group 3: Ingestion Error Metrics
```
tests/unit/test_ingestion_error_metrics.py::test_records_error_on_storage_failure
  Error: assert 3.0 > 3.0
```

**Fix**: Check why metric isn't incrementing. Likely timing or mock issue.

### Problem Group 4: Orchestrator Metrics Assertion
```
tests/unit/test_orchestrator_metrics.py::TestOrchestratorMetrics::test_storage_stage_records_duration_metric
  Error: AssertionError: Should record storage stage duration
```

**Fix**: Ensure storage stage metric is actually recorded.

### Fix Steps

#### Step 8.1: Fix Orchestrator Router Call
- **File**: `tests/unit/test_orchestrator.py`
- **Test**: test_orchestrator_query_uses_router
- **Change**:
  ```python
  mock_router.route_query.assert_called_once_with(
      query='What is Python?',
      collection_name='docs',
      force_rag=False  # ADD THIS
  )
  ```

#### Step 8.2: Fix LLM Client Mocking
- **File**: `tests/unit/test_llm_client.py`, `tests/unit/test_llm_client_tracing.py`
- **Find**: Where comparison happens
- **Fix**: Mock with actual numbers
  ```python
  mock_response.usage.total_tokens = 100  # Not MagicMock()
  mock_response.usage.prompt_tokens = 50
  ```

#### Step 8.3: Fix Error Metrics Test
- **File**: `tests/unit/test_ingestion_error_metrics.py`
- **Debug**: Why counter isn't incrementing
- **Check**: Metrics collection timing

#### Step 8.4: Fix Storage Metrics
- **File**: `tests/unit/test_orchestrator_metrics.py`
- **Check**: Storage stage is actually called
- **Verify**: Metric recording logic

#### Step 8.5: Run Tests
```bash
pytest tests/unit/test_orchestrator.py::test_orchestrator_query_uses_router -v
pytest tests/unit/test_llm_client.py -v
pytest tests/unit/test_ingestion_error_metrics.py -v
pytest tests/unit/test_orchestrator_metrics.py -v
```

**Estimated Time**: 2 hours
**Dependencies**: Various
**Priority**: 🟢 Low

---

## Execution Strategy

### Recommended Order
1. ✅ **Phase 1** (API Response Schema) - Affects 11 tests, critical for API functionality
2. **Phase 2** (Embedding Service) - Affects 14 tests, blocks multiple features
3. **Phase 4** (Query Router) - Quick win, only 3 tests
4. **Phase 3** (Query Logger) - 4 tests, moderate complexity
5. **Phase 5** (Query Graph) - 7 tests, depends on Phase 4
6. **Phase 6** (Readiness Endpoint) - 6 tests, important for deployment
7. **Phase 7** (Upload Endpoint) - 10 tests, context manager complexity
8. **Phase 8** (Miscellaneous) - 9 tests, various small fixes

### Parallel Execution Opportunities
- **Phase 1** and **Phase 2** can run in parallel (different files)
- **Phase 3** and **Phase 4** can run in parallel
- **Phase 6** and **Phase 7** can run in parallel

### CI/CD Integration
After each phase, run:
```bash
# Run affected tests
pytest tests/unit/test_<module>.py -v

# Check coverage impact
pytest tests/unit/ --cov=app --cov-report=term-missing

# Ensure no regression
pytest tests/unit/ -v
```

---

## Success Criteria

### Per Phase
- [ ] All targeted tests pass ✅
- [ ] No new test failures introduced ✅
- [ ] Coverage remains >= 80% ✅
- [ ] Tests run in < 5 minutes ✅

### Overall
- [ ] 0 failing unit tests (target: reduce from 70+ to 0)
- [ ] Coverage >= 88% (maintain or improve from 88.91%)
- [ ] CI workflow passes on all branches
- [ ] Documentation updated with any API changes

---

## Tracking Progress

### Daily Standup Questions
1. Which phase are you working on?
2. How many tests fixed today?
3. Any blockers or dependencies?
4. Estimated completion date?

### Metrics Dashboard
```
Total Tests: 363
Passing: 293 (80.7%)
Failing: 70 (19.3%)
Coverage: 88.91%

Phase 1: 0/11 fixed (0%)
Phase 2: 0/14 fixed (0%)
Phase 3: 0/4 fixed (0%)
Phase 4: 0/3 fixed (0%)
Phase 5: 0/7 fixed (0%)
Phase 6: 0/6 fixed (0%)
Phase 7: 0/10 fixed (0%)
Phase 8: 0/9 fixed (0%)
```

---

## Rollback Plan

If fixes introduce regressions:
1. **Identify**: Which phase caused the regression
2. **Isolate**: Revert the problematic commits
3. **Debug**: Fix the root cause
4. **Re-apply**: Test thoroughly before pushing

---

## Unresolved Questions

1. **Why did these tests pass before?** - Investigate git history for when they broke
2. **Are there integration tests affected?** - Check `tests/integration/` directory
3. **Should we skip flaky tests temporarily?** - Decision needed on using `@pytest.mark.skip`

---

**Last Updated**: 2025-11-29
**Author**: Phase 5 CI/CD Implementation
**Next Review**: After each phase completion
