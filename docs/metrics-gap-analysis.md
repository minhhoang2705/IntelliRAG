# Metrics Instrumentation Gap Analysis

**Date**: 2025-11-09
**Status**: 🔴 Critical gaps identified

## Executive Summary

Of 19 defined Prometheus metrics, **only 9 are instrumented** (47% coverage). Critical HTTP and LLM metrics are missing, preventing monitoring of requests/second, response times, and token usage.

## Metrics Inventory

### ✅ INSTRUMENTED (9 metrics)

| Metric | Location | Purpose |
|--------|----------|---------|
| `document_processing_stage_duration_seconds` | orchestrator.py:185-268 | Document processing stages timing |
| `ingestion_chunks_created` | orchestrator.py:202 | Chunks created per document |
| `ingestion_job_duration_seconds` | orchestrator.py:293-303 | Total job duration |
| `ingestion_errors_total` | orchestrator.py:189-272 | Ingestion errors by type |
| `file_upload_duration_seconds` | upload.py:125 | File upload timing |
| `file_upload_size_bytes` | upload.py:126 | Uploaded file sizes |
| `ingestion_jobs_total` | ingest.py:56,157,179 | Total ingestion jobs |
| `ingestion_jobs_active` | ingest.py:57,143-144,163 | Active ingestion jobs |
| `query_classification_duration_seconds` | classifier.py:82 | Query classification timing |
| `query_classification_confidence` | classifier.py:83 | Classification confidence scores |
| `query_classification_total` | classifier.py:84-86 | Total classifications by type |

### ❌ NOT INSTRUMENTED (10 metrics)

#### 🔴 CRITICAL - HTTP Metrics (No Middleware!)

| Metric | Defined | Missing From | Impact |
|--------|---------|--------------|--------|
| `http_requests_total` | metrics.py:58 | All endpoints | Cannot track requests/second |
| `http_request_duration_seconds` | metrics.py:64 | All endpoints | Cannot measure response times |

**Problem**: No HTTP middleware exists to automatically track ALL requests.
**Solution**: Create `MetricsMiddleware` to instrument all HTTP requests.

#### 🔴 CRITICAL - LLM Metrics

| Metric | Defined | Missing From | Impact |
|--------|---------|--------------|--------|
| `llm_token_count` | metrics.py:51 | llm_client.py | Cannot track token usage/costs |

**Problem**: LLM responses don't record token counts.
**Solution**: Extract token counts from OpenAI API responses and track input/output separately.

#### 🔴 CRITICAL - RAG Pipeline Metrics

| Metric | Defined | Missing From | Impact |
|--------|---------|--------------|--------|
| `rag_query_duration_seconds` | metrics.py:37 | rag_pipeline.py | Cannot measure stage-by-stage performance |
| `rag_retrieval_results` | metrics.py:44 | rag_pipeline.py | Cannot track retrieved documents count |

**Problem**: RAG pipeline has tracing but no Prometheus metrics.
**Solution**: Add timing instrumentation for embedding, retrieval, and generation stages.

#### 🟡 MEDIUM - Query Router Metrics

| Metric | Defined | Missing From | Impact |
|--------|---------|--------------|--------|
| `query_router_decisions_total` | metrics.py:30 | query_router_service.py | Cannot track routing decisions |

**Problem**: Router classifies queries but doesn't record decision types.
**Solution**: Instrument `route_query` to track RAG vs direct decisions.

#### 🟢 LOW - Supporting Metrics

| Metric | Defined | Missing From | Impact |
|--------|---------|--------------|--------|
| `vector_db_operations` | metrics.py:72 | vectordb.py | Cannot track DB operation counts |
| `embedding_cache_hits` | metrics.py:79 | embedding.py | Cannot measure cache efficiency |
| `gpu_utilization` | metrics.py:86 | N/A | Cannot monitor GPU usage |

## Impact Analysis

### What You're Missing Right Now

**Without HTTP Metrics:**
- ❌ No requests per second (RPS) monitoring
- ❌ No response time percentiles (P50, P95, P99)
- ❌ No error rate tracking (4xx, 5xx)
- ❌ No endpoint-specific performance metrics

**Without LLM Metrics:**
- ❌ No token usage tracking → Can't estimate costs
- ❌ No throughput visibility (tokens/second)
- ❌ No input vs output token breakdown

**Without RAG Pipeline Metrics:**
- ❌ No visibility into which stage is slow (embedding, retrieval, generation)
- ❌ Can't optimize based on data (e.g., "retrieval takes 80% of time")

### What You Have

**Ingestion Pipeline** - ✅ Well instrumented
- Can track document processing performance
- Can measure chunking efficiency
- Can monitor job success/failure rates

**Query Classification** - ✅ Well instrumented
- Can track classification accuracy
- Can measure classification latency

## Recommended Implementation Order

### Phase 1: HTTP Middleware (HIGHEST PRIORITY)
- [ ] Create `MetricsMiddleware` class
- [ ] Instrument `http_requests_total` for all requests
- [ ] Instrument `http_request_duration_seconds` with timing
- [ ] Add to FastAPI app in `main.py`

**Why First**: Gives immediate visibility into all API traffic.

### Phase 2: LLM Metrics (HIGH PRIORITY)
- [ ] Extract token counts from OpenAI response
- [ ] Instrument `llm_token_count` for input/output tokens
- [ ] Add to `LLMClientService.generate()`

**Why Second**: Critical for cost monitoring and performance.

### Phase 3: RAG Pipeline Metrics (HIGH PRIORITY)
- [ ] Add timing for embedding stage
- [ ] Add timing for retrieval stage
- [ ] Add timing for generation stage
- [ ] Track retrieved document counts
- [ ] Instrument in `RAGPipelineService.query_with_rag()`

**Why Third**: Needed for performance optimization.

### Phase 4: Query Router (MEDIUM PRIORITY)
- [ ] Track routing decisions (RAG vs direct)
- [ ] Instrument in `QueryRouterService.route_query()`

### Phase 5: Supporting Metrics (LOW PRIORITY)
- [ ] Vector DB operations tracking
- [ ] Embedding cache hit rate
- [ ] GPU utilization (requires nvidia-smi integration)

## Testing Strategy

Following TDD, for each metric:
1. Write failing test that checks metric value
2. Implement instrumentation
3. Verify test passes
4. Check Prometheus `/metrics` endpoint

## Success Criteria

- [ ] All 19 defined metrics are instrumented
- [ ] `/metrics` endpoint shows non-zero values for active metrics
- [ ] Tests validate metric values after operations
- [ ] Grafana dashboards can query all metrics
- [ ] Coverage target: 100% of defined metrics

## Next Steps

1. Review this gap analysis
2. Prioritize metrics based on business needs
3. Follow TDD workflow for each metric
4. Update Grafana dashboards to use new metrics
5. Set up alerting rules for critical metrics

---

**Note**: This analysis was generated on 2025-11-09. Metrics coverage: 47% (9/19 instrumented).
