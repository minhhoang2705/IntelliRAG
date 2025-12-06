# Observability Stack Documentation

**Version**: 1.0
**Date**: 2025-10-22
**Status**: Implementation Guide

---

## Executive Summary

This document defines the complete observability stack for IntelliRAG, providing comprehensive monitoring, tracing, logging, and data drift detection capabilities. The stack enables proactive issue detection, performance optimization, and data quality assurance for the production RAG system.

**Key Components:**
- **Prometheus**: Metrics collection and alerting
- **Grafana**: Visualization dashboards and analytics
- **Jaeger/Tempo**: Distributed tracing for request flows
- **Loki**: Centralized log aggregation
- **Evidently**: ML model and data drift monitoring

---

## Architecture Overview

```
Application Layer
    ├─ FastAPI (Instrumented)
    ├─ vLLM/KServe (GPU metrics)
    ├─ Qdrant (Vector DB metrics)
    └─ LangChain (Processing metrics)
        ↓
    ┌───────────────────────────────────┐
    │   METRICS (Prometheus)            │
    │   - Request rates                 │
    │   - Latency (P50/P95/P99)        │
    │   - Error rates                   │
    │   - GPU utilization               │
    │   - Cache hit rates               │
    └───────────┬───────────────────────┘
                │
    ┌───────────┴───────────────────────┐
    │   TRACES (Jaeger/Tempo)           │
    │   - Request spans                 │
    │   - Service dependencies          │
    │   - Bottleneck identification     │
    │   - Error propagation             │
    └───────────┬───────────────────────┘
                │
    ┌───────────┴───────────────────────┐
    │   LOGS (Loki)                     │
    │   - Structured JSON logs          │
    │   - Error tracking                │
    │   - Audit trails                  │
    │   - Debug information             │
    └───────────┬───────────────────────┘
                │
    ┌───────────┴───────────────────────┐
    │   DATA DRIFT (Evidently)          │
    │   - Input distribution shifts     │
    │   - Model performance degradation │
    │   - Feature drift detection       │
    │   - Prediction quality metrics    │
    └───────────────────────────────────┘
                ↓
    ┌───────────────────────────────────┐
    │   VISUALIZATION (Grafana)         │
    │   - Real-time dashboards          │
    │   - Alert management              │
    │   - Historical analysis           │
    │   - Anomaly detection             │
    └───────────────────────────────────┘
```

---

## 1. Prometheus Metrics Collection

### 1.1 Architecture

```
Application Metrics Endpoints
    ├─ FastAPI: /metrics (port 8000)
    ├─ vLLM: /metrics (port 8000)
    ├─ Qdrant: /metrics (port 6333)
    └─ Node Exporter: /metrics (port 9100)
        ↓
Prometheus Server (Scrape)
    ├─ Service Discovery (Kubernetes)
    ├─ Scrape Interval: 15s
    ├─ Retention: 15 days
    └─ Storage: 50GB PVC
        ↓
Prometheus Query
    ├─ PromQL queries
    ├─ Recording rules
    └─ Alerting rules
        ↓
Alert Manager
    ├─ Slack notifications
    ├─ PagerDuty escalation
    └─ Email alerts
```

### 1.2 Prometheus Configuration

**Helm Values** (`kubernetes/helm/monitoring/prometheus/values.yaml`):
```yaml
prometheus:
  prometheusSpec:
    retention: 15d
    retentionSize: 45GB
    scrapeInterval: 15s
    evaluationInterval: 15s

    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
          storageClassName: standard-rwo

    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2000m
        memory: 4Gi

    additionalScrapeConfigs:
      # FastAPI application
      - job_name: 'intellirag-fastapi'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - intellirag
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: intellirag-fastapi
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: pod
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace

      # vLLM model serving
      - job_name: 'vllm-inference'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - intellirag
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_serving_kserve_io_inferenceservice]
            action: keep
            regex: qwen-vllm

      # Qdrant vector database
      - job_name: 'qdrant'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - intellirag
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: qdrant

alertmanager:
  config:
    global:
      resolve_timeout: 5m
      slack_api_url: ${SLACK_WEBHOOK_URL}

    route:
      group_by: ['alertname', 'cluster', 'service']
      group_wait: 10s
      group_interval: 10s
      repeat_interval: 12h
      receiver: 'slack-critical'
      routes:
        - match:
            severity: critical
          receiver: 'pagerduty'
        - match:
            severity: warning
          receiver: 'slack-warnings'

    receivers:
      - name: 'slack-critical'
        slack_configs:
          - channel: '#intellirag-alerts-critical'
            title: 'Critical Alert: {{ .GroupLabels.alertname }}'
            text: '{{ range .Alerts }}{{ .Annotations.description }}{{ end }}'

      - name: 'slack-warnings'
        slack_configs:
          - channel: '#intellirag-alerts-warnings'

      - name: 'pagerduty'
        pagerduty_configs:
          - service_key: ${PAGERDUTY_SERVICE_KEY}
```

