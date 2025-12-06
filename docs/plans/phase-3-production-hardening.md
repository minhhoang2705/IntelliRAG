# Phase 3: Production Hardening

**Duration**: 4-5 days
**Status**: Pending
**Dependencies**: Phase 0-2 (Infrastructure, Application, Model Serving)

---

## 📋 Overview

This phase implements production-grade security, reliability, and scaling capabilities. We'll configure NGINX Ingress Controller with TLS termination, implement autoscaling policies, set resource quotas, establish backup procedures, and enforce security best practices.

**Key Components**:
- **NGINX Ingress Controller**: API gateway with TLS, rate limiting, and authentication
- **Horizontal Pod Autoscaler**: Dynamic scaling based on CPU/memory metrics
- **Resource Management**: Quotas, limits, and QoS classes
- **Network Policies**: Pod-level firewall rules
- **Security Policies**: Pod Security Standards and RBAC
- **Backup & Recovery**: Automated backup for Qdrant and configuration

---

## 🎯 Objectives

### Primary Goals
1. Deploy NGINX Ingress Controller with TLS certificates
2. Implement Horizontal Pod Autoscaler for application services
3. Configure resource quotas and limit ranges per namespace
4. Establish network policies for pod-to-pod communication
5. Enforce Pod Security Standards (restricted mode)
6. Set up automated backups for critical data
7. Implement rate limiting and authentication

### Success Criteria
- ✅ HTTPS enabled with valid TLS certificates
- ✅ Application autoscales from 3 to 15 replicas under load
- ✅ Resource quotas prevent namespace over-consumption
- ✅ Network policies restrict unauthorized traffic
- ✅ All pods run with non-root users and read-only filesystems
- ✅ Automated daily backups of Qdrant collections
- ✅ Rate limiting prevents API abuse (100 req/min per IP)
- ✅ Zero security vulnerabilities in deployment

---

## 🛠️ Prerequisites

- Phase 0-2 completed (GKE cluster, application, and models deployed)
- Domain name configured (e.g., intellirag.example.com)
- DNS pointing to GKE cluster IP
- cert-manager installed on GKE (for TLS certificates)

---

## 📦 Task 1: Deploy NGINX Ingress Controller

### 1.1 Install NGINX Ingress Controller

```bash
# Add NGINX Helm repository
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update

# Install NGINX Ingress Controller on GKE
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace \
  --set controller.service.type=LoadBalancer \
  --set controller.metrics.enabled=true \
  --set controller.podAnnotations."prometheus\.io/scrape"=true \
  --set controller.podAnnotations."prometheus\.io/port"=10254

# Wait for LoadBalancer IP
kubectl get svc -n ingress-nginx ingress-nginx-controller -w

# Get external IP
INGRESS_IP=$(kubectl get svc -n ingress-nginx ingress-nginx-controller -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
echo "Ingress IP: $INGRESS_IP"
```

### 1.2 Configure DNS

```bash
# Update DNS records to point to Ingress IP
# Example with CloudFlare API:
curl -X POST "https://api.cloudflare.com/client/v4/zones/ZONE_ID/dns_records" \
  -H "Authorization: Bearer YOUR_API_TOKEN" \
  -H "Content-Type: application/json" \
  --data '{
    "type": "A",
    "name": "api.intellirag.example.com",
    "content": "'$INGRESS_IP'",
    "ttl": 120,
    "proxied": false
  }'

# Verify DNS propagation
dig api.intellirag.example.com +short
```

### 1.3 Install cert-manager for TLS

```bash
# Install cert-manager
kubectl apply -f https://github.com/cert-manager/cert-manager/releases/download/v1.13.0/cert-manager.yaml

# Wait for cert-manager to be ready
kubectl wait --for=condition=Available --timeout=300s deployment/cert-manager -n cert-manager

# Create ClusterIssuer for Let's Encrypt
cat <<EOF | kubectl apply -f -
apiVersion: cert-manager.io/v1
kind: ClusterIssuer
metadata:
  name: letsencrypt-prod
spec:
  acme:
    server: https://acme-v02.api.letsencrypt.org/directory
    email: admin@intellirag.example.com
    privateKeySecretRef:
      name: letsencrypt-prod
    solvers:
    - http01:
        ingress:
          class: nginx
EOF
```

### 1.4 Create Ingress Resource

