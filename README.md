# IntelliRAG

Production-ready Retrieval-Augmented Generation (RAG) system with full MLOps pipeline, cloud-native Kubernetes deployment, and comprehensive observability.

---

## 🎯 Project Overview

**Status**: ~70% Complete (Development → Pre-Production)  
**Methodology**: Test-Driven Development (TDD)  
**Test Coverage**: >80% (enforced)  
**Last Updated**: 2025-11-06

IntelliRAG is an enterprise-grade RAG system featuring:

- ✅ Multi-format document processing (PDF, DOCX, CSV, TXT, Markdown, URLs)
- ✅ BGE-M3 embeddings (1024-dim, multilingual, hybrid retrieval)
- ✅ Qdrant vector database with payload metadata storage
- ✅ LangGraph-based intelligent query routing
- ✅ vLLM inference optimization (19x throughput vs Ollama)
- ✅ Comprehensive observability (19+ metrics, structured logging, distributed tracing)
- ⚠️ Kubernetes deployment configurations (ready for validation)
- ❌ CI/CD pipeline, Terraform IaC, MLFlow/DVC (planned)

---

## 📚 Documentation Hub

### Quick Start

- **[Project Status](./docs/PROJECT-STATUS.md)** - 📊 Complete project evaluation and remaining tasks
- **[Documentation Index](./docs/README.md)** - 🗺️ Navigate all documentation
- **[Current Architecture](./docs/architecture/current-architecture.md)** - 🏗️ System design and architecture (v2.0)

### For Developers

- **[CLAUDE.md](./CLAUDE.md)** - 💻 Development guidelines and coding standards
- **[AGENTS.md](./AGENTS.md)** - 🤖 Multi-agent workflow documentation
- **[Component Completeness](./docs/evaluation/component-completeness.md)** - Detailed component status
- **[Test Coverage Report](./docs/testing/test-coverage-report.md)** - Test metrics and coverage analysis

### For DevOps

- **[Infrastructure Readiness](./docs/evaluation/infrastructure-readiness.md)** - K8s deployment assessment
- **[Production Deployment Checklist](./docs/deployment/production-deployment-checklist.md)** - Pre-deployment validation
- **[Observability Deployment Guide](./docs/deployment/observability/observability-deployment-guide.md)** - Monitoring stack setup
- **[Remaining Tasks (Prioritized)](./docs/evaluation/remaining-tasks-prioritized.md)** - P0/P1/P2/P3 task breakdown

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- uv package manager
- Docker (for local GPU inference)
- NVIDIA GPU (RTX 4070Ti or similar)
- GCP account (for production deployment)

### Local Development Setup

```bash
# Clone repository
git clone <repository-url>
cd IntelliRAG

# Install dependencies
uv sync

# Start local services (Qdrant, etc.)
docker-compose up -d

# Run tests
pytest --cov=app --cov-report=term-missing

# Start FastAPI application
uvicorn app.main:app --reload
```

### Run with Local vLLM (GPU Inference)

```bash
# Start vLLM container
cd deploy/vllm-llm
docker-compose up -d

# Start embedding service
cd ../embedding-service
docker-compose up -d
```

---

## 🛠️ Tech Stack

**Core Application:**
- FastAPI (async API framework)
- Pydantic (data validation)
- LangChain/LangGraph (document processing, agentic workflows)

**Storage & Data:**
- Google Cloud Storage (raw document storage)
- Qdrant (vector database with payload metadata)

**ML & Inference:**
- BGE-M3 (1024-dim embeddings, multilingual)
- vLLM (high-throughput LLM serving)
- Qwen3-0.6B(primary text model)

**Infrastructure:**
- Kubernetes (GKE Autopilot planned)
- KServe (model serving)
- Helm/Helmfile (deployment management)

**Observability:**
- Prometheus (metrics collection - 19+ custom metrics)
- Grafana (5 production dashboards)
- Jaeger (distributed tracing)
- Loki (centralized logging)

---

## 📊 Current Status

### ✅ Completed Components (100%)

- **Document Processing**: 8 loaders (PDF, DOCX, CSV, TXT, Markdown, URL, GCS) + semantic chunking
- **Embedding Services**: BGE-M3 with auto-dimension migration
- **Vector Database**: Qdrant with hybrid search and payload storage
- **Query Router**: LangGraph-based classification (100% test coverage)
- **RAG Pipeline**: Retrieval → generation flow
- **LLM Client**: vLLM OpenAI-compatible client
- **Observability Instrumentation**: Metrics, logs, traces in code

