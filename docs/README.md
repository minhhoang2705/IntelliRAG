# IntelliRAG Documentation

Welcome to the IntelliRAG documentation! This guide helps you navigate all project documentation organized by category.

## 📖 Quick Navigation

| Category | Description | Location |
|----------|-------------|----------|
| **Architecture** | System design and architecture decisions | [`./architecture/`](./architecture/) |
| **Planning** | Implementation plans and feasibility studies | [`./planning/`](./planning/) |
| **Infrastructure** | MLOps, K8s, and observability setup | [`./infrastructure/`](./infrastructure/) |
| **Guides** | Developer how-to guides and references | [`./guides/`](./guides/) |
| **Summaries** | Phase summaries and implementation reports | [`./summaries/`](./summaries/) |
| **Reviews** | Code reviews and improvement recommendations | [`./reviews/`](./reviews/) |
| **Tasks** | Task tracking and implementation logs | [`./tasks/`](./tasks/) |
| **Product Requirements** | PRD and requirements specifications | [`./prd/`](./prd/) |
| **Archived** | Historical documentation and old plans | [`./archived/`](./archived/) |

---

## 🏗️ Architecture

**Current Architecture Documentation:**
- 📄 [Current Architecture Overview](./architecture/current-architecture.md) - Active GCS + Qdrant + LangChain architecture
- 📄 [High-Level System Overview](./architecture/high-level-overview.md) - Diagrams and system flow

**Deprecated Architectures:**
- 📄 [Phase 5 PostgreSQL + MinIO Architecture](./architecture/deprecated/phase5-postgresql-minio.md) - Original design (deprecated)

**Key Technologies:**
- **Storage**: Google Cloud Storage (GCS)
- **Vector DB**: Qdrant with payload metadata storage
- **Processing**: LangChain/LangGraph
- **Serving**: vLLM + KServe on GKE
- **Monitoring**: Prometheus + Loki + Jaeger
- **Drift Monitoring**: Evidently
- **Model & Data Versioning**: MLFlow + DVC

---

## 📋 Planning

**Active Implementation Plans:**
- 📄 [LangChain Refactoring Feasibility Analysis](./planning/langchain-refactoring-feasibility.md) - Cloud-native architecture strategy
- 📄 [GCS Integration Plan](./planning/gcs-integration-plan.md) - GCS client implementation and Qdrant payload schema

**Archived Plans:**
- 📁 [Archived Planning Documents](./planning/archived/) - Completed implementation plans

---

## 🚀 Infrastructure

**MLOps & Deployment:**
- 📄 [MLOps Stack](./infrastructure/mlops-stack.md) - CI/CD, MLFlow, DVC, deployment automation
- 📄 [Observability Stack](./infrastructure/observability-stack.md) - Prometheus, Grafana, Jaeger, Loki, Evidently

**Deployment Guides:**
- 📄 [Local KServe Setup Guide](./deployment/local-kserve-setup-guide.md) - **Complete guide for Minikube + KServe**
- 📄 [KServe Quick Reference](./deployment/kserve-quick-reference.md) - **Handy command reference**
- 📄 [Pre-Deployment Action Plan](./deployment/pre-deployment-action-plan.md) - GKE production deployment roadmap
- 📄 [Embedding Service Guide](./deployment/embedding-service-guide.md) - Standalone embedding service deployment

**Tech Stack:**
- **CI/CD**: GitHub Actions → Docker → GKE (Helm)
- **Model Management**: MLFlow + DVC
- **Model Serving**: KServe (local with Minikube or GKE)
- **Monitoring**: Prometheus + Grafana
- **Tracing**: Jaeger/Tempo
- **Logging**: Loki/ELK
- **Data Drift**: Evidently

---

## 📚 Guides

**Developer Guides:**
- 📄 [Integration Testing Guide](./guides/integration-testing-guide.md) - Testing best practices and setup
- 📄 [Query Router Guide](./guides/query-router-guide.md) - LangGraph-based query routing and classification
- 📄 [Embedding Model Switching Guide](./guides/embedding-model-switching-guide.md) - **How to switch between embedding models safely**

**Best Practices:**
- TDD methodology (>80% coverage required)
- Async operations with FastAPI
- vLLM for high-throughput inference
- GCS for cloud storage
- Qdrant payloads for metadata
- Automatic dimension migration for embedding models

---

## 🚧 Phase 2: Agentic RAG & Query Routing

**Implementation Status: ✅ COMPLETE**

**Phase 2 Documentation:**
- 📄 [Query Router FINAL STATUS](./phase-2/query-router-FINAL-STATUS.md) - ✅ Complete implementation (26/26 tests passing)

**Achievements:**
- ✅ **QueryClassifier**: LLM-based query classification (4 types: RAG, DIRECT, CLARIFICATION, MULTI_HOP)
- ✅ **LangGraph State Machine**: Conditional routing with error handling
- ✅ **E2E Testing**: 26 tests covering all flows, errors, and edge cases
- ✅ **100% Coverage**: Complete test coverage with 2.28:1 test-to-code ratio