### 1.3 Application Instrumentation

**FastAPI Metrics** (`app/api/middleware/metrics.py`):
```python
"""Prometheus metrics middleware for FastAPI."""
from prometheus_client import Counter, Histogram, Gauge, generate_latest
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
import time
from typing import Callable


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

# Query Router Metrics (LangGraph-based)
query_classification_total = Counter(
    'query_classification_total',
    'Total number of query classifications',
    ['query_type']  # 'rag', 'direct', 'clarification', 'multi_hop'
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

# Infrastructure Metrics
gpu_utilization = Gauge(
    'gpu_utilization_percent',
    'GPU utilization percentage',
    ['gpu_id']
)

vector_db_operations = Counter(
    'vector_db_operations_total',
    'Total vector database operations',
    ['operation', 'collection']
)

embedding_cache_hits = Counter(
    'embedding_cache_hits_total',
    'Embedding cache hits',
    ['hit']  # 'true' or 'false'
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    """Middleware to collect Prometheus metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request and collect metrics."""
        start_time = time.time()

        # Process request
        response = await call_next(request)

        # Record metrics
        duration = time.time() - start_time
        http_requests_total.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=response.status_code
        ).inc()

        http_request_duration_seconds.labels(
            method=request.method,
            endpoint=request.url.path
        ).observe(duration)

        return response


async def metrics_endpoint():
    """Expose Prometheus metrics at /metrics endpoint."""
    return Response(
        content=generate_latest(),
        media_type='text/plain; version=0.0.4; charset=utf-8'
    )
```

**Query Classifier Instrumentation** (`app/services/query_router/classifier.py`):
```python
"""Query classification with metrics instrumentation."""
import time
import json
from app.api.middleware.metrics import (
    query_classification_total,
    query_classification_confidence,
    query_classification_duration_seconds,
)


class QueryClassifier:
    """LangGraph-based query classifier with observability."""

    async def classify(self, query: str) -> QueryClassification:
        """Classify query with metrics recording."""
        # Start timing
        start_time = time.time()

        # Build prompt and classify
        prompt = build_classification_prompt(query)
        response = await self.llm_client.generate(
            prompt=prompt,
            temperature=0.1,
            max_tokens=150
        )

        # Parse classification result
        data = json.loads(response)
        classification = QueryClassification(
            query_type=QueryType(data["query_type"]),
            confidence=data["confidence"],
            reasoning=data["reasoning"]
        )

        # Record metrics
        duration = time.time() - start_time
        query_classification_duration_seconds.observe(duration)
        query_classification_confidence.observe(classification.confidence)
        query_classification_total.labels(
            query_type=classification.query_type.value
        ).inc()

        return classification
```

**RAG Pipeline Instrumentation** (`app/services/rag_pipeline.py`):
```python
"""RAG pipeline with observability instrumentation."""
import time
from typing import List, Dict, Any
from app.api.middleware.metrics import (
    rag_query_duration_seconds,
    rag_retrieval_results,
    llm_token_count,
)


class RAGPipeline:
    """RAG pipeline with metrics collection."""

    async def process_query(self, query: str) -> Dict[str, Any]:
        """Process RAG query with instrumentation."""
        # Stage 1: Embedding
        start_time = time.time()
        query_embedding = await self.embed_query(query)
        rag_query_duration_seconds.labels(stage='embedding').observe(
            time.time() - start_time
        )

        # Stage 2: Retrieval
        start_time = time.time()
        documents = await self.retrieve_documents(query_embedding)
        rag_query_duration_seconds.labels(stage='retrieval').observe(
            time.time() - start_time
        )
        rag_retrieval_results.observe(len(documents))

        # Stage 3: Generation
        start_time = time.time()
        response = await self.generate_response(query, documents)
        rag_query_duration_seconds.labels(stage='generation').observe(
            time.time() - start_time
        )

        # Track token usage
        llm_token_count.labels(
            model='Qwen3-0.6B-instruct',
            type='input'
        ).inc(response['usage']['prompt_tokens'])

        llm_token_count.labels(
            model='Qwen3-0.6B-instruct',
            type='output'
        ).inc(response['usage']['completion_tokens'])

        return response
```

### 1.4 Alert Rules

