# IntelliRAG Observability Implementation Plan

**Date**: 2025-11-06
**Project**: IntelliRAG
**Scope**: Complete observability stack implementation with Grafana dashboards, deployment documentation, integration tests, and best practices

## Executive Summary

This plan outlines the implementation of a comprehensive observability solution for the IntelliRAG project. The system already has basic OpenTelemetry tracing, structured logging with trace correlation, and Prometheus metrics instrumentation. This plan extends these capabilities with Grafana dashboards, deployment manifests, integration tests, and documentation.

## Current State Analysis

### Existing Components
- **Tracing**: OpenTelemetry with Jaeger exporter (`app/core/tracing.py`)
- **Logging**: Structured JSON logging with trace correlation (`app/core/logging.py`)
- **Metrics**: Comprehensive Prometheus metrics (`app/api/middleware/metrics.py`)
  - Query classification metrics
  - RAG pipeline performance metrics
  - Document ingestion metrics
  - HTTP request metrics
  - GPU utilization metrics

### Gaps to Address
1. No Grafana dashboard configurations
2. Missing Kubernetes deployment manifests for observability stack
3. No integration tests for observability
4. Lack of operational documentation

---

## Task 1: Create Grafana Dashboard JSON Configurations

### Objective
Design and implement comprehensive Grafana dashboards for monitoring the IntelliRAG system across different operational aspects.

### File Structure
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

### Dashboard 1: IntelliRAG Overview (`intellirag-overview.json`)

**Purpose**: High-level system health and KPIs

**Key Panels**:
1. **Request Rate** (Graph)
   - Query: `rate(http_requests_total[5m])`
   - Breakdown by endpoint and status code

2. **P95/P99 Latency** (Stat)
   - Query: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m]))`

3. **Active Ingestion Jobs** (Gauge)
   - Query: `ingestion_jobs_active`

4. **Query Classification Distribution** (Pie Chart)
   - Query: `sum by(query_type) (query_classification_total)`

5. **Error Rate** (Graph)
   - Query: `rate(http_requests_total{status_code=~"5.."}[5m])`

**JSON Template Structure**:
```json
{
  "dashboard": {
    "title": "IntelliRAG Overview",
    "uid": "intellirag-overview",
    "tags": ["intellirag", "overview"],
    "timezone": "browser",
    "refresh": "30s",
    "time": {
      "from": "now-6h",
      "to": "now"
    },
    "panels": [
      {
        "id": 1,
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "type": "graph",
        "title": "Request Rate",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}} {{status_code}}"
          }
        ]
      }
      // Additional panels...
    ]
  }
}
```

### Dashboard 2: Query Performance (`query-performance.json`)

**Purpose**: Detailed RAG query performance monitoring

**Key Panels**:
1. **Query Classification Confidence** (Heatmap)
   - Query: `query_classification_confidence_bucket`

2. **RAG Stage Duration** (Bar Gauge)
   - Query: `rag_query_duration_seconds` by stage

3. **Retrieved Documents Distribution** (Histogram)
   - Query: `rag_retrieval_results_bucket`

4. **Routing Decisions** (Time Series)
   - Query: `rate(query_router_decisions_total[5m])`

5. **Embedding Cache Hit Rate** (Stat)
   - Query: `rate(embedding_cache_hits_total{hit="true"}[5m]) / rate(embedding_cache_hits_total[5m])`

### Dashboard 3: Ingestion Pipeline (`ingestion-pipeline.json`)

**Purpose**: Document ingestion monitoring

**Key Panels**:
1. **Ingestion Jobs by Status** (Stacked Graph)
   - Query: `rate(ingestion_jobs_total[5m])` by status

2. **File Upload Size Distribution** (Heatmap)
   - Query: `file_upload_size_bytes_bucket`

3. **Processing Stage Duration** (Table)
   - Query: `document_processing_stage_duration_seconds` by stage

4. **Chunks Created per Document** (Bar Chart)
   - Query: `ingestion_chunks_created_sum / ingestion_chunks_created_count`

5. **Ingestion Errors** (Alert List)
   - Query: `increase(ingestion_errors_total[5m])`

### Dashboard 4: LLM Metrics (`llm-metrics.json`)

**Purpose**: LLM/vLLM performance and cost monitoring

**Key Panels**:
1. **Token Usage** (Counter)
   - Query: `sum(llm_token_count)` by type

2. **GPU Utilization** (Gauge)
   - Query: `gpu_utilization_percent`

3. **vLLM Throughput** (Graph)
   - Query: Custom vLLM metrics from OpenMetrics endpoint

4. **Model Latency P95** (Stat)
   - Query: vLLM generation latency metrics

5. **Cost Estimation** (Calculated Field)
   - Based on token counts and pricing

### Dashboard 5: Infrastructure (`infrastructure.json`)

**Purpose**: System resources and Kubernetes monitoring

**Key Panels**:
1. **Pod CPU/Memory Usage** (Graph)
2. **Vector DB Operations** (Counter)
3. **Network I/O** (Graph)
4. **Persistent Volume Usage** (Stat)
5. **Container Restart Count** (Table)

---

## Task 2: Write Deployment Documentation for Observability Stack

### File Structure
```
docs/deployment/
├── observability-deployment-guide.md
├── observability-configuration.md
└── troubleshooting-observability.md

