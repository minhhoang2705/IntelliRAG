# IntelliRAG High-Level System Overview

**Status**: ✅ Active  
**Last Updated**: 2025-10-23  
**Version**: 2.0

---

## System Architecture Diagram

The complete system architecture is visualized in the diagram below:

**Location**: [`../../images/high_level_architecture_v2.jpg`](../../images/high_level_architecture_v2.jpg)

---

## Quick Architecture Summary

IntelliRAG is a production-ready RAG system with cloud-native architecture:

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Interface                          │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                   NGINX API Gateway                             │
│            (Auth, Rate Limiting, Routing)                       │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Orchestrator                         │
│              (Async Operations, Middleware)                     │
└───────┬─────────────────────┬───────────────────┬───────────────┘
        │                     │                   │
        ↓                     ↓                   ↓
┌──────────────┐    ┌──────────────────┐    ┌──────────────┐
│   GCS        │    │  LangGraph       │    │   Qdrant     │
│   Storage    │    │  Query Router    │    │  Vector DB   │
│              │    │  (Agent)         │    │  + Metadata  │
└──────────────┘    └──────────────────┘    └──────────────┘
        │                     │                   │
        └──────────┬──────────┴──────────┬────────┘
                   │                     │
                   ↓                     ↓
        ┌──────────────────┐    ┌──────────────────┐
        │  Document        │    │   vLLM           │
        │  Processing      │    │   Inference      │
        │  (Docling +      │    │   (KServe)       │
        │   LangChain)     │    │                  │
        └──────────────────┘    └──────────────────┘
                   │                     │
                   └──────────┬──────────┘
                              │
                              ↓
        ┌─────────────────────────────────────────┐
        │        Observability Stack              │
        │  Prometheus | Grafana | Jaeger | Loki  │
        │            Evidently (Drift)            │
        └─────────────────────────────────────────┘
```

---

## Component Overview

### 1. **User Interface Layer**
- Web UI for document upload and queries
- RESTful API clients

### 2. **API Gateway (NGINX)**
- Authentication and authorization
- Rate limiting and DDoS protection
- SSL/TLS termination
- Request routing and load balancing

### 3. **Application Layer (FastAPI)**
- Main orchestration logic
- Async request handling
- Background task processing
- Middleware for tracing, logging, metrics

### 4. **Storage Layer (GCS)**
- Raw document storage
- Fully managed cloud storage
- Cost-effective and scalable
- Native GCP integration

### 5. **Query Intelligence (LangGraph)**
- Query classification and analysis
- Conditional RAG routing:
  - Direct answers for simple queries
  - RAG retrieval for complex queries
- Multi-step reasoning workflows

### 6. **Vector Database (Qdrant)**
- Semantic search with embeddings
- **Metadata storage in payloads** (no separate database needed)
- Full-text search and filtering
- High-performance vector similarity search

### 7. **Document Processing Pipeline**
- **Docling**: Multi-format parsing (PDF, images, tables)
- **LangChain**: Document loading and chunking
- **Sentence Transformers**: Embedding generation

### 8. **LLM Inference (vLLM + KServe)**
- High-throughput inference (793 TPS)
- PagedAttention for memory efficiency
- OpenAI-compatible API
- Autoscaling and model versioning

### 9. **Observability & Monitoring**
- **Prometheus**: Metrics collection
- **Grafana**: Dashboards and alerting
- **Jaeger**: Distributed tracing
- **Loki**: Centralized logging
- **Evidently**: Data drift detection

---

## Data Flow Examples

### Example 1: Document Upload & Ingestion

```
User → NGINX → FastAPI
                  ↓
         Store in GCS (raw document)
                  ↓
         Processing Pipeline:
           1. Load from GCS
           2. Parse with Docling
           3. Chunk with LangChain
           4. Embed with Sentence Transformers
                  ↓
         Store in Qdrant (vectors + metadata)
                  ↓
         Track with DVC (versioning)
