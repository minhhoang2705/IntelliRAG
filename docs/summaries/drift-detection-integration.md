# Drift Detection Integration Guide

**Created**: 2025-11-28
**Status**: Implemented
**Components**: Query Logging + Drift Detection + Prometheus Metrics

---

## 🔄 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│  1. User Query → FastAPI /api/v1/query                     │
│                                                             │
│     ┌─────────────────────────────────────────────────┐   │
│     │  Query Processing                                │   │
│     │  - Execute RAG pipeline                          │   │
│     │  - Generate answer                               │   │
│     │  - Measure response time                         │   │
│     └──────────────┬──────────────────────────────────┘   │
│                    ↓                                        │
│     ┌─────────────────────────────────────────────────┐   │
│     │  QueryLoggerService.log_query()                 │   │
│     │  - Extract metadata (length, keywords, etc.)    │   │
│     │  - Store in Qdrant 'query_logs' collection      │   │
│     │  - Runs in background (non-blocking)            │   │
│     └──────────────┬──────────────────────────────────┘   │
│                    ↓                                        │
│              Qdrant Collection:                             │
│              query_logs (payload-only storage)              │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  2. Daily CronJob (4 AM) - Drift Detection                 │
│                                                             │
│     ┌─────────────────────────────────────────────────┐   │
│     │  DriftDetector.monitor_query_patterns()         │   │
│     │  1. Fetch last 7 days (reference)               │   │
│     │  2. Fetch last 24 hours (current)               │   │
│     │  3. Run Evidently drift detection               │   │
│     └──────────────┬──────────────────────────────────┘   │
│                    ↓                                        │
│     ┌─────────────────────────────────────────────────┐   │
│     │  Outputs                                        │   │
│     │  - Log to MLFlow (metrics + HTML report)       │   │
│     │  - Export to Prometheus (drift_share metric)   │   │
│     │  - Store HTML report in GCS                    │   │
│     └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────┐
│  3. Monitoring & Visualization                              │
│                                                             │
│  - Grafana: MLOps dashboard shows drift_share metric       │
│  - MLFlow: View drift reports and historical trends        │
│  - Prometheus: Scrape drift metrics for alerting           │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Data Flow

### Query Logging (Real-time)

**When**: Every `/api/v1/query` request
**What**: Captures query metadata

```python
metadata = {
    "query": "What is RAG?",
    "query_length": 13,
    "num_words": 3,
    "num_keywords": 1,  # Excludes stop words
    "response_time_ms": 287.5,
    "used_rag": True,
    "sources_count": 5,
    "answer_length": 450,
    "query_type": "factual",
    "timestamp": "2025-11-28T10:30:00Z",
    "date": "2025-11-28"
}
```

**Storage**: Qdrant `query_logs` collection (payload-only)

### Drift Detection (Daily)

**When**: CronJob runs daily at 4 AM
**What**: Compares query patterns

**Reference Period**: Last 7 days (excluding last 2 days)
**Current Period**: Yesterday (last 24 hours)

**Features Monitored**:
1. `query_length` - Distribution of query character lengths
2. `num_keywords` - Distribution of meaningful keywords per query
3. `response_time_ms` - Response time patterns
4. `sources_count` - Number of retrieved sources

**Drift Detection**:
- Uses Evidently library
- Calculates drift share (% of drifted features)
- Generates HTML report with visualizations

---

## 🔧 Implementation Components

### 1. QueryLoggerService
**File**: `app/services/query_logger.py`

**Purpose**: Log query metadata to Qdrant for drift monitoring

**Key Methods**:
```python
async def log_query(
    query: str,
    response_time_ms: float,
    used_rag: bool,
    sources_count: int,
    answer_length: int,
    query_type: Optional[str]
)

async def get_query_logs(
    start_date: str,
    end_date: str,
    limit: int = 10000
) -> List[Dict]
```

**Features**:
- Non-blocking background logging
- Keyword extraction (excludes stop words)
- Date-based querying for drift detection

### 2. DriftDetector (Enhanced)
**File**: `mlops/monitoring/drift_detector.py`

**Purpose**: Detect data drift using Evidently

**Key Methods**:
```python
async def monitor_query_patterns(
    lookback_days: int = 7,
    use_mock_data: bool = False
) -> Dict

async def _fetch_real_query_data(
    lookback_days: int
) -> tuple[pd.DataFrame, pd.DataFrame]
```

**Features**:
- Fetches real data from Qdrant query logs
- Falls back to mock data if no logs available
- Exports metrics to Prometheus
- Logs results to MLFlow with HTML reports