kubernetes/
├── observability/
│   ├── namespace.yaml
│   ├── jaeger/
│   │   ├── values.yaml
│   │   └── helmfile.yaml
│   ├── loki/
│   │   ├── values.yaml
│   │   └── helmfile.yaml
│   ├── prometheus/
│   │   ├── values.yaml
│   │   └── helmfile.yaml
│   ├── grafana/
│   │   ├── values.yaml
│   │   └── helmfile.yaml
│   └── helmfile.yaml (root orchestrator)
```

### Main Deployment Guide (`observability-deployment-guide.md`)

**Content Structure**:
1. **Prerequisites**
   - Kubernetes cluster (1.28+)
   - Helm 3.12+
   - kubectl configured
   - Storage provisioner for PVCs

2. **Architecture Overview**
   - Component diagram
   - Data flow between services
   - Port mappings

3. **Step-by-Step Installation**
   ```bash
   # 1. Create namespace
   kubectl create namespace observability

   # 2. Add Helm repositories
   helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
   helm repo add grafana https://grafana.github.io/helm-charts
   helm repo add jaegertracing https://jaegertracing.github.io/helm-charts
   helm repo update

   # 3. Install using Helmfile
   cd kubernetes/observability
   helmfile sync
   ```

4. **Configuration Parameters**
   - Resource limits/requests
   - Retention policies
   - Ingress settings
   - Authentication setup

### Kubernetes Manifests

#### Namespace (`namespace.yaml`)
```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: observability
  labels:
    name: observability
    monitoring: "true"
```

#### Jaeger Helmfile (`jaeger/helmfile.yaml`)
```yaml
repositories:
  - name: jaegertracing
    url: https://jaegertracing.github.io/helm-charts

releases:
  - name: jaeger
    namespace: observability
    chart: jaegertracing/jaeger
    version: 0.71.0
    values:
      - values.yaml
```

#### Jaeger Values (`jaeger/values.yaml`)
```yaml
provisionDataStore:
  cassandra: false
  elasticsearch: true
  kafka: false

storage:
  type: elasticsearch
  elasticsearch:
    host: elasticsearch-master
    port: 9200

agent:
  enabled: true
  daemonset:
    hostPort: 6831

collector:
  service:
    zipkin:
      port: 9411
  resources:
    limits:
      memory: 1Gi
    requests:
      memory: 512Mi
      cpu: 250m

query:
  enabled: true
  ingress:
    enabled: true
    annotations:
      kubernetes.io/ingress.class: nginx
    hosts:
      - jaeger.intellirag.local
```

#### Loki Stack Values (`loki/values.yaml`)
```yaml
loki:
  auth_enabled: false
  storage:
    type: filesystem
  limits_config:
    retention_period: 168h
  schema_config:
    configs:
      - from: "2024-01-01"
        store: boltdb-shipper
        object_store: filesystem
        schema: v11
        index:
          prefix: index_
          period: 24h

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
        - labels:
            trace_id:
            span_id:
