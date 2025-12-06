# Day 2 Load Testing - Implementation Plan

**Created**: 2025-11-23
**Author**: IntelliRAG Planning Team
**Duration**: 5-6 hours implementation
**Output**: Reusable load testing framework with automated reporting

---

## Executive Summary

This plan implements a comprehensive, reusable load testing framework for Day 2 of Phase 3. Instead of direct CLI commands, we'll create modular, parameterized scripts that can be easily configured and rerun for future testing needs. The framework includes bash scripts for hey-based tests, enhanced Python locust tests, automated report generation, and a main orchestration script.

---

## Objectives

1. Create reusable, parameterized load testing scripts
2. Implement automated report generation in markdown format
3. Build a comprehensive test orchestration system
4. Enable easy configuration changes without script modification
5. Provide proper error handling and logging
6. Generate professional load test reports automatically

---

## Architecture Overview

```
tests/load/
├── config/
│   ├── test-config.yaml         # Main configuration file
│   ├── vllm-config.yaml        # vLLM-specific test configs
│   ├── embedding-config.yaml   # Embedding service configs
│   └── rag-config.yaml         # RAG endpoint configs
├── scripts/
│   ├── install-tools.sh        # Install hey and locust
│   ├── run-hey-test.sh         # Generic hey test runner
│   ├── test-vllm.sh           # vLLM-specific tests
│   ├── test-embedding.sh      # Embedding-specific tests
│   ├── test-endpoints.sh      # Endpoint availability checks
│   └── generate-report.py     # Report generation utility
├── locust/
│   ├── locustfile.py          # Main locust test file
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── rag_tasks.py       # RAG-specific tasks
│   │   ├── health_tasks.py    # Health check tasks
│   │   └── stress_tasks.py    # Stress test scenarios
│   └── users/
│       ├── __init__.py
│       ├── normal_user.py     # Normal load user behavior
│       ├── stress_user.py     # Stress test user behavior
│       └── spike_user.py      # Spike test user behavior
├── reports/
│   └── templates/
│       ├── vllm-report.md.j2   # vLLM report template
│       ├── embedding-report.md.j2 # Embedding report template
│       └── e2e-report.md.j2    # E2E report template
├── results/                    # Test results storage
│   └── .gitkeep
└── run-all-tests.sh           # Main orchestration script

scripts/load-testing/           # Alternative location in main scripts directory
├── [same structure as above]
```

---

## Implementation Plan

### Phase 1: Setup and Configuration (30 minutes)

#### Task 1.1: Create Directory Structure
```bash
# Create test load directory structure
mkdir -p tests/load/{config,scripts,locust/{tasks,users},reports/templates,results}

# Alternative: Create in scripts directory
mkdir -p scripts/load-testing/{config,tools,reports/templates,results}
```

#### Task 1.2: Create Configuration Files

**tests/load/config/test-config.yaml**:
```yaml
# Global test configuration
global:
  report_dir: "./reports"
  results_dir: "./results"
  timestamp_format: "%Y%m%d-%H%M%S"

endpoints:
  vllm:
    external: "https://llm.blockchainradar.xyz"
    local: "http://localhost:8000"
    health: "/health"
    chat: "/v1/chat/completions"
  embedding:
    external: "https://embed.blockchainradar.xyz"
    local: "http://localhost:8001"
    health: "/health"
    vectorize: "/vectorize"
  app:
    gke: "http://localhost:8000"  # via port-forward
    health: "/ready"
    query: "/api/v1/query"

test_profiles:
  baseline:
    concurrent: 50
    requests: 1000
    duration: null
  stress:
    concurrent: 100
    requests: 2000
    duration: null
  breaking:
    concurrent_levels: [100, 150, 200, 250, 300]
    requests_per_level: 500
    duration: null
  sustained:
    concurrent: 75
    requests: null
    duration: "5m"
```

**tests/load/config/vllm-config.yaml**:
```yaml
# vLLM-specific test configurations
model: "Qwen/Qwen3-0.6B"
test_prompts:
  short:
    - "Hello"
    - "Hi there"
    - "Test"
  medium:
    - "Explain AI in 30 words"
    - "What is machine learning?"
    - "Describe neural networks briefly"
  long:
    - "Explain transformers architecture in detail"
    - "Describe the history of artificial intelligence"
    - "What are the applications of deep learning?"

max_tokens:
  short: 20
  medium: 50
  long: 200

thresholds:
  success_rate_min: 99.0  # %
  p95_latency_max: 500    # ms
  p99_latency_max: 1000   # ms
```

### Phase 2: Bash Script Implementation (1.5 hours)

#### Task 2.1: Install Tools Script

**tests/load/scripts/install-tools.sh**:
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LOG_FILE="${SCRIPT_DIR}/../results/install-$(date +%Y%m%d-%H%M%S).log"

echo "=== Load Testing Tools Installation ==="
echo "Log file: ${LOG_FILE}"
echo ""

# Function to check if command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Install hey
install_hey() {
    echo -n "Checking hey... "
    if command_exists hey; then
        echo "✅ Already installed ($(hey -version 2>&1 | head -1))"
    else
        echo "📦 Installing..."
        if command_exists go; then
            go install github.com/rakyll/hey@latest >> "${LOG_FILE}" 2>&1
            export PATH=$PATH:$(go env GOPATH)/bin
            echo 'export PATH=$PATH:$(go env GOPATH)/bin' >> ~/.bashrc
            echo "✅ Installed successfully"
        else
            echo "❌ Go is not installed. Please install Go first."
            exit 1
        fi
    fi
}

