# Codebase Structure

## Main Application (app/)
- **main.py**: FastAPI app with /health and /metrics endpoints
- **config.py**: Configuration management
- **exceptions.py**: Custom exception classes
- **dependencies.py**: FastAPI dependency injection

### API Layer (app/api/)
- **v1/upload.py**: Document upload endpoint
- **v1/ingest.py**: Ingestion pipeline trigger
- **v1/query.py**: RAG query endpoint
- **middleware/**: Metrics, correlation, tracing middleware

### Services (app/services/)
- **orchestrator.py**: Main pipeline orchestration
- **job_state.py**: Job tracking and status
- **Document Loaders**: pdf_loader, docx_loader, csv_loader, text_loader, markdown_loader, url_loader, gcs_loader
- **file_validator.py**: Security and validation
- **semantic_chunker.py**: LangChain semantic splitting
- **bge_m3_embedding.py**: BGE-M3 embeddings (1024-dim)
- **vectordb.py**: Qdrant operations
- **llm_client.py**: vLLM async client
- **rag_pipeline.py**: Retrieval and generation
- **query_router/**: LangGraph query classification
- **gcs_storage.py**: GCS operations

### Core (app/core/)
- **logging.py**: Structured JSON logging
- **tracing.py**: OpenTelemetry setup

### Models (app/models/)
- **schemas.py**: Pydantic models and validation

## Tests (tests/)
- **unit/**: 50+ unit test files with mocked dependencies
- **integration/**: End-to-end flow tests
- **fixtures/**: Sample test data files
- **conftest.py**: Shared pytest fixtures

## Infrastructure
- **kubernetes/**: K8s manifests, Helm charts
  - observability/: Prometheus, Grafana, Jaeger, Loki
  - kserve/: Model serving configurations
- **terraform/**: GKE cluster provisioning (ready but not deployed)
- **deploy/**: Docker configurations

## Documentation (docs/)
- **architecture/**: System design docs
- **deployment/**: Deployment guides
- **planning/**: Implementation plans
- **phase-2/**: Phase 2 documentation
- **infrastructure/**: MLOps and observability docs

## Current State
- Core application: COMPLETE with >80% coverage
- Observability: INSTRUMENTED, needs K8s validation
- Kubernetes: Configs READY, deployment needed
- CI/CD: NOT implemented
- MLOps tools: NOT implemented