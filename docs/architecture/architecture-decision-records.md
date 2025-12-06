# Architecture Decision Records (ADR)

**Document**: Architecture Decision Records for IntelliRAG
**Created**: 2025-11-25
**Status**: Active
**Version**: 1.0

---

## Table of Contents

1. [ADR-001: Hybrid Cloud + Local GPU Deployment Architecture](#adr-001-hybrid-cloud--local-gpu-deployment-architecture)
2. [ADR-002: vLLM for Model Serving](#adr-002-vllm-for-model-serving)
3. [ADR-003: LangGraph for Query Routing](#adr-003-langgraph-for-query-routing)
4. [ADR-004: BGE-M3 Embedding Model Selection](#adr-004-bge-m3-embedding-model-selection)
5. [ADR-005: Qdrant Vector Database](#adr-005-qdrant-vector-database)
6. [ADR-006: KServe for Model Serving Platform](#adr-006-kserve-for-model-serving-platform)
7. [ADR-007: CloudFlare Tunnel for Secure Connectivity](#adr-007-cloudflare-tunnel-for-secure-connectivity)
8. [ADR-008: Load Testing Strategy](#adr-008-load-testing-strategy)
9. [ADR-009: Network Policies for Security](#adr-009-network-policies-for-security)
10. [ADR-010: Observability Stack Selection](#adr-010-observability-stack-selection)
11. [ADR-011: Test-Driven Development (TDD) Methodology](#adr-011-test-driven-development-tdd-methodology)
12. [ADR-012: GKE Standard vs Autopilot](#adr-012-gke-standard-vs-autopilot)
13. [ADR-013: Semantic Chunking Strategy](#adr-013-semantic-chunking-strategy)
14. [ADR-014: Horizontal Pod Autoscaling (HPA) Configuration](#adr-014-horizontal-pod-autoscaling-hpa-configuration)
15. [ADR-015: Pod Security Standards Enforcement](#adr-015-pod-security-standards-enforcement)

---

## ADR-001: Hybrid Cloud + Local GPU Deployment Architecture

### Status
**Accepted** - 2025-11-16

### Context
IntelliRAG requires GPU resources for ML model inference (LLM and embeddings). We needed to decide between:
1. Full cloud deployment with GKE GPU nodes
2. Fully local deployment
3. Hybrid architecture with cloud for stateless services and local GPU for inference

### Decision
Implement a **hybrid deployment architecture** combining:
- **GKE Standard (Cloud)**: FastAPI application, Qdrant vector DB, observability stack
- **Local GPU Server (RTX 4070Ti)**: vLLM and embedding model serving via KServe

### Rationale

**Cost Optimization**:
- GKE GPU nodes (T4/A100) cost $1,500-2,500/month
- Local RTX 4070Ti already available, electricity cost ~$25/month
- **Monthly savings: ~$1,500-2,400**

**Performance**:
- Local GPU provides dedicated resources with no multi-tenant overhead
- RTX 4070Ti 12GB VRAM sufficient for Qwen3-0.6B and BGE-M3
- Measured throughput: 793 TPS (19x vs Ollama baseline)

**Budget Compliance**:
- Total infrastructure cost: $85-300/month
- Stays within $300/month budget constraint

### Consequences
**Positive**:
- 80-90% cost reduction compared to full cloud GPU
- Dedicated GPU resources with consistent performance
- Full control over model serving configuration

**Negative**:
- Increased operational complexity (two clusters to manage)
- Network latency added via CloudFlare Tunnel (+10-30ms)
- Single point of failure for GPU server (mitigated by redundancy planning)

### Alternatives Considered
| Option | Monthly Cost | Pros | Cons |
|--------|-------------|------|------|
| GKE with T4 GPU | ~$1,500 | Fully managed | Over budget |
| GKE with A100 | ~$2,500 | High performance | Way over budget |
| Fully local | ~$25 | Cheapest | No cloud scalability |
| **Hybrid (chosen)** | ~$150 | Balanced | Operational complexity |

---

## ADR-002: vLLM for Model Serving

### Status
**Accepted** - 2025-11-01

### Context
We needed a high-performance inference engine for LLM serving. Options evaluated:
1. Ollama
2. vLLM
3. Text Generation Inference (TGI)
4. llama.cpp

### Decision
Use **vLLM** as the primary inference engine for LLM serving.

### Rationale

**Performance Benchmarks** (RTX 4070Ti):
| Metric | vLLM | Ollama | Improvement |
|--------|------|--------|-------------|
| Throughput | 793 TPS | 41 TPS | **19.3x** |
| P99 Latency | 80ms | 673ms | **8.4x faster** |
| Max Concurrent | 128+ | 22 | **5.8x** |
| GPU Utilization | 95% | 60% | **35% improvement** |

**Key Technical Advantages**:
1. **PagedAttention**: Virtual memory management for KV cache reduces fragmentation by 60%
2. **Continuous Batching**: Dynamic request merging maximizes throughput
3. **Prefix Caching**: Reuses computed prefixes for common RAG patterns
4. **OpenAI-Compatible API**: Drop-in replacement, minimal code changes

**Production Readiness**:
- Native integration with KServe
- Built-in metrics endpoint for Prometheus
- Supports model quantization (FP8/INT8) for memory optimization

### Consequences
**Positive**:
- 19x throughput improvement enables higher concurrent users
- Lower latency improves user experience
- Better GPU utilization maximizes hardware investment

**Negative**:
- More complex configuration than Ollama
- Requires GPU with sufficient VRAM (minimum 8GB recommended)

### Alternatives Considered
- **Ollama**: Simpler but significantly lower performance
- **TGI**: Comparable performance but less community support
- **llama.cpp**: Good for CPU inference, not optimized for our GPU use case

---

## ADR-003: LangGraph for Query Routing

### Status
**Accepted** - 2025-10-25

### Context
Not all user queries require RAG retrieval. Simple factual questions, greetings, and general knowledge queries can be answered directly by the LLM without vector database lookup.

### Decision
Implement a **LangGraph-based query router** that classifies queries and conditionally routes them to:
- **RAG Pipeline**: Domain-specific queries requiring document context
- **Direct LLM**: Simple factual questions, greetings, general knowledge

### Rationale

**Cost Optimization**:
- Skip unnecessary embedding generation (~30-50ms saved)
- Skip vector database queries (~10-30ms saved)
- Reduce Qdrant load by 30-50% (estimated based on query distribution)

**Latency Reduction**:
- Direct queries: 80-120ms (LLM only)
- RAG queries: 150-200ms (embedding + retrieval + LLM)
- **40-50% latency reduction** for simple queries

**Resource Efficiency**:
- Lower GPU utilization on embedding service
- Reduced Qdrant query volume
- Better resource allocation for complex RAG queries

**Why LangGraph**:
1. **State Machine Model**: Clean representation of routing logic as a graph
2. **Extensibility**: Easy to add new routing decisions (multi-hop, clarification)
3. **Observability**: Built-in tracing and state inspection
4. **LangChain Ecosystem**: Integrates with existing LangChain components

### Classification Logic
```
Query Analysis
     │
     ├─> Factual/Greeting/Math → Direct LLM Answer
     │   Examples: "What is 2+2?", "Hello", "Capital of France"
     │
     └─> Domain-specific/Document-based → RAG Pipeline
         Examples: "Summarize Q4 report", "Find technical specs"
```

### Consequences
**Positive**:
- Improved response times for simple queries
- Reduced infrastructure costs
- Better user experience with faster responses
- Scalable pattern for future routing logic

**Negative**:
- Classification overhead (~50-100ms for LLM-based classification)
- Potential misclassification requiring fallback logic
- Additional complexity in the query pipeline

### Metrics to Track
- Classification accuracy (target: >95%)
- Latency savings per query type
- RAG precision (queries correctly routed to RAG)

---

## ADR-004: BGE-M3 Embedding Model Selection

### Status
**Accepted** - 2025-11-01

### Context
RAG systems require high-quality embeddings for semantic search. We evaluated:
1. all-MiniLM-L6-v2 (384 dimensions)
2. BGE-M3 (1024 dimensions)
3. OpenAI ada-002 (1536 dimensions)

### Decision
Use **BAAI/BGE-M3** as the primary embedding model.

### Rationale

**Technical Superiority**:
| Feature | BGE-M3 | all-MiniLM-L6-v2 | ada-002 |
|---------|--------|------------------|---------|
| Dimensions | 1024 | 384 | 1536 |
| Multilingual | Yes (100+ languages) | Limited | Yes |
| Hybrid Retrieval | Dense + Sparse | Dense only | Dense only |
| Max Tokens | 8192 | 512 | 8191 |

**Performance Benchmarks** (MTEB):
- BGE-M3 MTEB average: 64.2
- all-MiniLM-L6-v2: 56.3
- **14% improvement** in retrieval quality

**Hybrid Retrieval**:
BGE-M3 supports both dense and sparse embeddings, enabling:
- Dense vectors for semantic similarity
- Sparse vectors for keyword matching
- Combined scoring for better retrieval accuracy

**Long Context Support**:
- 8192 token context window vs 512 for MiniLM
- Better handling of long documents without chunking artifacts

**Cost Consideration**:
- Self-hosted: No per-query API costs
- OpenAI ada-002: ~$0.0001/1K tokens (adds up at scale)
- **At 100K queries/month, saves ~$500/month vs OpenAI**

### Consequences
**Positive**:
- Higher retrieval accuracy
- No external API dependencies or costs
- Multilingual support for future expansion
- Hybrid retrieval improves relevance

**Negative**:
- Larger model size (~1.1GB)
- Higher VRAM requirements (~2.2GB)
- Slightly longer embedding time vs smaller models

---

## ADR-005: Qdrant Vector Database

### Status
**Accepted** - 2025-10-15

### Context
Vector databases evaluated:
1. Qdrant
2. Pinecone
3. Weaviate
4. Milvus
5. ChromaDB

### Decision
Use **Qdrant** as the vector database for storing and retrieving embeddings.

### Rationale

**Technical Features**:
1. **Payload Storage**: Store metadata alongside vectors (eliminates need for separate database)
2. **Filtering**: Rich filtering on payload fields during vector search
3. **HNSW Index**: High-performance approximate nearest neighbor search
4. **Async Client**: Native async support for Python (FastAPI compatibility)

**Cost Efficiency**:
- Open source, self-hosted: $0 licensing cost
- Pinecone: ~$70/month for comparable capacity
- **Saves ~$840/year** vs managed alternatives

**Performance**:
- Query latency: <30ms for top-5 retrieval
- Supports 100M+ vectors per collection
- Memory-efficient with mmap storage option

**Operational Simplicity**:
- Single binary deployment
- Built-in web UI for debugging
- Kubernetes-native with Helm charts
- Snapshot/backup support for disaster recovery

**API Design**:
- gRPC and REST APIs
- OpenAPI specification
- Well-documented Python client

### Consequences
**Positive**:
- No licensing costs
- Full control over data and infrastructure
- Rich feature set for RAG use cases
- Active community and development

**Negative**:
- Self-managed (no SLA from vendor)
- Requires backup/recovery planning
- Horizontal scaling requires cluster mode (more complex)

### Alternatives Considered
- **Pinecone**: Managed but expensive, vendor lock-in
- **Weaviate**: Good but heavier resource footprint
- **Milvus**: Powerful but complex operations
- **ChromaDB**: Too simple for production needs

---

## ADR-006: KServe for Model Serving Platform

### Status
**Accepted** - 2025-11-10

### Context
We needed a Kubernetes-native model serving platform that supports:
- vLLM runtime
- Autoscaling (including scale-to-zero)
- Model versioning
- Canary deployments

### Decision
Use **KServe v0.14.1** as the model serving platform on the local GPU server (minikube).

### Rationale

**Native vLLM Integration**:
- First-class vLLM runtime support
- OpenAI-compatible API out of the box
- Automatic model loading and health checks

**Kubernetes-Native**:
- InferenceService CRD for declarative model deployment
- Integrates with existing Kubernetes tooling (kubectl, Helm)
- Service mesh compatible (Istio)

**Autoscaling Capabilities**:
- Scale-to-zero for cost optimization during idle periods
- KPA (Knative Pod Autoscaler) for request-based scaling
- Configurable concurrency limits

**Production Features**:
- Model versioning and rollback
- Canary deployments for safe updates
- Request logging and tracing
- Prometheus metrics export

**Standardization**:
- KServe Predict v2 protocol (industry standard)
- Works with MLflow, TensorFlow Serving, Triton
- Future-proof for model migration

### Consequences
**Positive**:
- Standardized model serving across different frameworks
- Built-in autoscaling reduces operational burden
- Easy A/B testing and canary deployments

**Negative**:
- Additional complexity vs direct vLLM deployment
- Requires cert-manager and Istio/Kourier dependencies
- Learning curve for KServe-specific configurations

---

## ADR-007: CloudFlare Tunnel for Secure Connectivity

### Status
**Accepted** - 2025-11-16

### Context
The hybrid architecture requires secure connectivity between GKE (cloud) and the local GPU server. Options:
1. VPN (WireGuard, OpenVPN)
2. CloudFlare Tunnel
3. Direct public IP exposure
4. GCP Interconnect

### Decision
Use **CloudFlare Tunnel** to expose local KServe endpoints to GKE.

### Rationale

**Security**:
- No inbound firewall rules needed on local server
- No public IP exposure
- End-to-end TLS encryption
- CloudFlare Access for authentication (optional)

**Simplicity**:
- Single `cloudflared` binary
- Systemd service for reliability
- DNS management via CloudFlare dashboard

**Cost**:
- **Free tier** (up to 50 users)
- No hardware/software VPN appliances needed
- Saves ~$100-500/month vs dedicated VPN solutions

**Performance**:
- CloudFlare's global edge network (low latency)
- +10-30ms overhead (acceptable for our latency budget)
- 1Gbps+ throughput capacity

**Operational Benefits**:
- 99.99% uptime SLA from CloudFlare
- DDoS protection included
- Built-in rate limiting at edge

### Consequences
**Positive**:
- Zero infrastructure to manage
- Excellent security posture
- Free tier sufficient for our needs
- Easy to set up and maintain

**Negative**:
- Dependency on CloudFlare (vendor risk)
- +10-30ms latency overhead
- Debugging requires CloudFlare dashboard access

### Alternatives Considered
- **VPN**: More control but higher operational burden
- **Public IP**: Security risk, requires firewall management
- **GCP Interconnect**: Expensive (~$1,000/month)

---

## ADR-008: Load Testing Strategy

### Status
**Accepted** - 2025-11-21

### Context
Before production deployment, we need to:
1. Understand system capacity limits
2. Configure autoscaling thresholds
3. Identify bottlenecks
4. Plan for peak traffic

### Decision
Implement comprehensive load testing using **hey** (simple benchmarks) and **locust** (complex scenarios).

### Rationale

**Why Load Testing is Essential**:

1. **Capacity Planning**:
   - Determine maximum concurrent users before degradation
   - Calculate required replicas for target load
   - Justify infrastructure costs with data

2. **Bottleneck Identification**:
   - Identify which component breaks first (vLLM, embedding, Qdrant)
   - Focus optimization efforts on actual bottlenecks
   - Prevent production incidents from unknown limits

3. **HPA Configuration**:
   - Data-driven CPU/memory thresholds (not arbitrary 50%)
   - Example: If CPU hits 70% at 100 users, scale at 70%
   - Prevents over-provisioning (cost) or under-provisioning (failures)

4. **SLA Validation**:
   - Verify P95 latency <500ms under expected load
   - Confirm error rate <1% at target capacity
   - Document actual vs promised performance

**Tool Selection**:
| Tool | Use Case | Strengths |
|------|----------|-----------|
| **hey** | Quick benchmarks | Simple, fast, single endpoint |
| **locust** | Complex scenarios | Python scripting, realistic user simulation |

**Test Types**:
1. **Baseline**: Normal load (50 users) to establish metrics
2. **Stress**: High load (100 users) to measure degradation
3. **Breaking Point**: Incrementally increase until failure
4. **Endurance**: Sustained load over time (memory leaks, resource exhaustion)

### Consequences
**Positive**:
- Data-driven infrastructure decisions
- Early identification of issues
- Confidence in production capacity
- Documentation of system limits

**Negative**:
- Requires dedicated testing time (1-2 days)
- May reveal unexpected issues requiring fixes
- Needs production-like environment for accurate results

---

## ADR-009: Network Policies for Security

### Status
**Accepted** - 2025-11-21

### Context
Kubernetes clusters allow unrestricted pod-to-pod communication by default. This violates the principle of least privilege and increases attack surface.

### Decision
Implement **default-deny network policies** with explicit allow rules for authorized traffic.

### Rationale

**Security Principles**:

1. **Defense in Depth**:
   - Network policies add a layer beyond authentication
   - Limits blast radius of compromised pods
   - Complies with security best practices (CIS Kubernetes Benchmark)

2. **Principle of Least Privilege**:
   - Pods only communicate with explicitly allowed services
   - Prevents lateral movement in case of breach
   - Documents authorized communication paths

**Implemented Policies**:

```
Default: DENY ALL ingress and egress

Allowed Traffic:
├── Ingress NGINX → FastAPI (port 8000)
├── FastAPI → Qdrant (port 6333)
├── FastAPI → External HTTPS (CloudFlare Tunnel)
├── FastAPI → DNS (kube-dns)
├── Prometheus → FastAPI (metrics scraping)
└── FastAPI → Jaeger (tracing)
```

**Compliance**:
- Required for SOC 2 compliance
- Recommended by CIS Kubernetes Benchmark
- Standard practice for production environments

### Consequences
**Positive**:
- Reduced attack surface
- Clear documentation of allowed traffic
- Easier security audits
- Compliance with security standards

**Negative**:
- Additional configuration complexity
- Potential for misconfiguration blocking legitimate traffic
- Debugging requires understanding of network policies

---

## ADR-010: Observability Stack Selection

### Status
**Accepted** - 2025-10-22

### Context
Production systems require comprehensive observability for:
- Performance monitoring
- Issue diagnosis
- Capacity planning
- Alerting

### Decision
Implement a complete observability stack:
- **Prometheus**: Metrics collection
- **Grafana**: Visualization and dashboards
- **Jaeger/Tempo**: Distributed tracing
- **Loki**: Centralized logging
- **Evidently**: ML data drift monitoring (planned)

### Rationale

**Why This Stack**:

| Component | Purpose | Alternative | Why Chosen |
|-----------|---------|-------------|------------|
| Prometheus | Metrics | Datadog | Free, industry standard, native K8s |
| Grafana | Dashboards | Kibana | Supports all data sources, alerting |
| Jaeger | Tracing | Zipkin | Better UI, wider adoption |
| Loki | Logging | ELK Stack | Lighter weight, Grafana integration |
| Evidently | ML Drift | Custom | Purpose-built for ML monitoring |

**Key Metrics Tracked** (19+ custom metrics):
- `http_requests_total`: Request counts by endpoint/status
- `http_request_duration_seconds`: Latency distributions (P50/P95/P99)
- `rag_query_duration_seconds`: RAG pipeline stage latencies
- `query_classification_total`: Query router decisions
- `llm_token_count`: Token usage by model
- `gpu_utilization_percent`: GPU resource usage
- `embedding_cache_hits_total`: Cache efficiency

**Alerting Rules**:
- High error rate (>5% over 5 minutes)
- High latency (P99 >2s)
- GPU utilization anomalies (<30% or >95%)
- Model serving down
- Vector DB high error rate

**Cost**:
- All components open source: $0 licensing
- Storage costs: ~$25/month (GCS for traces/logs)
- Total: **~$25/month** vs $500-2000/month for managed solutions

### Consequences
**Positive**:
- Full visibility into system behavior
- Proactive issue detection via alerts
- Data-driven optimization decisions
- No vendor lock-in

**Negative**:
- Self-managed (maintenance overhead)
- Requires expertise in each tool
- Storage costs for retention

---

## ADR-011: Test-Driven Development (TDD) Methodology

### Status
**Accepted** - 2025-10-01

### Context
IntelliRAG is a complex system with multiple integrated components. Code quality and reliability are critical for production deployment.

### Decision
Enforce **strict TDD methodology** with >80% code coverage requirement.

### Rationale

**Why TDD is Mandatory**:

1. **Reliability**:
   - Tests verify behavior before implementation
   - Catches bugs early in development cycle
   - Reduces production incidents

2. **Maintainability**:
   - Tests serve as documentation
   - Safe refactoring with test coverage
   - Clear contracts between components

3. **Development Velocity**:
   - Faster debugging with failing tests
   - Confidence in code changes
   - Reduced regression testing time

**The TDD Cycle**:
```
RED (Write failing test)
  → GREEN (Implement minimal code)
    → REFACTOR (Improve while tests pass)
```

**Coverage Requirements**:
- Unit tests: >80% coverage
- Integration tests: Key flows covered
- E2E tests: Critical user journeys
- RAGAS evaluation: RAG quality metrics

**Enforced via CI/CD**:
- Pre-commit hooks run tests
- PR blocked if coverage drops
- No merge without passing tests

### Consequences
**Positive**:
- High code quality and reliability
- Comprehensive test documentation
- Confidence in deployments
- Reduced debugging time

**Negative**:
- Slower initial development (30-50% more time)
- Learning curve for TDD discipline
- Some tests may become brittle without maintenance

---

## ADR-012: GKE Standard vs Autopilot

### Status
**Accepted** - 2025-11-16

### Context
Google Kubernetes Engine offers two modes:
1. **GKE Standard**: Full control over nodes
2. **GKE Autopilot**: Fully managed, per-pod pricing

### Decision
Use **GKE Standard** for the cloud portion of the hybrid architecture.

### Rationale

**Cost Analysis**:
| Scenario | Standard | Autopilot |
|----------|----------|-----------|
| 1 node (baseline) | ~$98/month | ~$150/month |
| 3 nodes (peak) | ~$295/month | ~$450/month |
| Savings | - | 35-50% cheaper with Standard |

**Control Requirements**:
- Custom node types (e2-standard-4 for our workload)
- Specific machine configurations
- Predictable pricing model

**Deployment Speed**:
- Standard: Instant pod scheduling on existing nodes
- Autopilot: 30-60s provisioning delay for new pods

**Workload Characteristics**:
- Small, predictable workload (1-3 nodes)
- Mixed services (FastAPI, Qdrant, observability)
- Not highly variable traffic patterns

### Consequences
**Positive**:
- Lower cost for our workload profile
- Faster deployments
- More control over infrastructure

**Negative**:
- Node management responsibility
- Manual node pool configuration
- Potential for over/under-provisioning

---

## ADR-013: Semantic Chunking Strategy

### Status
**Accepted** - 2025-10-20

### Context
Document chunking significantly impacts RAG retrieval quality. Strategies considered:
1. Fixed-size chunks
2. Sentence-based chunks
3. Semantic chunking

### Decision
Use **semantic chunking** via LangChain's RecursiveCharacterTextSplitter with:
- Chunk size: 512 tokens
- Overlap: 20% (102 tokens)
- Table-aware chunking for structured data

### Rationale

**Semantic Boundaries**:
- Preserves logical document structure
- Keeps related information together
- Improves retrieval relevance

**Overlap for Context**:
- 20% overlap maintains context across chunk boundaries
- Prevents information loss at split points
- Improves answer generation with complete context

**Table-Aware Processing**:
- Tables chunked as units (not split mid-row)
- Preserves relationships in tabular data
- Better handling of structured documents

**Performance Balance**:
- 512 tokens fits model context windows
- Small enough for precise retrieval
- Large enough for meaningful context

### Consequences
**Positive**:
- Higher retrieval accuracy
- Better context preservation
- Improved answer quality

**Negative**:
- More complex chunking logic
- Slightly higher processing time
- Overlap increases storage (~20%)

---

## ADR-014: Horizontal Pod Autoscaling (HPA) Configuration

### Status
**Accepted** - 2025-11-21

### Context
Application pods need to scale based on traffic. HPA configuration requires:
- CPU/memory thresholds
- Min/max replica counts
- Scaling behavior

### Decision
Configure HPA with **data-driven thresholds** from load testing:
- CPU target: 70% utilization
- Memory target: 75% utilization
- Min replicas: 3 (availability)
- Max replicas: 15 (cost constraint)

### Rationale

**Why Data-Driven Thresholds**:
- Day 2 load testing showed CPU hits 70% at ~100 concurrent users
- Arbitrary 50% threshold would over-provision
- 70% provides scaling headroom while maximizing efficiency

**Why Min 3 Replicas**:
- Survives single pod failure
- Distributed across availability zones
- Maintains response times during pod updates

**Why Max 15 Replicas**:
- Calculated: 500 target users / 50 users per pod + 50% buffer
- Cost constraint: 15 pods × ~$50/month = ~$750/month max
- Prevents runaway scaling costs

**Scaling Behavior**:
```yaml
behavior:
  scaleDown:
    stabilizationWindowSeconds: 300  # 5 min cooldown
  scaleUp:
    stabilizationWindowSeconds: 60   # Quick scale-up
```

### Consequences
**Positive**:
- Efficient resource utilization
- Cost-controlled scaling
- Responsive to traffic changes

**Negative**:
- 5-minute scale-down delay (conservative)
- May hit max during unexpected spikes
- Requires periodic re-validation of thresholds

---

## ADR-015: Pod Security Standards Enforcement

### Status
**Accepted** - 2025-11-21

### Context
Kubernetes pods can run with various privilege levels. Security best practices require restricting container capabilities.

### Decision
Enforce **Restricted** Pod Security Standard:
- Non-root user (UID 1000)
- Read-only root filesystem
- All capabilities dropped
- seccomp profile: RuntimeDefault

### Rationale

**Security Posture**:
- Prevents privilege escalation attacks
- Limits impact of container breakout
- Complies with CIS Kubernetes Benchmark
- Required for many compliance frameworks

**Specific Controls**:
| Control | Value | Purpose |
|---------|-------|---------|
| runAsNonRoot | true | Prevent root access |
| runAsUser | 1000 | Consistent unprivileged user |
| readOnlyRootFilesystem | true | Prevent filesystem modifications |
| allowPrivilegeEscalation | false | Block privilege gains |
| capabilities.drop | ALL | Remove all Linux capabilities |

**Implementation**:
- Dockerfile creates `intellirag` user (UID 1000)
- EmptyDir volumes for writable paths (/tmp, /app/.cache, /app/logs)
- Namespace labels enforce policy at admission

### Consequences
**Positive**:
- Strong security posture
- Compliance with security standards
- Limited blast radius from compromises

**Negative**:
- Requires application changes (non-root user)
- More complex Dockerfile
- EmptyDir volumes for writable paths

---

## Document History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-25 | IntelliRAG Team | Initial ADR document |

---

## References

- [CLAUDE.md - Project Guidelines](/CLAUDE.md)
- [Hybrid Deployment Architecture](/docs/architecture/hybrid-deployment-architecture.md)
- [Phase 3 Implementation Plan](/docs/plans/phase-3-implementation-plan.md)
- [Observability Stack Documentation](/docs/infrastructure/observability-stack.md)
- [Query Router Guide](/docs/guides/query-router-guide.md)