```

#### Prometheus Values (`prometheus/values.yaml`)
```yaml
prometheus:
  prometheusSpec:
    retention: 30d
    storageSpec:
      volumeClaimTemplate:
        spec:
          accessModes: ["ReadWriteOnce"]
          resources:
            requests:
              storage: 50Gi
    serviceMonitorSelectorNilUsesHelmValues: false
    podMonitorSelectorNilUsesHelmValues: false
    additionalScrapeConfigs:
      - job_name: 'intellirag-metrics'
        static_configs:
          - targets:
            - 'intellirag-service.default:8000'
        metrics_path: '/metrics'
      - job_name: 'vllm-metrics'
        static_configs:
          - targets:
            - 'vllm-service.default:8000'
        metrics_path: '/metrics'

grafana:
  enabled: false  # We'll deploy separately
```

#### Grafana Values (`grafana/values.yaml`)
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
        url: http://prometheus-kube-prometheus-prometheus:9090
        access: proxy
        isDefault: true
      - name: Loki
        type: loki
        url: http://loki:3100
        access: proxy
        jsonData:
          derivedFields:
            - datasourceName: Jaeger
              matcherRegex: "trace_id=(\\w+)"
              name: trace_id
              url: '$${__value.raw}'
      - name: Jaeger
        type: jaeger
        url: http://jaeger-query:16686
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
        updateIntervalSeconds: 10
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
  annotations:
    kubernetes.io/ingress.class: nginx
  hosts:
    - grafana.intellirag.local
```

#### Root Helmfile (`observability/helmfile.yaml`)
```yaml
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

---

## Task 3: Add Integration Tests for End-to-End Observability

### Test Structure
```
tests/integration/observability/
├── test_trace_correlation.py
├── test_metrics_collection.py
├── test_log_aggregation.py
├── test_dashboard_queries.py
└── conftest.py
```

### Core Test File (`test_trace_correlation.py`)

```python
"""Integration tests for end-to-end observability.

Tests that traces, metrics, and logs are properly correlated
and collected across the entire system.
"""

import pytest
import asyncio
import httpx
import json
from opentelemetry import trace
from prometheus_client.parser import text_string_to_metric_families
from typing import Dict, Any
import time