# Install locust
install_locust() {
    echo -n "Checking locust... "
    if command_exists locust; then
        echo "✅ Already installed ($(locust --version 2>&1))"
    else
        echo "📦 Installing..."
        pip install locust >> "${LOG_FILE}" 2>&1
        echo "✅ Installed successfully"
    fi
}

# Install Python dependencies
install_python_deps() {
    echo -n "Installing Python dependencies... "
    pip install pyyaml jinja2 pandas matplotlib >> "${LOG_FILE}" 2>&1
    echo "✅ Done"
}

# Main installation
install_hey
install_locust
install_python_deps

echo ""
echo "=== Installation Complete ==="
```

#### Task 2.2: Generic Hey Test Runner

**tests/load/scripts/run-hey-test.sh**:
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CONFIG_DIR="${SCRIPT_DIR}/../config"
RESULTS_DIR="${SCRIPT_DIR}/../results"

# Default values
ENDPOINT=""
METHOD="POST"
CONCURRENT=50
REQUESTS=1000
DURATION=""
DATA=""
HEADERS=""
OUTPUT_FILE=""
TEST_NAME="hey-test"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -e|--endpoint) ENDPOINT="$2"; shift; shift ;;
        -m|--method) METHOD="$2"; shift; shift ;;
        -c|--concurrent) CONCURRENT="$2"; shift; shift ;;
        -n|--requests) REQUESTS="$2"; shift; shift ;;
        -z|--duration) DURATION="$2"; shift; shift ;;
        -d|--data) DATA="$2"; shift; shift ;;
        -H|--header) HEADERS="${HEADERS} -H \"$2\""; shift; shift ;;
        -o|--output) OUTPUT_FILE="$2"; shift; shift ;;
        -t|--test-name) TEST_NAME="$2"; shift; shift ;;
        -h|--help)
            echo "Usage: $0 [options]"
            echo "Options:"
            echo "  -e, --endpoint URL      Target endpoint"
            echo "  -m, --method METHOD     HTTP method (default: POST)"
            echo "  -c, --concurrent N      Concurrent connections (default: 50)"
            echo "  -n, --requests N        Total requests (conflicts with -z)"
            echo "  -z, --duration TIME     Test duration (e.g., 30s, 5m)"
            echo "  -d, --data JSON         Request body data"
            echo "  -H, --header HEADER     HTTP header (can be used multiple times)"
            echo "  -o, --output FILE       Output file path"
            echo "  -t, --test-name NAME    Test name for logging"
            exit 0
            ;;
        *) echo "Unknown option: $1"; exit 1 ;;
    esac
done

# Validate required parameters
if [[ -z "${ENDPOINT}" ]]; then
    echo "❌ Error: Endpoint is required (-e/--endpoint)"
    exit 1
fi

# Generate output file if not specified
if [[ -z "${OUTPUT_FILE}" ]]; then
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    OUTPUT_FILE="${RESULTS_DIR}/${TEST_NAME}-${TIMESTAMP}.txt"
fi

# Ensure results directory exists
mkdir -p "$(dirname "${OUTPUT_FILE}")"

# Build hey command
HEY_CMD="hey"
if [[ -n "${DURATION}" ]]; then
    HEY_CMD="${HEY_CMD} -z ${DURATION}"
else
    HEY_CMD="${HEY_CMD} -n ${REQUESTS}"
fi
HEY_CMD="${HEY_CMD} -c ${CONCURRENT} -m ${METHOD}"

# Add headers
if [[ -n "${HEADERS}" ]]; then
    HEY_CMD="${HEY_CMD} ${HEADERS}"
fi

# Add data
if [[ -n "${DATA}" ]]; then
    HEY_CMD="${HEY_CMD} -d '${DATA}'"
fi

# Add endpoint
HEY_CMD="${HEY_CMD} ${ENDPOINT}"

# Run test
echo "=== Running Load Test: ${TEST_NAME} ==="
echo "Endpoint: ${ENDPOINT}"
echo "Concurrent: ${CONCURRENT}"
if [[ -n "${DURATION}" ]]; then
    echo "Duration: ${DURATION}"
else
    echo "Requests: ${REQUESTS}"
fi
echo "Output: ${OUTPUT_FILE}"
echo "---"

# Execute and capture output
eval "${HEY_CMD}" | tee "${OUTPUT_FILE}"

# Parse and display key metrics
echo ""
echo "=== Key Metrics ==="
grep -E "Requests/sec:|Success rate:" "${OUTPUT_FILE}" || true
grep -E "50%|95%|99%" "${OUTPUT_FILE}" | head -3 || true

echo ""
echo "✅ Test complete. Results saved to: ${OUTPUT_FILE}"
```

#### Task 2.3: vLLM Test Script

**tests/load/scripts/test-vllm.sh**:
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="${SCRIPT_DIR}/.."
CONFIG_FILE="${BASE_DIR}/config/vllm-config.yaml"
RESULTS_DIR="${BASE_DIR}/results"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
REPORT_DIR="${RESULTS_DIR}/vllm-${TIMESTAMP}"

# Create report directory
mkdir -p "${REPORT_DIR}"

# Parse config (simplified - in real implementation use Python)
ENDPOINT="${VLLM_ENDPOINT:-https://llm.blockchainradar.xyz/v1/chat/completions}"
MODEL="${VLLM_MODEL:-Qwen/Qwen3-0.6B}"

echo "=== vLLM Load Testing Suite ==="
echo "Endpoint: ${ENDPOINT}"
echo "Model: ${MODEL}"
echo "Report Directory: ${REPORT_DIR}"
echo ""