**File**: `observability/prometheus/rules.yaml`

```yaml
groups:
  - name: intellirag-alerts
    interval: 30s
    rules:
      # High error rate
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          /
          sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }} (threshold: 5%)"

      # High latency
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99,
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint)
          ) > 2.0
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High request latency on {{ $labels.endpoint }}"
          description: "P99 latency is {{ $value }}s (threshold: 2s)"

      # GPU utilization
      - alert: GPUUtilizationLow
        expr: avg(gpu_utilization_percent) < 30
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "GPU utilization is low"
          description: "Average GPU utilization is {{ $value }}% (threshold: 30%)"

      - alert: GPUUtilizationHigh
        expr: avg(gpu_utilization_percent) > 95
        for: 10m
        labels:
          severity: critical
        annotations:
          summary: "GPU utilization is critically high"
          description: "Average GPU utilization is {{ $value }}% (threshold: 95%)"

      # RAG performance
      - alert: SlowRAGQueries
        expr: |
          histogram_quantile(0.95,
            sum(rate(rag_query_duration_seconds_bucket[5m])) by (le)
          ) > 10.0
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "RAG queries are slow"
          description: "P95 query duration is {{ $value }}s (threshold: 10s)"

      # Vector DB issues
      - alert: VectorDBHighErrorRate
        expr: |
          sum(rate(vector_db_operations_total{status="error"}[5m]))
          /
          sum(rate(vector_db_operations_total[5m])) > 0.01
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate in vector database"
          description: "Vector DB error rate is {{ $value | humanizePercentage }}"

      # Cache performance
      - alert: LowCacheHitRate
        expr: |
          sum(rate(embedding_cache_hits_total{hit="true"}[10m]))
          /
          sum(rate(embedding_cache_hits_total[10m])) < 0.5
        for: 15m
        labels:
          severity: warning
        annotations:
          summary: "Low embedding cache hit rate"
          description: "Cache hit rate is {{ $value | humanizePercentage }} (threshold: 50%)"

      # Model serving
      - alert: ModelServingDown
        expr: up{job="vllm-inference"} == 0
        for: 2m
        labels:
          severity: critical
        annotations:
          summary: "vLLM model serving is down"
          description: "vLLM inference service is not responding"
```

---

## 2. Grafana Dashboards

### 2.1 Dashboard Architecture

```
Grafana Instance
    ├─ Data Sources
    │   ├─ Prometheus (metrics)
    │   ├─ Tempo (traces)
    │   ├─ Loki (logs)
    │   └─ Evidently (drift reports)
    ├─ Dashboards
    │   ├─ System Overview
    │   ├─ Application Metrics
    │   ├─ RAG Performance
    │   ├─ GPU Monitoring
    │   └─ Data Quality
    └─ Alerts
        ├─ Alert rules
        └─ Notification channels
```

### 2.2 System Overview Dashboard

**File**: `observability/grafana/dashboards/system-overview.json`

```json
{
  "dashboard": {
    "title": "IntelliRAG System Overview",
    "uid": "intellirag-system",
    "timezone": "browser",
    "refresh": "30s",
    "panels": [
      {
        "title": "Request Rate",
        "gridPos": {"x": 0, "y": 0, "w": 8, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(http_requests_total[5m])) by (endpoint)",
            "legendFormat": "{{endpoint}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "P95 Latency",
        "gridPos": {"x": 8, "y": 0, "w": 8, "h": 8},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(http_request_duration_seconds_bucket[5m])) by (le, endpoint))",
            "legendFormat": "{{endpoint}}"
          }
        ],
        "type": "graph",
        "yaxes": [{"format": "s"}]
      },
      {
        "title": "Error Rate",
        "gridPos": {"x": 16, "y": 0, "w": 8, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(http_requests_total{status_code=~\"5..\"}[5m])) / sum(rate(http_requests_total[5m]))",
            "legendFormat": "Error Rate"
          }
        ],
        "type": "graph",
        "yaxes": [{"format": "percentunit"}],
        "thresholds": [
          {"value": 0.01, "color": "yellow"},
          {"value": 0.05, "color": "red"}
        ]
      },
      {
        "title": "Active Requests",
        "gridPos": {"x": 0, "y": 8, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "sum(http_requests_in_flight)"
          }
        ],
        "type": "stat",
        "fieldConfig": {
          "defaults": {
            "color": {"mode": "thresholds"},
            "thresholds": {
              "steps": [
                {"value": 0, "color": "green"},
                {"value": 50, "color": "yellow"},
                {"value": 100, "color": "red"}
              ]
            }
          }
        }
      },
      {
        "title": "GPU Utilization",
        "gridPos": {"x": 6, "y": 8, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "avg(gpu_utilization_percent)"
          }
        ],
        "type": "gauge",
        "fieldConfig": {
          "defaults": {
            "unit": "percent",
            "min": 0,
            "max": 100,
            "thresholds": {
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 30, "color": "yellow"},
                {"value": 50, "color": "green"},
                {"value": 95, "color": "red"}
              ]
            }
          }
        }
      },
      {
        "title": "Cache Hit Rate",
        "gridPos": {"x": 12, "y": 8, "w": 6, "h": 4},
        "targets": [
          {
            "expr": "sum(rate(embedding_cache_hits_total{hit=\"true\"}[5m])) / sum(rate(embedding_cache_hits_total[5m]))"
          }
        ],
        "type": "stat",
        "fieldConfig": {
          "defaults": {
            "unit": "percentunit",
            "thresholds": {
              "steps": [
                {"value": 0, "color": "red"},
                {"value": 0.5, "color": "yellow"},
                {"value": 0.8, "color": "green"}
              ]
            }
          }
        }
      }
    ]
  }
}
```

