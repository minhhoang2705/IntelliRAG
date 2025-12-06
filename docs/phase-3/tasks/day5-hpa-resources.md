# Day 5: HPA & Resource Management

**Duration**: 4-5 hours
**Prerequisites**: Day 2 capacity analysis complete, metrics-server running
**Output**: Optimized HPA configuration, Resource quotas, autoscaling validation

---

## 🎯 Objectives

1. Configure data-driven Horizontal Pod Autoscaler (HPA)
2. Implement ResourceQuota to prevent namespace over-consumption
3. Set LimitRange for default container resource constraints
4. Test autoscaling under realistic load
5. Verify cost controls and capacity limits

---

## 📋 Tasks Overview

| Task | Duration | Output |
|------|----------|--------|
| 5.1 Verify Metrics Server | 15 min | Metrics available |
| 5.2 Configure HPA | 1 hour | HPA with data-driven thresholds |
| 5.3 Create ResourceQuota | 1 hour | Namespace quotas enforced |
| 5.4 Create LimitRange | 30 min | Default limits applied |
| 5.5 Test Autoscaling | 2 hours | Autoscaling validated under load |

---

## Task 5.1: Verify Metrics Server (15 minutes)

### Check Metrics Server

```bash
# Switch to GKE context
kubectl config use-context <your-gke-context>

# Check if metrics-server exists (should be on GKE by default)
kubectl get deployment metrics-server -n kube-system

# If not found, install it
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Wait for metrics-server to be ready
kubectl wait --for=condition=Available --timeout=120s \
  deployment/metrics-server -n kube-system
```

### Verify Metrics Available

```bash
# Check node metrics
kubectl top nodes

# Check pod metrics
kubectl top pods -n app

# Both commands should show CPU and memory usage
# If showing "<unknown>", wait 1-2 minutes for metrics collection
```

**Success Criteria**:
- ✅ metrics-server deployment Running
- ✅ `kubectl top nodes` shows data
- ✅ `kubectl top pods -n app` shows data

---

## Task 5.2: Configure Optimized HPA (1 hour)

### Calculate Optimal Thresholds (from Day 2 data)

**Example calculation**:
```
From Day 2 capacity analysis:
- 50 users → 40% CPU, 50% memory
- 100 users → 65% CPU, 70% memory
- Breaking point: 200+ users → 90%+ CPU

Target: Scale before reaching 90%
CPU threshold: 70% (scales at ~110 users)
Memory threshold: 75% (scales at ~115 users)
```

### Create HPA Configuration

Create `kubernetes/app/hpa.yaml`:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: intellirag-app-hpa
  namespace: app
  labels:
    app.kubernetes.io/name: intellirag-app
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: intellirag-app
  minReplicas: 3
  maxReplicas: 15
  metrics:
  # CPU-based scaling (primary trigger)
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70  # From Day 2 analysis
  # Memory-based scaling (secondary trigger)
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 75  # From Day 2 analysis

  behavior:
    # Scale down conservatively (prevent thrashing)
    scaleDown:
      stabilizationWindowSeconds: 300  # Wait 5 min before scaling down
      policies:
      - type: Percent
        value: 50  # Max 50% of current replicas per minute
        periodSeconds: 60
      - type: Pods
        value: 2   # Or max 2 pods per minute
        periodSeconds: 60
      selectPolicy: Min  # Choose most conservative policy

    # Scale up aggressively (handle traffic spikes)
    scaleUp:
      stabilizationWindowSeconds: 60  # Wait 1 min before scaling up
      policies:
      - type: Percent
        value: 100  # Max 100% (double replicas)
        periodSeconds: 30
      - type: Pods
        value: 4    # Or max 4 pods per 30 seconds
        periodSeconds: 30
      selectPolicy: Max  # Choose most aggressive policy
```

### Apply HPA

```bash
kubectl apply -f kubernetes/app/hpa.yaml

# Verify HPA created
kubectl get hpa -n app

# Describe for details
kubectl describe hpa intellirag-app-hpa -n app

# Expected output:
# Name:                   intellirag-app-hpa
# Reference:              Deployment/intellirag-app
# Metrics:                ( current / target )
#   resource cpu:         XX% / 70%
#   resource memory:      XX% / 75%
# Min replicas:           3
# Max replicas:           15
# Deployment pods:        3 current / 3 desired
```

### Watch HPA in Real-Time

```bash
# Monitor HPA status
kubectl get hpa -n app -w