class TestObservabilityIntegration:
    """Test suite for observability integration."""

    @pytest.mark.asyncio
    async def test_trace_propagation_through_pipeline(self, test_client):
        """Test that traces propagate through the entire RAG pipeline."""
        # Submit a query that triggers RAG pipeline
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

        # Query Jaeger for the trace
        jaeger_response = await self._query_jaeger(trace_id)
        assert jaeger_response is not None

        # Verify expected spans exist
        spans = jaeger_response["data"][0]["spans"]
        span_operations = [span["operationName"] for span in spans]

        expected_operations = [
            "POST /api/v1/query",
            "query_classification",
            "embedding_generation",
            "vector_search",
            "llm_generation"
        ]

        for operation in expected_operations:
            assert operation in span_operations

    @pytest.mark.asyncio
    async def test_metrics_recorded_for_requests(self, test_client):
        """Test that Prometheus metrics are properly recorded."""
        # Get baseline metrics
        metrics_before = await self._get_metrics(test_client)

        # Make several requests
        for _ in range(5):
            await test_client.post(
                "/api/v1/query",
                json={"query": "Test query"}
            )

        # Wait for metrics to be updated
        await asyncio.sleep(1)

        # Get updated metrics
        metrics_after = await self._get_metrics(test_client)

        # Verify metrics increased
        assert self._get_metric_value(
            metrics_after,
            "http_requests_total"
        ) > self._get_metric_value(
            metrics_before,
            "http_requests_total"
        )

        # Verify query classification metrics
        assert self._get_metric_value(
            metrics_after,
            "query_classification_total"
        ) >= 5

    @pytest.mark.asyncio
    async def test_logs_contain_trace_context(self, test_client, log_capture):
        """Test that logs include trace_id and span_id."""
        # Make a request
        response = await test_client.post(
            "/api/v1/query",
            json={"query": "Test for logging"}
        )

        trace_id = response.headers.get("X-Trace-Id")

        # Check captured logs
        logs = log_capture.get_logs()

        # Find logs with this trace_id
        trace_logs = [
            log for log in logs
            if log.get("trace_id") == trace_id
        ]

        assert len(trace_logs) > 0

        # Verify log structure
        for log in trace_logs:
            assert "trace_id" in log
            assert "span_id" in log
            assert "timestamp" in log
            assert "level" in log
            assert "message" in log

    @pytest.mark.asyncio
    async def test_error_tracking_across_stack(self, test_client):
        """Test that errors are properly tracked in traces, metrics, and logs."""
        # Trigger an error (e.g., invalid file type)
        response = await test_client.post(
            "/api/v1/upload",
            files={"file": ("test.exe", b"invalid", "application/x-msdownload")}
        )

        assert response.status_code == 400

        # Get trace ID
        trace_id = response.headers.get("X-Trace-Id")

        # Check metrics for error count
        metrics = await self._get_metrics(test_client)
        error_count = self._get_metric_value(
            metrics,
            "http_requests_total",
            labels={"status_code": "400"}
        )
        assert error_count > 0

        # Check Jaeger for error spans
        jaeger_response = await self._query_jaeger(trace_id)
        spans = jaeger_response["data"][0]["spans"]

        # Find spans with errors
        error_spans = [
            span for span in spans
            if any(tag["key"] == "error" and tag["value"] == True
                   for tag in span.get("tags", []))
        ]
        assert len(error_spans) > 0

    @pytest.mark.asyncio
    async def test_ingestion_pipeline_observability(self, test_client):
        """Test observability for document ingestion pipeline."""
        # Upload a document
        with open("tests/fixtures/sample.pdf", "rb") as f:
            response = await test_client.post(
                "/api/v1/upload",
                files={"file": ("sample.pdf", f, "application/pdf")}
            )

        assert response.status_code == 200
        job_id = response.json()["job_id"]

        # Trigger ingestion
        response = await test_client.post(
            f"/api/v1/ingest/{job_id}"
        )

        # Wait for processing
        await asyncio.sleep(5)

        # Check metrics
        metrics = await self._get_metrics(test_client)

        # Verify ingestion metrics
        assert self._get_metric_value(
            metrics,
            "ingestion_jobs_total"
        ) > 0

        assert self._get_metric_value(
            metrics,
            "file_upload_size_bytes_count"
        ) > 0

        assert self._get_metric_value(
            metrics,
            "ingestion_chunks_created_sum"
        ) > 0

    @pytest.mark.asyncio
    async def test_gpu_metrics_collection(self, test_client):
        """Test that GPU metrics are collected when using vLLM."""
        # Make LLM request
        await test_client.post(
            "/api/v1/query",
            json={"query": "Generate a long response"}
        )

        # Get metrics
        metrics = await self._get_metrics(test_client)

        # Check GPU utilization metric exists
        gpu_util = self._get_metric_value(
            metrics,
            "gpu_utilization_percent"
        )

        assert gpu_util is not None
        assert 0 <= gpu_util <= 100

    # Helper methods
    async def _get_metrics(self, client) -> Dict[str, Any]:
        """Get Prometheus metrics from /metrics endpoint."""
        response = await client.get("/metrics")
        metrics = {}

        for family in text_string_to_metric_families(response.text):
            metrics[family.name] = family

        return metrics

    def _get_metric_value(self, metrics, name, labels=None):
        """Extract specific metric value."""
        if name not in metrics:
            return 0

        family = metrics[name]
        for sample in family.samples:
            if labels is None or all(
                sample.labels.get(k) == v
                for k, v in labels.items()
            ):
                return sample.value

        return 0

    async def _query_jaeger(self, trace_id):
        """Query Jaeger for a specific trace."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"http://jaeger-query:16686/api/traces/{trace_id}"
            )
            if response.status_code == 200:
                return response.json()
            return None
```

### Metrics Collection Test (`test_metrics_collection.py`)

```python
"""Test that all defined metrics are properly collected."""

import pytest
import asyncio
from prometheus_client.parser import text_string_to_metric_families


class TestMetricsCollection:
    """Test suite for metrics collection."""

    @pytest.mark.asyncio
    async def test_all_metrics_exported(self, test_client):
        """Test that all defined metrics are exported."""
        response = await test_client.get("/metrics")
        assert response.status_code == 200

        # Parse metrics
        metric_names = set()
        for family in text_string_to_metric_families(response.text):
            metric_names.add(family.name)

        # Expected metrics from metrics.py
        expected_metrics = [
            "query_classification_total",
            "query_classification_confidence",
            "query_classification_duration_seconds",
            "query_router_decisions_total",
            "rag_query_duration_seconds",
            "rag_retrieval_results",
            "llm_token_count",
            "http_requests_total",
            "http_request_duration_seconds",
            "vector_db_operations_total",
            "embedding_cache_hits_total",
            "gpu_utilization_percent",
            "ingestion_jobs_total",
            "ingestion_jobs_active",
            "file_upload_duration_seconds",
            "file_upload_size_bytes",
            "document_processing_stage_duration_seconds",
            "ingestion_chunks_created",
            "ingestion_job_duration_seconds",
            "ingestion_errors_total"
        ]

        for metric in expected_metrics:
            assert metric in metric_names, f"Metric {metric} not exported"

    @pytest.mark.asyncio
    async def test_histogram_buckets_configured(self, test_client):
        """Test that histograms have proper bucket configurations."""
        response = await test_client.get("/metrics")

        for family in text_string_to_metric_families(response.text):
            if family.type == "histogram":
                # Check that buckets are defined
                bucket_samples = [
                    s for s in family.samples
                    if s.name.endswith("_bucket")
                ]
                assert len(bucket_samples) > 0, \
                    f"Histogram {family.name} has no buckets"
```

### Dashboard Query Test (`test_dashboard_queries.py`)

```python
"""Test that Grafana dashboard queries return data."""

import pytest
import httpx
import json


class TestDashboardQueries:
    """Test suite for validating dashboard queries."""

    @pytest.mark.asyncio
    async def test_dashboard_queries_return_data(self, grafana_client):
        """Test that dashboard queries return valid data."""
        dashboards = [
            "intellirag-overview",
            "query-performance",
            "ingestion-pipeline",
            "llm-metrics",
            "infrastructure"
        ]

        for dashboard_uid in dashboards:
            # Get dashboard
            dashboard = await grafana_client.get_dashboard(dashboard_uid)
            assert dashboard is not None

            # Test each panel query
            for panel in dashboard["panels"]:
                if "targets" in panel:
                    for target in panel["targets"]:
                        query = target.get("expr")
                        if query:
                            # Execute query
                            result = await grafana_client.query_prometheus(
                                query,
                                time.time()
                            )

                            # Verify result has data
                            assert result is not None
                            assert "data" in result
```

---

## Task 4: Document Best Practices for Using Observability Tools

### Documentation Structure
```
docs/guides/
├── observability-best-practices.md
├── debugging-with-traces.md
├── log-analysis-guide.md
├── metrics-alerting.md
└── troubleshooting-guide.md
```

### Main Best Practices Document (`observability-best-practices.md`)

```markdown
# IntelliRAG Observability Best Practices

## Overview

This guide provides best practices for using the IntelliRAG observability stack to monitor, debug, and optimize system performance.

## 1. Debugging Issues Using Traces

### Finding Slow Requests

1. **Identify slow endpoints in Grafana**:
   - Dashboard: Query Performance
   - Look for high P95/P99 latency

2. **Get trace ID from logs**:
   ```bash
   kubectl logs -n default deployment/intellirag-api | \
     jq '. | select(.duration_seconds > 2) | .trace_id'
   ```

3. **Analyze trace in Jaeger**:
   - Navigate to: http://jaeger.intellirag.local
   - Search by trace ID
   - Look for:
     - Long-running spans
     - Sequential operations that could be parallelized
     - Failed spans (red color)

### Tracing Across Services

- All services include trace context propagation
- Use `trace_id` to correlate:
  - API requests
  - Background jobs
  - Vector DB operations
  - LLM calls

### Example: Debug RAG Pipeline Latency

```python
# In your code, add custom spans for debugging
from opentelemetry import trace

tracer = trace.get_tracer(__name__)

with tracer.start_as_current_span("custom_operation") as span:
    span.set_attribute("document_count", len(documents))
    span.set_attribute("chunk_size", chunk_size)
    # Your code here
```

## 2. Useful Loki Queries for Log Analysis

### Find All Logs for a Trace
```logql
{app="intellirag"} |= "trace_id" |~ "YOUR_TRACE_ID"
```

### Find Errors in Ingestion Pipeline
```logql
{app="intellirag"} |= "ingestion" |= "ERROR"
```

### Track Specific User Requests
```logql
{app="intellirag"}
  |= "user_id"
  |= "USER_123"
  | json
  | line_format "{{.timestamp}} {{.message}}"
```

### Performance Analysis
```logql
{app="intellirag"}
  | json
  | duration_seconds > 2
  | line_format "{{.timestamp}} {{.endpoint}} {{.duration_seconds}}s"
```

### Aggregate Error Counts by Type
```logql
sum by (error_type) (
  rate({app="intellirag"} |= "ERROR" | json | __error__="" [5m])
)
```

## 3. Key Metrics to Monitor and Alert On

### Critical Alerts (Page immediately)

| Metric | Condition | Alert |
|--------|-----------|--------|
| `up{job="intellirag"}` | == 0 for 1m | Service Down |
| `rate(http_requests_total{status_code=~"5.."}[5m])` | > 0.05 | High Error Rate |
| `http_request_duration_seconds{quantile="0.99"}` | > 5s | High Latency |
| `gpu_utilization_percent` | > 95% for 10m | GPU Overload |

### Warning Alerts (Notify team)

| Metric | Condition | Alert |
|--------|-----------|-------|
| `ingestion_jobs_active` | > 100 | Queue Backlog |
| `embedding_cache_hits_total{hit="false"} / embedding_cache_hits_total` | > 0.5 | Low Cache Hit Rate |
| `vector_db_operations{operation="search"}` | P95 > 1s | Slow Vector Search |
| `rate(ingestion_errors_total[5m])` | > 0.01 | Ingestion Errors |

### Prometheus Alert Configuration

```yaml
groups:
  - name: intellirag_critical
    rules:
      - alert: ServiceDown
        expr: up{job="intellirag"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "IntelliRAG service is down"
          description: "{{ $labels.instance }} has been down for more than 1 minute"

      - alert: HighErrorRate
        expr: rate(http_requests_total{status_code=~"5.."}[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
```

## 4. Troubleshooting Guide

### Issue: Missing Traces

**Symptoms**: Requests complete but no traces in Jaeger

**Check**:
1. Verify Jaeger agent is running:
   ```bash
   kubectl get pods -n observability | grep jaeger-agent
   ```

2. Check agent connection in app logs:
   ```bash
   kubectl logs deployment/intellirag-api | grep "jaeger"
   ```

3. Verify environment variables:
   ```bash
   kubectl describe deployment intellirag-api | grep JAEGER
   ```

**Solution**:
- Ensure `JAEGER_AGENT_HOST` is set correctly
- Check network policies allow UDP 6831

### Issue: Metrics Not Updating

**Symptoms**: Grafana shows "No Data"

**Check**:
1. Verify Prometheus is scraping:
   ```
   http://prometheus:9090/targets
   ```

2. Check /metrics endpoint:
   ```bash
   curl http://intellirag-service:8000/metrics
   ```

3. Verify ServiceMonitor (if using Prometheus Operator):
   ```bash
   kubectl get servicemonitor -n default
   ```

### Issue: High Memory Usage

**Symptoms**: OOM kills, slow performance

**Analysis**:
1. Check memory metrics in Grafana
2. Review heap profiles
3. Analyze cache sizes

**Common Causes**:
- Large embedding cache
- Unbounded queues
- Memory leaks in async tasks

### Issue: Slow RAG Queries

**Debug Steps**:
1. Check query classification time
2. Analyze embedding generation duration
3. Review vector search performance
4. Examine LLM generation latency

**Optimization**:
- Enable embedding cache
- Optimize chunk size
- Use GPU for embeddings
- Implement query result caching

## 5. Performance Optimization Tips

### Using Metrics for Optimization

1. **Identify Bottlenecks**:
   - Use `rag_query_duration_seconds` by stage
   - Find slowest component

2. **Cache Analysis**:
   - Monitor `embedding_cache_hits_total`
   - Adjust cache size based on hit rate

3. **Batch Processing**:
   - Track `ingestion_chunks_created`
   - Optimize batch sizes

### Using Traces for Optimization

1. **Parallelization Opportunities**:
   - Look for sequential spans that could run in parallel
   - Example: Embedding multiple chunks simultaneously

2. **Resource Contention**:
   - Check span timings during high load
   - Identify resource bottlenecks

### Using Logs for Optimization

1. **Error Patterns**:
   - Aggregate errors by type
   - Fix most common errors first

2. **Performance Logs**:
   - Add timing logs for critical operations
   - Analyze patterns over time

## 6. Dashboard Usage Guide

### IntelliRAG Overview Dashboard
- **Purpose**: High-level system health
- **When to use**: Daily standup, incident response
- **Key metrics**: Request rate, error rate, latency

### Query Performance Dashboard
- **Purpose**: RAG pipeline optimization
- **When to use**: Performance tuning, capacity planning
- **Key metrics**: Stage duration, cache hit rate

### Ingestion Pipeline Dashboard
- **Purpose**: Document processing monitoring
- **When to use**: Batch job monitoring, troubleshooting failures
- **Key metrics**: Job status, processing time, chunk creation

### LLM Metrics Dashboard
- **Purpose**: Model performance and cost
- **When to use**: Cost optimization, model evaluation
- **Key metrics**: Token usage, GPU utilization, generation latency

### Infrastructure Dashboard
- **Purpose**: Resource utilization
- **When to use**: Capacity planning, cost optimization
- **Key metrics**: CPU/memory usage, network I/O, storage

## 7. Integrating with CI/CD

### Pre-deployment Checks

```yaml
- name: Load Test with Observability
  run: |
    # Run load test
    k6 run tests/load/scenario.js

    # Check error rate
    ERROR_RATE=$(curl -s http://prometheus:9090/api/v1/query \
      -d 'query=rate(http_requests_total{status_code=~"5.."}[5m])' \
      | jq '.data.result[0].value[1]')

    if (( $(echo "$ERROR_RATE > 0.01" | bc -l) )); then
      echo "Error rate too high: $ERROR_RATE"
      exit 1
    fi
```

### Post-deployment Verification

```bash
#!/bin/bash
# verify-deployment.sh

# Check all services are up
for service in api ingestion vectordb; do
  if ! kubectl get pods -l app=$service | grep -q Running; then
    echo "Service $service not running"
    exit 1
  fi
done

# Verify metrics endpoint
if ! curl -f http://intellirag:8000/metrics; then
  echo "Metrics endpoint not responding"
  exit 1
fi

# Check Jaeger connectivity
if ! nc -zv jaeger-agent 6831; then
  echo "Cannot connect to Jaeger agent"
  exit 1
fi
```

## 8. Security Considerations

### Secure Access to Observability Tools

1. **Authentication**:
   - Enable Grafana authentication
   - Use OAuth2/OIDC integration
   - Implement RBAC

2. **Network Policies**:
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: NetworkPolicy
   metadata:
     name: observability-access
   spec:
     podSelector:
       matchLabels:
         app: grafana
     ingress:
       - from:
         - namespaceSelector:
             matchLabels:
               name: ingress-nginx
   ```

3. **Data Retention**:
   - Set appropriate retention periods
   - Implement PII scrubbing in logs
   - Encrypt sensitive metrics

### Monitoring Security Events

- Track authentication failures
- Monitor suspicious query patterns
- Alert on privilege escalations
- Audit configuration changes

## 9. Cost Optimization

### Reduce Storage Costs

1. **Metrics Retention**:
   - Keep high-resolution data for 7 days
   - Downsample older data
   - Archive to object storage

2. **Log Filtering**:
   - Filter out debug logs in production
   - Implement sampling for high-volume logs
   - Use structured logging to reduce size

3. **Trace Sampling**:
   - Implement head-based sampling (e.g., 10%)
   - Use tail-based sampling for errors
   - Adjust sampling rate by endpoint

### Resource Optimization

1. **Right-size Components**:
   - Monitor actual usage
   - Adjust resource requests/limits
   - Use autoscaling where appropriate

2. **Optimize Queries**:
   - Cache dashboard queries
   - Use recording rules for complex queries
   - Limit query time ranges

## 10. Maintenance Tasks

### Daily
- Check alert status
- Review error logs
- Monitor resource usage

### Weekly
- Review dashboard performance
- Update alert thresholds
- Clean up old traces

### Monthly
- Review retention policies
- Optimize slow queries
- Update documentation
- Capacity planning review

### Quarterly
- Security audit
- Cost optimization review
- Tool version updates
- Disaster recovery testing
```

---

## Implementation Timeline

### Phase 1: Dashboard Creation (2 days)
1. Create dashboard JSON files
2. Test queries against existing metrics
3. Configure datasources
4. Validate visualizations

### Phase 2: Deployment Setup (2 days)
1. Create Kubernetes manifests
2. Configure Helm values
3. Write deployment documentation
4. Test deployment in dev environment

### Phase 3: Integration Testing (2 days)
1. Implement integration test suite
2. Add fixtures and helpers
3. Validate end-to-end flows
4. Document test coverage

### Phase 4: Documentation (1 day)
1. Write best practices guide
2. Create troubleshooting documentation
3. Add operational runbooks
4. Review and polish all docs

## Success Criteria

1. **Dashboards**:
   - All 5 dashboards created and functional
   - Queries return valid data
   - Visualizations are meaningful

2. **Deployment**:
   - One-command deployment with Helmfile
   - All components accessible
   - Proper resource allocation

3. **Testing**:
   - Integration tests pass with >80% coverage
   - Trace correlation verified
   - Metrics collection validated

4. **Documentation**:
   - Clear deployment instructions
   - Comprehensive troubleshooting guide
   - Actionable best practices

## Risk Mitigation

1. **Resource Constraints**:
   - Risk: Observability stack consuming too many resources
   - Mitigation: Implement resource limits and monitoring

2. **Data Volume**:
   - Risk: High cardinality metrics causing storage issues
   - Mitigation: Implement proper label design and retention policies

3. **Integration Complexity**:
   - Risk: Difficulty correlating traces, metrics, and logs
   - Mitigation: Standardize correlation IDs and test thoroughly

## TODO Checklist

- [ ] Create Grafana dashboard JSON configurations
  - [ ] IntelliRAG Overview dashboard
  - [ ] Query Performance dashboard
  - [ ] Ingestion Pipeline dashboard
  - [ ] LLM Metrics dashboard
  - [ ] Infrastructure dashboard
- [ ] Write deployment documentation for observability stack
  - [ ] Create Kubernetes manifests structure
  - [ ] Write Helm values files
  - [ ] Create Helmfile configuration
  - [ ] Document deployment process
- [ ] Add integration tests for end-to-end observability
  - [ ] Test trace correlation
  - [ ] Test metrics collection
  - [ ] Test log aggregation
  - [ ] Test dashboard queries
- [ ] Document best practices for observability tools
  - [ ] Write debugging guide
  - [ ] Create log analysis queries
  - [ ] Define alerting rules
  - [ ] Write troubleshooting guide