**File**: `kubernetes/app/ingress.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: intellirag-ingress
  namespace: app
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/limit-rps: "10"
    nginx.ingress.kubernetes.io/limit-connections: "50"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    nginx.ingress.kubernetes.io/force-ssl-redirect: "true"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
    nginx.ingress.kubernetes.io/proxy-read-timeout: "300"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "300"
    nginx.ingress.kubernetes.io/enable-cors: "true"
    nginx.ingress.kubernetes.io/cors-allow-origin: "https://intellirag.example.com"
spec:
  ingressClassName: nginx
  tls:
  - hosts:
    - api.intellirag.example.com
    secretName: intellirag-tls
  rules:
  - host: api.intellirag.example.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: intellirag-app
            port:
              number: 8000
```

```bash
# Apply Ingress
kubectl apply -f kubernetes/app/ingress.yaml

# Watch certificate issuance
kubectl get certificate -n app -w

# Verify certificate is ready
kubectl describe certificate intellirag-tls -n app

# Test HTTPS endpoint
curl -v https://api.intellirag.example.com/health
```

---

## 📦 Task 2: Configure Horizontal Pod Autoscaler

### 2.1 Verify Metrics Server

```bash
# Check if metrics-server is running (should be enabled on GKE Autopilot by default)
kubectl get deployment metrics-server -n kube-system

# If not installed, install it:
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Verify metrics are available
kubectl top nodes
kubectl top pods -n app
```

### 2.2 Update HPA Configuration

**File**: `kubernetes/app/hpa.yaml`
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: intellirag-app-hpa
  namespace: app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: intellirag-app
  minReplicas: 3
  maxReplicas: 15
  metrics:
  # CPU-based scaling
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  # Memory-based scaling
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75
  # Custom metric: Request rate (if available)
  # - type: Pods
  #   pods:
  #     metric:
  #       name: http_requests_per_second
  #     target:
  #       type: AverageValue
  #       averageValue: "100"
  behavior:
    scaleDown:
      stabilizationWindowSeconds: 300
      policies:
      - type: Percent
        value: 50
        periodSeconds: 60
      - type: Pods
        value: 2
        periodSeconds: 60
      selectPolicy: Min
    scaleUp:
      stabilizationWindowSeconds: 60
      policies:
      - type: Percent
        value: 100
        periodSeconds: 30
      - type: Pods
        value: 4
        periodSeconds: 30
      selectPolicy: Max
```

```bash
# Apply HPA
kubectl apply -f kubernetes/app/hpa.yaml

# Verify HPA status
kubectl get hpa -n app
kubectl describe hpa intellirag-app-hpa -n app

# Expected output:
# - Current replicas: 3
# - Desired replicas: 3
# - Current CPU/Memory: <70%/75%
```

### 2.3 Test Autoscaling

```bash
# Port-forward to application
kubectl port-forward -n app svc/intellirag-app 8000:8000

# Run load test (in another terminal)
hey -n 10000 -c 100 -q 10 http://localhost:8000/health

# Watch HPA scale up
kubectl get hpa -n app -w
kubectl get pods -n app -w

# Expected: Replicas increase from 3 to 8-12 under load

# After test completes, watch scale down (takes 5 minutes)
# Expected: Gradual scale down back to 3 replicas
```

---

## 📦 Task 3: Resource Quotas and Limit Ranges

### 3.1 Create ResourceQuota

**File**: `kubernetes/app/resource-quota.yaml`
```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: app-quota
  namespace: app
spec:
  hard:
    requests.cpu: "30"
    requests.memory: 60Gi
    limits.cpu: "60"
    limits.memory: 120Gi
    persistentvolumeclaims: "10"
    services.loadbalancers: "0"
    count/deployments.apps: "10"
    count/services: "10"
```

```bash
# Apply ResourceQuota
kubectl apply -f kubernetes/app/resource-quota.yaml

# Verify quota
kubectl describe resourcequota app-quota -n app
```

### 3.2 Create LimitRange

**File**: `kubernetes/app/limit-range.yaml`
```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: app-limit-range
  namespace: app
spec:
  limits:
  # Container defaults
  - type: Container
    default:
      cpu: 1000m
      memory: 2Gi
    defaultRequest:
      cpu: 500m
      memory: 1Gi
    max:
      cpu: 4000m
      memory: 8Gi
    min:
      cpu: 100m
      memory: 128Mi
  # Pod limits
  - type: Pod
    max:
      cpu: 8000m
      memory: 16Gi
    min:
      cpu: 100m
      memory: 128Mi
