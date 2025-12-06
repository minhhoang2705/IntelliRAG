# Phase 4: MLOps Pipeline - Implementation TODOs

**Created**: 2025-11-27
**Status**: Active
**Duration Estimate**: 3-4 days
**Priority**: High

---

## Overview

Streamlined Phase 4 implementation focusing on:
1. MLFlow (model tracking & registry)
2. Evidently (drift monitoring)
3. Grafana dashboards (MLOps metrics)
4. Deployment webhooks (automation)

**Removed**: RAGAS evaluation (per user decision)

---

## 📋 Task Breakdown

### Task 1: Deploy PostgreSQL for MLFlow ⏱️ 30 min

- [ ] **1.1** Add Bitnami Helm repository
  ```bash
  helm repo add bitnami https://charts.bitnami.com/bitnami
  helm repo update
  ```

- [ ] **1.2** Create `mlflow` namespace
  ```bash
  kubectl create namespace mlflow
  ```

- [ ] **1.3** Install PostgreSQL via Helm
  ```bash
  helm install postgresql bitnami/postgresql \
    --namespace mlflow \
    --set auth.username=mlflow \
    --set auth.password=mlflow \
    --set auth.database=mlflow \
    --set primary.persistence.size=20Gi \
    --set primary.resources.requests.cpu=500m \
    --set primary.resources.requests.memory=512Mi
  ```

- [ ] **1.4** Verify PostgreSQL deployment
  ```bash
  kubectl get pods -n mlflow
  kubectl logs -n mlflow -l app.kubernetes.io/name=postgresql
  ```

- [ ] **1.5** Test PostgreSQL connection
  ```bash
  kubectl run postgresql-client --rm --tty -i --restart='Never' \
    --namespace mlflow \
    --image docker.io/bitnami/postgresql:14 \
    --command -- psql --host postgresql.mlflow.svc.cluster.local -U mlflow -d mlflow -c '\l'
  ```

**Success Criteria**: PostgreSQL pod running, database accessible

---

### Task 2: Create GCS Bucket for MLFlow Artifacts ⏱️ 15 min

- [ ] **2.1** Create GCS bucket
  ```bash
  gsutil mb -p intellirag-aide1-capstone \
    -c STANDARD \
    -l asia-southeast1 \
    gs://intellirag-mlflow-artifacts
  ```

- [ ] **2.2** Set lifecycle policy (90-day retention)
  ```bash
  cat > mlflow-lifecycle.json <<EOF
  {
    "lifecycle": {
      "rule": [{
        "action": {"type": "Delete"},
        "condition": {"age": 90}
      }]
    }
  }
  EOF
  gsutil lifecycle set mlflow-lifecycle.json gs://intellirag-mlflow-artifacts
  ```

- [ ] **2.3** Grant workload identity access
  ```bash
  gsutil iam ch serviceAccount:intellirag-cluster-workload-sa@intellirag-aide1-capstone.iam.gserviceaccount.com:objectAdmin \
    gs://intellirag-mlflow-artifacts
  ```

- [ ] **2.4** Verify bucket
  ```bash
  gsutil ls -L -b gs://intellirag-mlflow-artifacts
  ```

**Success Criteria**: Bucket created, lifecycle policy set, permissions granted

---

### Task 3: Deploy MLFlow Tracking Server ⏱️ 1 hour

- [ ] **3.1** Create Kubernetes manifests directory
  ```bash
  mkdir -p kubernetes/mlflow
  ```

- [ ] **3.2** Create `kubernetes/mlflow/namespace.yaml`
  - Copy from phase-4-mlops-simplified.md

- [ ] **3.3** Create `kubernetes/mlflow/serviceaccount.yaml`
  - Include workload identity annotation

- [ ] **3.4** Create `kubernetes/mlflow/deployment.yaml`
  - MLFlow v2.9.2 image
  - PostgreSQL backend
  - GCS artifacts storage
  - Resource limits: 1 CPU, 2Gi RAM
  - Health probes configured

- [ ] **3.5** Create `kubernetes/mlflow/service.yaml`
  - ClusterIP service on port 5000

- [ ] **3.6** Create `kubernetes/mlflow/ingress.yaml`
  - Host: mlflow.blockchainradar.xyz
  - TLS with cert-manager
  - NGINX ingress class

