# IntelliRAG Observability Stack Implementation Plan

**Branch**: `feature/observability-stack`  
**Date**: 2025-11-06  
**Status**: Research Complete - Ready for Implementation  

---

## Executive Summary

This document provides a detailed, step-by-step implementation plan for deploying the complete observability stack for IntelliRAG, including Grafana dashboards, Kubernetes manifests, integration tests, and comprehensive documentation.

**Research Findings:**
- ✅ OpenTelemetry tracing fully implemented (app/core/tracing.py)
- ✅ Structured JSON logging with trace correlation (app/core/logging.py)
- ✅ 19+ Prometheus metrics defined and actively instrumented
- ✅ Metrics used across all services (orchestrator, classifier, RAG pipeline, LLM client, etc.)
- ⚠️ **Gap**: No Grafana dashboard JSON configurations
- ⚠️ **Gap**: No Kubernetes deployment manifests for observability stack
- ⚠️ **Gap**: Limited integration tests for end-to-end observability
- ⚠️ **Gap**: Missing operational documentation and best practices

---

## Current State Analysis

### Existing Metrics (from app/api/middleware/metrics.py)

#### Query Classification & Routing
```python
query_classification_total              # Counter: ['query_type']
query_classification_confidence         # Histogram: buckets=[0.5-1.0]
query_classification_duration_seconds   # Histogram: buckets=[0.01-2.0]
query_router_decisions_total           # Counter: ['decision']
```

#### RAG Pipeline
```python
rag_query_duration_seconds             # Histogram: ['stage'] (embedding, retrieval, generation)
rag_retrieval_results                  # Histogram: buckets=[0-50]
```

#### LLM & Inference
```python
llm_token_count                        # Counter: ['model', 'type'] (input/output)
gpu_utilization_percent                # Gauge: ['gpu_id']
```

#### HTTP & Infrastructure
```python
http_requests_total                    # Counter: ['method', 'endpoint', 'status_code']
http_request_duration_seconds          # Histogram: ['method', 'endpoint']
vector_db_operations_total             # Counter: ['operation', 'collection']
embedding_cache_hits_total             # Counter: ['hit']
```

#### Document Ingestion
```python
ingestion_jobs_total                   # Counter: ['status', 'file_type']
ingestion_jobs_active                  # Gauge: ['status']
file_upload_duration_seconds           # Histogram: ['file_type']
file_upload_size_bytes                 # Histogram: ['file_type']
document_processing_stage_duration_seconds  # Histogram: ['stage', 'file_type']
ingestion_chunks_created               # Histogram: ['file_type']
ingestion_job_duration_seconds         # Histogram: ['status', 'file_type']
ingestion_errors_total                 # Counter: ['error_type', 'stage']
```

### Test Pattern Analysis (tests/conftest.py)

**Existing Fixtures:**
- `fixtures_dir`: Returns path to test fixtures
- `mock_embedding_service`: Mock for EmbeddingService (avoids loading 560MB model)
- `mock_sentence_transformer`: Mock for SentenceTransformer model
- Sample content fixtures: `sample_text_content`, `sample_csv_content`

**Test Organization:**
- `tests/unit/`: Component-level tests with mocking
- `tests/integration/`: End-to-end tests (currently sparse)
- `tests/fixtures/`: Sample files (pdf, csv, txt, integration_data.py)

**Testing Tools:**
- pytest + pytest-asyncio (async testing)
- pytest-mock (mocking)
- pytest-cov (coverage >80% enforced)
- unittest.mock (Mock, AsyncMock)

---

## Implementation Plan

### Phase 1: Grafana Dashboard Creation (Days 1-2)

#### Task 1.1: Create Dashboard JSON Configurations

**Directory Structure to Create:**
```
observability/
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/
│   │   │   └── datasources.yaml
│   │   └── dashboards/
│   │       ├── dashboards.yaml
│   │       └── json/
│   │           ├── intellirag-overview.json
│   │           ├── query-performance.json
│   │           ├── ingestion-pipeline.json
│   │           ├── llm-metrics.json
│   │           └── infrastructure.json
│   └── alerts/
│       └── alerting-rules.yaml
```

**Implementation Order:**

1. **Start with Overview Dashboard** (intellirag-overview.json)
   - **Why first?** Provides immediate value, uses simplest metrics
   - **Panels (8 total):**
     1. Request Rate (Graph): `rate(http_requests_total[5m])`
     2. P95/P99 Latency (Stat): `histogram_quantile(0.95, ...)`
     3. Error Rate (Graph): `rate(http_requests_total{status_code=~"5.."}[5m])`
     4. Active Ingestion Jobs (Gauge): `ingestion_jobs_active`
     5. Query Classification Distribution (Pie): `sum by(query_type)(query_classification_total)`
     6. GPU Utilization (Gauge): `avg(gpu_utilization_percent)`
     7. Cache Hit Rate (Stat): `rate(embedding_cache_hits_total{hit="true"}[5m])`
     8. Vector DB Operations (Counter): `rate(vector_db_operations_total[5m])`
   - **Time to Complete**: 2-3 hours