### 3. FastAPI Integration
**File**: `app/api/v1/query.py`

**Changes**:
```python
@router.post("/api/v1/query")
async def query_endpoint(
    request: QueryRequest,
    background_tasks: BackgroundTasks,  # NEW
    query_logger: QueryLoggerService = Depends(get_query_logger)  # NEW
):
    start_time = time.time()
    
    result = await orchestrator.query(...)
    
    response_time_ms = (time.time() - start_time) * 1000
    
    # Log in background (non-blocking)
    background_tasks.add_task(
        query_logger.log_query,
        query=request.query,
        response_time_ms=response_time_ms,
        used_rag=result["used_rag"],
        sources_count=len(result["sources"]),
        answer_length=len(result["answer"]),
        query_type=query_type
    )
    
    return response
```

---

## 📈 Prometheus Metrics

### Exposed Metrics

```
# Drift share (0.0 to 1.0)
evidently_drift_share 0.23

# Last detection timestamp (Unix epoch)
evidently_drift_detection_timestamp 1732780800
```

### Grafana Dashboard Query

```promql
# Drift share percentage
evidently_drift_share * 100

# Time since last detection
(time() - evidently_drift_detection_timestamp) / 3600
```

### Alerting Rules (Example)

```yaml
groups:
  - name: drift_alerts
    rules:
      - alert: HighDataDrift
        expr: evidently_drift_share > 0.3
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High data drift detected"
          description: "Drift share is {{ $value | humanizePercentage }}"
```

---

## 🚀 Deployment Steps

### Step 1: Update Application Code

All code changes are already implemented:
- ✅ `app/services/query_logger.py`
- ✅ `app/api/v1/query.py`
- ✅ `app/dependencies.py`
- ✅ `mlops/monitoring/drift_detector.py`

### Step 2: Build and Deploy New Image

```bash
# Build image with updated code
cd /home/minh-ubs-k8s/AIDE-1/capstone/IntelliRAG
docker build -t gcr.io/intellirag-aide1-capstone/intellirag-api:v1.0.9 .

# Push to GCR
docker push gcr.io/intellirag-aide1-capstone/intellirag-api:v1.0.9

# Update Helm deployment
helm upgrade intellirag-app ./helm/intellirag-app \
  --namespace app \
  --set image.tag=v1.0.9 \
  --reuse-values
```

### Step 3: Verify Query Logging

```bash
# Send test query
curl -X POST https://intellirag-api.blockchainradar.xyz/api/v1/query \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"query": "What is retrieval-augmented generation?", "top_k": 5}'

# Check if query_logs collection was created
kubectl port-forward -n app svc/qdrant 6333:6333
curl http://localhost:6333/collections/query_logs
```

### Step 4: Deploy Drift Monitoring CronJob

```bash
# Update CronJob image tag
kubectl apply -f kubernetes/mlops/drift-monitoring-cronjob.yaml

# Manually trigger for testing
kubectl create job --from=cronjob/drift-monitoring drift-manual -n mlflow

# Check logs
kubectl logs -n mlflow -l job-name=drift-manual -f
```

### Step 5: Verify MLFlow Integration

```bash
# Check drift detection runs in MLFlow UI
open https://mlflow.blockchainradar.xyz

# Navigate to: Experiments → drift-detection-*
# Should see:
# - drift_share metric
# - HTML report artifact
```

### Step 6: Verify Prometheus Metrics

```bash
# Port-forward to FastAPI metrics endpoint
kubectl port-forward -n app svc/intellirag-api 8000:8000

# Check metrics
curl http://localhost:8000/metrics | grep evidently

# Should see:
# evidently_drift_share 0.0
# evidently_drift_detection_timestamp 1732780800
```

---

## 🧪 Testing

### Test Query Logging

```python
import httpx
import asyncio

async def test_query_logging():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://intellirag-api.blockchainradar.xyz/api/v1/query",
            headers={"Authorization": f"Bearer {API_KEY}"},
            json={
                "query": "Explain transformer architecture",
                "top_k": 5
            }
        )
        print(response.json())

asyncio.run(test_query_logging())
```

### Test Drift Detection (Mock Data)

```python
from mlops.monitoring.drift_detector import DriftDetector
import asyncio

async def test_drift_detection():
    detector = DriftDetector(
        mlflow_tracking_uri="http://mlflow-server.mlflow.svc.cluster.local:5000"
    )
    
    # Use mock data
    results = await detector.monitor_query_patterns(
        lookback_days=7,
        use_mock_data=True
    )
    
    print(f"Drift share: {results['metrics'][0]['result']['drift_share']:.2%}")

asyncio.run(test_drift_detection())
```

