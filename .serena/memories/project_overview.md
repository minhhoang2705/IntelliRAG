# IntelliRAG Project Overview

## Purpose
IntelliRAG is a production-ready RAG (Retrieval-Augmented Generation) system with full MLOps pipeline, integrating local GPU inference with cloud-native Kubernetes deployment. The system processes multi-modal documents and provides intelligent query routing with high-performance LLM inference.

## Tech Stack
- **Python**: 3.12 with uv package manager
- **Framework**: FastAPI with async/await patterns
- **Vector DB**: Qdrant (stores vectors + metadata payloads)
- **Storage**: Google Cloud Storage (GCS) for raw documents
- **LLM**: vLLM with Qwen3-0.6B model (19x throughput vs Ollama)
- **Embeddings**: embeddinggemma-300m (768 dimension)
- **Document Processing**: LangChain/LangGraph for loaders and chunking
- **Query Routing**: LangGraph for conditional RAG vs direct answer
- **Observability**: OpenTelemetry, Prometheus, Grafana, Jaeger, Loki
- **Infrastructure**: Kubernetes (GKE + local GPU via KServe)
- **Testing**: Pytest with >80% coverage requirement

## Architecture
- Hybrid deployment: GKE for application, local RTX 4070Ti for GPU inference
- Document ingestion pipeline: Upload → GCS → Parse → Chunk → Embed → Store in Qdrant
- Query pipeline: Query → Route (LangGraph) → Retrieve (if needed) → Generate (vLLM)
- Job state management for tracking ingestion progress
- Comprehensive observability with metrics, tracing, and structured logging