# Embedding Dimension Migration Plan

**Date**: 2025-11-27
**Status**: Planning
**Priority**: Medium

---

## Overview

The IntelliRAG system is transitioning from **BAAI/bge-m3** (1024-dimensional) embeddings to **google/embeddinggemma-300m** (768-dimensional) embeddings. This migration requires careful handling of existing vector data in Qdrant to ensure both data preservation and system continuity.

---

## Current State

### Embedding Models

| Aspect | Old Model | New Model |
|--------|-----------|-----------|
| **Name** | BAAI/bge-m3 | google/embeddinggemma-300m |
| **Dimensions** | 1024 | 768 |
| **Size** | ~2.2GB | ~300MB |
| **Framework** | sentence-transformers | Google Gemma |
| **Performance** | Higher accuracy, slower | Faster inference, good accuracy |
| **Deployment** | KServe (historical) | KServe (current) |
| **Endpoint** | N/A (discontinued) | https://embed.blockchainradar.xyz |

### Qdrant Collections

Current collections in GKE Qdrant:
- **Status**: Empty (fresh deployment)
- **Expected on first ingestion**: Auto-creation of `default` collection with 768-dim

Historical deployments may have:
- `default` (1024-dim) - Old bge-m3 embeddings
- Needs migration strategy if re-deploying with existing data

---

## Migration Strategy

### Option 1: Parallel Collections (Recommended)

**Approach**: Keep both embedding dimensions operational in separate collections.

#### Advantages
- ✅ **Zero downtime**: No service interruption
- ✅ **Data preservation**: All historical data retained
- ✅ **Gradual migration**: Re-ingest documents at your own pace
- ✅ **Rollback capability**: Can revert if issues arise
- ✅ **A/B testing**: Compare query performance between models

#### Implementation

```python
# Qdrant Collections Structure
{
    "default": {
        "dimension": 1024,
        "status": "read-only",
        "vectors": 15000,  # Example
        "description": "Historical bge-m3 embeddings (legacy)"
    },
    "default_768": {
        "dimension": 768,
        "status": "active",
        "vectors": 0,  # Growing as docs are re-ingested
        "description": "Current embeddinggemma-300m embeddings"
    }
}
```

#### Migration Steps

1. **Phase 1: Auto-Migration (Built-in)**
   ```bash
   # Already implemented in app/services/vectordb.py:162-268
   # When first document is ingested with 768-dim embeddings:

   Result:
   - Detects dimension mismatch (1024 vs 768)
   - Creates new collection: default_768
   - Logs warning about migration
   - Preserves old collection: default (1024)
   ```

2. **Phase 2: Configure Application**
   ```bash
   # Update Helm values or .env
   QDRANT_COLLECTION_NAME=default_768  # Use new collection
   ```

3. **Phase 3: Re-ingest Priority Documents**
   ```bash
   # Identify critical documents in old collection
   curl http://localhost:9000/api/v1/collections/default/points \
     | jq '.result.points[] | select(.payload.importance == "high")'

   # Re-upload and ingest these documents
   # They will automatically go to default_768
   ```

4. **Phase 4: Monitor Query Performance**
   ```python
   # Compare retrieval quality between collections
   # Use RAGAS metrics (Phase 4 MLOps)

   Metrics to track:
   - Answer relevance
   - Context precision
   - Response time
   - User satisfaction
   ```

5. **Phase 5: Sunset Old Collection (After 90 days)**
   ```bash
   # Once all critical docs re-ingested and validated
   # Delete old collection
   curl -X DELETE http://localhost:6333/collections/default

   # Rename new collection to default
   # (Requires Qdrant collection aliasing or manual rename)
   ```

---

### Option 2: Full Re-ingestion (Clean Slate)

**Approach**: Delete old data, re-ingest everything with new embeddings.

#### Advantages
- ✅ **Simplicity**: Single collection, no naming complexity
- ✅ **Consistency**: All vectors use same model
- ✅ **Storage efficiency**: No duplicate data
- ✅ **Fresh start**: Clean up any data quality issues

#### Disadvantages
- ❌ **Downtime required**: Service interruption during re-ingestion
- ❌ **Data loss risk**: If source documents unavailable
- ❌ **No rollback**: Cannot revert to old embeddings
- ❌ **Resource intensive**: Re-compute all embeddings

#### Implementation

1. **Backup Metadata**
   ```bash
   # Export document metadata from old collection
   curl http://localhost:6333/collections/default/points/scroll \
     -H "Content-Type: application/json" \
     -d '{"limit": 10000, "with_payload": true, "with_vector": false}' \
     > backup_metadata.json
   ```

2. **Delete Old Collection**
   ```bash
   curl -X DELETE http://localhost:6333/collections/default
   ```

3. **Re-ingest from Source**
   ```bash
   # Upload all documents from GCS
   for file in $(gsutil ls gs://intellirag-raw-documents/**); do
       curl -X POST http://localhost:9000/api/v1/upload \
         -H "Authorization: Bearer $API_KEY" \
         -F "file=@${file}"
   done
   ```

4. **Verify Completeness**
   ```python
   # Compare document counts
   old_count = len(backup_metadata["points"])
   new_count = qdrant_client.count("default").count

   assert new_count >= old_count, "Missing documents!"
   ```

---

### Option 3: Hybrid Query Approach (Advanced)

**Approach**: Query both collections, merge results.