# Test 1: Baseline
run_baseline_test() {
    echo "### Test 1: Baseline (50 concurrent, 1000 requests) ###"

    "${SCRIPT_DIR}/run-hey-test.sh" \
        -e "${ENDPOINT}" \
        -c 50 \
        -n 1000 \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Hello\"}],\"max_tokens\":20}" \
        -o "${REPORT_DIR}/baseline.txt" \
        -t "vllm-baseline"

    echo "✅ Baseline test complete"
    echo ""
}

# Test 2: Stress Test
run_stress_test() {
    echo "### Test 2: Stress Test (100 concurrent, 2000 requests) ###"

    "${SCRIPT_DIR}/run-hey-test.sh" \
        -e "${ENDPOINT}" \
        -c 100 \
        -n 2000 \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Explain AI in 30 words\"}],\"max_tokens\":50}" \
        -o "${REPORT_DIR}/stress.txt" \
        -t "vllm-stress"

    echo "✅ Stress test complete"
    echo ""
}

# Test 3: Breaking Point Analysis
run_breaking_point_test() {
    echo "### Test 3: Breaking Point Analysis ###"

    for concurrent in 100 150 200 250 300; do
        echo "Testing with ${concurrent} concurrent connections..."

        "${SCRIPT_DIR}/run-hey-test.sh" \
            -e "${ENDPOINT}" \
            -c ${concurrent} \
            -n 500 \
            -H "Content-Type: application/json" \
            -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"Test\"}],\"max_tokens\":10}" \
            -o "${REPORT_DIR}/breaking-${concurrent}.txt" \
            -t "vllm-breaking-${concurrent}"

        # Check for errors
        if grep -q "Status code distribution:" "${REPORT_DIR}/breaking-${concurrent}.txt"; then
            SUCCESS_RATE=$(grep -A10 "Status code distribution:" "${REPORT_DIR}/breaking-${concurrent}.txt" | grep "200" | grep -oE '[0-9]+' | head -1)
            TOTAL=$(grep "Total:" "${REPORT_DIR}/breaking-${concurrent}.txt" | grep -oE '[0-9]+' | head -1)
            if [[ -n "${SUCCESS_RATE}" && -n "${TOTAL}" ]]; then
                RATE=$((SUCCESS_RATE * 100 / 500))
                echo "Success rate: ${RATE}%"
                if [[ ${RATE} -lt 99 ]]; then
                    echo "⚠️ Breaking point detected at ${concurrent} concurrent users"
                    break
                fi
            fi
        fi

        echo ""
        sleep 5  # Brief pause between tests
    done

    echo "✅ Breaking point analysis complete"
    echo ""
}

# Test 4: Sustained Load
run_sustained_test() {
    echo "### Test 4: Sustained Load (75 concurrent, 5 minutes) ###"

    "${SCRIPT_DIR}/run-hey-test.sh" \
        -e "${ENDPOINT}" \
        -c 75 \
        -z 5m \
        -H "Content-Type: application/json" \
        -d "{\"model\":\"${MODEL}\",\"messages\":[{\"role\":\"user\",\"content\":\"What is neural network?\"}],\"max_tokens\":30}" \
        -o "${REPORT_DIR}/sustained.txt" \
        -t "vllm-sustained"

    echo "✅ Sustained load test complete"
    echo ""
}

# Run all tests
run_baseline_test
run_stress_test
run_breaking_point_test
run_sustained_test

# Generate report
echo "### Generating vLLM Report ###"
python3 "${SCRIPT_DIR}/generate-report.py" \
    --type vllm \
    --input-dir "${REPORT_DIR}" \
    --output "${REPORT_DIR}/vllm-report.md"

echo ""
echo "=== vLLM Testing Complete ==="
echo "Results: ${REPORT_DIR}"
echo "Report: ${REPORT_DIR}/vllm-report.md"
```

### Phase 3: Python Locust Implementation (1.5 hours)

#### Task 3.1: Enhanced Locust File Structure

**tests/load/locust/locustfile.py**:
```python
#!/usr/bin/env python3
"""Main locust file for load testing."""

import os
import sys
import json
import random
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from locust import HttpUser, task, between, events
from locust.runners import MasterRunner
import yaml

# Import custom tasks and users
from tasks.rag_tasks import RAGTaskSet
from tasks.health_tasks import HealthTaskSet
from tasks.stress_tasks import StressTaskSet
from users.normal_user import NormalUser
from users.stress_user import StressUser
from users.spike_user import SpikeUser

# Load configuration
config_path = Path(__file__).parent.parent / "config" / "rag-config.yaml"
with open(config_path) as f:
    config = yaml.safe_load(f)

# Statistics collection
stats_file = None

@events.init.add_listener
def on_locust_init(environment, **kwargs):
    """Initialize locust environment."""
    if isinstance(environment.runner, MasterRunner):
        print("Running in distributed mode as master")
    else:
        print(f"Running with {environment.parsed_options.users} users")

@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Initialize test statistics file."""
    global stats_file
    timestamp = Path(__file__).parent.parent / "results" / f"locust-stats-{int(environment.runner.start_time)}.json"
    stats_file = open(timestamp, 'w')
    stats_file.write("[\n")

@events.request.add_listener
def on_request(request_type, name, response_time, response_length, response, context, exception, **kwargs):
    """Log individual request statistics."""
    if stats_file:
        stats = {
            "request_type": request_type,
            "name": name,
            "response_time": response_time,
            "response_length": response_length,
            "success": exception is None,
            "exception": str(exception) if exception else None
        }
        stats_file.write(json.dumps(stats) + ",\n")
        stats_file.flush()

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Finalize statistics collection."""
    if stats_file:
        stats_file.write("]\n")
        stats_file.close()