2. **Query Performance Dashboard** (query-performance.json)
   - **Why second?** Core business logic, detailed RAG metrics
   - **Panels (7 total):**
     1. RAG Stage Duration (Stacked Graph): By embedding/retrieval/generation
     2. Query Classification Confidence (Heatmap): Bucket distribution
     3. Retrieved Documents Distribution (Histogram): Document counts
     4. Routing Decisions (Time Series): RAG vs Direct vs Multi-hop
     5. Embedding Cache Hit Rate (Stat): Real-time cache efficiency
     6. Classification Duration (Bar Gauge): Classification latency
     7. LLM Token Usage (Graph): Input vs Output tokens over time
   - **Time to Complete**: 3-4 hours

3. **Ingestion Pipeline Dashboard** (ingestion-pipeline.json)
   - **Why third?** Document processing monitoring
   - **Panels (6 total):**
     1. Ingestion Jobs by Status (Stacked Graph): Success/Failed/Pending
     2. File Upload Size Distribution (Heatmap): By file type
     3. Processing Stage Duration (Table): Load/Parse/Chunk/Embed
     4. Chunks Created per Document (Bar Chart): Average chunks by file type
     5. Ingestion Errors (Alert List): Recent errors by type/stage
     6. Active Jobs Counter (Stat): Current processing jobs
   - **Time to Complete**: 2-3 hours

4. **LLM Metrics Dashboard** (llm-metrics.json)
   - **Why fourth?** Model performance and cost tracking
   - **Panels (5 total):**
     1. Token Usage Over Time (Graph): Input/Output by model
     2. GPU Utilization (Gauge + History): Real-time + 24h trend
     3. LLM Request Rate (Graph): Requests per second
     4. Token Cost Estimation (Calculated Stat): Based on pricing
     5. Model Latency P95 (Stat): Generation latency
   - **Time to Complete**: 2-3 hours

5. **Infrastructure Dashboard** (infrastructure.json)
   - **Why last?** System-level monitoring (less critical initially)
   - **Panels (6 total):**
     1. Pod CPU/Memory Usage (Graph): Container resource usage
     2. Vector DB Operations (Counter): Search/Insert/Update/Delete
     3. Network I/O (Graph): Ingress/Egress bandwidth
     4. Persistent Volume Usage (Stat): Storage consumption
     5. Container Restart Count (Table): Pod health
     6. HTTP Response Codes (Heatmap): Status code distribution
   - **Note:** Some metrics may require additional exporters (node-exporter, kube-state-metrics)
   - **Time to Complete**: 2-3 hours

**Dashboard Configuration Standards:**
```json
{
  "dashboard": {
    "title": "IntelliRAG <Name>",
    "uid": "intellirag-<slug>",
    "tags": ["intellirag", "<category>"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {"from": "now-6h", "to": "now"},
    "templating": {
      "list": [
        {
          "name": "datasource",
          "type": "datasource",
          "query": "prometheus"
        }
      ]
    }
  }
}
```

#### Task 1.2: Create Datasource Configuration

**File**: `observability/grafana/provisioning/datasources/datasources.yaml`

```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    url: http://prometheus-kube-prometheus-prometheus.observability:9090
    access: proxy
    isDefault: true
    jsonData:
      timeInterval: "15s"
      
  - name: Loki
    type: loki
    url: http://loki.observability:3100
    access: proxy
    jsonData:
      derivedFields:
        - datasourceName: Jaeger
          matcherRegex: "trace_id=(\\w+)"
          name: TraceID
          url: '$${__value.raw}'
          
  - name: Jaeger
    type: jaeger
    url: http://jaeger-query.observability:16686
    access: proxy
```

#### Task 1.3: Create Dashboard Provider Configuration

**File**: `observability/grafana/provisioning/dashboards/dashboards.yaml`

```yaml
apiVersion: 1
providers:
  - name: 'intellirag'
    orgId: 1
    folder: 'IntelliRAG'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /var/lib/grafana/dashboards/intellirag
```

#### Task 1.4: Create Alert Rules

**File**: `observability/grafana/alerts/alerting-rules.yaml`

```yaml
groups:
  - name: intellirag-critical
    interval: 30s
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status_code=~"5.."}[5m]))
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99,
            rate(http_request_duration_seconds_bucket[5m])
          ) > 5.0
        for: 5m
        labels:
          severity: warning
          
      - alert: GPUOverload
        expr: avg(gpu_utilization_percent) > 95
        for: 10m
        labels:
          severity: critical
```

**Testing Strategy:**
- Manual verification: Deploy to local Grafana instance
- Validate queries return data using Prometheus
- Check panel rendering and layout
- Verify datasource connectivity

---

### Phase 2: Kubernetes Deployment Manifests (Days 2-3)

#### Task 2.1: Create Directory Structure

```bash
# Create complete directory structure
mkdir -p kubernetes/observability/{namespace,jaeger,loki,prometheus,grafana}
mkdir -p kubernetes/observability/grafana/{dashboards,provisioning}
mkdir -p docs/deployment/observability
```

#### Task 2.2: Namespace Configuration

**File**: `kubernetes/observability/namespace.yaml`

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: observability
  labels:
    name: observability
    monitoring: "true"
```

#### Task 2.3: Jaeger Deployment

**Files to Create:**
1. `kubernetes/observability/jaeger/helmfile.yaml`
2. `kubernetes/observability/jaeger/values.yaml`

**values.yaml** (Key configurations):
```yaml
provisionDataStore:
  cassandra: false
  elasticsearch: true  # Or use in-memory for dev

storage:
  type: elasticsearch
  elasticsearch:
    host: elasticsearch-master
    port: 9200

