# Phase 4 MLOps Architecture Decisions

**Date**: 2025-11-27
**Status**: Approved
**Decision Maker**: User + Engineering Analysis

---

## Decision Summary

| Decision Point | Choice | Rationale |
|----------------|--------|-----------|
| **Component Priority** | MLFlow → Dashboards → Evidently → Webhooks | Foundation-first approach |
| **RAGAS Evaluation** | ❌ Removed | Simplified scope, can add later |
| **MLFlow Database** | In-cluster PostgreSQL | Cost savings, learning value |
| **MLFlow Location** | GKE (Cloud) | Production-ready, team access |
| **Budget Impact** | +$17/month → $131 total | Well under $300 limit ✅ |
| **Data Migration** | N/A (fresh start) | No existing data to migrate |

---

## Detailed Decisions

### 1. Component Implementation Priority

**Decision**: Sequential implementation in this order:
1. MLFlow (foundation for tracking)
2. Dashboards (visualization)
3. Evidently (drift monitoring)
4. Webhooks (automation)

**Removed**: RAGAS evaluation

**Rationale**:
- MLFlow is foundational - everything else builds on it
- Dashboards provide immediate visibility
- Evidently enables long-term monitoring
- Webhooks are advanced automation (optional)
- RAGAS removed to simplify Phase 4 scope

**Impact**:
- Reduced complexity by ~30%
- Faster implementation (3-4 days vs 5-7 days)
- Can add RAGAS in Phase 5 or later if needed

---

### 2. RAGAS Evaluation - REMOVED

**Decision**: Remove RAGAS from Phase 4

**Rationale**:
- User preference for simpler, focused implementation
- Can be added as future enhancement
- Reduces dependencies and complexity
- Phase 4 still provides core MLOps capabilities

**What we're keeping**:
- Model tracking (MLFlow)
- Model registry (MLFlow)
- Drift monitoring (Evidently)
- Performance dashboards (Grafana)

**What we're removing**:
- Automated RAG quality evaluation
- Faithfulness/relevance metrics
- RAGAS CronJob
- Test dataset preparation

**Future addition**: Can implement RAGAS in Phase 5 or as standalone enhancement

---

### 3. MLFlow Database Backend

**Decision**: In-cluster PostgreSQL via Bitnami Helm chart

**Alternatives Considered**:
- ❌ Cloud SQL PostgreSQL (~$50-100/month)
- ❌ SQLite (not production-ready)
- ✅ In-cluster PostgreSQL (~$5/month)

**Rationale**:
- **Cost**: $5/month vs $50-100/month (90% savings)
- **Learning**: Hands-on Kubernetes StatefulSet experience
- **Sufficient**: Adequate for current scale
- **Upgradeable**: Can migrate to Cloud SQL later if needed

**Configuration**:
```yaml
Database: PostgreSQL 14
Storage: 20Gi PersistentVolume
Resources: 500m CPU, 512Mi RAM
Backup: Manual (can automate later)
High Availability: Single replica (sufficient for dev/demo)
```

**Trade-offs**:
- ✅ Lower cost
- ✅ Full control
- ✅ Learning experience
- ⚠️ Requires manual backups
- ⚠️ Not HA by default

**Migration Path**: If traffic grows → migrate to Cloud SQL with:
```bash
pg_dump | psql (Cloud SQL connection string)
```

---

### 4. MLFlow Deployment Location

**Decision**: Deploy MLFlow on GKE (Cloud)

**Alternatives Considered**:
- ❌ Local deployment (~$0/month but limited access)
- ❌ Hybrid (complex, unnecessary)
- ✅ GKE deployment (~$17/month)

**Rationale**:
- **Accessibility**: Available from anywhere via HTTPS
- **Integration**: Co-located with FastAPI, Qdrant, Grafana
- **Production-Ready**: Industry-standard architecture
- **Portfolio Value**: Demonstrates real MLOps skills
- **Team Collaboration**: Shared access for team/advisors
- **Budget**: $17/month is acceptable ($131 < $300 budget)

**Configuration**:
```yaml
URL: https://mlflow.blockchainradar.xyz
Replicas: 1 (sufficient for current load)
Resources: 500m CPU, 1Gi RAM
Ingress: NGINX with TLS (cert-manager)
Backend: PostgreSQL (in-cluster)
Artifacts: GCS (gs://intellirag-mlflow-artifacts)
```

**Benefits**:
- ✅ Centralized experiment tracking
- ✅ Same cluster as other services (fast internal networking)
- ✅ Prometheus metrics integration
- ✅ Loki log aggregation
- ✅ Professional setup for portfolio

---

### 5. Budget Analysis

**Current Monthly Cost**: $114
**Phase 4 Additions**: $17
**New Total**: $131/month

**Breakdown**:
| Component | Cost |
|-----------|------|
| **Existing (Phase 0-3)** | |
| GKE cluster (1 node, e2-standard-4) | $109 |
| Qdrant storage (20GB) | $4 |
| GCS raw documents (~5GB) | $0.13 |
| Network egress | $1 |
| **Phase 4 Additions** | |
| PostgreSQL storage (20GB) | $4 |
| MLFlow pod (500m CPU, 1GB RAM) | $10 |
| GCS MLFlow artifacts (~10GB) | $0.26 |
| Drift monitoring CronJob | $2 |
| **Total** | **$130.39** |

**Budget Compliance**: ✅ **$131 < $300** (43% utilization)