- [ ] **3.7** Apply all manifests
  ```bash
  kubectl apply -f kubernetes/mlflow/
  ```

- [ ] **3.8** Verify deployment
  ```bash
  kubectl get pods -n mlflow
  kubectl logs -n mlflow -l app=mlflow-server
  ```

- [ ] **3.9** Add DNS A record
  - Type: A
  - Host: mlflow
  - Domain: blockchainradar.xyz
  - Value: 34.143.244.90
  - TTL: 300

- [ ] **3.10** Wait for TLS certificate
  ```bash
  kubectl get certificate -n mlflow -w
  ```

- [ ] **3.11** Access MLFlow UI
  - URL: https://mlflow.blockchainradar.xyz
  - Verify UI loads

**Success Criteria**: MLFlow accessible via HTTPS, UI functional

---

### Task 4: Register Models in MLFlow ⏱️ 30 min

- [ ] **4.1** Create `mlops/register_models.py`
  - Copy script from phase-4-mlops-simplified.md
  - Configure tracking URI: https://mlflow.blockchainradar.xyz

- [ ] **4.2** Register LLM model (Qwen3-0.6B)
  - Model name: qwen3-0.6b-instruct
  - Tags: task=text-generation, framework=vllm
  - Log performance metrics (793 TPS, 80ms P99)
  - Transition to Production stage

- [ ] **4.3** Register Embedding model (EmbeddingGemma-300m)
  - Model name: embeddinggemma-300m
  - Tags: task=embedding, dimension=768
  - Log performance metrics (287ms latency)
  - Transition to Production stage

- [ ] **4.4** Run registration script
  ```bash
  python mlops/register_models.py
  ```

- [ ] **4.5** Verify in MLFlow UI
  - Navigate to https://mlflow.blockchainradar.xyz/#/models
  - Check both models registered
  - Verify Production stage

**Success Criteria**: Both models visible in MLFlow registry with Production stage

---

### Task 5: Implement Evidently Drift Monitoring ⏱️ 1.5 hours

- [ ] **5.1** Install Evidently
  ```bash
  uv add evidently
  ```

- [ ] **5.2** Create `mlops/monitoring/drift_detector.py`
  - Copy DriftDetector class from plan
  - Configure MLFlow integration
  - Implement drift detection logic

- [ ] **5.3** Test drift detection locally
  ```python
  from mlops.monitoring.drift_detector import DriftDetector
  detector = DriftDetector("https://mlflow.blockchainradar.xyz")
  results = detector.monitor_query_patterns()
  ```

- [ ] **5.4** Create `kubernetes/mlops/drift-monitoring-cronjob.yaml`
  - Schedule: Daily at 4 AM
  - Use FastAPI image
  - Configure environment variables

- [ ] **5.5** Build and push updated Docker image
  ```bash
  docker build -t gcr.io/intellirag-aide1-capstone/intellirag-api:v1.0.8 .
  docker push gcr.io/intellirag-aide1-capstone/intellirag-api:v1.0.8
  ```

- [ ] **5.6** Deploy drift monitoring CronJob
  ```bash
  kubectl apply -f kubernetes/mlops/drift-monitoring-cronjob.yaml
  ```

- [ ] **5.7** Manually trigger first run
  ```bash
  kubectl create job --from=cronjob/drift-monitoring drift-manual -n mlflow
  kubectl logs -n mlflow -l job-name=drift-manual -f
  ```

- [ ] **5.8** Verify drift report in MLFlow
  - Check for new run in MLFlow UI
  - Verify drift_share metric logged
  - Download HTML report artifact

**Success Criteria**: Drift monitoring running daily, reports in MLFlow

---

### Task 6: Create MLOps Grafana Dashboards ⏱️ 1 hour

- [ ] **6.1** Create `observability/grafana/provisioning/dashboards/json/mlops-metrics.json`
  - Copy dashboard JSON from plan
  - Include panels:
    - Model versions count
    - Production models count
    - Data drift score
    - Inference latency P95

- [ ] **6.2** Add dashboard to Grafana
  ```bash
  kubectl create configmap mlops-dashboard \
    --from-file=observability/grafana/provisioning/dashboards/json/mlops-metrics.json \
    -n observability \
    --dry-run=client -o yaml | kubectl apply -f -
  ```