agent:
  enabled: true
  daemonset:
    hostPort: 6831
    useHostNetwork: true

collector:
  service:
    zipkin:
      port: 9411
  resources:
    limits:
      memory: 1Gi
      cpu: 1000m
    requests:
      memory: 512Mi
      cpu: 250m

query:
  enabled: true
  ingress:
    enabled: true
    hosts:
      - jaeger.intellirag.local
```

#### Task 2.4: Loki Deployment

**Files to Create:**
1. `kubernetes/observability/loki/helmfile.yaml`
2. `kubernetes/observability/loki/values.yaml`

**values.yaml** (Key configurations):
```yaml
loki:
  auth_enabled: false
  
  storage:
    type: filesystem  # Use GCS in production
    
  limits_config:
    retention_period: 168h  # 7 days
    ingestion_rate_mb: 10
    
  compactor:
    enabled: true
    retention_enabled: true

promtail:
  enabled: true
  config:
    clients:
      - url: http://loki:3100/loki/api/v1/push
    
    snippets:
      pipelineStages:
        - docker: {}
        - json:
            expressions:
              trace_id: trace_id
              span_id: span_id
              level: level
              message: message
        - labels:
            trace_id:
            level:
```

#### Task 2.5: Prometheus Deployment

**Files to Create:**
1. `kubernetes/observability/prometheus/helmfile.yaml`
2. `kubernetes/observability/prometheus/values.yaml`

**values.yaml** (Key configurations):
```yaml
prometheus:
  prometheusSpec:
    retention: 15d
    retentionSize: 45GB
    scrapeInterval: 15s
    
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    
    resources:
      requests:
        cpu: 500m
        memory: 2Gi
      limits:
        cpu: 2000m
        memory: 4Gi
    
    additionalScrapeConfigs:
      - job_name: 'intellirag-fastapi'
        kubernetes_sd_configs:
          - role: pod
            namespaces:
              names:
                - default
        relabel_configs:
          - source_labels: [__meta_kubernetes_pod_label_app]
            action: keep
            regex: intellirag
        metrics_path: '/metrics'
        
      - job_name: 'vllm-inference'
        static_configs:
          - targets: ['vllm-service.default:8000']
        metrics_path: '/metrics'

grafana:
  enabled: false  # We'll deploy separately
```

#### Task 2.6: Grafana Deployment

**Files to Create:**
1. `kubernetes/observability/grafana/helmfile.yaml`
2. `kubernetes/observability/grafana/values.yaml`

**values.yaml** (Key configurations):
```yaml
persistence:
  enabled: true
  size: 10Gi

adminPassword: ${GRAFANA_ADMIN_PASSWORD}

datasources:
  datasources.yaml:
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        url: http://prometheus-kube-prometheus-prometheus.observability:9090
        access: proxy
        isDefault: true
      - name: Loki
        type: loki
        url: http://loki.observability:3100
        access: proxy
      - name: Jaeger
        type: jaeger
        url: http://jaeger-query.observability:16686
        access: proxy

dashboardProviders:
  dashboardproviders.yaml:
    apiVersion: 1
    providers:
      - name: 'intellirag'
        orgId: 1
        folder: 'IntelliRAG'
        type: file
        disableDeletion: false
        options:
          path: /var/lib/grafana/dashboards

dashboards:
  intellirag:
    overview:
      file: dashboards/intellirag-overview.json
    query-performance:
      file: dashboards/query-performance.json
    ingestion:
      file: dashboards/ingestion-pipeline.json
    llm:
      file: dashboards/llm-metrics.json
    infrastructure:
      file: dashboards/infrastructure.json

ingress:
  enabled: true
  hosts:
    - grafana.intellirag.local
```

#### Task 2.7: Root Helmfile Orchestrator

**File**: `kubernetes/observability/helmfile.yaml`

```yaml
repositories:
  - name: prometheus-community
    url: https://prometheus-community.github.io/helm-charts
  - name: grafana
    url: https://grafana.github.io/helm-charts
  - name: jaegertracing
    url: https://jaegertracing.github.io/helm-charts

helmfiles:
  - path: jaeger/helmfile.yaml
  - path: loki/helmfile.yaml
  - path: prometheus/helmfile.yaml
  - path: grafana/helmfile.yaml

hooks:
  - events: ["presync"]
    command: "kubectl"
    args:
      - "apply"
      - "-f"
      - "namespace.yaml"
```

#### Task 2.8: Documentation

**Files to Create:**
1. `docs/deployment/observability/observability-deployment-guide.md`
2. `docs/deployment/observability/observability-configuration.md`
3. `docs/deployment/observability/troubleshooting-observability.md`

**observability-deployment-guide.md** (Structure):
```markdown
# IntelliRAG Observability Stack Deployment Guide

## Prerequisites
- Kubernetes cluster (1.28+)
- Helm 3.12+
- Helmfile installed
- kubectl configured

## Quick Start