**Implementation Files:**
```
app/services/query_router/
├── __init__.py
├── classifier.py      # QueryClassifier service
├── prompts.py         # Few-shot classification prompts
└── graph.py           # LangGraph state machine

tests/unit/
├── test_query_classifier.py  # 5 tests
└── test_query_graph.py        # 21 tests (including E2E)
```

**Archived Phase 2 Documentation:**
- 📁 [Phase 2 Implementation History](./archived/phase-2/) - Historical implementation progress and completion summaries

---

## 📊 Summaries

**Recent Implementation Summaries:**
- 📄 [Phase 4 RAG Pipeline](./summaries/phase4-rag-pipeline.md) - RAG pipeline implementation summary
- 📄 [Observability Fixes Summary](./observability-fixes-summary.md) - Observability instrumentation fixes (2025-10-30)

**Archived Summaries:**
- 📁 [2025 Summaries Archive](./archived/summaries-2025/) - Historical implementation summaries from 2025
- 📁 [Older Archived Summaries](./summaries/archived/) - Historical phase summaries and older test reports

---

## 🔍 Reviews

**Code Reviews & Improvements:**
- 📄 [Code Review - Phase 5](./reviews/code-review-phase5.md) - Phase 5 code review findings
- 📄 [Phase 5 Improvements](./reviews/phase5-improvements.md) - Critical improvements and recommendations

---

## ✅ Tasks

**Task Tracking:**
- 📁 [Active Tasks](./tasks/active/) - Currently in-progress tasks
- 📁 [Completed Tasks](./tasks/completed/) - Finished task summaries
  - Task 8: Structured Logging
  - Task 9: Remove Duplicate Chunking
  - **Task 10: Auto-Dimension Migration** (2025-11-05) - Automatic embedding model switching
  - Remaining Tasks (2025-10-09)
- 📁 [Security Fixes](./tasks/security-fixes/) - Security-related task logs
  - CSV Bomb Fix

---

## 📋 Product Requirements

**Requirements Documentation:**
- 📄 [Product Requirements Document (PRD)](./prd/PRD.md) - Core product requirements and specifications

---

## 🗄️ Archived

**Historical Documentation:**
- 📁 [2025 Plans Archive](./archived/plans-2025/) - Superseded implementation plans from 2025
- 📁 [Phase 2 Archive](./archived/phase-2/) - Phase 2 implementation history and progress logs
- 📁 [2025 Summaries Archive](./archived/summaries-2025/) - Historical implementation summaries from 2025
- 📁 [Old Plans](./archived/old-plans/) - Older superseded implementation plans
  - Vector Database Implementation Plan (2025-10-14)
  - Phase 3 Integration Testing Plan (2025-10-17)

---

## 🎯 Core Project Information

**Project:** Production-Ready RAG System with MLOps Pipeline  
**Methodology:** Test-Driven Development (TDD) - **STRICTLY ENFORCED**  
**Coverage Target:** >80% (CI/CD enforced)  
**Budget:** $300/month (GKE + Local GPU hybrid)

### Key Features
- Multi-modal document processing (PDF, DOCX, CSV, TXT, images)
- Local GPU inference (RTX 4070Ti) + KServe deployment
- Full observability stack (Prometheus, Grafana, Jaeger, Loki)
- Cloud-native GCS + Qdrant architecture
- Complete CI/CD pipeline with automated testing

### Tech Stack Overview
- **Framework**: FastAPI + Pydantic
- **Storage**: Google Cloud Storage (GCS)
- **Vector DB**: Qdrant (with payload metadata)
- **Processing**: LangChain/LangGraph + Docling
- **Inference**: vLLM (19x throughput vs Ollama)
- **Serving**: KServe on GKE
- **Embeddings**: BAAI BGE-M3 (1024-dimensional, multilingual, hybrid retrieval)
- **MLOps**: MLFlow + DVC
- **Observability**: Prometheus + Grafana + Jaeger + Loki + Evidently

---

## 📖 Additional Resources

- **Main Project Guidelines**: [`../CLAUDE.md`](../CLAUDE.md) - Comprehensive coding guidelines and project overview
- **Architecture Diagram**: [`../images/high_level_architecture_v2.jpg`](../images/high_level_architecture_v2.jpg)
- **Agent Guidelines**: [`../AGENTS.md`](../AGENTS.md) - Multi-agent workflow documentation

---

## 🗺️ Document Organization Principles

1. **By Type**: Documents organized by their primary purpose (architecture, planning, guides, etc.)
2. **Active vs Archived**: Current/active docs separated from historical/deprecated ones
3. **Consistent Naming**: kebab-case naming, descriptive titles, no redundant prefixes
4. **Scalability**: Each category can grow independently
5. **Discoverability**: This README provides a clear navigation map

---

## 📝 Contributing to Documentation

When adding new documentation:

1. **Choose the Right Category**: Select the most appropriate directory
2. **Use Descriptive Names**: Use kebab-case (e.g., `feature-implementation-plan.md`)
3. **Update This README**: Add links to new important documents
4. **Archive Old Docs**: Move superseded documents to `archived/` or category-specific `archived/` subdirectories
5. **Follow TDD**: Document architecture decisions before implementation

---

**Last Updated**: 2025-11-06  
**Maintained By**: IntelliRAG Development Team