### 2.3 RAG Performance Dashboard

**File**: `observability/grafana/dashboards/rag-performance.json`

```json
{
  "dashboard": {
    "title": "RAG Pipeline Performance",
    "uid": "intellirag-rag",
    "panels": [
      {
        "title": "RAG Query Duration by Stage",
        "gridPos": {"x": 0, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(rag_query_duration_seconds_bucket[5m])) by (le, stage))",
            "legendFormat": "P95 - {{stage}}"
          },
          {
            "expr": "histogram_quantile(0.50, sum(rate(rag_query_duration_seconds_bucket[5m])) by (le, stage))",
            "legendFormat": "P50 - {{stage}}"
          }
        ],
        "type": "graph",
        "yaxes": [{"format": "s"}]
      },
      {
        "title": "Retrieved Documents Distribution",
        "gridPos": {"x": 12, "y": 0, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "histogram_quantile(0.95, sum(rate(rag_retrieval_results_bucket[5m])) by (le))",
            "legendFormat": "P95"
          },
          {
            "expr": "histogram_quantile(0.50, sum(rate(rag_retrieval_results_bucket[5m])) by (le))",
            "legendFormat": "P50"
          }
        ],
        "type": "graph"
      },
      {
        "title": "LLM Token Usage",
        "gridPos": {"x": 0, "y": 8, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(llm_token_count[5m])) by (type)",
            "legendFormat": "{{type}}"
          }
        ],
        "type": "graph"
      },
      {
        "title": "Vector DB Operations",
        "gridPos": {"x": 12, "y": 8, "w": 12, "h": 8},
        "targets": [
          {
            "expr": "sum(rate(vector_db_operations_total[5m])) by (operation)",
            "legendFormat": "{{operation}}"
          }
        ],
        "type": "graph"
      }
    ]
  }
}
```

---

## 3. Distributed Tracing (Jaeger/Tempo)

### 3.1 Architecture

```
FastAPI Request
    ↓ (Trace ID generated)
Jaeger Client (OpenTelemetry)
    ├─ Span: HTTP Request
    ├─ Span: Query Embedding
    │   └─ Span: Sentence Transformer
    ├─ Span: Vector Retrieval
    │   └─ Span: Qdrant Query
    └─ Span: LLM Generation
        └─ Span: vLLM Request
            ↓
Tempo Backend (Storage)
    ├─ Trace aggregation
    └─ Span indexing
            ↓
Grafana (Query Interface)
    ├─ Trace search
    ├─ Service map
    └─ Latency analysis
```

### 3.2 OpenTelemetry Instrumentation

**Tracing Middleware** (`app/api/middleware/tracing.py`):
```python
"""OpenTelemetry tracing middleware."""
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from fastapi import FastAPI
import os


def setup_tracing(app: FastAPI):
    """Configure OpenTelemetry tracing."""
    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer_provider = trace.get_tracer_provider()

    # Configure OTLP exporter (Tempo)
    otlp_exporter = OTLPSpanExporter(
        endpoint=os.getenv("TEMPO_ENDPOINT", "http://tempo:4317"),
        insecure=True,
    )

    # Add span processor
    tracer_provider.add_span_processor(
        BatchSpanProcessor(otlp_exporter)
    )

    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)

    # Instrument HTTP client
    HTTPXClientInstrumentor().instrument()

    return trace.get_tracer(__name__)


# Usage in services
class RAGPipeline:
    """RAG pipeline with tracing."""

    def __init__(self, tracer):
        self.tracer = tracer

    async def process_query(self, query: str):
        """Process query with distributed tracing."""
        with self.tracer.start_as_current_span("rag_query") as span:
            span.set_attribute("query.length", len(query))

            # Embedding
            with self.tracer.start_as_current_span("embedding"):
                embedding = await self.embed_query(query)
                span.set_attribute("embedding.dimension", len(embedding))

            # Retrieval
            with self.tracer.start_as_current_span("retrieval") as retrieval_span:
                documents = await self.retrieve_documents(embedding)
                retrieval_span.set_attribute("documents.count", len(documents))

            # Generation
            with self.tracer.start_as_current_span("generation") as gen_span:
                response = await self.generate_response(query, documents)
                gen_span.set_attribute("response.tokens", response['usage']['total_tokens'])

            return response
```

