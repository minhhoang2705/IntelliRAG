# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository. For each user query, ask questions about the user's requirements to stimulate the user's critical and analytical thinking, don't provide an answer at all. Always breakdown large task and ask clarifying questions when needed. Think step by step and show reasoning for complex problems, use specific examples. When giving feedback, explain thought process and highlight issues and opportunities

## Project Overview

IntelliRAG is a production-ready RAG (Retrieval-Augmented Generation) system with full MLOps pipeline, integrating local GPU inference with cloud-native Kubernetes deployment.

**Project**: Production-Ready RAG System with MLOps Pipeline  
**Methodology**: Test-Driven Development (TDD) - **STRICTLY ENFORCED**  
**Timeline**: 4-6 weeks  
**Coverage Target**: >80% (CI/CD enforced)  
**Budget**: $300/month (GKE + Local GPU hybrid) 

## 🎯 Core Mission

Build an enterprise RAG system that:
- Processes multi-modal documents (PDF, DOCX, CSV, TXT, images)
- Serves LLM inference via local GPU (RTX 4070Ti) + KServe
- Deploys to GKE with full observability stack
- Maintains production-grade quality standards
- Implements complete CI/CD with automated testing (>80% coverage)
- Provides real-time monitoring, tracing, and logging

## High-level Architecture

The high-level architecture can be seen at this path `./images/high_level_architecture_v2.jpg`

---

## 🛠️ Tech Stack & Documentation

### **Package Management**
- Python 3.11, 3.12
- Package Manager: `uv`

### **Core Framework**
- **FastAPI** (`/tiangolo/fastapi` - Trust: 9.9)
  - Async path operations with `async def`
  - Dependency injection via `Depends()`
  - Background tasks with `BackgroundTasks`
  - Router-level dependencies with `APIRouter`
  - Middleware for tracing, logging, metrics
  
- **Pydantic** (`/pydantic/pydantic` - Trust: 9.6)
  - `BaseModel` for data validation
  - `@field_validator` for custom validation
  - `Field()` for strict mode and constraints
  - Nested model validation

### **API Gateway & Load Balancing**
- **NGINX** 
  - API Gateway with authentication
  - Rate limiting
  - Request routing
  - SSL/TLS termination
  - Kubernetes Ingress Controller

### **Storage & Data Management**
- **Google Cloud Storage (GCS)**
  - Raw document storage
  - Fully managed cloud storage
  - Native GCP integration
  - Async operations via `gcloud-aio-storage`
  - Cost-effective ($0.026/GB/month)

### **Vector Database & Embeddings**
- **Qdrant** (`/qdrant/qdrant-client` - Trust: 9.8)
  - Async operations supported
  - Collection management
  - Vector search with filters
  - **Payload metadata storage** (replaces traditional database)
  - Full-text search and filtering on payloads
  - Co-located vectors + metadata for performance

- **Sentence Transformers** (`/ukplab/sentence-transformers` - Trust: 7.8)
  - Pre-trained embedding models
  - Batch encoding support
  - `all-MiniLM-L6-v2` (384 dim, recommended)

### **Document Processing**
- **Docling**: Multi-format parsing (PDF, images)
- **LangChain/LangGraph**: Document chunking and text splitting
- **Chunking Strategy**:
  - Semantic chunking for text
  - Table-aware chunking for structured data
  - Image extraction and description

### **LLM & Model Serving**
- **vLLM**: High-throughput inference engine
  - PagedAttention for 95%+ GPU memory efficiency
  - Continuous batching for 19x throughput vs Ollama
  - OpenAI-compatible API
  - Native multimodal support
- **KServe**: Model serving on Kubernetes
  - Native vLLM integration
  - Autoscaling (scale to zero)
  - Model versioning
  - Canary deployments
- **Models**:
  - Qwen2.5-7B-Instruct (primary text model)
  - MiniCPM-V-2 (multimodal vision model)
- **Deployment**:
  - Development: vLLM Docker container
  - Production: KServe InferenceService with vLLM runtime
- **httpx**: Async HTTP client with OpenAI SDK