# Monitor pods and HPA together
watch -n 2 'kubectl get hpa,pods -n app'
```

**Success Criteria**:
- ✅ HPA created and active
- ✅ Current metrics showing (not `<unknown>`)
- ✅ Desired replicas = current replicas at baseline

---

## Task 5.3: Create ResourceQuota (1 hour)

### Calculate Quota Limits

**Based on Day 2 capacity analysis**:
```
Max replicas: 15
Per-pod resources: 2 CPU req, 4 CPU limit, 4Gi mem req, 8Gi mem limit
At max scale: 30 CPU req, 60 CPU limit, 60Gi mem req, 120Gi mem limit

Add 50% buffer for Qdrant, jobs: 45 CPU req, 90 CPU limit, 90Gi req, 180Gi limit
```

### Create ResourceQuota

Create `kubernetes/app/resource-quota.yaml`:

```yaml
apiVersion: v1
kind: ResourceQuota
metadata:
  name: app-quota
  namespace: app
spec:
  hard:
    # Compute resources
    requests.cpu: "45"         # 15 pods × 2 CPU + 50% buffer
    requests.memory: 90Gi      # 15 pods × 4Gi + 50% buffer
    limits.cpu: "90"           # 15 pods × 4 CPU + 50% buffer
    limits.memory: 180Gi       # 15 pods × 8Gi + 50% buffer

    # Storage
    persistentvolumeclaims: "10"
    requests.storage: 100Gi

    # Objects (prevent runaway resource creation)
    count/deployments.apps: "10"
    count/services: "10"
    count/configmaps: "20"
    count/secrets: "20"
    count/pods: "50"

    # Network
    services.loadbalancers: "0"  # Force use of Ingress instead
```

### Apply ResourceQuota

```bash
kubectl apply -f kubernetes/app/resource-quota.yaml

# Verify quota created
kubectl get resourcequota -n app

# Describe to see current usage
kubectl describe resourcequota app-quota -n app

# Expected output:
# Name:                   app-quota
# Namespace:              app
# Resource                Used    Hard
# --------                ----    ----
# requests.cpu            6       45
# requests.memory         12Gi    90Gi
# limits.cpu              12      90
# limits.memory           24Gi    180Gi
# ...
```

### Test Quota Enforcement

```bash
# Try to create a pod that exceeds quota
kubectl run test-quota-violation -n app --image=nginx \
  --requests=cpu=50 --limits=cpu=50

# Expected: Error "exceeded quota"

# Clean up
kubectl delete pod test-quota-violation -n app --ignore-not-found
```

**Success Criteria**:
- ✅ ResourceQuota created
- ✅ Current usage shown correctly
- ✅ Quota violations blocked

---

## Task 5.4: Create LimitRange (30 minutes)

### Create LimitRange Configuration

Create `kubernetes/app/limit-range.yaml`:

```yaml
apiVersion: v1
kind: LimitRange
metadata:
  name: app-limit-range
  namespace: app
spec:
  limits:
  # Container-level limits
  - type: Container
    default:  # Default limits if not specified
      cpu: 2000m
      memory: 4Gi
    defaultRequest:  # Default requests if not specified
      cpu: 500m
      memory: 1Gi
    max:  # Maximum allowed
      cpu: 4000m
      memory: 8Gi
    min:  # Minimum required
      cpu: 100m
      memory: 128Mi
    maxLimitRequestRatio:  # Max ratio between limit and request
      cpu: 4      # limit can be max 4x request
      memory: 4

  # Pod-level limits (sum of all containers in pod)
  - type: Pod
    max:
      cpu: 8000m
      memory: 16Gi
    min:
      cpu: 100m
      memory: 128Mi

  # PVC limits
  - type: PersistentVolumeClaim
    max:
      storage: 50Gi
    min:
      storage: 1Gi
```

### Apply LimitRange

```bash
kubectl apply -f kubernetes/app/limit-range.yaml

# Verify LimitRange created
kubectl get limitrange -n app

# Describe to see details
kubectl describe limitrange app-limit-range -n app
```

### Test LimitRange Defaults

```bash
# Create pod without resource requests/limits
kubectl run test-defaults -n app --image=nginx --rm -it --restart=Never -- sh -c "sleep 10"