### ⚠️ In Progress

- **Kubernetes Deployment**: Configurations ready, validation needed
- **Observability Stack**: Infrastructure configured, integration testing needed
- **Model Serving**: KServe manifests ready

### ❌ Planned (P1-P3)

- **CI/CD Pipeline**: GitHub Actions workflow
- **Terraform IaC**: GKE cluster provisioning
- **NGINX Ingress**: API gateway, rate limiting, auth
- **MLOps Tooling**: MLFlow, DVC, Evidently

**See [PROJECT-STATUS.md](./docs/PROJECT-STATUS.md) for complete breakdown.**

---

## 🧪 Testing

- **Test Files**: 62
- **Test Coverage**: >80% (88.5% average)
- **Test-to-Code Ratio**: 2.58:1
- **Methodology**: TDD (Test-Driven Development)

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=term-missing --cov-report=html

# Run specific test
pytest tests/unit/test_query_classifier.py -v

# Run integration tests only
pytest tests/integration/ -v
```

---

## 📈 Performance Benchmarks

### vLLM Inference (RTX 4070Ti 12GB)

- **Throughput**: 793 TPS (19.3x vs Ollama)
- **P99 Latency**: 80ms (8.4x faster than Ollama)
- **GPU Utilization**: 95%+
- **Concurrent Users**: 128+

### Embedding Performance

- **BGE-M3**: <10ms per chunk
- **Batch Processing**: Up to 32 documents
- **Dimension**: 1024 (multilingual, hybrid retrieval)

### System Targets

- **Query Latency (P95)**: <500ms
- **Query Latency (P99)**: <1000ms
- **Error Rate**: <0.1%
- **Uptime SLA**: 99.9%

---

## 🤝 Contributing

We follow strict TDD methodology:

1. ✅ Write failing test first
2. ✅ Implement minimal code to pass
3. ✅ Refactor while keeping tests green
4. ✅ Maintain >80% coverage
5. ❌ Never skip tests or commit failing code

See [CLAUDE.md](./CLAUDE.md) for complete development guidelines.

---

## 📖 Key Documentation

### Architecture & Design
- [Current Architecture v2.0](./docs/architecture/current-architecture.md)
- [High-Level Overview](./docs/architecture/high-level-overview.md)
- [Component Completeness Analysis](./docs/evaluation/component-completeness.md)

### Deployment & Operations
- [Infrastructure Readiness Assessment](./docs/evaluation/infrastructure-readiness.md)
- [Production Deployment Checklist](./docs/deployment/production-deployment-checklist.md)
- [Local KServe Setup Guide](./docs/deployment/local-kserve-setup-guide.md)
- [Embedding Service Guide](./docs/deployment/embedding-service-guide.md)

### Development Guides
- [Integration Testing Guide](./docs/guides/integration-testing-guide.md)
- [Query Router Guide](./docs/guides/query-router-guide.md)
- [Embedding Model Switching Guide](./docs/guides/embedding-model-switching-guide.md)

---

## 🗺️ Roadmap

### Critical Path to Production (29 days)

**P0 Tasks (11 days)**: MVP Deployment
- FastAPI + Qdrant K8s manifests
- Observability stack validation
- Integration testing on K8s
- Environment configuration & secrets management

**P1 Tasks (18 days)**: Production Quality
- CI/CD pipeline (GitHub Actions)
- NGINX Ingress with auth & rate limiting
- Terraform IaC for GKE
- Performance testing & optimization

**P2 Tasks (26 days)**: Optimization & Scaling
- MLFlow + DVC integration
- Multi-GPU vLLM configuration
- Evidently data drift monitoring
- Blue-green deployment strategy

**See [Remaining Tasks (Prioritized)](./docs/evaluation/remaining-tasks-prioritized.md) for complete task breakdown.**

---

## 📞 Support & Contact

- **Issues**: [GitHub Issues](./issues)
- **Documentation**: [`./docs/`](./docs/)
- **Architecture Diagrams**: [`./images/`](./images/)

---

## 📄 License

[Add license information]

---

**Project maintained by IntelliRAG Development Team**  
**Last Updated**: 2025-11-06