```

```bash
# Apply LimitRange
kubectl apply -f kubernetes/app/limit-range.yaml

# Verify limit range
kubectl describe limitrange app-limit-range -n app
```

---

## 📦 Task 4: Network Policies

### 4.1 Create Default Deny Policy

**File**: `kubernetes/app/network-policy-deny-all.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: app
spec:
  podSelector: {}
  policyTypes:
  - Ingress
  - Egress
```

### 4.2 Create Application Network Policy

**File**: `kubernetes/app/network-policy-app.yaml`
```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: intellirag-app-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: intellirag-app
  policyTypes:
  - Ingress
  - Egress
  ingress:
  # Allow traffic from Ingress Controller
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  # Allow traffic from same namespace (for debugging)
  - from:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 8000
  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    - podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
  # Allow Qdrant
  - to:
    - podSelector:
        matchLabels:
          app: qdrant
    ports:
    - protocol: TCP
      port: 6333
  # Allow external HTTPS (for GCS, LLM, embeddings)
  - to:
    - namespaceSelector: {}
    ports:
    - protocol: TCP
      port: 443
  # Allow Jaeger tracing
  - to:
    - namespaceSelector:
        matchLabels:
          name: observability
    ports:
    - protocol: UDP
      port: 6831
  # Allow Prometheus scraping
  - to:
    - namespaceSelector:
        matchLabels:
          name: observability
    ports:
    - protocol: TCP
      port: 8000
```

```bash
# Apply network policies
kubectl apply -f kubernetes/app/network-policy-deny-all.yaml
kubectl apply -f kubernetes/app/network-policy-app.yaml

# Verify policies
kubectl get networkpolicy -n app
kubectl describe networkpolicy intellirag-app-policy -n app
```

---

## 📦 Task 5: Pod Security Standards

### 5.1 Enforce Restricted Security Standard

```bash
# Label namespace for restricted security
kubectl label namespace app pod-security.kubernetes.io/enforce=restricted
kubectl label namespace app pod-security.kubernetes.io/audit=restricted
kubectl label namespace app pod-security.kubernetes.io/warn=restricted

# Verify labels
kubectl get namespace app --show-labels
```

### 5.2 Update Deployment for Compliance

**File**: Update `helm/intellirag-app/templates/deployment.yaml`

Ensure the following security context is set:

```yaml
spec:
  template:
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        fsGroup: 1000
        seccompProfile:
          type: RuntimeDefault
      containers:
      - name: {{ .Chart.Name }}
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true
        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/.cache
      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}
```

```bash
# Upgrade Helm release with security updates
helm upgrade intellirag ./helm/intellirag-app \
  --namespace app \
  --values helm/intellirag-app/values-prod.yaml \
  --wait

# Verify pods are running with restricted security
kubectl get pods -n app
kubectl describe pod -n app <pod-name> | grep -A 10 "Security Context"
```

---

## 📦 Task 6: Backup and Disaster Recovery

### 6.1 Create Backup CronJob for Qdrant

**File**: `kubernetes/backup/qdrant-backup-cronjob.yaml`
```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: qdrant-backup
  namespace: app
spec:
  schedule: "0 2 * * *"  # Daily at 2 AM
  successfulJobsHistoryLimit: 7
  failedJobsHistoryLimit: 3
  jobTemplate:
    spec:
      template:
        spec:
          serviceAccountName: intellirag-app
          restartPolicy: OnFailure
          containers:
          - name: backup
            image: google/cloud-sdk:slim
            command:
            - /bin/bash
            - -c
            - |
              set -e
              TIMESTAMP=$(date +%Y%m%d-%H%M%S)
              BACKUP_PATH="backups/qdrant-${TIMESTAMP}.snapshot"

              echo "Creating Qdrant snapshot..."
              curl -X POST http://qdrant.database.svc.cluster.local:6333/collections/intellirag/snapshots

              echo "Uploading to GCS..."
              # Implement actual backup logic here
              # Example: Download snapshot from Qdrant and upload to GCS

              echo "Backup completed: ${BACKUP_PATH}"
            env:
            - name: GCS_BUCKET
              value: "intellirag-backups"
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            fsGroup: 1000
```

```bash
# Create backup bucket
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l us-central1 gs://intellirag-backups

# Set lifecycle policy (delete backups older than 30 days)
cat > backup-lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"age": 30}
    }]
  }
}
EOF
gsutil lifecycle set backup-lifecycle.json gs://intellirag-backups