### 1. Install Helmfile
\```bash
# Install Helmfile (if not already installed)
wget https://github.com/helmfile/helmfile/releases/download/v0.159.0/helmfile_0.159.0_linux_amd64.tar.gz
tar -xzf helmfile_0.159.0_linux_amd64.tar.gz
sudo mv helmfile /usr/local/bin/
\```

### 2. Add Helm Repositories
\```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
helm repo update
\```

### 3. Set Environment Variables
\```bash
export GRAFANA_ADMIN_PASSWORD="your-secure-password"
\```

### 4. Deploy Observability Stack
\```bash
cd kubernetes/observability
helmfile sync
\```

### 5. Verify Deployment
\```bash
kubectl get pods -n observability
kubectl get svc -n observability
\```

### 6. Access Services

**Grafana:**
\```bash
kubectl port-forward -n observability svc/grafana 3000:80
# Access: http://localhost:3000
# Username: admin
# Password: $GRAFANA_ADMIN_PASSWORD
\```

**Prometheus:**
\```bash
kubectl port-forward -n observability svc/prometheus-kube-prometheus-prometheus 9090:9090
# Access: http://localhost:9090
\```

**Jaeger:**
\```bash
kubectl port-forward -n observability svc/jaeger-query 16686:16686
# Access: http://localhost:16686
\```

## Component Details
[Details for each component...]

## Configuration Options
[Customization options...]

## Troubleshooting
[Common issues and solutions...]
```

---

### Phase 3: Integration Tests (Days 3-4)

#### Task 3.1: Create Test Directory Structure

```bash
mkdir -p tests/integration/observability
touch tests/integration/observability/__init__.py
```

#### Task 3.2: Update conftest.py with Observability Fixtures

**File**: `tests/conftest.py` (additions)

```python
# ========== OBSERVABILITY TEST FIXTURES ==========

import httpx
from prometheus_client.parser import text_string_to_metric_families
from typing import Dict, Any
import json


@pytest.fixture
async def test_client():
    """Async HTTP client for testing API endpoints."""
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        yield client


@pytest.fixture
def prometheus_metrics_parser():
    """Helper to parse Prometheus metrics."""
    def parse_metrics(metrics_text: str) -> Dict[str, Any]:
        metrics = {}
        for family in text_string_to_metric_families(metrics_text):
            metrics[family.name] = {
                'type': family.type,
                'samples': family.samples,
                'documentation': family.documentation
            }
        return metrics
    return parse_metrics


@pytest.fixture
def log_capture():
    """Fixture to capture structured logs during tests."""
    class LogCapture:
        def __init__(self):
            self.logs = []
            
        def capture(self, record):
            """Capture log record as JSON."""
            try:
                log_dict = json.loads(record.getMessage())
                self.logs.append(log_dict)
            except json.JSONDecodeError:
                pass
        
        def get_logs(self, level=None, trace_id=None):
            """Get captured logs with optional filtering."""
            filtered = self.logs
            if level:
                filtered = [log for log in filtered if log.get('level') == level]
            if trace_id:
                filtered = [log for log in filtered if log.get('trace_id') == trace_id]
            return filtered
    
    return LogCapture()


@pytest.fixture
def mock_jaeger_client():
    """Mock Jaeger client for trace verification."""
    client = Mock()
    
    async def mock_query_trace(trace_id):
        return {
            'data': [{
                'traceID': trace_id,
                'spans': [
                    {
                        'operationName': 'POST /api/v1/query',
                        'spanID': 'abc123',
                        'tags': []
                    }
                ]
            }]
        }
    
    client.query_trace = AsyncMock(side_effect=mock_query_trace)
    return client


@pytest.fixture
def sample_metrics_response():
    """Sample Prometheus metrics response for testing."""
    return """
# HELP http_requests_total Total HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="POST",endpoint="/api/v1/query",status_code="200"} 5.0

# HELP query_classification_total Total query classifications
# TYPE query_classification_total counter
query_classification_total{query_type="rag"} 3.0
query_classification_total{query_type="direct"} 2.0

# HELP gpu_utilization_percent GPU utilization percentage
# TYPE gpu_utilization_percent gauge
gpu_utilization_percent{gpu_id="0"} 75.5
"""
```

#### Task 3.3: Mocked Unit Tests

**File**: `tests/unit/test_metrics_collection.py`

```python
"""Unit tests for metrics collection (mocked)."""

import pytest
from unittest.mock import Mock, patch
from prometheus_client import Counter, Histogram, Gauge


class TestMetricsCollection:
    """Test suite for metrics collection."""
    
    def test_all_metrics_defined(self):
        """Test that all required metrics are defined."""
        from app.api.middleware import metrics
        
        expected_metrics = [
            'query_classification_total',
            'query_classification_confidence',
            'query_classification_duration_seconds',
            'query_router_decisions_total',
            'rag_query_duration_seconds',
            'rag_retrieval_results',
            'llm_token_count',
            'http_requests_total',
            'http_request_duration_seconds',
            'vector_db_operations_total',
            'embedding_cache_hits_total',
            'gpu_utilization_percent',
            'ingestion_jobs_total',
            'ingestion_jobs_active',
            'file_upload_duration_seconds',
            'file_upload_size_bytes',
            'document_processing_stage_duration_seconds',
            'ingestion_chunks_created',
            'ingestion_job_duration_seconds',
            'ingestion_errors_total'
        ]
        
        for metric_name in expected_metrics:
            assert hasattr(metrics, metric_name), \
                f"Metric {metric_name} not defined"
    
    def test_counter_increment(self):
        """Test Counter metric increments correctly."""
        from app.api.middleware.metrics import query_classification_total
        
        initial_value = query_classification_total.labels(query_type='rag')._value._value
        query_classification_total.labels(query_type='rag').inc()
        new_value = query_classification_total.labels(query_type='rag')._value._value
        
        assert new_value > initial_value
    
    def test_histogram_observe(self):
        """Test Histogram metric observes values."""
        from app.api.middleware.metrics import query_classification_duration_seconds
        
        query_classification_duration_seconds.observe(0.5)
        query_classification_duration_seconds.observe(1.2)
        
        # Verify observations were recorded
        assert query_classification_duration_seconds._sum._value > 0
    
    def test_gauge_set(self):
        """Test Gauge metric sets values."""
        from app.api.middleware.metrics import gpu_utilization_percent
        
        gpu_utilization_percent.labels(gpu_id='0').set(75.5)
        value = gpu_utilization_percent.labels(gpu_id='0')._value._value
        
        assert value == 75.5
```