# Export user classes
__all__ = ['NormalUser', 'StressUser', 'SpikeUser']
```

**tests/load/locust/tasks/rag_tasks.py**:
```python
"""RAG-specific task definitions."""

import random
import json
from locust import task, TaskSet

class RAGTaskSet(TaskSet):
    """Task set for RAG operations."""

    # Diverse query set for realistic testing
    QUERIES = [
        # Simple queries
        "What is machine learning?",
        "Explain neural networks",
        "How does RAG work?",

        # Medium complexity
        "What are the key differences between supervised and unsupervised learning?",
        "Explain the transformer architecture in NLP",
        "How do convolutional neural networks process images?",

        # Complex queries
        "Compare and contrast different optimization algorithms in deep learning",
        "What are the latest advances in multimodal AI systems?",
        "Explain the attention mechanism and its importance in modern NLP",

        # Domain-specific
        "What are the best practices for deploying ML models in production?",
        "How can I optimize inference latency for real-time applications?",
        "What are the security considerations for RAG systems?",
    ]

    @task(10)
    def query_rag_simple(self):
        """Execute a simple RAG query."""
        query = random.choice(self.QUERIES[:3])
        payload = {
            "query": query,
            "top_k": 5,
            "temperature": 0.7
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            catch_response=True,
            timeout=30,
            name="RAG Query (Simple)"
        ) as response:
            self._handle_response(response)

    @task(5)
    def query_rag_complex(self):
        """Execute a complex RAG query."""
        query = random.choice(self.QUERIES[6:])
        payload = {
            "query": query,
            "top_k": 10,
            "temperature": 0.8,
            "max_tokens": 500
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            catch_response=True,
            timeout=60,
            name="RAG Query (Complex)"
        ) as response:
            self._handle_response(response)

    @task(2)
    def query_with_filters(self):
        """Query with metadata filters."""
        query = random.choice(self.QUERIES)
        payload = {
            "query": query,
            "top_k": 5,
            "filters": {
                "source": random.choice(["pdf", "docx", "web"]),
                "date_range": "last_30_days"
            }
        }

        with self.client.post(
            "/api/v1/query",
            json=payload,
            catch_response=True,
            timeout=45,
            name="RAG Query (Filtered)"
        ) as response:
            self._handle_response(response)

    def _handle_response(self, response):
        """Handle and validate response."""
        try:
            if response.status_code == 200:
                data = response.json()
                if "answer" in data and "sources" in data:
                    # Validate response quality
                    if len(data["answer"]) < 10:
                        response.failure("Answer too short")
                    elif data["sources"] is None or len(data["sources"]) == 0:
                        response.failure("No sources returned")
                    else:
                        response.success()
                else:
                    response.failure("Missing required fields in response")
            else:
                response.failure(f"HTTP {response.status_code}: {response.text[:100]}")
        except json.JSONDecodeError:
            response.failure("Invalid JSON response")
        except Exception as e:
            response.failure(f"Unexpected error: {str(e)}")
```

### Phase 4: Report Generation (1 hour)

#### Task 4.1: Report Generator

**tests/load/scripts/generate-report.py**:
```python
#!/usr/bin/env python3
"""Generate markdown reports from load test results."""

import argparse
import json
import re
import yaml
from pathlib import Path
from datetime import datetime
from jinja2 import Template
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

