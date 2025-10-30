"""Prometheus metrics for IntelliRAG.

This module defines metrics for monitoring query classification,
routing decisions, RAG pipeline performance, and document ingestion pipeline.
"""

from prometheus_client import Counter, Histogram, Gauge


# Query Classification Metrics
query_classification_total = Counter(
    'query_classification_total',
    'Total number of query classifications',
    ['query_type']
)

query_classification_confidence = Histogram(
    'query_classification_confidence',
    'Confidence scores for query classifications',
    buckets=[0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 1.0]
)

query_classification_duration_seconds = Histogram(
    'query_classification_duration_seconds',
    'Time taken to classify queries',
    buckets=[0.01, 0.05, 0.1, 0.2, 0.5, 1.0, 2.0]
)

# Query Routing Metrics
query_router_decisions_total = Counter(
    'query_router_decisions_total',
    'Total routing decisions by type',
    ['decision']  # 'rag', 'direct', 'clarification', 'multi_hop'
)

# RAG Pipeline Metrics
rag_query_duration_seconds = Histogram(
    'rag_query_duration_seconds',
    'RAG query processing time',
    ['stage'],  # 'embedding', 'retrieval', 'generation'
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0]
)

rag_retrieval_results = Histogram(
    'rag_retrieval_results',
    'Number of retrieved documents',
    buckets=[0, 1, 3, 5, 10, 20, 50]
)

# LLM Metrics
llm_token_count = Counter(
    'llm_token_count',
    'Total tokens processed by LLM',
    ['model', 'type']  # type: 'input' or 'output'
)

# HTTP Metrics
http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# Vector DB Metrics
vector_db_operations = Counter(
    'vector_db_operations_total',
    'Total vector database operations',
    ['operation', 'collection']
)

# Cache Metrics
embedding_cache_hits = Counter(
    'embedding_cache_hits_total',
    'Embedding cache hits',
    ['hit']  # 'true' or 'false'
)

# GPU Metrics
gpu_utilization = Gauge(
    'gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id']
)

# Ingestion Pipeline Metrics
ingestion_jobs_total = Counter(
    'ingestion_jobs_total',
    'Total number of ingestion jobs by status and file type',
    ['status', 'file_type']
)

ingestion_jobs_active = Gauge(
    'ingestion_jobs_active',
    'Number of currently active ingestion jobs by status',
    ['status']
)

file_upload_duration_seconds = Histogram(
    'file_upload_duration_seconds',
    'Time taken to upload file to storage',
    ['file_type'],
    buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

file_upload_size_bytes = Histogram(
    'file_upload_size_bytes',
    'Size of uploaded files in bytes',
    ['file_type'],
    buckets=[1024, 10240, 102400, 1048576, 10485760, 52428800]
)

document_processing_stage_duration_seconds = Histogram(
    'document_processing_stage_duration_seconds',
    'Duration of each document processing stage',
    ['stage', 'file_type'],
    buckets=[0.5, 1.0, 2.0, 5.0, 10.0, 30.0, 60.0]
)

ingestion_chunks_created = Histogram(
    'ingestion_chunks_created',
    'Number of chunks created per document',
    ['file_type'],
    buckets=[10, 50, 100, 200, 500, 1000]
)

ingestion_job_duration_seconds = Histogram(
    'ingestion_job_duration_seconds',
    'Total time from job creation to completion',
    ['status', 'file_type']
)

ingestion_errors_total = Counter(
    'ingestion_errors_total',
    'Total number of ingestion errors by type and stage',
    ['error_type', 'stage']
)