**File**: `tests/unit/test_structured_logging.py`

```python
"""Unit tests for structured logging (mocked)."""

import pytest
import json
import logging
from unittest.mock import Mock, patch


class TestStructuredLogging:
    """Test suite for structured logging."""
    
    def test_json_formatter_output(self):
        """Test that logs are formatted as JSON."""
        from app.core.logging import StructuredJSONFormatter
        
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_dict = json.loads(formatted)
        
        assert 'timestamp' in log_dict
        assert 'level' in log_dict
        assert 'message' in log_dict
        assert log_dict['message'] == 'Test message'
    
    @patch('app.core.logging.trace.get_current_span')
    def test_trace_context_in_logs(self, mock_get_span):
        """Test that trace context is included in logs."""
        from app.core.logging import StructuredJSONFormatter
        
        # Mock span context
        mock_span = Mock()
        mock_span_context = Mock()
        mock_span_context.is_valid = True
        mock_span_context.trace_id = 12345
        mock_span_context.span_id = 67890
        mock_span.get_span_context.return_value = mock_span_context
        mock_get_span.return_value = mock_span
        
        formatter = StructuredJSONFormatter()
        record = logging.LogRecord(
            name='test',
            level=logging.INFO,
            pathname='',
            lineno=0,
            msg='Test with trace',
            args=(),
            exc_info=None
        )
        
        formatted = formatter.format(record)
        log_dict = json.loads(formatted)
        
        assert 'trace_id' in log_dict
        assert 'span_id' in log_dict
```

#### Task 3.4: Integration Tests (Real Services)

**File**: `tests/integration/observability/test_trace_correlation.py`

```python
"""Integration tests for end-to-end trace correlation.

These tests require real services running (marked with pytest.mark.integration).
"""

import pytest
import asyncio
import httpx
from opentelemetry import trace


@pytest.mark.integration
class TestTraceCorrelation:
    """Test suite for trace correlation across services."""
    
    @pytest.mark.asyncio
    async def test_trace_propagation_through_query_pipeline(self, test_client):
        """Test that traces propagate through query endpoint."""
        # Make query request
        response = await test_client.post(
            "/api/v1/query",
            json={"query": "What is machine learning?"}
        )
        
        assert response.status_code == 200
        
        # Extract trace ID from response headers
        trace_id = response.headers.get("X-Trace-Id")
        assert trace_id is not None
        
        # Wait for spans to be exported
        await asyncio.sleep(2)
        
        # Query Jaeger for the trace (requires Jaeger running)
        async with httpx.AsyncClient() as client:
            jaeger_response = await client.get(
                f"http://localhost:16686/api/traces/{trace_id}"
            )
            
            if jaeger_response.status_code == 200:
                trace_data = jaeger_response.json()
                spans = trace_data["data"][0]["spans"]
                span_operations = [span["operationName"] for span in spans]
                
                # Verify expected spans exist
                expected_operations = [
                    "POST /api/v1/query",
                    "query_classification",
                    "embedding_generation",
                    "vector_search",
                    "llm_generation"
                ]
                
                for operation in expected_operations:
                    assert any(operation in op for op in span_operations), \
                        f"Missing span operation: {operation}"
    
    @pytest.mark.asyncio
    async def test_logs_contain_trace_context(self, test_client, log_capture):
        """Test that logs include trace_id and span_id."""
        # Make a request
        response = await test_client.post(
            "/api/v1/query",
            json={"query": "Test for logging"}
        )
        
        trace_id = response.headers.get("X-Trace-Id")
        assert trace_id is not None
        
        # Check captured logs
        logs = log_capture.get_logs()
        trace_logs = [log for log in logs if log.get('trace_id') == trace_id]
        
        assert len(trace_logs) > 0
        
        for log in trace_logs:
            assert 'trace_id' in log
            assert 'span_id' in log
            assert 'timestamp' in log
```

**File**: `tests/integration/observability/test_metrics_collection.py`