class LoadTestReportGenerator:
    """Generate comprehensive load test reports."""

    def __init__(self, test_type, input_dir, output_path):
        self.test_type = test_type
        self.input_dir = Path(input_dir)
        self.output_path = Path(output_path)
        self.data = {}

    def parse_hey_output(self, file_path):
        """Parse hey command output."""
        with open(file_path, 'r') as f:
            content = f.read()

        metrics = {}

        # Parse summary statistics
        if match := re.search(r'Total:\s+([0-9.]+) secs', content):
            metrics['total_time'] = float(match.group(1))

        if match := re.search(r'Requests/sec:\s+([0-9.]+)', content):
            metrics['requests_per_sec'] = float(match.group(1))

        # Parse latency distribution
        latency_pattern = r'(\d+)% in ([0-9.]+) secs'
        latencies = {}
        for match in re.finditer(latency_pattern, content):
            percentile = int(match.group(1))
            latency = float(match.group(2)) * 1000  # Convert to ms
            latencies[f'p{percentile}'] = latency
        metrics['latencies'] = latencies

        # Parse status codes
        status_pattern = r'\[(\d+)\]\s+(\d+) responses'
        status_codes = {}
        total_responses = 0
        for match in re.finditer(status_pattern, content):
            code = match.group(1)
            count = int(match.group(2))
            status_codes[code] = count
            total_responses += count

        metrics['status_codes'] = status_codes
        metrics['total_responses'] = total_responses

        # Calculate success rate
        success_count = status_codes.get('200', 0)
        metrics['success_rate'] = (success_count / total_responses * 100) if total_responses > 0 else 0

        return metrics

    def parse_all_results(self):
        """Parse all test result files."""
        for file_path in self.input_dir.glob("*.txt"):
            test_name = file_path.stem
            self.data[test_name] = self.parse_hey_output(file_path)

    def generate_chart(self, data, chart_type='latency'):
        """Generate charts for the report."""
        fig, ax = plt.subplots(figsize=(10, 6))

        if chart_type == 'latency':
            # Latency comparison chart
            tests = []
            p50_values = []
            p95_values = []
            p99_values = []

            for test_name, metrics in data.items():
                if 'latencies' in metrics:
                    tests.append(test_name)
                    p50_values.append(metrics['latencies'].get('p50', 0))
                    p95_values.append(metrics['latencies'].get('p95', 0))
                    p99_values.append(metrics['latencies'].get('p99', 0))

            x = range(len(tests))
            width = 0.25

            ax.bar([i - width for i in x], p50_values, width, label='P50', alpha=0.8)
            ax.bar(x, p95_values, width, label='P95', alpha=0.8)
            ax.bar([i + width for i in x], p99_values, width, label='P99', alpha=0.8)

            ax.set_xlabel('Test')
            ax.set_ylabel('Latency (ms)')
            ax.set_title('Latency Distribution Comparison')
            ax.set_xticks(x)
            ax.set_xticklabels(tests, rotation=45, ha='right')
            ax.legend()
            ax.grid(True, alpha=0.3)

        elif chart_type == 'throughput':
            # Throughput comparison
            tests = []
            throughputs = []

            for test_name, metrics in data.items():
                if 'requests_per_sec' in metrics:
                    tests.append(test_name)
                    throughputs.append(metrics['requests_per_sec'])

            ax.bar(tests, throughputs, alpha=0.8, color='green')
            ax.set_xlabel('Test')
            ax.set_ylabel('Requests/sec')
            ax.set_title('Throughput Comparison')
            ax.set_xticklabels(tests, rotation=45, ha='right')
            ax.grid(True, alpha=0.3)

        # Convert to base64 for embedding in markdown
        buffer = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buffer, format='png', dpi=100)
        buffer.seek(0)
        image_base64 = base64.b64encode(buffer.read()).decode()
        plt.close()

        return f"data:image/png;base64,{image_base64}"

    def generate_report(self):
        """Generate the final markdown report."""
        self.parse_all_results()

        # Create report based on test type
        if self.test_type == 'vllm':
            report = self.generate_vllm_report()
        elif self.test_type == 'embedding':
            report = self.generate_embedding_report()
        elif self.test_type == 'e2e':
            report = self.generate_e2e_report()
        else:
            report = self.generate_generic_report()

        # Save report
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.output_path, 'w') as f:
            f.write(report)

        print(f"✅ Report generated: {self.output_path}")

    def generate_vllm_report(self):
        """Generate vLLM-specific report."""
        template = '''# vLLM Load Test Report

**Date**: {{ date }}
**Endpoint**: {{ endpoint }}
**Model**: {{ model }}

## Executive Summary

{{ summary }}

## Test Results

| Test | Concurrent Users | Total Requests | Success Rate | P50 (ms) | P95 (ms) | P99 (ms) | Throughput (req/s) |
|------|-----------------|----------------|--------------|----------|----------|----------|-------------------|
{% for test_name, metrics in data.items() %}
| {{ test_name }} | - | {{ metrics.total_responses }} | {{ "%.1f"|format(metrics.success_rate) }}% | {{ "%.1f"|format(metrics.latencies.p50) }} | {{ "%.1f"|format(metrics.latencies.p95) }} | {{ "%.1f"|format(metrics.latencies.p99) }} | {{ "%.1f"|format(metrics.requests_per_sec) }} |
{% endfor %}

## Performance Analysis

### Latency Distribution
![Latency Chart]({{ latency_chart }})

### Throughput Comparison
![Throughput Chart]({{ throughput_chart }})

## Breaking Point Analysis

{{ breaking_point_analysis }}

## Recommendations

{{ recommendations }}

## Detailed Test Results

{% for test_name, metrics in data.items() %}
### {{ test_name }}

- **Total Time**: {{ "%.2f"|format(metrics.total_time) }} seconds
- **Success Rate**: {{ "%.2f"|format(metrics.success_rate) }}%
- **Requests/sec**: {{ "%.2f"|format(metrics.requests_per_sec) }}
- **Status Codes**: {{ metrics.status_codes }}

{% endfor %}
'''

        # Analyze breaking point
        breaking_point = self.find_breaking_point()

        # Generate recommendations
        recommendations = self.generate_recommendations()

        # Render template
        template_obj = Template(template)
        report = template_obj.render(
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            endpoint="https://llm.blockchainradar.xyz/v1/chat/completions",
            model="Qwen/Qwen3-0.6B",
            summary=self.generate_summary(),
            data=self.data,
            latency_chart=self.generate_chart(self.data, 'latency'),
            throughput_chart=self.generate_chart(self.data, 'throughput'),
            breaking_point_analysis=breaking_point,
            recommendations=recommendations
        )

        return report

    def find_breaking_point(self):
        """Analyze and find the breaking point."""
        breaking_tests = {k: v for k, v in self.data.items() if 'breaking' in k}

        if not breaking_tests:
            return "No breaking point tests found."

        analysis = []
        for test_name, metrics in sorted(breaking_tests.items()):
            concurrent = int(re.search(r'breaking-(\d+)', test_name).group(1))
            success_rate = metrics['success_rate']
            p95_latency = metrics['latencies'].get('p95', 0)

            analysis.append(f"- **{concurrent} concurrent users**: {success_rate:.1f}% success rate, {p95_latency:.1f}ms P95 latency")

            if success_rate < 99:
                analysis.append(f"\n**Breaking point identified at {concurrent} concurrent users** (success rate < 99%)")
                break
            elif p95_latency > 1000:
                analysis.append(f"\n**Performance degradation at {concurrent} concurrent users** (P95 > 1000ms)")

        return '\n'.join(analysis)

    def generate_summary(self):
        """Generate executive summary."""
        baseline = self.data.get('baseline', {})
        stress = self.data.get('stress', {})

        summary = []

        if baseline:
            summary.append(f"Baseline testing showed {baseline['success_rate']:.1f}% success rate with {baseline['requests_per_sec']:.1f} req/s throughput.")

        if stress:
            summary.append(f"Under stress conditions, the system maintained {stress['success_rate']:.1f}% success rate with P95 latency of {stress['latencies'].get('p95', 0):.1f}ms.")

        # Find breaking point
        breaking_tests = {k: v for k, v in self.data.items() if 'breaking' in k}
        for test_name, metrics in sorted(breaking_tests.items()):
            if metrics['success_rate'] < 99:
                concurrent = int(re.search(r'breaking-(\d+)', test_name).group(1))
                summary.append(f"Breaking point identified at {concurrent} concurrent users.")
                break

        return ' '.join(summary) if summary else "Load testing completed successfully."

    def generate_recommendations(self):
        """Generate recommendations based on test results."""
        recommendations = []

        # Analyze baseline performance
        baseline = self.data.get('baseline', {})
        if baseline and baseline['success_rate'] < 100:
            recommendations.append("1. **Baseline Performance**: Success rate below 100% even at baseline load. Investigate service health and error logs.")

        # Analyze stress test
        stress = self.data.get('stress', {})
        if stress:
            if stress['latencies'].get('p95', 0) > 500:
                recommendations.append("2. **Latency Optimization**: P95 latency exceeds 500ms under stress. Consider:")
                recommendations.append("   - Increasing vLLM batch size")
                recommendations.append("   - Optimizing model inference parameters")
                recommendations.append("   - Adding more GPU resources")

        # Find safe operating range
        breaking_tests = {k: v for k, v in self.data.items() if 'breaking' in k}
        max_safe_concurrent = 0
        for test_name, metrics in sorted(breaking_tests.items()):
            concurrent = int(re.search(r'breaking-(\d+)', test_name).group(1))
            if metrics['success_rate'] >= 99:
                max_safe_concurrent = concurrent
            else:
                break

        if max_safe_concurrent > 0:
            recommendations.append(f"3. **Capacity Planning**: Safe operating range is 0-{max_safe_concurrent} concurrent users")
            recommendations.append(f"   - Configure HPA max replicas based on {int(max_safe_concurrent * 0.7)} users (30% buffer)")
            recommendations.append(f"   - Set alerting threshold at {int(max_safe_concurrent * 0.8)} concurrent users")

        return '\n'.join(recommendations) if recommendations else "System performing within acceptable parameters."


