---
title: "Phase 2: Two-Stage Retrieval with LLM Reranking"
status: pending
effort: 1d
---

# Phase 2: Two-Stage Retrieval with LLM Reranking

## Context

- [Plan Overview](./plan.md)
- [Phase 1: Template System](./phase-01-template-system.md)
- Current: `rag_pipeline.py` does single-stage top_k=5 retrieval

## Overview

Implement two-stage retrieval: broad recall (top_k=10) followed by LLM reranking (top_n=3) for precision.

## Key Insights

1. **Stage 1**: Vector search returns top_k=10 candidates (broader net)
2. **Stage 2**: **Dedicated cross-encoder reranker** (bge-reranker-v2-m3) scores candidates → top_n=3
3. **350-char preview**: Limit context for fast reranking
4. **Fallback**: If reranker fails, use vector scores

**VALIDATED DECISION**: Use dedicated bge-reranker model instead of LLM-based reranking for better performance isolation and lower latency.

## Requirements

### Functional
- Retrieve 10 candidates in Stage 1
- LLM rerank to 3 documents in Stage 2
- Use rerank.j2 templates (vi/en)
- Fallback to vector-order on parse failure

### Non-Functional
- Reranking latency <100ms
- No regression in context relevance
- 10-15% improvement in answer quality

## Architecture

```
query_with_rag() Flow:
1. Embed query → BGE-M3 (1024-dim)
2. Stage 1: Qdrant search (limit=10)
3. Stage 2: _rerank_documents() → top 3
4. Format context with citations
5. Generate answer with rag_system.j2
```

## Implementation Steps

### Task 2.1: Create Rerank Templates (0.25d)

**File**: `app/services/query_router/templates/en/rerank.j2`

```jinja2
Rank these documents by relevance to the query.
Return ONLY the indices of the top {{ top_n }} most relevant documents.

Query: {{ query }}

Documents:
{% for doc in documents %}
[{{ loop.index0 }}] {{ doc.preview }}
{% endfor %}

Return format: [idx1, idx2, idx3]
Response:
```

**File**: `app/services/query_router/templates/vi/rerank.j2`

```jinja2
Xep hang cac tai lieu theo muc do lien quan den cau hoi.
Chi tra ve chi so cua {{ top_n }} tai lieu lien quan nhat.

Cau hoi: {{ query }}

Tai lieu:
{% for doc in documents %}
[{{ loop.index0 }}] {{ doc.preview }}
{% endfor %}

Dinh dang tra ve: [idx1, idx2, idx3]
Tra loi:
```

### Task 2.2: Implement Reranker Service (0.5d)

**NEW File**: `app/services/reranker_service.py`

```python
import httpx
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

class RerankerService:
    """Cross-encoder reranking using bge-reranker-v2-m3.

    Uses dedicated reranker model for better performance isolation
    (validated decision: not using LLM-based reranking).
    """

    def __init__(self, endpoint: str, timeout: float = 10.0):
        """
        Args:
            endpoint: Reranker inference endpoint (KServe or local)
            timeout: Request timeout in seconds
        """
        self.endpoint = endpoint
        self.timeout = timeout
        self._client = httpx.AsyncClient(timeout=timeout)

    async def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_n: int = 3
    ) -> List[Dict]:
        """Rerank documents using cross-encoder model.

        Args:
            query: User query
            documents: List with 'text', 'score', 'id' keys
            top_n: Number of documents to return

        Returns:
            Top-n reranked documents sorted by rerank score
        """
        if len(documents) <= top_n:
            return documents

        try:
            # Prepare pairs for cross-encoder: (query, doc_text)
            pairs = [
                {"query": query, "text": doc.get("text", "")[:500]}
                for doc in documents
            ]

            # Call reranker endpoint
            response = await self._client.post(
                f"{self.endpoint}/rerank",
                json={"pairs": pairs}
            )
            response.raise_for_status()

            # Parse scores: [{"index": 0, "score": 0.95}, ...]
            scores = response.json().get("scores", [])

            # Sort by rerank score descending
            scored_docs = []
            for item in scores:
                idx = item["index"]
                if 0 <= idx < len(documents):
                    doc = documents[idx].copy()
                    doc["rerank_score"] = item["score"]
                    scored_docs.append(doc)

            scored_docs.sort(key=lambda x: x["rerank_score"], reverse=True)
            return scored_docs[:top_n]

        except Exception as e:
            logger.warning(f"Reranker failed: {e}, falling back to vector scores")
            # Fallback: return first top_n by original vector score
            return documents[:top_n]

    async def close(self):
        await self._client.aclose()
```

**Update**: `app/services/rag_pipeline.py` - Use RerankerService

```python
from app.services.reranker_service import RerankerService

class RAGPipelineService:
    def __init__(
        self,
        ...,
        reranker_service: RerankerService = None  # NEW
    ):
        self.reranker = reranker_service

    async def _rerank_documents(
        self,
        query: str,
        documents: List[Dict],
        top_n: int = 3
    ) -> List[Dict]:
        """Rerank using dedicated cross-encoder model."""
        if not self.reranker:
            # No reranker configured, return by vector score
            return documents[:top_n]

        return await self.reranker.rerank(query, documents, top_n)
```