# Apply CronJob
kubectl apply -f kubernetes/backup/qdrant-backup-cronjob.yaml

# Verify CronJob
kubectl get cronjob -n app

# Manually trigger backup for testing
kubectl create job --from=cronjob/qdrant-backup qdrant-backup-manual -n app
kubectl logs -n app -l job-name=qdrant-backup-manual
```

### 6.2 Create Disaster Recovery Runbook

**File**: `docs/disaster-recovery.md`
```markdown
# Disaster Recovery Runbook

## Scenario 1: Qdrant Data Loss

### Symptoms
- Vector search returns empty results
- Application errors: "Collection not found"

### Recovery Steps
1. List available backups:
   ```bash
   gsutil ls gs://intellirag-backups/backups/
   ```

2. Identify latest backup:
   ```bash
   LATEST_BACKUP=$(gsutil ls gs://intellirag-backups/backups/ | sort -r | head -1)
   ```

3. Restore snapshot to Qdrant:
   ```bash
   # Download backup
   gsutil cp $LATEST_BACKUP /tmp/qdrant-backup.snapshot

   # Upload to Qdrant
   curl -X PUT http://qdrant.database.svc.cluster.local:6333/collections/intellirag/snapshots/recover \
     -F "snapshot=@/tmp/qdrant-backup.snapshot"
   ```

4. Verify restoration:
   ```bash
   curl http://qdrant.database.svc.cluster.local:6333/collections/intellirag
   ```

## Scenario 2: GKE Cluster Failure

### Recovery Steps
1. Provision new cluster with Terraform:
   ```bash
   cd terraform/
   terraform apply
   ```

2. Restore configurations:
   ```bash
   # Deploy observability stack
   cd kubernetes/observability/
   helmfile apply

   # Deploy application
   helm install intellirag ./helm/intellirag-app \
     --namespace app --create-namespace \
     --values helm/intellirag-app/values-prod.yaml
   ```

3. Restore Qdrant data (see Scenario 1)

4. Verify all services are healthy:
   ```bash
   kubectl get pods -A
   ```

## RTO/RPO Targets
- **Recovery Time Objective (RTO)**: 4 hours
- **Recovery Point Objective (RPO)**: 24 hours (daily backups)
```

---

## 📦 Task 7: Rate Limiting and Authentication

### 7.1 Implement API Key Authentication (Basic)

**File**: `kubernetes/app/api-key-secret.yaml`
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: api-keys
  namespace: app
type: Opaque
stringData:
  api-key-1: "sk_prod_abc123..."
  api-key-2: "sk_prod_def456..."
```

```bash
# Generate secure API keys
openssl rand -hex 32

# Create secret
kubectl apply -f kubernetes/app/api-key-secret.yaml
```

### 7.2 Update Application with Authentication Middleware

**File**: `app/api/middleware/auth.py`
```python
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os

security = HTTPBearer()

async def verify_api_key(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify API key from Authorization header."""
    api_key = credentials.credentials
    valid_keys = os.getenv("API_KEYS", "").split(",")

    if api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )

    return api_key
```

**File**: Update `app/main.py`
```python
from app.api.middleware.auth import verify_api_key
from fastapi import Depends

# Protect endpoints with API key
@app.post("/api/v1/query", dependencies=[Depends(verify_api_key)])
async def query_endpoint(request: QueryRequest):
    # ...existing code...
    pass

# Public endpoints (no auth required)
@app.get("/health")
async def health():
    return {"status": "healthy"}
```

### 7.3 Configure NGINX Rate Limiting

Update Ingress annotations (already in `kubernetes/app/ingress.yaml`):

```yaml
metadata:
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"      # 100 req/min per IP
    nginx.ingress.kubernetes.io/limit-rps: "10"        # 10 req/sec
    nginx.ingress.kubernetes.io/limit-connections: "50" # 50 concurrent connections
    nginx.ingress.kubernetes.io/limit-whitelist: "10.0.0.0/8"  # Whitelist internal IPs
```

---

## 🧪 Testing and Verification

### Test 1: TLS Certificate

```bash
# Test HTTPS endpoint
curl -v https://api.intellirag.example.com/health

# Verify certificate
openssl s_client -connect api.intellirag.example.com:443 -servername api.intellirag.example.com

# Check certificate expiry
echo | openssl s_client -connect api.intellirag.example.com:443 2>/dev/null | openssl x509 -noout -dates
```