### 3.3 Tempo Configuration

**Helm Values** (`kubernetes/helm/monitoring/tempo/values.yaml`):
```yaml
tempo:
  retention: 720h  # 30 days

  compactor:
    enabled: true

  storage:
    trace:
      backend: gcs
      gcs:
        bucket_name: intellirag-traces
        chunk_buffer_size: 10485760
        endpoint: https://storage.googleapis.com

  receivers:
    otlp:
      protocols:
        grpc:
          endpoint: 0.0.0.0:4317
        http:
          endpoint: 0.0.0.0:4318

  query:
    enabled: true
    replicas: 2

  resources:
    limits:
      cpu: 2000m
      memory: 4Gi
    requests:
      cpu: 500m
      memory: 1Gi
```

---

## 4. Centralized Logging (Loki)

### 4.1 Architecture

```
Application Logs
    ├─ FastAPI (JSON structured)
    ├─ vLLM (stdout/stderr)
    ├─ Qdrant (JSON)
    └─ Kubernetes logs
        ↓
Promtail (Log Collector)
    ├─ Label extraction
    ├─ Pipeline processing
    └─ Log forwarding
        ↓
Loki (Storage & Indexing)
    ├─ Chunk storage (GCS)
    ├─ Index (BoltDB)
    └─ Query interface
        ↓
Grafana (Log Exploration)
    ├─ LogQL queries
    ├─ Log correlation with traces
    └─ Error tracking
```

### 4.2 Structured Logging

**Logging Configuration** (`app/config/logging_config.py`):
```python
"""Structured logging configuration."""
import logging
import json
import sys
from datetime import datetime
from typing import Any, Dict
from contextvars import ContextVar

# Context variable for trace ID
trace_id_var: ContextVar[str] = ContextVar('trace_id', default='')


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'trace_id': trace_id_var.get(''),
        }

        # Add exception info
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # Add extra fields
        if hasattr(record, 'extra'):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging(level: str = "INFO"):
    """Configure structured logging."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())

    logging.basicConfig(
        level=getattr(logging, level.upper()),
        handlers=[handler]
    )

    # Disable noisy loggers
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)


# Usage
logger = logging.getLogger(__name__)

# Log with context
logger.info(
    "RAG query processed",
    extra={
        'query_length': 150,
        'documents_retrieved': 5,
        'response_tokens': 250,
        'duration_ms': 1250,
    }
)
```

### 4.3 Loki Configuration

**Helm Values** (`kubernetes/helm/monitoring/loki/values.yaml`):
```yaml
loki:
  auth_enabled: false

  commonConfig:
    replication_factor: 1

  storage:
    type: gcs
    bucketNames:
      chunks: intellirag-loki-chunks
      ruler: intellirag-loki-ruler
      admin: intellirag-loki-admin
    gcs:
      chunkBufferSize: 10485760
      requestTimeout: 30s

  schemaConfig:
    configs:
      - from: 2024-01-01
        store: boltdb-shipper
        object_store: gcs
        schema: v12
        index:
          prefix: loki_index_
          period: 24h

  limits_config:
    retention_period: 720h  # 30 days
    ingestion_rate_mb: 10
    ingestion_burst_size_mb: 20
    max_query_series: 10000

  compactor:
    enabled: true
    retention_enabled: true

  resources:
    limits:
      cpu: 1000m
      memory: 2Gi
    requests:
      cpu: 500m
      memory: 1Gi

promtail:
  enabled: true
  config:
    clients:
      - url: http://loki:3100/loki/api/v1/push

    scrapeConfigs:
      # FastAPI application logs
      - job_name: intellirag-fastapi
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - intellirag
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: intellirag-fastapi
          - source_labels: [__meta_kubernetes_pod_name]
            target_label: pod
          - source_labels: [__meta_kubernetes_namespace]
            target_label: namespace
        pipeline_stages:
          - json:
              expressions:
                level: level
                timestamp: timestamp
                logger: logger
                message: message
                trace_id: trace_id
          - labels:
              level:
              trace_id:
          - timestamp:
              source: timestamp
              format: RFC3339Nano

      # vLLM model serving logs
      - job_name: vllm-inference
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - intellirag
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_serving_kserve_io_inferenceservice]
            action: keep
            regex: qwen-vllm
```

