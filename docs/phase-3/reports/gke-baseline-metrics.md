# GKE Baseline Metrics

**Date**: 2025-11-22
**Cluster**: intellirag-cluster
**Region**: asia-southeast1
**Context**: gke_intellirag-aide1-capstone_asia-southeast1_intellirag-cluster
**Image**: gcr.io/intellirag-aide1-capstone/intellirag-api:v1.0.6

---

## Executive Summary

The GKE cluster is operating efficiently with low CPU utilization (3-9% across nodes) but experiencing memory pressure in application pods (93% vs 80% HPA target). The HPA is maxed out at 5 replicas due to this memory pressure, not CPU load. Readiness probes show high variance (235ms-5.2s) indicating dependency on external services.

**Key Finding**: Memory requests (1Gi) are too low for actual pod usage (~1GB), causing unnecessary horizontal scaling to max replicas instead of optimizing resource allocation.

---

## Current State

### Cluster Overview
- **Cluster Name**: intellirag-cluster
- **Provider**: Google Kubernetes Engine (GKE)
- **Region**: asia-southeast1
- **Nodes**: 3 active nodes
- **Node Type**: e2-standard-4 (4 vCPU, 16GB RAM per node)

### Namespaces
- **app**: FastAPI application (5 pods)
- **database**: Qdrant vector database (1 pod)
- **kube-system**: GKE system components
- **gmp-system**: Google Managed Prometheus
- **gke-managed-cim**: Cluster monitoring

---

## Application Pods (app namespace)

### Pod Status
- **Total Replicas**: 5/5 running
- **Desired Replicas**: 5 (HPA maxed out)
- **Deployment**: intellirag-app-8564d85bbb
- **Age**: 2 days 8 hours

### Individual Pod Metrics

| Pod Name | CPU (millicores) | CPU % of Request | Memory (Mi) | Memory % of Request | Status |
|----------|------------------|------------------|-------------|---------------------|--------|
| intellirag-app-8564d85bbb-88dnm | 21m | 4.2% | 907Mi | 88.5% | Running |
| intellirag-app-8564d85bbb-d4tck | 19m | 3.8% | 953Mi | 93.1% | Running |
| intellirag-app-8564d85bbb-gqfs7 | 23m | 4.6% | 1075Mi | 105.0% | Running |
| intellirag-app-8564d85bbb-s6t67 | 20m | 4.0% | 922Mi | 90.0% | Running |
| intellirag-app-8564d85bbb-ztdh2 | 19m | 3.8% | 903Mi | 88.2% | Running |

**Averages**:
- CPU: 20.4m (4.1% of 500m request)
- Memory: 952Mi (93.0% of 1Gi request)

### Resource Configuration

```yaml
resources:
  requests:
    cpu: 500m      # 0.5 cores per pod
    memory: 1Gi    # 1024Mi per pod
  limits:
    cpu: 2         # 2 cores max
    memory: 4Gi    # 4096Mi max
```

**Analysis**:
- ✅ CPU requests are appropriate (80% headroom)
- ⚠️ Memory requests are too low (7% headroom, 1 pod exceeds request)
- ✅ Limits provide adequate burst capacity
- ❌ Memory pressure causing HPA to scale to max replicas

---

## Node-Level Metrics

| Node Name | CPU Usage | CPU % | Memory Usage | Memory % | Status |
|-----------|-----------|-------|--------------|----------|--------|
| gke-intellirag-clust-intellirag-clust-5a6a7cac-bl9d | 140m | 3% | 3933Mi | 29% | Ready |
| gke-intellirag-clust-intellirag-clust-5a6a7cac-mhx2 | 354m | 9% | 4991Mi | 37% | Ready |
| gke-intellirag-clust-intellirag-clust-885f31a1-jc7k | 181m | 4% | 5441Mi | 40% | Ready |

**Cluster Totals**:
- CPU: 675m / ~12 cores = 5.6% utilization
- Memory: 14.4GB / ~48GB = 30% utilization

**Analysis**:
- ✅ Excellent CPU headroom (94.4% available)
- ✅ Good memory headroom (70% available)
- ✅ Balanced load distribution across nodes
- ✅ No node resource pressure

---

## Horizontal Pod Autoscaler (HPA)

### Configuration

```yaml
Name: intellirag-app
Namespace: app
Min Replicas: 2
Max Replicas: 5
Current Replicas: 5
```