```python
"""Integration tests for Prometheus metrics collection."""

import pytest
import asyncio
from prometheus_client.parser import text_string_to_metric_families


@pytest.mark.integration
class TestMetricsCollection:
    """Test suite for metrics collection."""
    
    @pytest.mark.asyncio
    async def test_metrics_endpoint_accessible(self, test_client):
        """Test that /metrics endpoint returns data."""
        response = await test_client.get("/metrics")
        
        assert response.status_code == 200
        assert "text/plain" in response.headers.get("content-type", "")
        
        # Verify it's valid Prometheus format
        metrics = list(text_string_to_metric_families(response.text))
        assert len(metrics) > 0
    
    @pytest.mark.asyncio
    async def test_all_metrics_exported(self, test_client, prometheus_metrics_parser):
        """Test that all defined metrics are exported."""
        response = await test_client.get("/metrics")
        metrics = prometheus_metrics_parser(response.text)
        
        expected_metrics = [
            "query_classification_total",
            "query_classification_confidence",
            "rag_query_duration_seconds",
            "http_requests_total",
            "gpu_utilization_percent",
            "ingestion_jobs_total"
        ]
        
        for metric in expected_metrics:
            assert metric in metrics, f"Metric {metric} not exported"
    
    @pytest.mark.asyncio
    async def test_metrics_update_after_requests(self, test_client, prometheus_metrics_parser):
        """Test that metrics increment after making requests."""
        # Get baseline metrics
        response = await test_client.get("/metrics")
        metrics_before = prometheus_metrics_parser(response.text)
        
        # Make several requests
        for _ in range(5):
            await test_client.post(
                "/api/v1/query",
                json={"query": "Test query"}
            )
        
        # Wait for metrics update
        await asyncio.sleep(1)
        
        # Get updated metrics
        response = await test_client.get("/metrics")
        metrics_after = prometheus_metrics_parser(response.text)
        
        # Verify http_requests_total increased
        http_metric_before = sum(
            s.value for s in metrics_before['http_requests_total']['samples']
            if s.name == 'http_requests_total'
        )
        http_metric_after = sum(
            s.value for s in metrics_after['http_requests_total']['samples']
            if s.name == 'http_requests_total'
        )
        
        assert http_metric_after > http_metric_before
```

**File**: `tests/integration/observability/test_dashboard_queries.py`

```python
"""Integration tests for Grafana dashboard queries."""

import pytest
import httpx
import json


@pytest.mark.integration
class TestDashboardQueries:
    """Test suite for validating dashboard queries."""
    
    @pytest.mark.asyncio
    async def test_prometheus_queries_return_data(self):
        """Test that dashboard Prometheus queries return valid data."""
        # Requires Prometheus running
        prometheus_url = "http://localhost:9090"
        
        # Test queries from dashboards
        queries = [
            'rate(http_requests_total[5m])',
            'histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))',
            'sum by(query_type)(query_classification_total)',
            'avg(gpu_utilization_percent)'
        ]
        
        async with httpx.AsyncClient() as client:
            for query in queries:
                response = await client.get(
                    f"{prometheus_url}/api/v1/query",
                    params={"query": query}
                )
                
                assert response.status_code == 200, \
                    f"Query failed: {query}"
                
                data = response.json()
                assert data['status'] == 'success', \
                    f"Query returned error: {query}"
                
                # Data may be empty if no metrics yet, but should be valid format
                assert 'data' in data
                assert 'result' in data['data']
```

#### Task 3.5: Test Configuration

**File**: `pytest.ini` (additions)

```ini
[pytest]
markers =
    unit: Unit tests with mocked dependencies
    integration: Integration tests with real services (Qdrant, model, Prometheus, Jaeger)
    observability: Tests for observability stack (traces, metrics, logs)
    slow: Tests that take >10 seconds

# Timeout settings
timeout = 300
timeout_method = "thread"

# Async settings
asyncio_mode = auto
```

---

### Phase 4: Documentation (Day 4)

#### Task 4.1: Best Practices Guide

**File**: `docs/guides/observability-best-practices.md`

**Content Structure:**
```markdown
# IntelliRAG Observability Best Practices

## 1. Debugging with Traces

### Finding Slow Requests
[Step-by-step guide using Jaeger...]

### Tracing Example Code
\```python
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("document_count", len(documents))
    # Your code here
\```

## 2. Log Analysis with Loki

### Common LogQL Queries

**Find all errors:**
\```logql
{app="intellirag"} |= "ERROR" | json
\```

**Trace logs by ID:**
\```logql
{app="intellirag"} | json | trace_id = "YOUR_TRACE_ID"
\```

**Performance analysis:**
\```logql
{app="intellirag"} | json | duration_seconds > 2.0
\```

## 3. Metrics to Monitor

### Critical Alerts
| Metric | Threshold | Action |
|--------|-----------|--------|
| `up{job="intellirag"}` | == 0 for 1m | Page on-call |
| Error rate | > 5% for 5m | Investigate immediately |
| P99 latency | > 5s for 5m | Performance review |
| GPU utilization | > 95% for 10m | Scale or optimize |

## 4. Troubleshooting Guide
[Common issues and solutions...]

## 5. Performance Optimization
[Using observability data for optimization...]
```

#### Task 4.2: Troubleshooting Guide

**File**: `docs/deployment/observability/troubleshooting-observability.md`

```markdown
# Observability Stack Troubleshooting

## Common Issues

### Issue: Missing Traces in Jaeger

**Symptoms**: Requests complete but no traces visible

**Check:**
1. Verify Jaeger agent is running:
   \```bash
   kubectl get pods -n observability | grep jaeger-agent
   \```

2. Check agent logs:
   \```bash
   kubectl logs -n observability daemonset/jaeger-agent
   \```

3. Verify environment variables in application:
   \```bash
   kubectl describe deployment intellirag-api | grep JAEGER
   \```

**Solution**:
- Ensure `JAEGER_AGENT_HOST` points to correct service
- Check network policies allow UDP 6831
- Verify OpenTelemetry exporter configuration

### Issue: Metrics Not Updating

**Symptoms**: Grafana shows "No Data"

**Check:**
1. Verify Prometheus is scraping:
   \```bash
   kubectl port-forward -n observability svc/prometheus 9090:9090
   # Visit: http://localhost:9090/targets
   \```

2. Check /metrics endpoint:
   \```bash
   curl http://intellirag-service:8000/metrics
   \```

3. Verify ServiceMonitor:
   \```bash
   kubectl get servicemonitor -n default
   \```

### Issue: High Memory Usage

[Detailed troubleshooting steps...]

### Issue: Slow Dashboard Queries

[Query optimization tips...]
```