### 4.4 LogQL Queries

**Common Queries**:
```logql
# All errors in the last hour
{namespace="intellirag"} |= "ERROR" | json

# RAG query logs with high latency
{app="intellirag-fastapi"} | json
  | duration_ms > 5000
  | line_format "{{.message}} ({{.duration_ms}}ms)"

# Trace all requests for a specific trace_id
{namespace="intellirag"} | json
  | trace_id = "abc123def456"

# Error rate by endpoint
sum(rate({app="intellirag-fastapi", level="ERROR"}[5m])) by (endpoint)

# Top 10 slowest queries
topk(10,
  avg_over_time({app="intellirag-fastapi"} | json | unwrap duration_ms [5m])
) by (endpoint)
```

---

## 5. Data Drift Monitoring (Evidently)

### 5.1 Architecture

```
Production Data
    ├─ User queries
    ├─ Retrieved documents
    ├─ LLM responses
    └─ User feedback
        ↓
Evidently Monitoring
    ├─ Input drift detection
    ├─ Prediction drift
    ├─ Data quality checks
    └─ Model performance
        ↓
Reports & Alerts
    ├─ Drift detection reports
    ├─ Performance degradation
    └─ Data quality issues
        ↓
Grafana Dashboard
    ├─ Drift visualization
    └─ Alert notifications
```

### 5.2 Drift Detection Service

**Evidently Integration** (`app/services/monitoring/drift_detector.py`):
```python
"""Data and model drift detection using Evidently."""
import pandas as pd
from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import (
    DataDriftPreset,
    DataQualityPreset,
    TextOverviewPreset,
)
from evidently.metrics import (
    ColumnDriftMetric,
    DatasetDriftMetric,
    TextDescriptorsDrift,
)
from typing import Dict, List, Any
import json
from datetime import datetime


class DriftDetector:
    """Monitor data and model drift."""

    def __init__(
        self,
        reference_data_path: str,
        drift_threshold: float = 0.5,
    ):
        """Initialize drift detector.

        Args:
            reference_data_path: Path to reference dataset
            drift_threshold: Threshold for drift detection (0-1)
        """
        self.reference_data = pd.read_parquet(reference_data_path)
        self.drift_threshold = drift_threshold
        self.column_mapping = ColumnMapping(
            text_features=["query", "response"],
            numerical_features=["query_length", "response_length", "retrieval_count"],
            categorical_features=["query_type"],
        )

    def detect_data_drift(
        self,
        current_data: pd.DataFrame,
    ) -> Dict[str, Any]:
        """Detect data drift in current production data.

        Args:
            current_data: Current production data

        Returns:
            Drift detection results
        """
        # Create drift report
        report = Report(metrics=[
            DataDriftPreset(drift_share=self.drift_threshold),
            DataQualityPreset(),
            TextOverviewPreset(column_name="query"),
        ])

        report.run(
            reference_data=self.reference_data,
            current_data=current_data,
            column_mapping=self.column_mapping,
        )

        # Extract results
        results = report.as_dict()

        # Check for significant drift
        dataset_drift = results['metrics'][0]['result']['dataset_drift']
        drift_share = results['metrics'][0]['result']['drift_share']

        return {
            'timestamp': datetime.utcnow().isoformat(),
            'dataset_drift_detected': dataset_drift,
            'drift_share': drift_share,
            'drifted_columns': self._get_drifted_columns(results),
            'data_quality_issues': self._get_quality_issues(results),
            'text_drift': self._get_text_drift(results),
        }

    def _get_drifted_columns(self, results: Dict) -> List[str]:
        """Extract columns with detected drift."""
        drifted = []
        for metric in results['metrics']:
            if metric['metric'] == 'ColumnDriftMetric':
                if metric['result']['drift_detected']:
                    drifted.append(metric['result']['column_name'])
        return drifted

    def _get_quality_issues(self, results: Dict) -> Dict[str, Any]:
        """Extract data quality issues."""
        quality_metrics = {}
        for metric in results['metrics']:
            if 'DataQuality' in metric['metric']:
                quality_metrics[metric['metric']] = metric['result']
        return quality_metrics

    def _get_text_drift(self, results: Dict) -> Dict[str, Any]:
        """Extract text-specific drift metrics."""
        text_drift = {}
        for metric in results['metrics']:
            if 'Text' in metric['metric']:
                text_drift[metric['metric']] = metric['result']
        return text_drift

    async def monitor_production(
        self,
        batch_size: int = 1000,
        interval_hours: int = 1,
    ):
        """Continuously monitor production data for drift.

        Args:
            batch_size: Number of samples per batch
            interval_hours: Monitoring interval in hours
        """
        while True:
            # Fetch recent production data
            current_data = await self._fetch_production_data(
                batch_size=batch_size,
                hours=interval_hours,
            )

            # Detect drift
            drift_results = self.detect_data_drift(current_data)

            # Alert if drift detected
            if drift_results['dataset_drift_detected']:
                await self._send_drift_alert(drift_results)

            # Log results
            logger.info(
                "Drift detection completed",
                extra=drift_results
            )

            # Wait for next interval
            await asyncio.sleep(interval_hours * 3600)

    async def _send_drift_alert(self, drift_results: Dict[str, Any]):
        """Send alert when drift is detected."""
        # Implementation depends on alert system (Slack, PagerDuty, etc.)
        pass

    async def _fetch_production_data(
        self,
        batch_size: int,
        hours: int,
    ) -> pd.DataFrame:
        """Fetch recent production data from database."""
        # Implementation depends on data storage
        pass
```