#### Implementation

```python
# app/services/rag_pipeline.py
async def retrieve_hybrid(self, query_embedding: List[float], top_k: int = 5):
    """Query both 1024-dim and 768-dim collections."""

    # Query old collection (1024-dim)
    # Requires converting 768-dim query to 1024-dim (padding/interpolation)
    results_old = await self.query_old_collection(query_embedding, top_k)

    # Query new collection (768-dim)
    results_new = await self.vectordb.search(
        collection_name="default_768",
        query_vector=query_embedding,
        limit=top_k
    )

    # Merge and re-rank results
    combined = self.merge_results(results_old, results_new)
    return combined[:top_k]
```

#### Challenges
- Complex implementation
- Requires embedding transformation logic
- Higher latency (2x queries)
- Difficult to maintain

---

## Auto-Migration Code Reference

The system already has built-in auto-migration protection:

**File**: `app/services/vectordb.py` (lines 162-268)

```python
async def ensure_collection_with_dimension(
    self,
    collection_name: str,
    vector_size: int,
    distance: str = "cosine",
    recreate_if_mismatch: bool = False,
    auto_migrate: bool = False
):
    """
    Ensure collection exists with correct dimension.

    Handles dimension mismatches intelligently:
    1. Collection doesn't exist → create it
    2. Collection exists with same dimension → accept it
    3. Dimension mismatch + auto_migrate=True → create suffixed collection
    4. Dimension mismatch + recreate_if_mismatch=True → delete and recreate
    """
```

**Usage in Orchestrator** (app/services/orchestrator.py:261-266):

```python
result = await self.vectordb_service.ensure_collection_with_dimension(
    collection_name="default",
    vector_size=768,  # New dimension from embedding service
    distance="cosine",
    auto_migrate=True  # ✅ Enables auto-migration
)
```

---

## Recommended Approach

**Use Option 1: Parallel Collections**

### Rationale

1. **Zero Risk**: Existing data preserved
2. **Production-Grade**: No downtime required
3. **Flexibility**: Can A/B test model performance
4. **Cost-Effective**: Only re-ingest critical documents initially
5. **Built-in Support**: Auto-migration code already implemented

### Timeline

| Phase | Duration | Tasks |
|-------|----------|-------|
| **Week 1** | Setup | Enable auto-migration, configure collection naming |
| **Week 2-3** | Re-ingestion | Re-ingest top 20% critical documents |
| **Week 4** | Validation | Compare query quality with RAGAS metrics |
| **Week 5-8** | Gradual Migration | Re-ingest remaining documents |
| **Week 12** | Cleanup | Archive/delete old collection |

---

## Monitoring & Validation

### Key Metrics

```yaml
Collection Health:
  - Vector count: Track growth of default_768
  - Storage usage: Monitor Qdrant disk space
  - Query latency: P50, P95, P99 response times

Embedding Quality:
  - RAGAS faithfulness: >0.8
  - RAGAS relevance: >0.85
  - Context precision: >0.9

System Performance:
  - Embedding service latency: <500ms
  - End-to-end query time: <2s
  - GPU utilization: 70-90%
```

### Alerts

```yaml
Critical:
  - Collection creation fails
  - Dimension mismatch not handled
  - Embedding service unavailable

Warning:
  - Query latency >3s
  - RAGAS metrics drop >10%
  - Storage >80% full
```

---

## Rollback Plan

If issues arise with 768-dim embeddings:

1. **Immediate Action**
   ```bash
   # Switch back to old collection
   export QDRANT_COLLECTION_NAME=default
   kubectl set env deployment/intellirag-app -n app QDRANT_COLLECTION_NAME=default
   ```

2. **Revert Embedding Service**
   ```bash
   # Redeploy bge-m3 model to KServe
   # Update CloudFlare tunnel to point to old service
   # Update .env and Helm values
   ```

3. **Investigate Root Cause**
   - Check logs for embedding service errors
   - Review RAGAS metrics comparison
   - Analyze user feedback
   - Test with sample queries

---

## Cost Analysis

### Storage Costs

| Scenario | Collection | Vectors | Size | Monthly Cost (GCS) |
|----------|-----------|---------|------|-------------------|
| Parallel (1 month) | default (1024) | 15,000 | ~600 MB | $0.016 |
|  | default_768 (768) | 5,000 | ~150 MB | $0.004 |
| **Total** |  |  | ~750 MB | **$0.020** |

### Compute Costs

| Activity | Frequency | Cost per Run | Monthly Total |
|----------|-----------|--------------|---------------|
| Re-embedding documents | One-time | GPU time (~2 hours) | ~$0.50 |
| Dual collection queries | Temporary | Negligible | ~$0.00 |
| **Total Migration Cost** |  |  | **~$0.50** |

**Conclusion**: Migration is cost-effective (<$1 total).

---

## Next Steps

1. ✅ **Current Status**: Auto-migration code is active
2. ⏳ **Action Required**: None (migration happens automatically on first ingestion)
3. 📊 **Monitoring**: Set up Grafana dashboards for collection metrics (Phase 4)
4. 📝 **Documentation**: Update API docs to reflect new embedding model
5. 🧪 **Testing**: Run RAGAS evaluation on new embeddings (Phase 4)

---

**Status**: Ready for Phase 4 MLOps implementation
**Last Updated**: 2025-11-27
**Owner**: Engineering Team