### Metrics

| Metric | Current | Target | Status |
|--------|---------|--------|--------|
| CPU (% of request) | 4% (21m) | 70% | ✅ Well below target |
| Memory (% of request) | 93% (998Mi) | 80% | ⚠️ Above target |

### Scaling Status

```
Conditions:
  AbleToScale:     True  (ReadyForNewScale)
  ScalingActive:   True  (ValidMetricFound)
  ScalingLimited:  True  (TooManyReplicas) ⚠️
```

**Analysis**:
- ❌ **Scaling Limited**: HPA wants to scale up further but is at max (5 replicas)
- **Root Cause**: Memory usage (93%) exceeds target (80%)
- **CPU**: Well below target (4% vs 70%), plenty of headroom
- **Recommendation**: Increase memory requests to 1200Mi to fix scaling behavior

### Scaling Events
No recent scaling events (cluster stable at 5 replicas for 2+ days)

---

## Database Pod (database namespace)

### Qdrant Metrics

| Pod | CPU | Memory | Status |
|-----|-----|--------|--------|
| qdrant-0 | 4m | 16Mi | Running |

**Analysis**:
- ✅ Extremely light resource usage
- ✅ No performance bottlenecks
- ✅ Stable operation

---

## Readiness Probe Performance

### Test Methodology
- **Endpoint**: `http://localhost:8000/ready` (internal)
- **Method**: HTTP GET from within pod
- **Samples**: 10 consecutive requests

### Results

| Test # | Response Time |
|--------|---------------|
| 1 | 0.928s |
| 2 | 0.249s |
| 3 | 0.236s |
| 4 | 5.175s ⚠️ |
| 5 | 0.243s |
| 6 | 0.321s |
| 7 | 0.366s |
| 8 | 4.564s ⚠️ |
| 9 | 3.159s ⚠️ |
| 10 | 5.166s ⚠️ |

### Statistics
- **Average**: 2.04 seconds
- **Median**: 0.475 seconds
- **Min**: 236ms (fast path)
- **Max**: 5.175s (slow path)
- **P95**: ~5.1 seconds
- **Variance**: Very high (2σ = ~2.2s)

### Analysis
- ⚠️ **High Variance**: 235ms to 5.2s indicates external dependency checks
- **Likely Dependencies**:
  - Qdrant health check (database connection)
  - vLLM health check via CloudFlare Tunnel (GPU server)
  - Embedding service health check via CloudFlare Tunnel
- **Impact**: Kubernetes may mark pods as not ready during slow checks
- **Recommendation**: Add timeout or use simpler liveness/readiness probes

---

## Network Connectivity

### Service Configuration

| Service | Type | Cluster IP | Port | External Access |
|---------|------|------------|------|-----------------|
| intellirag-app | ClusterIP | 34.118.235.37 | 8000 | No (internal only) |

### Ingress Status
- **Ingress**: None configured in app namespace
- **External Access**: Via CloudFlare Tunnel (not Ingress)
- **Public Endpoint**: Not directly exposed from GKE

**Analysis**:
- ✅ Service discovery working (ClusterIP functional)
- ⚠️ No Ingress for direct HTTP/HTTPS access
- ℹ️ External access relies on CloudFlare Tunnel to local GPU server
- **Architecture**: GKE → CloudFlare Tunnel → Local GPU Server → KServe

---

## Resource Utilization Summary

### Pod-Level
| Resource | Requests | Used | % of Request | Limits | Status |
|----------|----------|------|--------------|--------|--------|
| CPU | 2500m (5 pods × 500m) | 102m | 4.1% | 10 cores | ✅ Underutilized |
| Memory | 5Gi (5 pods × 1Gi) | 4.76Gi | 95.2% | 20Gi | ⚠️ Near limit |

### Node-Level
| Resource | Capacity (3 nodes) | Used | % Utilization | Available |
|----------|-------------------|------|---------------|-----------|
| CPU | ~12 cores | 675m | 5.6% | 94.4% |
| Memory | ~48Gi | 14.4Gi | 30% | 70% |

**Key Observations**:
1. **CPU**: Massively over-provisioned (94.4% idle)
2. **Memory**: Pod-level pressure (95.2%) but node-level headroom (70%)
3. **Discrepancy**: Memory requests too low, causing false scaling signals

---

## Identified Issues