# While pod is running (in another terminal):
kubectl get pod test-defaults -n app -o yaml | grep -A 10 resources

# Expected: Default requests and limits applied
#   requests:
#     cpu: 500m
#     memory: 1Gi
#   limits:
#     cpu: 2000m
#     memory: 4Gi
```

**Success Criteria**:
- ✅ LimitRange created
- ✅ Defaults applied to pods without resource specs
- ✅ Max/min constraints enforced

---

## Task 5.5: Test Autoscaling (2 hours)

### Test 1: Gradual Scale Up

```bash
# Terminal 1: Watch HPA and pods
watch -n 2 'kubectl get hpa,pods -n app'

# Terminal 2: Generate increasing load
# Start light
hey -n 3000 -c 30 -q 5 https://api.intellirag.example.com/ready

# Wait 1-2 minutes, observe metrics...

# Increase load
hey -n 5000 -c 60 -q 10 https://api.intellirag.example.com/ready

# Wait 1-2 minutes...

# Heavy load
hey -n 10000 -c 100 -q 20 https://api.intellirag.example.com/ready

# Expected behavior:
# 1. CPU/Memory utilization increases
# 2. After 60s (stabilization window), HPA triggers scale up
# 3. New pods created (3 → 5 → 7 → ...)
# 4. Load distributes across pods
# 5. CPU/Memory utilization drops back to target levels
```

**Record observations**:
- Time to first scale up: ____ seconds
- Max replicas reached: ____
- Final CPU/memory: ____% / ____%

### Test 2: Stress Test (Scale to Max)

```bash
# Use locust for sustained load
cd tests/load

# Port-forward to GKE app
kubectl port-forward -n app svc/intellirag-app 8000:8000 &

# Run heavy load (from Day 2)
locust -f locustfile.py \
  --user-classes StressTestUser \
  --headless \
  --users 200 \
  --spawn-rate 20 \
  --run-time 10m \
  --host http://localhost:8000

# Monitor in separate terminal:
watch -n 2 'kubectl get hpa,pods -n app'

# Expected behavior:
# - HPA scales from 3 → 15 replicas over 5-8 minutes
# - CPU stays around 70-80%
# - Memory stays around 75-85%
# - Response times remain within SLA
```

### Test 3: Scale Down

```bash
# Stop all load tests
# Kill port-forward: pkill -f "port-forward"

# Monitor scale down (takes ~5 minutes due to stabilization window)
watch -n 10 'kubectl get hpa,pods -n app'

# Expected behavior:
# - After 5 min (stabilizationWindowSeconds: 300), HPA starts scaling down
# - Scales down by 50% or 2 pods per minute (whichever is less)
# - Eventually settles back to 3 replicas (minReplicas)
# - Total scale down time: ~8-12 minutes
```

### Test 4: Resource Quota at Max Scale

```bash
# While at max scale (15 pods), check quota usage
kubectl describe resourcequota app-quota -n app

# Expected:
# requests.cpu:    ~30/45 (within limit)
# limits.cpu:      ~60/90 (within limit)

# Try to scale beyond max (manually)
kubectl scale deployment intellirag-app -n app --replicas=20

# Check deployment events
kubectl describe deployment intellirag-app -n app | tail -20

# Expected: Some pods fail to create due to quota exceeded
# Note: HPA will override manual scale, but test shows quota works

# Let HPA take control again
kubectl patch deployment intellirag-app -n app --type merge -p '{"spec":{"replicas":null}}'
```

### Create Test Report

Create `docs/phase-3/reports/day5-hpa-testing-results.md`:

```markdown
# Day 5: HPA & Autoscaling Test Results

**Date**: 2025-11-21

## HPA Configuration

- **CPU Target**: 70%
- **Memory Target**: 75%
- **Min Replicas**: 3
- **Max Replicas**: 15
- **Scale Up**: Aggressive (100% or 4 pods per 30s)
- **Scale Down**: Conservative (50% or 2 pods per 60s, 5 min stabilization)

## Test Results

### Test 1: Gradual Scale Up