**Cost Optimization**:
- Using in-cluster PostgreSQL saves $45-95/month vs Cloud SQL
- Shared LoadBalancer (NGINX Ingress) saves $10/month per service
- Total savings: ~$55-105/month

---

### 6. Data Migration Strategy

**Decision**: Fresh start (no migration needed)

**Context**:
- Qdrant collections are empty (fresh GKE deployment)
- No existing MLFlow data
- No historical experiments to migrate

**Impact**:
- ✅ No migration complexity
- ✅ Clean slate for Phase 4
- ✅ Auto-migration code already in place for future dimension changes

**Embedding Dimension Migration**:
- Old model: BAAI/bge-m3 (1024-dim) - never deployed to production
- New model: google/embeddinggemma-300m (768-dim) - current
- Auto-migration: Will create `default_768` if needed
- Strategy: Parallel collections (documented in embedding-dimension-migration-plan.md)

---

## Architecture Overview

```
┌────────────────────────────────────────────────────────────┐
│                    GKE CLUSTER (Cloud)                     │
│                                                            │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │   FastAPI    │  │   Qdrant     │  │   Prometheus   │  │
│  │   (Phase 1)  │  │  (Phase 0)   │  │   + Grafana    │  │
│  │              │  │              │  │   (Phase 3)    │  │
│  └──────────────┘  └──────────────┘  └────────────────┘  │
│                                                            │
│  ┌──────────────────────────────────────────────────────┐ │
│  │            MLFlow Stack (Phase 4)                    │ │
│  │  ┌──────────────┐  ┌──────────────┐                 │ │
│  │  │   MLFlow     │──│  PostgreSQL  │                 │ │
│  │  │   Server     │  │   (Backend)  │                 │ │
│  │  └──────┬───────┘  └──────────────┘                 │ │
│  │         │                                            │ │
│  │         ↓                                            │ │
│  │  GCS: intellirag-mlflow-artifacts                   │ │
│  │  (Model artifacts, experiments, drift reports)      │ │
│  │                                                      │ │
│  │  CronJob: Evidently Drift Monitoring (Daily 4 AM)   │ │
│  └──────────────────────────────────────────────────────┘ │
│                                                            │
└────────────────────────────────────────────────────────────┘

External Access (via NGINX Ingress + CloudFlare DNS):
• https://api.blockchainradar.xyz (FastAPI)
• https://grafana.blockchainradar.xyz (Grafana)
• https://mlflow.blockchainradar.xyz (MLFlow) ← NEW

Local GPU Services (via CloudFlare Tunnel):
• https://llm.blockchainradar.xyz (vLLM)
• https://embed.blockchainradar.xyz (Embedding)
```

---

## Implementation Strategy

### Phase 4 Timeline

**Total Duration**: 3-4 days

**Day 1** (2 hours):
- Task 1: PostgreSQL deployment (30 min)
- Task 2: GCS bucket setup (15 min)
- Task 3: MLFlow deployment (1 hour)
- Task 3 cont: DNS + TLS setup (15 min)

**Day 2** (2 hours):
- Task 4: Register models (30 min)
- Task 5: Evidently implementation (1.5 hours)

**Day 3** (2 hours):
- Task 6: Grafana dashboards (1 hour)
- Task 7: Webhooks (optional) (1 hour)

**Day 4** (1 hour):
- Task 8: Documentation (30 min)
- Final testing & verification (30 min)

---

## Success Metrics

### Technical Metrics
- ✅ MLFlow UI accessible (<200ms load time)
- ✅ 2 models registered (LLM + Embedding)
- ✅ Drift monitoring running daily
- ✅ Grafana dashboard shows MLOps metrics
- ✅ Total cost < $135/month

### Business Metrics
- ✅ Centralized model tracking
- ✅ Automated drift detection
- ✅ Visible model performance
- ✅ Production-ready MLOps foundation

### Learning Objectives
- ✅ Kubernetes StatefulSets (PostgreSQL)
- ✅ MLFlow deployment & configuration
- ✅ Evidently integration
- ✅ GCS lifecycle policies
- ✅ CronJobs for scheduled tasks

---

## Risk Mitigation

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| PostgreSQL data loss | Low | High | Regular manual backups, can upgrade to Cloud SQL |
| MLFlow downtime | Low | Medium | GKE auto-restart, can scale to 2 replicas |
| Drift monitoring fails | Medium | Low | Non-critical, can debug via CronJob logs |
| Budget overrun | Low | Medium | Monthly monitoring, auto-shutdown non-essential pods |
| TLS cert issues | Low | Low | cert-manager auto-renewal, fallback to HTTP if needed |

---

## Future Enhancements

**Phase 5 (Optional)**:
- Add RAGAS evaluation
- Implement model retraining pipelines
- Add A/B testing framework
- Upgrade to Cloud SQL (if needed)
- Add CI/CD for model deployment

**Production Hardening**:
- PostgreSQL High Availability (2+ replicas)
- Automated backup to GCS
- Monitoring alerts for all components
- Load testing MLFlow endpoints

---

## Approval & Sign-off

**Decision Date**: 2025-11-27
**Approved By**: User
**Implementation Start**: TBD
**Expected Completion**: 3-4 days from start

**Documentation**:
- ✅ Implementation plan: `docs/plans/phase-4-mlops-simplified.md`
- ✅ TODO list: `docs/todos/phase-4-mlops-todos.md`
- ✅ Architecture decisions: `docs/architecture/phase-4-decisions.md` (this file)

**Status**: Ready to Begin Implementation