```

### Example 2: RAG Query Flow

```
User Query → NGINX → FastAPI
                       ↓
              LangGraph Agent
              (Classify Query)
                       ↓
        ┌──────────────┴──────────────┐
        │                             │
   Need RAG?                     Direct Answer?
        │                             │
        ↓                             ↓
  Qdrant Retrieval            vLLM Generation
  (vectors + context)                │
        │                             │
        ↓                             │
  Format Prompt                       │
        │                             │
        └──────────┬──────────────────┘
                   ↓
          vLLM Generation
                   ↓
           Response to User
```

---

## Technology Stack Summary

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **API Gateway** | NGINX | Routing, auth, rate limiting |
| **Framework** | FastAPI | Async API server |
| **Storage** | Google Cloud Storage | Raw document storage |
| **Vector DB** | Qdrant | Vector search + metadata |
| **Processing** | LangChain + Docling | Document parsing and chunking |
| **Embeddings** | Sentence Transformers | Vector embeddings |
| **LLM** | vLLM + KServe | High-throughput inference |
| **Orchestration** | LangGraph | Query routing and agents |
| **Monitoring** | Prometheus + Grafana | Metrics and dashboards |
| **Tracing** | Jaeger/Tempo | Request tracing |
| **Logging** | Loki/ELK | Centralized logs |
| **Drift Detection** | Evidently | Data quality monitoring |
| **ML Ops** | MLFlow + DVC | Model and data versioning |
| **Infrastructure** | Kubernetes (GKE) | Container orchestration |
| **Deployment** | Helm + Terraform | IaC and app deployment |

---

## Key Architectural Decisions

### Cloud-Native Design
- **Fully Managed Services**: GCS, GKE, no self-hosted databases
- **Auto-Scaling**: HPA for FastAPI, KServe for models
- **Cost Optimization**: Scale-to-zero support, efficient resource usage

### No Traditional Database
- **Qdrant Payloads**: All metadata stored co-located with vectors
- **Benefits**: Reduced latency, simplified architecture, easier deployment
- **Trade-off**: Less flexibility for complex relational queries (not needed for RAG)

### High-Performance Inference
- **vLLM**: 19x throughput improvement over Ollama
- **PagedAttention**: 95%+ GPU utilization
- **Continuous Batching**: Handle 128+ concurrent users

### Observability-First
- **Full Stack Monitoring**: Every layer instrumented
- **Tracing**: End-to-end request visibility
- **Data Quality**: Drift detection for model inputs

---

## Performance Characteristics

### Throughput
- **LLM Inference**: 793 tokens/second
- **Concurrent Users**: 128+
- **Document Processing**: ~100 pages/minute

### Latency
- **API Response**: <100ms (P99)
- **LLM Generation**: 80ms (P99)
- **Vector Search**: <10ms (P95)

### Scalability
- **Horizontal Scaling**: FastAPI pods autoscale
- **Vertical Scaling**: GPU node pools for KServe
- **Storage**: Unlimited (GCS)
- **Vector DB**: Qdrant clustering support

---

## Deployment Topology

### Development Environment
- Local GPU (RTX 4070Ti)
- vLLM Docker container
- Local Qdrant instance
- GCS for storage (dev bucket)

### Production Environment (GKE)
- **Compute**: GKE Autopilot cluster
- **GPU Nodes**: For KServe inference
- **Storage**: GCS (production bucket)
- **Vector DB**: Qdrant StatefulSet
- **Monitoring**: Full observability stack
- **Ingress**: NGINX Ingress Controller

---

## Security & Compliance

- **Authentication**: OAuth2/JWT via NGINX
- **Authorization**: Role-based access control
- **Data Encryption**: At rest (GCS) and in transit (TLS)
- **Network Security**: Private GKE cluster, VPC networking
- **Secrets Management**: Kubernetes Secrets + GCP Secret Manager
- **Input Validation**: Strict validation with Pydantic

---

## Related Documentation

- **Detailed Architecture**: [`./current-architecture.md`](./current-architecture.md)
- **Planning Docs**: [`../planning/`](../planning/)
- **Infrastructure**: [`../infrastructure/`](../infrastructure/)
- **Implementation Guides**: [`../guides/`](../guides/)

---

**For the complete visual diagram, see**: [`../../images/high_level_architecture_v2.jpg`](../../images/high_level_architecture_v2.jpg)

---

**Maintainer**: IntelliRAG Development Team  
**Status**: ✅ Production Architecture
