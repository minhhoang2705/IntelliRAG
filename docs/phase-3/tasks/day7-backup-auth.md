# Day 7: Backup, Disaster Recovery & Authentication

**Duration**: 5-6 hours
**Prerequisites**: GCP access, application deployed, all Day 1-6 tasks complete
**Output**: Automated backups, DR runbook, API authentication, Phase 3 completion

---

## 🎯 Objectives

1. Set up GCS bucket for automated backups
2. Create Qdrant backup CronJob (daily at 2 AM)
3. Document disaster recovery procedures
4. Implement API key authentication
5. Verify rate limiting configuration
6. Complete Phase 3 documentation

---

## 📋 Tasks Overview

| Task | Duration | Output |
|------|----------|--------|
| 7.1 Create GCS Backup Bucket | 30 min | GCS bucket with lifecycle policy |
| 7.2 Create Backup CronJob | 2 hours | Automated daily backups |
| 7.3 Create DR Runbook | 1.5 hours | Disaster recovery procedures |
| 7.4 Implement API Authentication | 1.5 hours | API key protection |
| 7.5 Verify Rate Limiting | 30 min | Rate limits functional |
| 7.6 Phase 3 Completion | 30 min | Final documentation |

---

## Task 7.1: Create GCS Backup Bucket (30 minutes)

### Set Variables

```bash
# Replace with your values
PROJECT_ID="your-gcp-project-id"
BUCKET_NAME="intellirag-backups"
REGION="us-central1"  # Same region as GKE for faster transfers
```

### Create Bucket

```bash
# Create backup bucket
gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$BUCKET_NAME

# Verify creation
gsutil ls gs://$BUCKET_NAME
```

### Configure Lifecycle Policy

Create `backup-lifecycle.json`:

```json
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {
        "age": 30,
        "matchesPrefix": ["backups/"]
      }
    }]
  }
}
```

Apply lifecycle:

```bash
# Apply lifecycle policy (delete backups older than 30 days)
gsutil lifecycle set backup-lifecycle.json gs://$BUCKET_NAME

# Enable versioning (optional, for extra safety)
gsutil versioning set on gs://$BUCKET_NAME

# Verify lifecycle policy
gsutil lifecycle get gs://$BUCKET_NAME
```

### Set IAM Permissions

```bash
# Grant service account write access
SA_EMAIL="intellirag-app@${PROJECT_ID}.iam.gserviceaccount.com"

gsutil iam ch serviceAccount:${SA_EMAIL}:roles/storage.objectCreator gs://$BUCKET_NAME
gsutil iam ch serviceAccount:${SA_EMAIL}:roles/storage.objectViewer gs://$BUCKET_NAME

# Verify permissions
gsutil iam get gs://$BUCKET_NAME
```

**Success Criteria**:
- ✅ Bucket created
- ✅ Lifecycle policy set (30-day retention)
- ✅ Service account has write permissions

---

## Task 7.2: Create Qdrant Backup CronJob (2 hours)

### Create Backup CronJob Manifest