#### Task 4.3: Configuration Reference

**File**: `docs/deployment/observability/observability-configuration.md`

```markdown
# Observability Stack Configuration Reference

## Prometheus Configuration

### Scrape Interval
Default: 15s
Recommended: 15-30s for production

### Retention Period
Default: 15 days
Configure: `prometheus.prometheusSpec.retention`

### Storage
Default: 50Gi PVC
Configure: `prometheus.prometheusSpec.storageSpec.volumeClaimTemplate`

## Loki Configuration

### Retention Period
Default: 168h (7 days)
Configure: `loki.limits_config.retention_period`

### Ingestion Limits
[Rate limits and configuration...]

## Grafana Configuration

### Data Sources
[Configuration details...]

### Dashboard Provisioning
[How to add custom dashboards...]
```

---

## Implementation Order & Dependencies

### Recommended Sequence

```
Day 1:
├── Morning: Task 1.1 (Overview Dashboard) 
├── Afternoon: Task 1.1 (Query Performance Dashboard)
└── Evening: Task 1.1 (Ingestion Dashboard)

Day 2:
├── Morning: Task 1.1 (LLM + Infrastructure Dashboards)
├── Afternoon: Task 1.2-1.4 (Datasources, Providers, Alerts)
├── Evening: Task 2.1-2.3 (Namespace, Directory Structure, Jaeger)

Day 3:
├── Morning: Task 2.4-2.6 (Loki, Prometheus, Grafana manifests)
├── Afternoon: Task 2.7-2.8 (Root Helmfile, Deployment docs)
├── Evening: Task 3.1-3.2 (Test directory, conftest updates)

Day 4:
├── Morning: Task 3.3-3.4 (Unit and integration tests)
├── Afternoon: Task 3.5, 4.1-4.2 (Test config, documentation)
└── Evening: Task 4.3 (Final documentation, review)
```

### Dependency Graph

```
Dashboards (Task 1)
    ↓
├→ Datasource Config (Task 1.2)
├→ Provider Config (Task 1.3)
└→ Alert Rules (Task 1.4)
    ↓
Namespace (Task 2.1)
    ↓
├→ Jaeger (Task 2.3)
├→ Loki (Task 2.4)
├→ Prometheus (Task 2.5)
└→ Grafana (Task 2.6)
    ↓
Root Helmfile (Task 2.7)
    ↓
Deployment Docs (Task 2.8)
    ↓
├→ Test Infrastructure (Task 3.1-3.2)
├→ Unit Tests (Task 3.3)
├→ Integration Tests (Task 3.4)
└→ Test Config (Task 3.5)
    ↓
Best Practices Docs (Task 4.1-4.3)
```

---

## Testing Strategy

### Unit Tests (Mocked - CI-Friendly)

**Purpose**: Fast, isolated testing without external dependencies

**Coverage:**
- Metrics definition and type checking
- Log formatting and structure
- Trace context propagation (mocked)
- Configuration validation

**Run Command:**
```bash
pytest tests/unit/test_metrics_collection.py -v
pytest tests/unit/test_structured_logging.py -v
```

**Characteristics:**
- Fast execution (<1s per test)
- No external services required
- High coverage of code paths
- Run in CI/CD pipeline

### Integration Tests (Real Services)

**Purpose**: Validate end-to-end observability flows

**Coverage:**
- Actual trace collection in Jaeger
- Metrics scraping by Prometheus
- Log aggregation in Loki
- Dashboard query validation

**Run Command:**
```bash
# Start required services first
docker-compose -f docker-compose.observability.yml up -d

# Run integration tests
pytest tests/integration/observability/ -v -m integration
```

**Characteristics:**
- Slower execution (2-5s per test)
- Requires running services
- Tests real integrations
- Optional in CI (mark with pytest.mark.integration)

### Manual Testing Checklist

```markdown
- [ ] Deploy observability stack with helmfile
- [ ] Verify all pods are running
- [ ] Access Grafana and check datasources
- [ ] Load each dashboard and verify panels render
- [ ] Make API requests and verify metrics appear
- [ ] Check traces appear in Jaeger
- [ ] Verify logs in Loki with LogQL queries
- [ ] Test alert rules trigger correctly
- [ ] Validate dashboard provisioning
- [ ] Test ingress/port-forwarding access
```

---

## Potential Challenges & Mitigations

### Challenge 1: Dashboard Query Complexity

**Issue**: Complex PromQL queries may not return data initially

**Mitigation:**
- Start with simple queries (e.g., `http_requests_total`)
- Progressively add complexity
- Use Prometheus UI to test queries before adding to dashboards
- Include query comments in dashboard JSON

### Challenge 2: Jaeger Storage

**Issue**: In-memory storage loses traces on restart

**Mitigation:**
- Use Elasticsearch backend for production
- Start with in-memory for development
- Document storage backend options clearly
- Provide migration path