| Time | Load Level | Replicas | CPU % | Memory % | Observations |
|------|-----------|----------|-------|----------|--------------|
| 0:00 | Baseline | 3 | XX% | XX% | Stable |
| 1:00 | Light (30c) | 3 | XX% | XX% | Below threshold |
| 2:30 | Medium (60c) | 5 | XX% | XX% | Scaled up |
| 4:00 | Heavy (100c) | 8 | XX% | XX% | Scaled up again |
| 6:00 | Load stopped | 8 | XX% | XX% | Waiting to scale down |

### Test 2: Stress Test (Max Scale)

- **Start**: 3 replicas
- **Peak**: XX replicas (max 15)
- **Time to max scale**: X minutes
- **CPU at max scale**: XX%
- **Memory at max scale**: XX%
- **Response times**: P95 < 5s ✅
- **Error rate**: X.X% (target: <1%)

### Test 3: Scale Down

- **Start**: XX replicas
- **Time to min replicas**: XX minutes
- **Behavior**: Gradual, no thrashing

### ResourceQuota Usage at Max Scale

| Resource | Used | Limit | Utilization |
|----------|------|-------|-------------|
| CPU requests | XX | 45 | XX% |
| CPU limits | XX | 90 | XX% |
| Memory requests | XXGi | 90Gi | XX% |
| Memory limits | XXGi | 180Gi | XX% |

## Observations

1. **HPA Responsiveness**: [fast/moderate/slow]
2. **Scale Up Behavior**: [smooth/aggressive/adequate]
3. **Scale Down Behavior**: [stable/oscillating]
4. **Quota Enforcement**: [effective/needs adjustment]

## Recommendations

- [Any threshold adjustments needed]
- [Any policy adjustments needed]
- [Cost optimization opportunities]
```

---

## ✅ Day 5 Completion Checklist

- [ ] Metrics-server verified working
- [ ] HPA configured with data-driven thresholds (70% CPU, 75% memory)
- [ ] HPA applied and active
- [ ] ResourceQuota created (45 CPU req, 90Gi memory req)
- [ ] LimitRange created with defaults
- [ ] Gradual scale up test passed
- [ ] Stress test to max replicas passed
- [ ] Scale down test passed (gradual, no thrashing)
- [ ] ResourceQuota enforcement validated
- [ ] Test results documented

**Success Criteria**:
- HPA scales from 3 → max replicas under load
- CPU stays around target (70% ± 10%)
- Memory stays around target (75% ± 10%)
- ResourceQuota prevents exceeding limits
- Scale down gradual and stable (5+ min stabilization)

---

## 🔧 Troubleshooting

### Issue: HPA shows `<unknown>` for metrics

```bash
# Check metrics-server logs
kubectl logs -n kube-system deployment/metrics-server

# Verify resource requests are set
kubectl get deployment intellirag-app -n app -o yaml | grep -A 5 resources

# If no requests set, HPA cannot calculate utilization
# Update deployment to include resource requests
```

### Issue: HPA not scaling

```bash
# Check HPA events
kubectl describe hpa intellirag-app-hpa -n app

# Common issues:
# 1. Metrics not available (see above)
# 2. Already at min/max replicas
# 3. Deployment has replicas set (HPA needs full control)

# Give HPA full control
kubectl patch deployment intellirag-app -n app --type merge -p '{"spec":{"replicas":null}}'
```

### Issue: Pods fail to create at max scale

```bash
# Check quota usage
kubectl describe resourcequota app-quota -n app

# Check deployment events
kubectl describe deployment intellirag-app -n app

# If quota exceeded, options:
# 1. Increase quota (if cluster has capacity)
# 2. Reduce HPA maxReplicas
# 3. Reduce per-pod resource requests
```

### Issue: HPA oscillating (thrashing)

```bash
# Increase stabilization windows
# Edit HPA:
# scaleUp.stabilizationWindowSeconds: 120 (from 60)
# scaleDown.stabilizationWindowSeconds: 600 (from 300)
```

---

## 📚 Resources

- [Kubernetes HPA Docs](https://kubernetes.io/docs/tasks/run-application/horizontal-pod-autoscale/)
- [ResourceQuota Guide](https://kubernetes.io/docs/concepts/policy/resource-quotas/)
- [LimitRange Guide](https://kubernetes.io/docs/concepts/policy/limit-range/)

---

**Next**: [Day 6: Security Policies](./day6-security-policies.md)

**Last Updated**: 2025-11-21