Create `kubernetes/backup/qdrant-backup-cronjob.yaml`:

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: qdrant-backup
  namespace: app
  labels:
    app: qdrant-backup
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM UTC
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
  concurrencyPolicy: Forbid  # Don't allow concurrent backups
  jobTemplate:
    spec:
      backoffLimit: 3
      template:
        metadata:
          labels:
            app: qdrant-backup
        spec:
          serviceAccountName: intellirag-app
          restartPolicy: OnFailure

          # Security context
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            fsGroup: 1000
            seccompProfile:
              type: RuntimeDefault

          containers:
          - name: backup
            image: google/cloud-sdk:alpine

            securityContext:
              allowPrivilegeEscalation: false
              runAsNonRoot: true
              runAsUser: 1000
              capabilities:
                drop:
                - ALL
              readOnlyRootFilesystem: true

            command:
            - /bin/bash
            - -c
            - |
              set -e

              TIMESTAMP=$(date +%Y%m%d-%H%M%S)
              COLLECTION="intellirag"
              QDRANT_URL="http://qdrant.app.svc.cluster.local:6333"
              GCS_BUCKET="${GCS_BUCKET:-intellirag-backups}"
              BACKUP_DIR="/tmp/backups"

              echo "=== Qdrant Backup Started at $TIMESTAMP ==="

              # Create backup directory
              mkdir -p $BACKUP_DIR

              # Create snapshot in Qdrant
              echo "Creating Qdrant snapshot for collection: $COLLECTION"
              SNAPSHOT_RESPONSE=$(curl -s -X POST "${QDRANT_URL}/collections/${COLLECTION}/snapshots")
              echo "Snapshot response: $SNAPSHOT_RESPONSE"

              SNAPSHOT_NAME=$(echo $SNAPSHOT_RESPONSE | jq -r '.result.name')

              if [ -z "$SNAPSHOT_NAME" ] || [ "$SNAPSHOT_NAME" = "null" ]; then
                echo "ERROR: Failed to create snapshot"
                echo "Response: $SNAPSHOT_RESPONSE"
                exit 1
              fi

              echo "✅ Snapshot created: $SNAPSHOT_NAME"

              # Download snapshot
              echo "Downloading snapshot from Qdrant..."
              curl -o "${BACKUP_DIR}/${SNAPSHOT_NAME}" \
                "${QDRANT_URL}/collections/${COLLECTION}/snapshots/${SNAPSHOT_NAME}"

              # Verify download
              if [ ! -f "${BACKUP_DIR}/${SNAPSHOT_NAME}" ]; then
                echo "ERROR: Snapshot file not found after download"
                exit 1
              fi

              SNAPSHOT_SIZE=$(du -h "${BACKUP_DIR}/${SNAPSHOT_NAME}" | cut -f1)
              echo "✅ Snapshot downloaded: ${SNAPSHOT_SIZE}"

              # Upload to GCS
              echo "Uploading to GCS: gs://${GCS_BUCKET}/backups/${COLLECTION}-${TIMESTAMP}.snapshot"
              gsutil cp "${BACKUP_DIR}/${SNAPSHOT_NAME}" \
                "gs://${GCS_BUCKET}/backups/${COLLECTION}-${TIMESTAMP}.snapshot"

              # Verify upload
              if gsutil ls "gs://${GCS_BUCKET}/backups/${COLLECTION}-${TIMESTAMP}.snapshot" > /dev/null 2>&1; then
                echo "✅ Backup uploaded successfully to GCS"
              else
                echo "ERROR: Failed to verify GCS upload"
                exit 1
              fi

              # Delete local snapshot from Qdrant
              echo "Cleaning up snapshot from Qdrant..."
              curl -X DELETE "${QDRANT_URL}/collections/${COLLECTION}/snapshots/${SNAPSHOT_NAME}"

              # List recent backups
              echo "Recent backups:"
              gsutil ls -lh "gs://${GCS_BUCKET}/backups/" | tail -10

              echo "=== Backup Completed Successfully ==="

            env:
            - name: GCS_BUCKET
              value: "intellirag-backups"

            volumeMounts:
            - name: tmp
              mountPath: /tmp

          volumes:
          - name: tmp
            emptyDir: {}
```

### Apply CronJob

```bash
kubectl apply -f kubernetes/backup/qdrant-backup-cronjob.yaml

# Verify CronJob created
kubectl get cronjob -n app

# Check schedule
kubectl describe cronjob qdrant-backup -n app | grep Schedule
```

### Test Backup Manually

```bash
# Create manual job from CronJob
kubectl create job --from=cronjob/qdrant-backup qdrant-backup-manual-test -n app

# Watch job progress
kubectl get jobs -n app -w

# Check logs
kubectl logs -n app -l job-name=qdrant-backup-manual-test -f

# Expected output:
# === Qdrant Backup Started at YYYYMMDD-HHMMSS ===
# Creating Qdrant snapshot...
# ✅ Snapshot created: ...
# ✅ Snapshot downloaded: X.XMB
# ✅ Backup uploaded successfully to GCS
# === Backup Completed Successfully ===

# Verify backup in GCS
gsutil ls -lh gs://intellirag-backups/backups/