### **Agentic RAG & Query Routing**
- **LangGraph** (`/langchain-ai/langgraph`)
  - Query analysis and classification
  - Conditional RAG routing (retrieval vs direct answer)
  - Multi-step reasoning workflows
  - State management for complex queries
  - Graph-based agent orchestration

### **MLOps & Versioning**
- **MLFlow**: Model registry and versioning
  - Model tracking
  - Experiment management
  - Model packaging for deployment
- **DVC**: Data version control
  - Dataset versioning
  - Pipeline tracking
  - Remote storage (S3/GCS)

### **Testing**
- **Pytest** (`/pytest-dev/pytest` - Trust: 9.5)
  - `pytest-asyncio` for async tests
  - `pytest-cov` for coverage (>80% enforced)
  - `pytest-mock` for mocking
  - Fixtures with `@pytest.fixture`
- **RAGAS**: RAG evaluation metrics
  - Context relevance
  - Answer faithfulness
  - Answer relevance

### **Infrastructure**
- **Kubernetes**: GKE Autopilot
- **Helm**: Application deployment
  - Helmfile for multi-chart management
- **Terraform**: IaC for GKE provisioning
- **HPA**: Horizontal Pod Autoscaler for FastAPI services

### **Inference Performance**
- **vLLM Optimizations**:
  - **PagedAttention**: Virtual memory management for KV cache
  - **Continuous Batching**: Dynamic request merging
  - **Prefix Caching**: Reuse computed prefixes for common queries
  - **Tensor Parallelism**: Multi-GPU support (future scaling)