def main():
    parser = argparse.ArgumentParser(description='Generate load test reports')
    parser.add_argument('--type', choices=['vllm', 'embedding', 'e2e', 'generic'],
                       required=True, help='Type of report to generate')
    parser.add_argument('--input-dir', required=True, help='Directory containing test results')
    parser.add_argument('--output', required=True, help='Output report file path')

    args = parser.parse_args()

    generator = LoadTestReportGenerator(args.type, args.input_dir, args.output)
    generator.generate_report()


if __name__ == '__main__':
    main()
```

### Phase 5: Main Orchestration Script (30 minutes)

#### Task 5.1: Main Test Runner

**tests/load/run-all-tests.sh**:
```bash
#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TIMESTAMP=$(date +%Y%m%d-%H%M%S)
RESULTS_DIR="${SCRIPT_DIR}/results/full-test-${TIMESTAMP}"
REPORTS_DIR="${SCRIPT_DIR}/reports/full-test-${TIMESTAMP}"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Create directories
mkdir -p "${RESULTS_DIR}" "${REPORTS_DIR}"

# Logging
LOG_FILE="${RESULTS_DIR}/test-run.log"
exec 1> >(tee -a "${LOG_FILE}")
exec 2>&1

echo -e "${BLUE}=== IntelliRAG Load Testing Suite ===${NC}"
echo "Timestamp: ${TIMESTAMP}"
echo "Results: ${RESULTS_DIR}"
echo "Reports: ${REPORTS_DIR}"
echo ""

# Function to check prerequisites
check_prerequisites() {
    echo -e "${YELLOW}### Checking Prerequisites ###${NC}"

    # Check for hey
    if ! command -v hey &> /dev/null; then
        echo -e "${RED}❌ hey is not installed${NC}"
        echo "Running installation script..."
        "${SCRIPT_DIR}/scripts/install-tools.sh"
    else
        echo -e "${GREEN}✅ hey is installed${NC}"
    fi

    # Check for locust
    if ! command -v locust &> /dev/null; then
        echo -e "${RED}❌ locust is not installed${NC}"
        echo "Running installation script..."
        "${SCRIPT_DIR}/scripts/install-tools.sh"
    else
        echo -e "${GREEN}✅ locust is installed${NC}"
    fi

    # Check endpoints
    echo -e "${YELLOW}Checking endpoint availability...${NC}"

    if curl -s -f https://llm.blockchainradar.xyz/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ vLLM endpoint is accessible${NC}"
    else
        echo -e "${RED}❌ vLLM endpoint is not accessible${NC}"
        exit 1
    fi

    if curl -s -f https://embed.blockchainradar.xyz/health > /dev/null 2>&1; then
        echo -e "${GREEN}✅ Embedding endpoint is accessible${NC}"
    else
        echo -e "${RED}❌ Embedding endpoint is not accessible${NC}"
        exit 1
    fi

    echo ""
}