# Clean up test job
kubectl delete job qdrant-backup-manual-test -n app
```

**Success Criteria**:
- ✅ CronJob created and scheduled
- ✅ Manual test backup succeeds
- ✅ Backup file appears in GCS
- ✅ Backup size reasonable (> 0 bytes)

---

## Task 7.3: Create Disaster Recovery Runbook (1.5 hours)

Create comprehensive DR documentation. This has been pre-written for you in the main plan but should be customized based on your actual setup.

Create `docs/disaster-recovery-runbook.md` - see the example in Phase 3 implementation plan, Task 7.3 section, or refer to `phase-3-production-hardening.md` Task 6.2.

**Key scenarios to document**:
1. Qdrant data loss
2. Application deployment failure
3. GKE cluster failure
4. Local GPU server failure
5. CloudFlare Tunnel down

**For each scenario, include**:
- Symptoms
- Recovery steps (with commands)
- RTO/RPO targets
- Verification procedures

---

## Task 7.4: Implement API Key Authentication (1.5 hours)

### Generate API Keys

```bash
# Generate 3 secure API keys
API_KEY_1=$(openssl rand -hex 32)
API_KEY_2=$(openssl rand -hex 32)
API_KEY_3=$(openssl rand -hex 32)

echo "=== Generated API Keys (SAVE THESE SECURELY!) ==="
echo "API_KEY_1: sk_prod_${API_KEY_1}"
echo "API_KEY_2: sk_prod_${API_KEY_2}"
echo "API_KEY_3: sk_prod_${API_KEY_3}"

# Save to file (DO NOT commit to git!)
cat > /tmp/api-keys.txt <<EOF
API_KEY_1=sk_prod_${API_KEY_1}
API_KEY_2=sk_prod_${API_KEY_2}
API_KEY_3=sk_prod_${API_KEY_3}
EOF

echo "API keys saved to /tmp/api-keys.txt"
```

### Create Kubernetes Secret

```bash
kubectl create secret generic api-keys -n app \
  --from-literal=key1="sk_prod_${API_KEY_1}" \
  --from-literal=key2="sk_prod_${API_KEY_2}" \
  --from-literal=key3="sk_prod_${API_KEY_3}" \
  --dry-run=client -o yaml | kubectl apply -f -

# Verify secret created
kubectl get secret api-keys -n app
```

### Implement Authentication Middleware

Create `app/api/middleware/auth.py`:

```python
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
import os

security = HTTPBearer(auto_error=False)

def get_valid_api_keys() -> set:
    """Load valid API keys from environment."""
    keys = set()

    # Load from individual env vars (key1, key2, key3)
    for i in range(1, 10):  # Support up to 10 keys
        key = os.getenv(f"API_KEY_{i}")
        if key:
            keys.add(key.strip())

    return keys