- [ ] **6.3** Restart Grafana to load dashboard
  ```bash
  kubectl rollout restart deployment prometheus-grafana -n observability
  ```

- [ ] **6.4** Access Grafana and verify dashboard
  - URL: https://grafana.blockchainradar.xyz
  - Navigate to Dashboards → MLOps Model Performance
  - Verify panels load data

- [ ] **6.5** Configure alerts (optional)
  - High drift score (>30%)
  - High inference latency (P95 >2s)

**Success Criteria**: MLOps dashboard visible in Grafana with metrics

---

### Task 7: Model Deployment Webhook (Optional) ⏱️ 1 hour

- [ ] **7.1** Create `mlops/webhooks/mlflow_webhook_handler.py`
  - Copy webhook handler from plan
  - Configure KServe webhook URL

- [ ] **7.2** Test webhook locally (optional)
  ```bash
  uvicorn mlops.webhooks.mlflow_webhook_handler:app --port 8001
  ```

- [ ] **7.3** Configure MLFlow webhook (future task)
  - Add webhook endpoint in MLFlow settings
  - Test model transition triggers webhook

**Success Criteria**: Webhook handler code ready for future integration

---

### Task 8: Documentation & Verification ⏱️ 30 min

- [ ] **8.1** Update CLAUDE.md
  - Add MLFlow tracking URI
  - Document model registration process
  - Add drift monitoring commands

- [ ] **8.2** Create Phase 4 completion summary
  - Document deployment URLs
  - List all registered models
  - Include cost breakdown

- [ ] **8.3** Update quick-start-guide.md
  - Add MLFlow access instructions
  - Document drift monitoring commands

- [ ] **8.4** Test end-to-end workflow
  1. Register new model version in MLFlow
  2. Run drift monitoring manually
  3. View results in Grafana dashboard

- [ ] **8.5** Take screenshots for documentation
  - MLFlow UI (models page)
  - Grafana MLOps dashboard
  - Drift report example

**Success Criteria**: All documentation updated, workflow validated

---

## ✅ Phase 4 Completion Checklist

### Infrastructure
- [ ] PostgreSQL running in mlflow namespace
- [ ] GCS bucket `intellirag-mlflow-artifacts` created
- [ ] MLFlow server deployed and accessible
- [ ] MLFlow UI at https://mlflow.blockchainradar.xyz ✅

### Model Registry
- [ ] Qwen3-0.6B registered in MLFlow
- [ ] EmbeddingGemma-300m registered in MLFlow
- [ ] Both models in Production stage
- [ ] Model metadata logged (endpoints, metrics)

### Drift Monitoring
- [ ] Evidently installed and configured
- [ ] Drift detection script working
- [ ] CronJob scheduled (daily 4 AM)
- [ ] Drift reports in MLFlow ✅

### Dashboards
- [ ] MLOps dashboard added to Grafana
- [ ] All panels showing data
- [ ] Alerts configured (optional)

### Documentation
- [ ] CLAUDE.md updated
- [ ] Quick-start guide updated
- [ ] Phase 4 summary created
- [ ] Architecture diagrams updated

---

## 🚀 Getting Started

1. **Read the plan**: Review `docs/plans/phase-4-mlops-simplified.md`
2. **Start with Task 1**: Deploy PostgreSQL (easiest first)
3. **Work sequentially**: Each task builds on previous ones
4. **Test frequently**: Verify each component before moving on
5. **Document as you go**: Update docs after each major task

---

## 📊 Progress Tracking

| Task | Status | Duration | Completed |
|------|--------|----------|-----------|
| 1. PostgreSQL | ⏳ Not Started | 30 min | - |
| 2. GCS Bucket | ⏳ Not Started | 15 min | - |
| 3. MLFlow Server | ⏳ Not Started | 1 hour | - |
| 4. Register Models | ⏳ Not Started | 30 min | - |
| 5. Drift Monitoring | ⏳ Not Started | 1.5 hours | - |
| 6. Grafana Dashboard | ⏳ Not Started | 1 hour | - |
| 7. Webhook (Optional) | ⏳ Not Started | 1 hour | - |
| 8. Documentation | ⏳ Not Started | 30 min | - |

**Total Estimated Time**: 6-7 hours (across 3-4 days)

---

**Start Date**: TBD
**Target Completion**: TBD
**Last Updated**: 2025-11-27