# Function to run vLLM tests
run_vllm_tests() {
    echo -e "${BLUE}### Phase 1: vLLM Load Testing ###${NC}"

    VLLM_RESULTS="${RESULTS_DIR}/vllm"
    mkdir -p "${VLLM_RESULTS}"

    # Export environment variables for the test script
    export VLLM_ENDPOINT="https://llm.blockchainradar.xyz/v1/chat/completions"
    export VLLM_MODEL="Qwen/Qwen3-0.6B"

    # Run vLLM tests
    "${SCRIPT_DIR}/scripts/test-vllm.sh" 2>&1 | tee "${VLLM_RESULTS}/test.log"

    # Copy results
    cp -r "${SCRIPT_DIR}/results/vllm-"* "${VLLM_RESULTS}/" 2>/dev/null || true

    echo -e "${GREEN}✅ vLLM testing complete${NC}"
    echo ""
}

# Function to run embedding tests
run_embedding_tests() {
    echo -e "${BLUE}### Phase 2: Embedding Service Load Testing ###${NC}"

    EMBEDDING_RESULTS="${RESULTS_DIR}/embedding"
    mkdir -p "${EMBEDDING_RESULTS}"

    export EMBEDDING_ENDPOINT="https://embed.blockchainradar.xyz/vectorize"

    # Run embedding tests
    "${SCRIPT_DIR}/scripts/test-embedding.sh" 2>&1 | tee "${EMBEDDING_RESULTS}/test.log"

    # Copy results
    cp -r "${SCRIPT_DIR}/results/embedding-"* "${EMBEDDING_RESULTS}/" 2>/dev/null || true

    echo -e "${GREEN}✅ Embedding testing complete${NC}"
    echo ""
}

# Function to run E2E RAG tests
run_e2e_tests() {
    echo -e "${BLUE}### Phase 3: End-to-End RAG Testing ###${NC}"

    E2E_RESULTS="${RESULTS_DIR}/e2e"
    mkdir -p "${E2E_RESULTS}"

    # Check if port-forward is needed
    if ! curl -s -f http://localhost:8000/ready > /dev/null 2>&1; then
        echo "Setting up port-forward to GKE..."
        kubectl port-forward -n app svc/intellirag-app 8000:8000 &
        PF_PID=$!
        sleep 5
    fi

    # Run locust tests
    cd "${SCRIPT_DIR}/locust"

    # Test 1: Normal load
    echo "Running normal load test (50 users, 5 minutes)..."
    locust -f locustfile.py \
        --headless \
        --users 50 \
        --spawn-rate 5 \
        --run-time 5m \
        --html "${E2E_RESULTS}/normal-50users.html" \
        --csv "${E2E_RESULTS}/normal" \
        2>&1 | tee "${E2E_RESULTS}/normal.log"

    # Test 2: High load
    echo "Running high load test (100 users, 5 minutes)..."
    locust -f locustfile.py \
        --headless \
        --users 100 \
        --spawn-rate 10 \
        --run-time 5m \
        --html "${E2E_RESULTS}/high-100users.html" \
        --csv "${E2E_RESULTS}/high" \
        2>&1 | tee "${E2E_RESULTS}/high.log"

    # Test 3: Stress test
    echo "Running stress test (200 users, 3 minutes)..."
    locust -f locustfile.py \
        --user-classes StressUser \
        --headless \
        --users 200 \
        --spawn-rate 20 \
        --run-time 3m \
        --html "${E2E_RESULTS}/stress-200users.html" \
        --csv "${E2E_RESULTS}/stress" \
        2>&1 | tee "${E2E_RESULTS}/stress.log"

    # Clean up port-forward if we started it
    if [[ -n "${PF_PID}" ]]; then
        kill ${PF_PID} 2>/dev/null || true
    fi

    cd "${SCRIPT_DIR}"

    echo -e "${GREEN}✅ E2E testing complete${NC}"
    echo ""
}

# Function to generate final report
generate_final_report() {
    echo -e "${BLUE}### Generating Final Reports ###${NC}"

    # Generate individual reports
    python3 "${SCRIPT_DIR}/scripts/generate-report.py" \
        --type vllm \
        --input-dir "${RESULTS_DIR}/vllm" \
        --output "${REPORTS_DIR}/vllm-report.md"

    python3 "${SCRIPT_DIR}/scripts/generate-report.py" \
        --type embedding \
        --input-dir "${RESULTS_DIR}/embedding" \
        --output "${REPORTS_DIR}/embedding-report.md"

    python3 "${SCRIPT_DIR}/scripts/generate-report.py" \
        --type e2e \
        --input-dir "${RESULTS_DIR}/e2e" \
        --output "${REPORTS_DIR}/e2e-report.md"

    # Generate executive summary
    cat > "${REPORTS_DIR}/executive-summary.md" << EOF
# Load Testing Executive Summary

**Date**: $(date '+%Y-%m-%d %H:%M:%S')
**Test Suite Version**: 1.0.0

## Test Execution Summary

| Component | Status | Duration | Report |
|-----------|--------|----------|--------|
| vLLM | ✅ Complete | - | [View Report](./vllm-report.md) |
| Embedding | ✅ Complete | - | [View Report](./embedding-report.md) |
| E2E RAG | ✅ Complete | - | [View Report](./e2e-report.md) |

## Key Findings

### Performance Metrics
- **vLLM**: [Summary from vLLM tests]
- **Embedding**: [Summary from embedding tests]
- **E2E RAG**: [Summary from E2E tests]

### Breaking Points
- **vLLM**: XXX concurrent users
- **Embedding**: XXX concurrent users
- **E2E System**: XXX concurrent users

### Recommendations
1. Configure HPA with max replicas: XX
2. Set CPU threshold: XX%
3. Set Memory threshold: XX%

## Next Steps
- Review detailed reports for each component
- Apply Day 3 optimizations based on findings
- Configure HPA settings for Day 5

---
*Generated by IntelliRAG Load Testing Suite v1.0.0*
EOF

    echo -e "${GREEN}✅ Reports generated${NC}"
    echo ""
}