### 5.3 RAGAS Evaluation Monitoring

**Continuous Evaluation** (`app/services/monitoring/ragas_monitor.py`):
```python
"""RAGAS metrics monitoring for RAG quality."""
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_relevancy,
    context_recall,
)
from datasets import Dataset
import pandas as pd
from prometheus_client import Gauge
from typing import List, Dict, Any


# Define Prometheus metrics
ragas_faithfulness_score = Gauge(
    'ragas_faithfulness_score',
    'RAGAS faithfulness metric',
)
ragas_answer_relevancy_score = Gauge(
    'ragas_answer_relevancy_score',
    'RAGAS answer relevancy metric',
)
ragas_context_relevancy_score = Gauge(
    'ragas_context_relevancy_score',
    'RAGAS context relevancy metric',
)


class RAGASMonitor:
    """Monitor RAG quality using RAGAS metrics."""

    def __init__(self):
        self.metrics = [
            faithfulness,
            answer_relevancy,
            context_relevancy,
            context_recall,
        ]

    async def evaluate_batch(
        self,
        questions: List[str],
        answers: List[str],
        contexts: List[List[str]],
        ground_truths: List[str],
    ) -> Dict[str, float]:
        """Evaluate batch of RAG outputs.

        Args:
            questions: User queries
            answers: Generated answers
            contexts: Retrieved contexts
            ground_truths: Reference answers

        Returns:
            RAGAS metric scores
        """
        # Create dataset
        data = {
            'question': questions,
            'answer': answers,
            'contexts': contexts,
            'ground_truth': ground_truths,
        }
        dataset = Dataset.from_dict(data)

        # Evaluate
        results = evaluate(
            dataset,
            metrics=self.metrics,
        )

        # Update Prometheus metrics
        ragas_faithfulness_score.set(results['faithfulness'])
        ragas_answer_relevancy_score.set(results['answer_relevancy'])
        ragas_context_relevancy_score.set(results['context_relevancy'])

        return results

    async def monitor_production(
        self,
        sample_rate: float = 0.1,
        min_samples: int = 50,
    ):
        """Monitor production RAG quality.

        Args:
            sample_rate: Fraction of queries to evaluate
            min_samples: Minimum samples before evaluation
        """
        buffer = []

        async for query_result in self._stream_production_queries():
            # Sample queries
            if random.random() < sample_rate:
                buffer.append(query_result)

            # Evaluate when buffer is full
            if len(buffer) >= min_samples:
                await self._evaluate_and_alert(buffer)
                buffer = []
```

### 5.4 Evidently Integration with Prometheus