### 🔴 Critical: Memory Request Misconfiguration
- **Issue**: Memory requests (1Gi) don't match actual usage (~950Mi)
- **Impact**: HPA scales to max replicas (5) unnecessarily
- **Cost**: Running 3 extra pods (~60% more resources than needed)
- **Fix**: Increase memory requests to 1200Mi

### 🟡 Warning: High Readiness Probe Latency
- **Issue**: P95 readiness probe latency is 5.1 seconds
- **Impact**: Pods may be marked NotReady during slow checks
- **Cause**: External dependency checks (Qdrant, CloudFlare Tunnel)
- **Fix**: Add timeout or separate liveness/readiness checks

### 🟢 Informational: No Ingress Configured
- **Issue**: No Kubernetes Ingress in app namespace
- **Impact**: Cannot access app directly from GKE
- **Architecture**: Intentional - using CloudFlare Tunnel instead
- **Action**: Document architecture decision

---

## Recommendations for Day 3 Optimization

### 1. Fix Memory Requests (High Priority)

**Current**:
```yaml
resources:
  requests:
    memory: 1Gi  # Too low
```

**Recommended**:
```yaml
resources:
  requests:
    cpu: 500m
    memory: 1200Mi  # Match actual usage + 20% buffer
  limits:
    cpu: 2
    memory: 4Gi
```

**Expected Impact**:
- HPA will scale down to 2-3 replicas (from 5)
- Cost reduction: ~40-60% fewer pods
- More accurate autoscaling based on CPU

### 2. Optimize HPA Thresholds

**Current**:
```yaml
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
```

**Recommended**:
```yaml
metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 60  # Lower to allow earlier scaling
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75  # Lower for buffer after fixing requests
```

**Rationale**:
- CPU target lowered to trigger scaling before hitting 70%
- Memory target lowered since requests will be more accurate

### 3. Improve Readiness Probe (Medium Priority)

**Current** (assumed):
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 10
```

**Recommended**:
```yaml
readinessProbe:
  httpGet:
    path: /ready
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10
  timeoutSeconds: 3      # Fail fast if dependencies slow
  failureThreshold: 3    # Allow some failures
livenessProbe:
  httpGet:
    path: /health         # Separate lightweight endpoint
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 30
  timeoutSeconds: 2
```

**Rationale**:
- Separate health check that doesn't query external dependencies
- Readiness probe can fail without killing pod (liveness)
- Faster timeouts prevent long waits

### 4. Consider Ingress for Direct Access (Optional)

If direct HTTPS access to GKE is desired (without CloudFlare Tunnel):

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: intellirag-app
  namespace: app
  annotations:
    kubernetes.io/ingress.class: "gce"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - api.intellirag.example.com
    secretName: intellirag-tls
  rules:
  - host: api.intellirag.example.com
    http:
      paths:
      - path: /*
        pathType: ImplementationSpecific
        backend:
          service:
            name: intellirag-app
            port:
              number: 8000
```

---

## Cost Analysis

### Current Configuration
- **Nodes**: 3 × e2-standard-4 (4 vCPU, 16GB)
- **Estimated Cost**: ~$150-180/month (asia-southeast1)
- **App Pods**: 5 replicas (2.5 CPU requested, 5Gi memory)
- **Utilization**: 4.1% CPU, 93% memory

### With Optimized Configuration
- **Nodes**: Potentially 2 × e2-standard-4
- **Estimated Cost**: ~$100-120/month (33% reduction)
- **App Pods**: 2-3 replicas (1-1.5 CPU requested, 2.4-3.6Gi memory)
- **Utilization**: 10-15% CPU, 75% memory

**Potential Savings**: $50-60/month (~33%)

---

## Next Steps

1. **Day 3 Optimization**:
   - Update pod resource requests (memory: 1Gi → 1200Mi)
   - Observe HPA scaling behavior (should reduce to 2-3 pods)
   - Adjust HPA targets based on new baseline

2. **Day 4 Validation**:
   - Run load tests with updated configuration
   - Verify autoscaling works correctly
   - Monitor readiness probe failures

3. **Day 5 Production Readiness**:
   - Implement separate liveness/readiness probes
   - Consider Ingress setup (optional)
   - Document final architecture

---

**Conclusion**: GKE cluster is stable but over-scaled due to memory request misconfiguration. Simple resource adjustment will reduce costs by ~33% while maintaining performance.

**Status**: ✅ GKE Health Check Complete - Optimization Opportunities Identified