# Main execution
main() {
    check_prerequisites

    # Parse command line arguments
    SKIP_VLLM=false
    SKIP_EMBEDDING=false
    SKIP_E2E=false

    while [[ $# -gt 0 ]]; do
        case $1 in
            --skip-vllm) SKIP_VLLM=true; shift ;;
            --skip-embedding) SKIP_EMBEDDING=true; shift ;;
            --skip-e2e) SKIP_E2E=true; shift ;;
            --help)
                echo "Usage: $0 [options]"
                echo "Options:"
                echo "  --skip-vllm      Skip vLLM tests"
                echo "  --skip-embedding Skip embedding tests"
                echo "  --skip-e2e       Skip E2E tests"
                exit 0
                ;;
            *) echo "Unknown option: $1"; exit 1 ;;
        esac
    done

    # Run tests
    [[ "${SKIP_VLLM}" == "false" ]] && run_vllm_tests
    [[ "${SKIP_EMBEDDING}" == "false" ]] && run_embedding_tests
    [[ "${SKIP_E2E}" == "false" ]] && run_e2e_tests

    # Generate reports
    generate_final_report

    echo -e "${BLUE}=== Load Testing Complete ===${NC}"
    echo "Results: ${RESULTS_DIR}"
    echo "Reports: ${REPORTS_DIR}"
    echo ""
    echo -e "${GREEN}View executive summary: ${REPORTS_DIR}/executive-summary.md${NC}"
}

# Run main function
main "$@"
```

---

## Testing Strategy

### Unit Testing
Each script component should be tested individually:
1. Test configuration loading
2. Test hey command generation
3. Test result parsing
4. Test report generation

### Integration Testing
1. Test full workflow with mock endpoints
2. Validate report generation
3. Test error handling and recovery

### Load Test Validation
1. Start with small-scale tests to validate scripts
2. Gradually increase load to production levels
3. Monitor system resources during tests

---

## Implementation Timeline

| Phase | Tasks | Duration |
|-------|-------|----------|
| Phase 1 | Setup and Configuration | 30 min |
| Phase 2 | Bash Script Implementation | 1.5 hours |
| Phase 3 | Python Locust Implementation | 1.5 hours |
| Phase 4 | Report Generation | 1 hour |
| Phase 5 | Orchestration Script | 30 min |
| Phase 6 | Testing and Validation | 1.5 hours |
| **Total** | **Complete Implementation** | **6 hours** |

---

## TODO Checklist

- [ ] Create directory structure for load testing framework
- [ ] Implement configuration files (YAML)
- [ ] Create install-tools.sh script
- [ ] Implement run-hey-test.sh generic runner
- [ ] Create test-vllm.sh script
- [ ] Create test-embedding.sh script
- [ ] Implement enhanced locustfile.py
- [ ] Create RAG task definitions
- [ ] Implement user behavior classes
- [ ] Create generate-report.py script
- [ ] Implement report templates
- [ ] Create run-all-tests.sh orchestration script
- [ ] Test individual components
- [ ] Run integration tests
- [ ] Validate report generation
- [ ] Document usage and configuration
- [ ] Create example reports
- [ ] Package for distribution

---

## Success Criteria

1. **Reusability**: Scripts can be run multiple times with different configurations
2. **Parameterization**: All key values configurable via files or environment variables
3. **Automation**: Complete test suite runs with single command
4. **Reporting**: Professional markdown reports with charts and analysis
5. **Error Handling**: Graceful failure recovery and clear error messages
6. **Maintainability**: Clean, documented code following best practices

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Endpoint unavailability | High | Pre-flight checks, fallback to local endpoints |
| Resource exhaustion | Medium | Gradual load increase, monitoring |
| Script failures | Medium | Error handling, logging, checkpoints |
| Invalid results | Low | Result validation, data sanity checks |

---

## Future Enhancements

1. **Dashboard Integration**: Real-time Grafana dashboard updates
2. **CI/CD Integration**: GitHub Actions workflow for automated testing
3. **Multi-region Testing**: Support for testing across different regions
4. **Advanced Analytics**: ML-based anomaly detection in results
5. **Cost Analysis**: Calculate and report infrastructure costs per test

---

## Conclusion

This implementation plan provides a comprehensive, reusable load testing framework that transforms the Day 2 manual testing procedures into an automated, professional testing suite. The modular design ensures easy maintenance and extension for future testing needs.

The framework emphasizes:
- **Modularity**: Each component can be used independently
- **Configurability**: Easy adjustment without code changes
- **Professionalism**: Enterprise-grade reporting and analysis
- **Automation**: Minimal manual intervention required
- **Scalability**: Ready for CI/CD integration and expansion

---

**Last Updated**: 2025-11-23
**Next Steps**: Review plan, confirm requirements, then proceed with implementation