### Challenge 3: Test Environment Dependencies

**Issue**: Integration tests require multiple services running

**Mitigation:**
- Create docker-compose.observability.yml for local testing
- Mark integration tests with pytest markers
- Provide clear setup instructions
- Use mocked tests for CI/CD

### Challenge 4: Dashboard Provisioning

**Issue**: Dashboard JSON format is verbose and hard to maintain

**Mitigation:**
- Use Grafana UI to create dashboards initially
- Export JSON for version control
- Document export/import process
- Use dashboard provisioning for automation

### Challenge 5: Metrics Cardinality

**Issue**: Too many label combinations can cause high memory usage

**Mitigation:**
- Limit label values (e.g., don't include user IDs)
- Use histogram buckets appropriately
- Monitor Prometheus memory usage
- Document label design best practices

---

## Success Criteria

### Phase 1: Dashboards
- ✅ All 5 dashboards created as JSON files
- ✅ Queries tested and return valid data
- ✅ Datasources configured
- ✅ Alert rules defined

### Phase 2: Deployment
- ✅ Complete Kubernetes manifests in place
- ✅ Helmfile orchestrates all components
- ✅ One-command deployment works
- ✅ All services accessible via port-forward or ingress
- ✅ Documentation covers installation and configuration

### Phase 3: Testing
- ✅ Unit tests pass with >80% coverage
- ✅ Integration tests validate end-to-end flows
- ✅ Trace correlation verified
- ✅ Metrics collection validated
- ✅ Log aggregation tested

### Phase 4: Documentation
- ✅ Clear deployment guide
- ✅ Comprehensive troubleshooting section
- ✅ Best practices documented
- ✅ Example queries provided
- ✅ Configuration reference complete

---

## Post-Implementation Tasks

### Immediate (Week 1)
1. Deploy to local development environment
2. Validate all dashboards with real traffic
3. Test alert rules trigger correctly
4. Document any deployment issues encountered

### Short-term (Month 1)
1. Optimize dashboard queries for performance
2. Add custom metrics based on usage patterns
3. Implement trace sampling if needed
4. Set up actual alert channels (Slack, PagerDuty)

### Long-term (Month 3)
1. Migrate to production storage backends (GCS)
2. Implement data retention policies
3. Add cost monitoring dashboards
4. Conduct observability training for team

---

## Appendix

### A. Existing Metrics Quick Reference

```python
# Classification & Routing (4 metrics)
query_classification_total
query_classification_confidence
query_classification_duration_seconds
query_router_decisions_total

# RAG Pipeline (2 metrics)
rag_query_duration_seconds
rag_retrieval_results

# LLM & GPU (2 metrics)
llm_token_count
gpu_utilization_percent

# HTTP & Infrastructure (3 metrics)
http_requests_total
http_request_duration_seconds
vector_db_operations_total
embedding_cache_hits_total

# Ingestion Pipeline (8 metrics)
ingestion_jobs_total
ingestion_jobs_active
file_upload_duration_seconds
file_upload_size_bytes
document_processing_stage_duration_seconds
ingestion_chunks_created
ingestion_job_duration_seconds
ingestion_errors_total
```

### B. Useful Commands

```bash
# Check all metrics exported
curl http://localhost:8000/metrics | grep -E "^# TYPE"

# Port-forward to Prometheus
kubectl port-forward -n observability svc/prometheus 9090:9090

# Port-forward to Grafana
kubectl port-forward -n observability svc/grafana 3000:80

# Port-forward to Jaeger
kubectl port-forward -n observability svc/jaeger-query 16686:16686

# Check Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets'

# Query Prometheus
curl -G http://localhost:9090/api/v1/query \
  --data-urlencode 'query=http_requests_total'

# View Loki logs
curl -G http://localhost:3100/loki/api/v1/query_range \
  --data-urlencode 'query={app="intellirag"}' \
  | jq '.data.result'
```

### C. File Checklist

**Observability Directory:**
```
observability/
├── grafana/
│   ├── provisioning/
│   │   ├── datasources/datasources.yaml
│   │   └── dashboards/dashboards.yaml
│   └── dashboards/json/
│       ├── intellirag-overview.json
│       ├── query-performance.json
│       ├── ingestion-pipeline.json
│       ├── llm-metrics.json
│       └── infrastructure.json
```

**Kubernetes Directory:**
```
kubernetes/observability/
├── namespace.yaml
├── helmfile.yaml (root)
├── jaeger/
│   ├── helmfile.yaml
│   └── values.yaml
├── loki/
│   ├── helmfile.yaml
│   └── values.yaml
├── prometheus/
│   ├── helmfile.yaml
│   └── values.yaml
└── grafana/
    ├── helmfile.yaml
    └── values.yaml
```

**Test Directory:**
```
tests/integration/observability/
├── __init__.py
├── test_trace_correlation.py
├── test_metrics_collection.py
├── test_log_aggregation.py
└── test_dashboard_queries.py
```

**Documentation:**
```
docs/deployment/observability/
├── observability-deployment-guide.md
├── observability-configuration.md
└── troubleshooting-observability.md

docs/guides/
└── observability-best-practices.md
```

---

**Document Version**: 1.0  
**Last Updated**: 2025-11-06  
**Status**: Ready for Implementation  
**Estimated Total Time**: 4 days (32 hours)  