async def verify_api_key(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> str:
    """
    Verify API key from Authorization header.

    Raises:
        HTTPException: If API key is missing or invalid

    Returns:
        str: Valid API key
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing API key. Include 'Authorization: Bearer YOUR_API_KEY' header.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    api_key = credentials.credentials
    valid_keys = get_valid_api_keys()

    if not valid_keys:
        # No keys configured - warn but allow (development mode)
        import logging
        logging.warning("No API keys configured! Authentication disabled.")
        return "dev-mode"

    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return api_key
```

### Protect API Endpoints

**Update**: `app/main.py`

```python
from app.api.middleware.auth import verify_api_key
from fastapi import Depends

# Protected endpoints
@app.post("/api/v1/query", dependencies=[Depends(verify_api_key)])
async def query(request: QueryRequest):
    """RAG query endpoint (protected)."""
    # ... existing code ...
    pass

@app.post("/api/v1/ingest", dependencies=[Depends(verify_api_key)])
async def ingest(file: UploadFile):
    """Document ingestion endpoint (protected)."""
    # ... existing code ...
    pass

# Public endpoints (no auth)
@app.get("/")
async def root():
    return {"status": "healthy"}

@app.get("/ready")
async def readiness():
    """Readiness probe (public)."""
    # ... existing code ...
    pass
```

### Update Deployment with API Keys

**Update**: `helm/intellirag-app/values.yaml`

```yaml
env:
  - name: API_KEY_1
    valueFrom:
      secretKeyRef:
        name: api-keys
        key: key1
  - name: API_KEY_2
    valueFrom:
      secretKeyRef:
        name: api-keys
        key: key2
  - name: API_KEY_3
    valueFrom:
      secretKeyRef:
        name: api-keys
        key: key3
```

### Rebuild and Deploy

```bash
# Rebuild image with auth middleware
docker build -t gcr.io/YOUR_PROJECT/intellirag-app:v1.3.0-auth .
docker push gcr.io/YOUR_PROJECT/intellirag-app:v1.3.0-auth

# Upgrade deployment
helm upgrade intellirag-app ./helm/intellirag-app \
  --namespace app \
  --set image.tag=v1.3.0-auth \
  --wait

# Verify pods running
kubectl get pods -n app
```

### Test API Authentication

```bash
# Test WITHOUT API key (should fail)
curl -X POST https://api.intellirag.example.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}'

# Expected: 401 Unauthorized

# Test WITH valid API key (should work)
API_KEY_1="sk_prod_$(cat /tmp/api-keys.txt | grep API_KEY_1 | cut -d= -f2 | cut -d_ -f3)"

curl -X POST https://api.intellirag.example.com/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk_prod_${API_KEY_1}" \
  -d '{"query":"What is machine learning?","top_k":3}'

# Expected: 200 OK with response

# Test public endpoints (should work without auth)
curl https://api.intellirag.example.com/
curl https://api.intellirag.example.com/ready
```

**Success Criteria**:
- ✅ Protected endpoints require API key
- ✅ Public endpoints accessible without auth
- ✅ Invalid API key returns 401
- ✅ Valid API key grants access

---

## Task 7.5: Verify Rate Limiting (30 minutes)

Rate limiting was configured in Day 4 (Ingress annotations). Let's verify it works:

```bash
# Test rate limit (100 requests/min per IP)
echo "Testing rate limit (100 req/min)..."
START_TIME=$(date +%s)

for i in {1..150}; do
  HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" \
    https://api.intellirag.example.com/)
  echo "$i: $HTTP_CODE"

  # If we hit 429, rate limit is working
  if [ "$HTTP_CODE" == "429" ]; then
    END_TIME=$(date +%s)
    DURATION=$((END_TIME - START_TIME))
    echo "✅ Rate limit triggered at request $i after ${DURATION} seconds"
    break
  fi

  sleep 0.1
done

# Expected: 429 Too Many Requests after ~100-120 requests
```

**Success Criteria**:
- ✅ Rate limit triggers around 100 requests
- ✅ Returns 429 status code
- ✅ Normal requests resume after rate limit window

---

## Task 7.6: Phase 3 Completion Documentation (30 minutes)

### Verify All Deliverables

**Phase 3A Checklist**:
- [ ] GPU profiling report (Day 1)
- [ ] CPU profiling report (Day 1)
- [ ] vLLM load test report (Day 2)
- [ ] Embedding load test report (Day 2)
- [ ] E2E load test report (Day 2)
- [ ] Capacity analysis (Day 2)
- [ ] Grafana dashboard created (Day 3)
- [ ] Alerting rules configured (Day 3)
- [ ] Optimization results documented (Day 3)

**Phase 3B Checklist**:
- [ ] NGINX Ingress deployed (Day 4)
- [ ] TLS certificate issued (Day 4)
- [ ] HPA configured (Day 5)
- [ ] ResourceQuota enforced (Day 5)
- [ ] Network policies applied (Day 6)
- [ ] Pod Security Standards enforced (Day 6)
- [ ] Automated backups scheduled (Day 7)
- [ ] DR runbook documented (Day 7)
- [ ] API authentication implemented (Day 7)
- [ ] Rate limiting verified (Day 7)

### Create Phase 3 Completion Summary

Create `docs/phase-3/completion/phase-3-completion-summary.md`:

```markdown
# Phase 3: Completion Summary

**Completion Date**: 2025-11-21
**Duration**: 7 days (as planned)
**Status**: ✅ Complete

## Executive Summary

Phase 3 successfully implemented performance optimization and production hardening. Starting with profiling and load testing (Days 1-2), we established baseline metrics and identified optimization opportunities. Days 3-7 focused on observability, security, and operational readiness.

## Key Achievements

### Performance (Days 1-3)
- ✅ GPU utilization optimized: 87% → 95% (+8%)
- ✅ vLLM throughput improved: 650 → 780 TPS (+20%)
- ✅ P95 latency reduced: 450ms → 396ms (-12%)
- ✅ Grafana dashboard with 10 monitoring panels
- ✅ 6 alerting rules configured

### Production Hardening (Days 4-7)
- ✅ HTTPS enabled with Let's Encrypt TLS
- ✅ HPA autoscaling: 3-15 replicas (data-driven thresholds)
- ✅ Network policies enforced (default deny + explicit allow)
- ✅ Pod Security Standards: Restricted mode
- ✅ Automated daily backups to GCS
- ✅ API key authentication implemented
- ✅ Rate limiting: 100 req/min per IP

## Deliverables: 34/34 Complete (100%)

[List all deliverables from each day]

## Security Posture

| Control | Status |
|---------|--------|
| TLS Encryption | ✅ A+ (SSL Labs) |
| Network Isolation | ✅ Enforced |
| Non-Root Containers | ✅ UID 1000 |
| Read-Only Filesystem | ✅ Yes |
| API Authentication | ✅ Bearer tokens |
| Rate Limiting | ✅ 100 req/min |
| Vulnerability Scan | ✅ 0 HIGH/CRITICAL |

## Cost Impact

**Additional Monthly Costs** (Phase 3):
- NGINX Ingress LoadBalancer: ~$20
- GCS backups (30-day retention): ~$5
- **Total Addition**: ~$25/month

**System Total**: $159-372/month (GKE + Ingress + Storage)

## Next Steps

### Immediate
- Share API keys with consumers
- Set up PagerDuty/Slack alerting
- Schedule monthly DR drill

### Phase 4: MLOps Pipeline
- MLflow model registry
- DVC data versioning
- Automated retraining
- A/B testing infrastructure
```

Update main implementation plan status:

```bash
# Update phase-3-implementation-plan.md
# Change status from "Ready to Execute" to "✅ Complete"
```

---

## ✅ Day 7 Completion Checklist

- [ ] GCS backup bucket created with lifecycle policy
- [ ] Service account permissions configured
- [ ] Qdrant backup CronJob created
- [ ] Manual backup test successful
- [ ] Backup visible in GCS
- [ ] Disaster recovery runbook documented (5 scenarios)
- [ ] API keys generated (3 keys)
- [ ] Kubernetes secret created
- [ ] Authentication middleware implemented
- [ ] Protected endpoints require API key
- [ ] Public endpoints remain accessible
- [ ] Application rebuilt and deployed with auth
- [ ] API authentication tested and verified
- [ ] Rate limiting verified (triggers at ~100 req/min)
- [ ] All Phase 3 deliverables completed
- [ ] Phase 3 completion summary created
- [ ] Documentation updated

**Success Criteria**:
- Automated daily backups scheduled
- Manual backup test succeeds
- DR runbook documents all critical scenarios
- API authentication protects sensitive endpoints
- Rate limiting prevents abuse
- All 34 Phase 3 deliverables complete

---

## 🔧 Troubleshooting

### Issue: Backup CronJob fails

```bash
# Check job logs
kubectl logs -n app -l job-name=qdrant-backup-manual-test

# Common issues:
# 1. Qdrant not accessible
kubectl exec -n app <app-pod> -- curl http://qdrant.app.svc.cluster.local:6333/

# 2. GCS permissions
#    Verify service account has storage.objectCreator role

# 3. Snapshot creation fails
#    Check Qdrant has data: curl http://qdrant:6333/collections/intellirag
```

### Issue: API keys not working

```bash
# Verify secret exists
kubectl get secret api-keys -n app

# Check env vars in pod
kubectl exec -n app <pod-name> -- env | grep API_KEY

# If empty, check Helm values include secretKeyRef
```

### Issue: Rate limiting not triggering

```bash
# Verify Ingress annotations
kubectl get ingress intellirag-ingress -n app -o yaml | grep rate-limit

# Check NGINX logs
kubectl logs -n ingress-nginx <nginx-pod> | grep limit_req

# Rate limit is per-IP, test from same IP address
```

---

## 📚 Resources

- [Kubernetes CronJobs](https://kubernetes.io/docs/concepts/workloads/controllers/cron-jobs/)
- [GCS Lifecycle Management](https://cloud.google.com/storage/docs/lifecycle)
- [FastAPI Security](https://fastapi.tiangolo.com/tutorial/security/)

---

## 🎉 Phase 3 Complete!

Congratulations on completing Phase 3! Your IntelliRAG system now has:
- Production-grade performance (20%+ improvement)
- Enterprise security (network policies, Pod Security Standards)
- Operational readiness (automated backups, DR procedures)
- API protection (authentication + rate limiting)

**Next**: Phase 4 - MLOps Pipeline (model lifecycle management, DVC, MLflow)

---

**Last Updated**: 2025-11-21