**Metrics Exporter** (`app/services/monitoring/evidently_exporter.py`):
```python
"""Export Evidently metrics to Prometheus."""
from prometheus_client import Gauge
from app.services.monitoring.drift_detector import DriftDetector


# Define metrics
data_drift_score = Gauge(
    'data_drift_score',
    'Data drift score from Evidently',
    ['feature']
)

data_quality_score = Gauge(
    'data_quality_score',
    'Data quality score',
    ['metric']
)


async def export_evidently_metrics():
    """Export Evidently metrics to Prometheus."""
    detector = DriftDetector(
        reference_data_path='data/reference/baseline.parquet'
    )

    while True:
        # Fetch current data
        current_data = await fetch_recent_data(hours=1)

        # Detect drift
        results = detector.detect_data_drift(current_data)

        # Export to Prometheus
        data_drift_score.labels(feature='overall').set(
            results['drift_share']
        )

        for column in results['drifted_columns']:
            data_drift_score.labels(feature=column).set(1.0)

        # Wait for next interval
        await asyncio.sleep(3600)  # 1 hour
```

---

## 6. Deployment

### 6.1 Helm Deployment

**Deploy Observability Stack**:
```bash
# Add Helm repos
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Deploy Prometheus
helm install prometheus prometheus-community/kube-prometheus-stack \
  --namespace monitoring \
  --create-namespace \
  --values kubernetes/helm/monitoring/prometheus/values.yaml

# Deploy Tempo
helm install tempo grafana/tempo \
  --namespace monitoring \
  --values kubernetes/helm/monitoring/tempo/values.yaml

# Deploy Loki
helm install loki grafana/loki-stack \
  --namespace monitoring \
  --values kubernetes/helm/monitoring/loki/values.yaml

# Access Grafana
kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80
```

### 6.2 Import Dashboards

```bash
# Import dashboards to Grafana
kubectl create configmap grafana-dashboards \
  --from-file=observability/grafana/dashboards/ \
  --namespace=monitoring

# Restart Grafana
kubectl rollout restart deployment/prometheus-grafana -n monitoring
```

---

## 7. Integration Testing

### 7.1 Observability Tests

**Test Metrics Collection** (`tests/integration/test_observability.py`):
```python
"""Test observability stack integration."""
import pytest
import httpx
from prometheus_client.parser import text_string_to_metric_families


class TestObservability:
    """Test observability integration."""

    @pytest.mark.asyncio
    async def test_metrics_endpoint_accessible(self):
        """Test metrics endpoint returns data."""
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/metrics")

            assert response.status_code == 200
            assert "http_requests_total" in response.text

    @pytest.mark.asyncio
    async def test_metrics_recorded(self):
        """Test metrics are recorded after request."""
        async with httpx.AsyncClient() as client:
            # Make request
            await client.post("http://localhost:8000/api/v1/query", json={"query": "test"})

            # Check metrics
            response = await client.get("http://localhost:8000/metrics")
            metrics = list(text_string_to_metric_families(response.text))

            # Find http_requests_total metric
            request_metric = next(
                (m for m in metrics if m.name == "http_requests_total"),
                None
            )

            assert request_metric is not None
            assert any(s.value > 0 for s in request_metric.samples)

    @pytest.mark.asyncio
    async def test_tracing_context_propagation(self):
        """Test trace context is propagated."""
        async with httpx.AsyncClient() as client:
            # Make request with trace header
            response = await client.post(
                "http://localhost:8000/api/v1/query",
                json={"query": "test"},
                headers={"traceparent": "00-abc123-def456-01"}
            )

            assert response.status_code == 200
            # Verify trace ID in logs/traces

    @pytest.mark.asyncio
    async def test_structured_logging(self, caplog):
        """Test logs are structured JSON."""
        import json

        # Trigger log
        logger.info("test message", extra={"key": "value"})

        # Verify JSON structure
        log_record = caplog.records[0]
        log_json = json.loads(log_record.getMessage())

        assert "timestamp" in log_json
        assert "level" in log_json
        assert "message" in log_json
```

---

## 8. Cost Analysis

**Monthly Cost Breakdown** ($300 budget):
```
Prometheus:             Included in GKE
Grafana:                Open source (free)
Tempo:                  Storage only
  └─ GCS (traces):      $10/month (~100GB)
Loki:                   Storage only
  └─ GCS (logs):        $15/month (~150GB)
Evidently:              Open source (free)
Alert Manager:          Included

Total Observability:    $25/month
Remaining for App:      $275/month
```

---

## 9. Next Steps

1. **Deploy Monitoring Stack**:
   ```bash
   helmfile --environment production apply
   ```

2. **Configure Alerts**:
   ```bash
   kubectl apply -f observability/prometheus/rules.yaml
   ```

3. **Import Dashboards**:
   ```bash
   ./scripts/import_dashboards.sh
   ```

4. **Setup Drift Monitoring**:
   ```bash
   python -m app.services.monitoring.drift_detector
   ```

---

**Document Status**: ✅ Ready for Implementation
**Last Updated**: 2025-10-22
**Next Review**: After MLOps Stack Deployment