### Test 2: Autoscaling Under Load

```bash
# Baseline: Check current replicas
kubectl get hpa -n app

# Generate load
hey -n 50000 -c 200 -q 20 https://api.intellirag.example.com/health

# Watch scaling in real-time (separate terminal)
watch -n 1 'kubectl get hpa,pods -n app'

# Expected: Replicas increase from 3 to 10-15
# After load stops: Gradual scale down to 3 over 5 minutes
```

### Test 3: Network Policy Enforcement

```bash
# Create test pod in app namespace
kubectl run test-pod -n app --image=curlimages/curl --rm -it --restart=Never -- sh

# Inside pod, test connectivity:
# Should work: Access to application service
curl http://intellirag-app.app.svc.cluster.local:8000/health

# Should work: DNS resolution
nslookup google.com

# Should be blocked: Access to other namespaces
curl http://prometheus-server.observability.svc.cluster.local

# Expected: Connection timeout or refused
```

### Test 4: Rate Limiting

```bash
# Exceed rate limit (100 req/min)
for i in {1..150}; do
  curl -s -o /dev/null -w "%{http_code}\n" https://api.intellirag.example.com/health
  sleep 0.1
done

# Expected: First 100 requests return 200, subsequent requests return 429 (Too Many Requests)
```

### Test 5: API Key Authentication

```bash
# Without API key (should fail)
curl -X POST https://api.intellirag.example.com/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{"query":"test"}'

# Expected: 401 Unauthorized

# With valid API key (should work)
curl -X POST https://api.intellirag.example.com/api/v1/query \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer sk_prod_abc123..." \
  -d '{"query":"test"}'

# Expected: 200 OK with response
```

---

## 🚨 Troubleshooting

### Issue 1: Certificate Not Issued

**Symptom**: `kubectl get certificate` shows "False" for Ready

**Debug Steps**:
```bash
# Check certificate status
kubectl describe certificate intellirag-tls -n app

# Check cert-manager logs
kubectl logs -n cert-manager deployment/cert-manager

# Check challenge status
kubectl get challenges -n app

# Common issues:
# - DNS not propagated: Wait 5-10 minutes
# - Firewall blocking port 80: Ensure Ingress is accessible
# - Rate limit hit: Wait 1 hour and retry
```

### Issue 2: HPA Not Scaling

**Symptom**: HPA shows `<unknown>` for metrics

**Debug Steps**:
```bash
# Check metrics-server
kubectl get deployment metrics-server -n kube-system
kubectl logs -n kube-system deployment/metrics-server

# Verify resource requests are set
kubectl get pod -n app <pod-name> -o yaml | grep -A 10 resources

# Check if metrics are available
kubectl top pods -n app

# Manually test scaling
kubectl scale deployment intellirag-app -n app --replicas=5
```

### Issue 3: Network Policy Blocking Legitimate Traffic

**Symptom**: Application cannot connect to dependencies

**Debug Steps**:
```bash
# Check network policy events
kubectl describe networkpolicy -n app

# Temporarily disable network policy for debugging
kubectl delete networkpolicy default-deny-all -n app

# Test connectivity
kubectl exec -it -n app <pod-name> -- curl http://qdrant.database.svc.cluster.local:6333/health

# Re-apply network policy with corrections
kubectl apply -f kubernetes/app/network-policy-app.yaml
```

---

## ✅ Deliverables Checklist

- [ ] NGINX Ingress Controller deployed on GKE
- [ ] DNS configured to point to Ingress IP
- [ ] TLS certificate issued and valid
- [ ] HTTPS endpoint accessible
- [ ] Horizontal Pod Autoscaler configured and tested
- [ ] Resource quotas applied to app namespace
- [ ] LimitRange enforcing container limits
- [ ] Network policies restricting pod communication
- [ ] Pod Security Standards (restricted) enforced
- [ ] All pods running with non-root users
- [ ] Automated backup CronJob scheduled
- [ ] Disaster recovery runbook documented
- [ ] Rate limiting configured (100 req/min)
- [ ] API key authentication implemented
- [ ] Load testing passed with autoscaling
- [ ] Security scan shows zero critical vulnerabilities

---

## 📝 Next Steps

After completing Phase 3, proceed to:
- **[Phase 4: MLOps Pipeline](./phase-4-mlops.md)** - Implement model lifecycle management and monitoring

---

**Phase Status**: Pending
**Last Updated**: 2025-11-13