### Test Drift Detection (Real Data)

```python
from mlops.monitoring.drift_detector import DriftDetector
from app.services.query_logger import QueryLoggerService
from app.services.vectordb import QdrantService
import asyncio

async def test_real_drift_detection():
    # Initialize services
    qdrant = QdrantService(
        url="http://qdrant.app.svc.cluster.local:6333"
    )
    query_logger = QueryLoggerService(qdrant_service=qdrant)
    
    detector = DriftDetector(
        mlflow_tracking_uri="http://mlflow-server.mlflow.svc.cluster.local:5000",
        query_logger_service=query_logger
    )
    
    # Fetch real data
    results = await detector.monitor_query_patterns(
        lookback_days=7,
        use_mock_data=False
    )
    
    if results.get("status") == "insufficient_data":
        print("Not enough query logs yet")
    else:
        print(f"Drift share: {results['metrics'][0]['result']['drift_share']:.2%}")

asyncio.run(test_real_drift_detection())
```

---

## 🔍 Monitoring & Debugging

### Check Query Logs in Qdrant

```python
from qdrant_client import QdrantClient

client = QdrantClient(url="http://localhost:6333")

# Get collection info
info = client.get_collection("query_logs")
print(f"Total points: {info.points_count}")

# Scroll through logs
results = client.scroll(
    collection_name="query_logs",
    limit=10,
    with_payload=True
)

for point in results[0]:
    print(point.payload)
```

### Check Drift Detection History in MLFlow

```bash
# List all drift detection runs
curl http://mlflow-server.mlflow.svc.cluster.local:5000/api/2.0/mlflow/runs/search \
  -d '{"experiment_ids": ["0"]}'

# Get specific run
curl http://mlflow-server.mlflow.svc.cluster.local:5000/api/2.0/mlflow/runs/get \
  -d '{"run_id": "abc123"}'
```

### Check Prometheus Metrics

```bash
# Query drift share
curl -G http://prometheus-server:9090/api/v1/query \
  --data-urlencode 'query=evidently_drift_share'

# Query detection timestamp
curl -G http://prometheus-server:9090/api/v1/query \
  --data-urlencode 'query=evidently_drift_detection_timestamp'
```

---

## 📊 Expected Behavior

### Initial State (No Data)
- Query logs collection: Empty
- Drift detection: Returns `insufficient_data`
- Prometheus metrics: Not yet exposed

### After 24 Hours
- Query logs: Contains logs from user queries
- Drift detection: Still returns `insufficient_data` (need 7+ days reference)
- Prometheus metrics: Still not exposed

### After 7 Days
- Query logs: 7 days of data accumulated
- Drift detection: Runs successfully with real data
- Prometheus metrics: `evidently_drift_share` exposed
- MLFlow: Drift reports available

### Production State
- Query logs: Continuously growing (with automatic cleanup)
- Drift detection: Daily runs at 4 AM
- Prometheus metrics: Updated daily
- MLFlow: Historical drift trends visible
- Grafana: Real-time drift monitoring

---

## 🎯 Success Criteria

- ✅ Every query logs metadata to Qdrant
- ✅ Query logging doesn't impact response time (background task)
- ✅ Drift detection runs daily without failures
- ✅ Drift metrics exposed to Prometheus
- ✅ Drift reports viewable in MLFlow
- ✅ Grafana dashboard shows drift trends
- ✅ Alerts trigger when drift exceeds threshold

---

## 🔄 Future Enhancements

1. **Additional Features**:
   - Query complexity (nested queries, multi-turn)
   - User demographics (if available)
   - Embedding distributions
   - Retrieved document relevance scores

2. **Advanced Drift Detection**:
   - Per-query-type drift analysis
   - Semantic drift detection (query intent shifts)
   - Concept drift (answer quality degradation)

3. **Automated Responses**:
   - Auto-retrain recommendation
   - Dynamic routing adjustments
   - Automated model version rollback

4. **Data Management**:
   - Automatic query log cleanup (>90 days)
   - Query log sampling for large volumes
   - Privacy-preserving logging (PII removal)

---

## 📚 References

- [Evidently Documentation](https://docs.evidentlyai.com/)
- [Prometheus Client Python](https://github.com/prometheus/client_python)
- [MLFlow Tracking API](https://mlflow.org/docs/latest/tracking.html)
- [Qdrant Payload Indexing](https://qdrant.tech/documentation/concepts/payload/)

---

**Status**: Implemented & Ready for Deployment
**Next Steps**: Build and deploy updated Docker image