### Task 2.3: Update query_with_rag() (0.25d)

**Update**: `app/services/rag_pipeline.py`

```python
async def query_with_rag(
    self,
    query: str,
    collection_name: str,
    top_k: int = 10,      # Increased for Stage 1
    top_n: int = 3,       # NEW: Stage 2 result count
    temperature: float = 0.7,
    max_tokens: int = 512,
    language: str = None  # NEW: explicit language
) -> Dict[str, Any]:
    """Two-stage RAG: retrieve top_k → rerank to top_n → generate."""

    with tracer.start_as_current_span("rag.query") as span:
        span.set_attribute("rag.top_k", top_k)
        span.set_attribute("rag.top_n", top_n)

        # Step 1: Embed query
        query_embedding = await self.embedding_service.embed_single_async(query)

        # Step 2: Stage 1 - Broad recall
        search_results = await self.vectordb_service.search_vectors(
            collection_name=collection_name,
            query_vector=query_embedding,
            limit=top_k  # Retrieve more candidates
        )

        # Convert to dict format
        candidates = [
            {
                "text": r.payload.get("text", ""),
                "score": float(r.score),
                "id": str(r.id),
                "title": r.payload.get("title", "")
            }
            for r in search_results
        ]

        # Step 3: Stage 2 - LLM reranking
        reranked = await self._rerank_documents(
            query=query,
            documents=candidates,
            top_n=top_n,
            language=language
        )
        span.set_attribute("rag.reranked_count", len(reranked))

        # Step 4: Format context
        context_texts = [doc["text"] for doc in reranked]

        # Step 5: Generate with template
        system_prompt = self.template_loader.render(
            "rag_system.j2",
            language=language,
            query=query,
            context=context_texts
        )

        answer = await self.llm_client.generate(
            prompt=f"{system_prompt}\n\nQuestion: {query}\n\nAnswer:",
            temperature=temperature,
            max_tokens=max_tokens
        )

        return {
            "answer": answer,
            "sources": reranked
        }
```

## Test Coverage

**File**: `tests/unit/test_rerank.py`

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

class TestRerank:
    @pytest.fixture
    def rag_service(self):
        # Mock dependencies
        ...

    async def test_rerank_returns_top_n(self, rag_service):
        """Should return exactly top_n documents."""
        docs = [{"text": f"doc{i}", "score": 0.9-i*0.1, "id": str(i)} for i in range(10)]
        # Mock LLM to return [2, 0, 5]
        rag_service.llm_client.generate = AsyncMock(return_value="[2, 0, 5]")

        result = await rag_service._rerank_documents("query", docs, top_n=3)
        assert len(result) == 3
        assert result[0]["id"] == "2"

    async def test_rerank_fallback_on_parse_error(self, rag_service):
        """Should fallback to first top_n on parse failure."""
        docs = [{"text": f"doc{i}", "score": 0.9-i*0.1, "id": str(i)} for i in range(10)]
        rag_service.llm_client.generate = AsyncMock(return_value="invalid response")

        result = await rag_service._rerank_documents("query", docs, top_n=3)
        assert len(result) == 3
        assert result[0]["id"] == "0"  # First by vector score

    async def test_rerank_handles_fewer_than_top_n(self, rag_service):
        """Should return all docs if fewer than top_n."""
        docs = [{"text": "doc1", "score": 0.9, "id": "1"}]
        result = await rag_service._rerank_documents("query", docs, top_n=3)
        assert len(result) == 1

    async def test_query_with_rag_uses_reranking(self, rag_service):
        """Integration: full two-stage flow."""
        # Test that top_k=10 retrieves 10, rerank returns 3
        ...
```

## Success Criteria

- [ ] Rerank templates render correctly for vi/en
- [ ] _rerank_documents() returns top_n results
- [ ] Fallback works on parse failure
- [ ] query_with_rag() uses two-stage flow
- [ ] Latency increase <100ms (rerank step)
- [ ] Tests pass with >80% coverage

## Risk Assessment

| Risk | Probability | Mitigation |
|------|-------------|------------|
| LLM returns invalid indices | Medium | Robust parsing + fallback |
| Rerank latency too high | Low | Use small model, limit preview |
| Quality regression | Low | A/B test before full rollout |

## Metrics to Track

```python
# Add to metrics.py
rerank_duration_seconds = Histogram(
    "rag_rerank_duration_seconds",
    "Time spent on LLM reranking"
)
rerank_fallback_total = Counter(
    "rag_rerank_fallback_total",
    "Number of times rerank parsing failed"
)
```

## Security Considerations

1. **Preview length limit**: Prevents prompt injection via long docs
2. **Index validation**: Only accept valid indices
3. **No raw eval()**: Use regex parsing only