- **Performance Metrics** (RTX 4070Ti 12GB):
  - Throughput: 793 TPS (19.3x vs Ollama's 41 TPS)
  - P99 Latency: 80ms (8.4x faster vs Ollama's 673ms)
  - Concurrent Users: 128+ (5.8x vs Ollama's 22)
  - GPU Utilization: 95%+ (35% improvement vs Ollama)
  - Memory Efficiency: PagedAttention reduces fragmentation by 60%
- **Deployment Configurations**:
  - **Development**: vLLM Docker container with GPU passthrough
    - Model cache mounted from host: `~/.cache/huggingface`
    - OpenAI-compatible API on `localhost:8000`
    - Hot reload for rapid testing
  - **Production**: KServe InferenceService with vLLM runtime
    - GKE Autopilot with GPU node pools
    - Horizontal autoscaling with scale-to-zero
    - Prometheus metrics export enabled
    - Model versioning via S3/GCS storage

### **Observability Stack**
- **Prometheus**: Metrics collection
  - Service metrics
  - Custom application metrics
  - Resource utilization
- **Grafana**: Visualization dashboards
  - System monitoring
  - Application metrics
  - Alerting
- **Jaeger/Tempo**: Distributed tracing
  - Request flow tracking
  - Performance bottleneck identification
- **Loki/ELK**: Centralized logging
  - Application logs
  - Error tracking
  - Audit trails
- **Evidently**: Data drift monitoring
  - Input distribution shifts
  - Model performance degradation
  - Feature drift detection

---

## 🔴🟢♻️ TDD Workflow (MANDATORY)

### **The Sacred TDD Cycle**

```
RED (Fail) → GREEN (Pass) → REFACTOR (Clean)
     ↓            ↓              ↓
  Write Test   Implement     Improve Code
  & See FAIL   Minimal       Keep Tests
               Solution      Green
```

### **Before ANY Code Implementation**

```bash
# 1. Create test file FIRST
touch tests/unit/test_<component>.py

# 2. Write test that WILL FAIL
vim tests/unit/test_<component>.py

# 3. Run test - MUST see failure
pytest tests/unit/test_<component>.py::<TestClass>::<test_method> -v
# Expected: FAILED ❌

# 4. Implement minimal code
vim app/services/<component>.py

# 5. Run test - MUST pass
pytest tests/unit/test_<component>.py::<TestClass>::<test_method> -v
# Expected: PASSED ✅

# 6. Refactor 
# Improve code while keeping tests green

# 7. Check coverage
pytest tests/unit/test_<component>.py --cov=app.services.<component> --cov-report=term-missing
# Target: >80%
```

### **Critical TDD Rules**

**ALWAYS:**
- ✅ Write failing test first, DO NOT write implementation code yet.
- ✅ Run test and verify it FAILS
- ✅ Write minimal code to pass. DO NOT modify tests.
- ✅ Improve code quality while keeping all tests pass.
- ✅ Commit only when all tests pass
- ✅ Maintain >80% coverage

**NEVER:**
- ❌ Skip failing tests (`@pytest.mark.skip`)
- ❌ Comment out assertions to pass tests
- ❌ Implement without test
- ❌ Ignore test failures
- ❌ Commit code without tests
- ❌ Commit with failing tests
- ❌ Commit secrets (`.env`, API keys)
- ❌ Ignore coverage drops
- ❌ Add AI attributions in code

---

## 📁 Project Structure

```
rag-system/
├── app/
│   ├── __init__.py
│   ├── main.py                    # FastAPI orchestrator
│   ├── config.py                  # Configuration management
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py          # POST /api/v1/upload
│   │   │   ├── ingest.py          # POST /api/v1/ingest (trigger pipeline)
│   │   │   └── query.py           # POST /api/v1/query (RAG endpoint)
│   │   └── middleware/
│   │       ├── __init__.py
│   │       ├── tracing.py         # Jaeger integration
│   │       ├── logging.py         # Structured logging
│   │       └── metrics.py         # Prometheus metrics
│   ├── services/
│   │   ├── __init__.py
│   │   ├── orchestrator.py        # Main orchestration logic
│   │   ├── query_router/
│   │   │   ├── __init__.py
│   │   │   ├── langgraph_agent.py # LangGraph query classifier
│   │   │   ├── prompts.py         # Classification prompts
│   │   │   └── graph.py           # State graph definition
│   │   ├── pdf_loader.py          # PDFLoaderService (LangChain)
│   │   ├── docx_loader.py         # DOCXLoaderService (LangChain)
│   │   ├── csv_loader.py          # CSVLoaderService (LangChain)
│   │   ├── text_loader.py         # TextLoaderService (LangChain)
│   │   ├── markdown_loader.py     # MarkdownLoaderService (LangChain)
│   │   ├── url_loader.py          # URLLoaderService (LangChain)
│   │   ├── gcs_loader.py          # GCSLoaderService (LangChain GCS integration)
│   │   ├── file_validator.py      # FileValidatorService (security validations)
│   │   ├── semantic_chunker.py    # SemanticChunkerService (LangChain semantic splitting)
│   │   ├── embedding.py           # EmbeddingService
│   │   ├── vectordb.py            # QdrantService
│   │   ├── llm_client.py          # vLLM OpenAI client (async)
│   │   ├── rag_pipeline.py        # Retrieve → Generate pipeline
│   │   └── monitoring/
│   │       ├── __init__.py
│   │       ├── drift_detector.py  # Evidently integration
│   │       └── metrics.py         # Custom metrics
│   └── models/
│       ├── __init__.py
│       └── schemas.py             # Pydantic models
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Shared fixtures
│   ├── unit/
│   │   ├── test_pdf_loader_service.py
│   │   ├── test_docx_loader.py
│   │   ├── test_csv_loader_service.py
│   │   ├── test_text_loader_service.py
│   │   ├── test_markdown_loader.py
│   │   ├── test_url_loader.py
│   │   ├── test_gcs_loader.py
│   │   ├── test_file_validator_service.py
│   │   ├── test_semantic_chunker_service.py
│   │   ├── test_embedding.py
│   │   ├── test_query_router.py    # LangGraph classification tests
│   │   ├── test_llm_client.py
│   │   ├── test_vectordb.py
│   │   ├── test_rag_pipeline.py
│   │   ├── test_orchestrator.py
│   │   └── test_drift_detector.py
│   ├── integration/
│   │   ├── test_api_endpoints.py
│   │   ├── test_ingestion_flow.py
│   │   └── test_rag_flow.py
│   ├── evaluation/
│   │   └── test_ragas.py          # RAGAS metrics
│   └── fixtures/
│       ├── sample.pdf
│       ├── sample.docx
│       ├── sample.csv
│       ├── sample.txt
│       └── sample.jpg
├── kubernetes/
│   ├── helm/
│   │   ├── intellirag/           # Main application chart
│   │   │   ├── Chart.yaml
│   │   │   ├── values.yaml
│   │   │   └── templates/
│   │   │       ├── deployment.yaml
│   │   │       ├── service.yaml
│   │   │       ├── hpa.yaml
│   │   │       ├── ingress.yaml  # NGINX ingress
│   │   │       └── configmap.yaml
│   │   ├── kserve/               # Model serving
│   │   │   └── inferenceservice.yaml
│   │   ├── qdrant/               # Vector DB
│   │   ├── monitoring/           # Prometheus, Grafana, Jaeger, Loki
│   │   └── helmfile.yaml         # Manage all charts
│   └── manifests/
│       └── namespace.yaml
├── terraform/
│   ├── main.tf                   # GKE cluster
│   ├── variables.tf
│   ├── outputs.tf
│   └── modules/
│       ├── gke/
│       ├── networking/
│       └── iam/
├── observability/
│   ├── prometheus/
│   │   └── rules.yaml            # Alert rules
│   ├── grafana/
│   │   └── dashboards/
│   │       ├── system.json
│   │       ├── application.json
│   │       └── rag-metrics.json
│   └── evidently/
│       └── reports/
├── mlops/
│   ├── mlflow/
│   │   └── models/               # Model artifacts
│   └── dvc/
│       ├── .dvc/
│       └── data.dvc              # Data versioning
├── docs/
│   ├── architecture.md
│   ├── api-spec.md
│   ├── deployment.md
│   └── monitoring.md
├── .github/
│   └── workflows/
│       └── ci-cd.yml             # Test → Build → Deploy
├── .env.example
├── pytest.ini                    # Pytest config
├── pyproject.toml                # uv/pip config
├── requirements.txt
├── requirements-dev.txt
├── Dockerfile
└── CLAUDE.md                     # This file
```

---

## 🔄 System Flows

### **Flow 1: Document Ingestion**

```
User → UI → NGINX → Orchestrator
                        ↓
                ┌───────┴────────┐
                ↓                ↓
    Store Raw Document      Preprocessing Pipeline
    in GCS Bucket              ├─> Load (LangChain GCS Loader)
                              ├─> Parse (Docling)
                              ├─> Chunk (LangChain)
                              └─> Embed (SentenceTransformers)
                                  ↓
                              Qdrant (Store Vectors + Metadata)
                              - Vector embeddings
                              - Document metadata in payload
                              - GCS path reference
                                  ↓
                              DVC (Version Dataset)
```

### **Flow 2: Query/RAG (Conditional Routing)**

```
User → UI → NGINX → Orchestrator
                        ↓
                   LangGraph Agent
                   (Query Analysis)
                        ↓
                   ┌────┴────┐
                   │         │
              Need RAG?   No (Direct)
                   │         │
                  Yes        └──────────┐
                   │                    │
                   ↓                    │
              Embed Query               │
                   ↓                    │
              Qdrant (Retrieve)         │
                   ↓                    │
              Format Prompt             │
              (Query + Context)         │
                   │                    │
                   └─────────┬──────────┘
                             ↓
                    vLLM Service (OpenAI API)
                    ├─> Dev: Docker Container
                    └─> Prod: KServe → vLLM → GPU (Qwen2.5)
                             ↓
                    Generate Answer
                             ↓
                    User ← UI ← NGINX

Decision Logic:
- Factual questions → Direct answer (no RAG)
- Domain-specific → RAG retrieval
- Conversational → Direct answer
- Document queries → RAG retrieval

Performance:
- Throughput: 793 TPS (19x vs Ollama)
- P99 Latency: 80ms (8x faster vs Ollama)
- GPU Utilization: 95%+ (PagedAttention)
```

### **Flow 3: CI/CD**

```
Developer → Git Push → GitHub Actions
                           ↓
                      Test (Pytest)
                      Coverage > 80%?
                           ↓ (auto)
                      Build (Docker)
                           ↓
                      Push to Registry
                           ↓ (manual trigger)
                      Deploy to GKE (Helm)
                           ↓
                      ├─> Update FastAPI
                      ├─> Update KServe
                      └─> Update NGINX
```

### **Flow 4: Observability (Continuous)**

```
Every Request:
    ├─> Jaeger (Trace ID)
    ├─> Prometheus (Metrics)
    ├─> Loki (Logs)
    └─> Evidently (Data Drift)
         ↓
    Grafana (Visualization)
```

---

## 🔒 CRITICAL CONSTRAINTS

### DO NOT:
- Skip writing tests before implementation
- Modify tests to make implementation pass (except fixing actual test bugs)
- Mock everything (over-mocking makes tests brittle)
- Test implementation details (test behavior, not internals)
- Use production API keys or production databases in tests

### DO:
- Write tests that define expected behavior clearly
- Use fixtures for reusable test data
- Keep tests independent (no test should depend on another)
- Test edge cases and error conditions
- Use meaningful assertion messages
- Run full test suite before committing

---

## Development Rules

### General
- Update existing docs (Markdown files) in `./docs` directory before any code refactoring
- Add new docs (Markdown files) to `./docs` directory after new feature implementation (do not create duplicated docs)
- Use `context7` mcp tools for docs of plugins/packages
- Use `senera` mcp tools for semantic retrieval and editing capabilities
- Whenever you want to see the whole code base, use this command: `repomix` and read the output summary file

### vLLM & Inference Guidelines
- Use vLLM for all LLM inference in both development and production environments
- Test with vLLM Docker container locally before deploying to KServe
- Monitor GPU memory usage to stay within 12GB VRAM limit (RTX 4070Ti)
- Use quantization (FP8/INT8) if model exceeds available GPU memory
- Leverage OpenAI-compatible API for consistent interface across environments
- Enable prefix caching for repeated query patterns in RAG workflows
- Set `--gpu-memory-utilization` to 0.95 for optimal throughput
- Use `--max-model-len` based on actual use case (default: 8192 tokens)
- Monitor vLLM metrics via Prometheus in production (TPS, latency, GPU utilization)

### Code Quality Guidelines
- Before you start, delegate to `planner-researcher` agent to create an implemnetation plan with TODO tasks in `./docs/todos` directory
- Write clean, readable, maintainable code
- Handle edge cases and error scenarios
- Don't be too harsh on code linting and formatting
- Prioritize functionality and readability over strict style enforcement
- Use reasonable code quality standards that enhance developer productivity
- Allow for minor style variations when they improve code clarity
- Add proper type hints for better IDE support
- Document complex logic with clear comments
- Type hints required for all functions and methods
- Classes: PascalCase with descriptive name
- Functions/Variables: snake_case
- Constants: UPPERCASE_WITH_UNDERSCORES
- Import organization with isort:
  1. Standard library imports
  2. Third-party imports
  3. Local application imports
- Error handling: Use  specific exception types
- Logging: Use the logging module with appropriate levels
- Delegate to `senior-code-reviewer` agent to review code
- Following code standards and conventions
- Write self-documenting code
- Add meaningful comments for complex logic
- Optimize for performance and maintainability

### Pre-commit/Push Rules
- Keep commits focused on the actual code changes
- **DO NOT** commit and push any confidential information (such as dotenv files, API keys, database credentials, etc.) to git repository!
- NEVER automatically add AI attribution signatures like:
  - "🤖 Generated with [Claude Code]"
  - "Co-Authored-By: Claude noreply@anthropic.com"
  - Any AI tool attribution or signature
- Create clean, professional commit messages without AI references
- Use conventional commit format: `<type>(<scope>): <description>`
  - Examples: `feat(api): add query endpoint`, `fix(vectordb): handle connection timeout`

### Observability Integration
- Add structured logging to all services
- Instrument critical paths with tracing spans
- Expose Prometheus metrics for monitoring
- Log errors with full context and stack traces
- Include correlation IDs in all logs

---

## 💡 Pro Tips

1. **Always trace requests end-to-end** - Use Jaeger to understand bottlenecks
2. **Monitor data drift early** - Set up alerts in Evidently before production
3. **Test with production-like data** - Use DVC to version realistic datasets
4. **Keep models versioned** - Never deploy unversioned models
5. **Automate everything** - If you do it twice, automate it
6. **Think about scale-to-zero** - Optimize cold start times for KServe
7. **Watch your costs** - Monitor GKE and GPU utilization closely
8. **Document as you go** - Update docs when changing architecture