# Day 6: Security Policies

**Duration**: 5-6 hours
**Prerequisites**: Application running on GKE, NGINX Ingress deployed
**Output**: Network policies, Pod Security Standards enforced, security validated

---

## 🎯 Objectives

1. Implement network policies for pod-to-pod traffic control
2. Enforce Pod Security Standards (restricted mode)
3. Update Dockerfile and deployment for security compliance
4. Run security vulnerability scans
5. Verify zero HIGH/CRITICAL vulnerabilities

---

## 📋 Tasks Overview

| Task | Duration | Output |
|------|----------|--------|
| 6.1 Create Network Policies | 2 hours | Default deny + explicit allow rules |
| 6.2 Enforce Pod Security Standards | 2 hours | Restricted mode active |
| 6.3 Update Security Context | 1 hour | Non-root containers, read-only FS |
| 6.4 Security Scanning | 1 hour | Vulnerability reports |

---

## Task 6.1: Create Network Policies (2 hours)

### Label Namespaces

```bash
# Label namespaces for network policy selectors
kubectl label namespace ingress-nginx name=ingress-nginx
kubectl label namespace observability name=observability
kubectl label namespace kube-system name=kube-system
kubectl label namespace app name=app

# Verify labels
kubectl get namespaces --show-labels | grep -E "ingress-nginx|observability|kube-system|app"
```

### Create Default Deny-All Policy

Create `kubernetes/app/network-policy-deny-all.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: default-deny-all
  namespace: app
spec:
  podSelector: {}  # Applies to all pods in namespace
  policyTypes:
  - Ingress
  - Egress
```

### Create Application Network Policy

Create `kubernetes/app/network-policy-app.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: intellirag-app-policy
  namespace: app
  labels:
    app.kubernetes.io/name: intellirag-app
spec:
  podSelector:
    matchLabels:
      app.kubernetes.io/name: intellirag-app
  policyTypes:
  - Ingress
  - Egress

  ingress:
  # Allow from NGINX Ingress Controller
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
      podSelector:
        matchLabels:
          app.kubernetes.io/name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000

  # Allow from same namespace (for debugging, internal health checks)
  - from:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 8000

  # Allow Prometheus scraping
  - from:
    - namespaceSelector:
        matchLabels:
          name: observability
      podSelector:
        matchLabels:
          app.kubernetes.io/name: prometheus
    ports:
    - protocol: TCP
      port: 8000

  egress:
  # Allow DNS resolution
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
      podSelector:
        matchLabels:
          k8s-app: kube-dns
    ports:
    - protocol: UDP
      port: 53
    - protocol: TCP
      port: 53

  # Allow Qdrant (same namespace)
  - to:
    - podSelector:
        matchLabels:
          app: qdrant
    ports:
    - protocol: TCP
      port: 6333

  # Allow external HTTPS (GCS, CloudFlare Tunnel for vLLM/embedding)
  - ports:
    - protocol: TCP
      port: 443

  # Allow HTTP (for CloudFlare Tunnel if using custom ports)
  - ports:
    - protocol: TCP
      port: 8080

  # Allow Jaeger tracing
  - to:
    - namespaceSelector:
        matchLabels:
          name: observability
    ports:
    - protocol: UDP
      port: 6831
    - protocol: UDP
      port: 6832
```

### Create Qdrant Network Policy

Create `kubernetes/app/network-policy-qdrant.yaml`:

```yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: qdrant-policy
  namespace: app
spec:
  podSelector:
    matchLabels:
      app: qdrant
  policyTypes:
  - Ingress
  - Egress

  ingress:
  # Allow from intellirag-app
  - from:
    - podSelector:
        matchLabels:
          app.kubernetes.io/name: intellirag-app
    ports:
    - protocol: TCP
      port: 6333

  # Allow from same namespace
  - from:
    - podSelector: {}
    ports:
    - protocol: TCP
      port: 6333

  egress:
  # Allow DNS
  - to:
    - namespaceSelector:
        matchLabels:
          name: kube-system
    ports:
    - protocol: UDP
      port: 53

  # Allow external (for backups to GCS)
  - ports:
    - protocol: TCP
      port: 443
```

### Apply Network Policies

```bash
# Apply policies
kubectl apply -f kubernetes/app/network-policy-deny-all.yaml
kubectl apply -f kubernetes/app/network-policy-app.yaml
kubectl apply -f kubernetes/app/network-policy-qdrant.yaml

# Verify policies created
kubectl get networkpolicy -n app

# Describe policies
kubectl describe networkpolicy intellirag-app-policy -n app
```

### Test Network Policies

```bash
# Test 1: Pod can access Ingress endpoint (should work)
curl https://api.intellirag.example.com/ready
# Expected: 200 OK

# Test 2: Create test pod in app namespace
kubectl run test-netpol -n app --image=curlimages/curl --rm -it --restart=Never -- sh

# Inside test pod:
# Should work: Access to intellirag-app service
curl http://intellirag-app.app.svc.cluster.local:8000/

# Should work: DNS resolution
nslookup google.com

# Should work: Access to Qdrant
curl http://qdrant.app.svc.cluster.local:6333/

# Should be BLOCKED: Access to observability namespace (unless explicitly allowed)
curl http://prometheus-server.observability.svc.cluster.local:80 --max-time 10
# Expected: Connection timeout or refused

# Exit test pod
exit

# Test 3: Verify application still works
curl https://api.intellirag.example.com/ready
# Expected: 200 OK (network policies allow Ingress → App)
```

**Success Criteria**:
- ✅ Network policies created (3 policies)
- ✅ Authorized traffic allowed (Ingress → App, App → Qdrant, App → External HTTPS)
- ✅ Unauthorized traffic blocked (inter-namespace without explicit allow)

---

## Task 6.2: Enforce Pod Security Standards (2 hours)

### Label Namespace for Restricted Security

```bash
# Enforce restricted security standard
kubectl label namespace app pod-security.kubernetes.io/enforce=restricted
kubectl label namespace app pod-security.kubernetes.io/audit=restricted
kubectl label namespace app pod-security.kubernetes.io/warn=restricted

# Verify labels
kubectl get namespace app --show-labels | grep pod-security
```

### Update Deployment Security Context

**Update**: `helm/intellirag-app/templates/deployment.yaml`

```yaml
spec:
  template:
    spec:
      # Pod-level security context
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
        fsGroupChangePolicy: "OnRootMismatch"
        seccompProfile:
          type: RuntimeDefault

      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"

        # Container-level security context
        securityContext:
          allowPrivilegeEscalation: false
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
          capabilities:
            drop:
            - ALL
          readOnlyRootFilesystem: true

        volumeMounts:
        - name: tmp
          mountPath: /tmp
        - name: cache
          mountPath: /app/.cache
        - name: logs
          mountPath: /app/logs

        # ... rest of container spec

      volumes:
      - name: tmp
        emptyDir: {}
      - name: cache
        emptyDir: {}
      - name: logs
        emptyDir: {}
```

---

## Task 6.3: Update Dockerfile for Non-Root User (1 hour)

**Update**: `Dockerfile`

```dockerfile
FROM python:3.11-slim

# Create non-root user
RUN groupadd -r intellirag -g 1000 && \
    useradd -r -g intellirag -u 1000 -m -s /bin/bash intellirag

# Set working directory
WORKDIR /app

# Copy dependencies
COPY --chown=intellirag:intellirag requirements.txt .

# Install dependencies as root
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=intellirag:intellirag app ./app

# Create writable directories
RUN mkdir -p /tmp /app/.cache /app/logs && \
    chown -R intellirag:intellirag /tmp /app/.cache /app/logs && \
    chmod -R 755 /tmp /app/.cache /app/logs

# Switch to non-root user
USER intellirag

# Expose port
EXPOSE 8000

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Rebuild and Deploy

```bash
# Rebuild Docker image
docker build -t gcr.io/YOUR_PROJECT/intellirag-app:v1.2.0-secure .

# Push to registry
docker push gcr.io/YOUR_PROJECT/intellirag-app:v1.2.0-secure

# Update Helm values
helm upgrade intellirag-app ./helm/intellirag-app \
  --namespace app \
  --set image.tag=v1.2.0-secure \
  --wait \
  --timeout 10m

# Verify pods running with restricted security
kubectl get pods -n app
kubectl describe pod -n app <pod-name> | grep -A 20 "Security Context"

# Expected output showing:
# runAsNonRoot: true
# runAsUser: 1000
# readOnlyRootFilesystem: true
# capabilities dropped: ALL
```

### Verify Application Still Works

```bash
# Test application endpoints
curl https://api.intellirag.example.com/ready

# Check logs for any permission errors
kubectl logs -n app -l app.kubernetes.io/name=intellirag-app --tail=50

# If errors about write permissions, ensure volumes mounted for:
# - /tmp
# - /app/.cache
# - /app/logs
```

**Success Criteria**:
- ✅ Pods running with UID 1000 (non-root)
- ✅ Read-only root filesystem
- ✅ All capabilities dropped
- ✅ Application functional

---

## Task 6.4: Security Scanning (1 hour)

### Scan Docker Image

```bash
# Scan with trivy
trivy image gcr.io/YOUR_PROJECT/intellirag-app:v1.2.0-secure

# Filter for HIGH and CRITICAL
trivy image --severity HIGH,CRITICAL gcr.io/YOUR_PROJECT/intellirag-app:v1.2.0-secure

# Expected: Zero HIGH or CRITICAL vulnerabilities
# If vulnerabilities found:
# 1. Update base image (python:3.11-slim → latest patch)
# 2. Update vulnerable packages in requirements.txt
# 3. Rebuild and rescan
```

### Scan Kubernetes Manifests

```bash
# Scan all Kubernetes configs
trivy config kubernetes/app/

# Review output for security issues
# Common issues:
# - Missing security context
# - No resource limits
# - Privileged containers
```

### Run kube-bench (Optional)

```bash
# Run CIS Kubernetes Benchmark
kubectl apply -f https://raw.githubusercontent.com/aquasecurity/kube-bench/main/job.yaml

# Wait for job to complete
kubectl wait --for=condition=complete --timeout=300s job/kube-bench

# View results
kubectl logs job/kube-bench

# Focus on FAIL items, create remediation plan if needed
```

### Create Security Report

Create `docs/phase-3/reports/day6-security-audit.md`:

```markdown
# Day 6: Security Audit Report

**Date**: 2025-11-21

## Network Policies

- **Status**: ✅ Enforced
- **Policies Created**: 3 (default-deny-all, app-policy, qdrant-policy)
- **Traffic Allowed**:
  - Ingress NGINX → Application (port 8000)
  - Application → Qdrant (port 6333)
  - Application → External HTTPS (port 443)
  - Prometheus → Application (metrics scraping)
- **Traffic Blocked**:
  - Unauthorized inter-namespace communication
  - Direct access to application pods from outside

## Pod Security Standards

- **Mode**: Restricted (enforced)
- **User**: UID 1000 (non-root)
- **Filesystem**: Read-only root
- **Capabilities**: ALL dropped
- **Privileged**: false
- **seccompProfile**: RuntimeDefault

## Vulnerability Scan Results

### Docker Image Scan (trivy)
| Severity | Count |
|----------|-------|
| CRITICAL | 0 |
| HIGH | 0 |
| MEDIUM | X |
| LOW | X |

**Status**: ✅ Zero HIGH/CRITICAL vulnerabilities

### Kubernetes Config Scan
- **Issues Found**: X
- **Critical Issues**: 0
- **Status**: ✅ Passed

## Compliance

- ✅ CIS Kubernetes Benchmark: XX/XX checks passed
- ✅ OWASP Top 10: Mitigations in place
- ✅ Pod Security Standards: Restricted mode enforced

## Recommendations

1. [Any improvements identified]
2. [Regular rescanning schedule: weekly]
3. [Update dependencies monthly]
```

---

## ✅ Day 6 Completion Checklist

- [ ] Namespaces labeled for network policies
- [ ] Default deny-all network policy created
- [ ] Application network policy created (explicit allow rules)
- [ ] Qdrant network policy created
- [ ] Network policies tested and validated
- [ ] Pod Security Standards labels applied (restricted)
- [ ] Deployment updated with security context
- [ ] Dockerfile updated for non-root user
- [ ] Docker image rebuilt with security updates
- [ ] Application deployed with restricted security
- [ ] Application functionality verified
- [ ] Docker image scanned (trivy)
- [ ] Kubernetes configs scanned
- [ ] Zero HIGH/CRITICAL vulnerabilities confirmed
- [ ] Security audit report created

**Success Criteria**:
- Network policies block unauthorized traffic
- All pods run as non-root (UID 1000)
- Read-only root filesystem enforced
- Zero HIGH/CRITICAL vulnerabilities
- Application fully functional with security controls

---

## 🔧 Troubleshooting

### Issue: Pods fail to start after Pod Security Standards

```bash
# Check pod events
kubectl describe pod -n app <pod-name>

# Common issues:
# 1. "runAsNonRoot" violation
#    Fix: Update Dockerfile to use non-root user

# 2. "readOnlyRootFilesystem" violation (app tries to write to /)
#    Fix: Mount emptyDir volumes for writable paths

# 3. "capabilities" violation
#    Fix: Ensure securityContext drops ALL capabilities
```

### Issue: Network policy blocking legitimate traffic

```bash
# Temporarily disable default-deny for debugging
kubectl delete networkpolicy default-deny-all -n app

# Test connectivity
kubectl exec -n app <pod-name> -- curl http://service-name

# If works without policy, update policy to explicitly allow

# Re-apply policy
kubectl apply -f kubernetes/app/network-policy-deny-all.yaml
```

### Issue: Application can't write logs/cache

```bash
# Verify volumes mounted
kubectl describe pod -n app <pod-name> | grep -A 10 Mounts

# Ensure emptyDir volumes present:
# - /tmp
# - /app/.cache
# - /app/logs

# Check permissions
kubectl exec -n app <pod-name> -- ls -la /app/
kubectl exec -n app <pod-name> -- touch /tmp/test
```

---

## 📚 Resources

- [Network Policies](https://kubernetes.io/docs/concepts/services-networking/network-policies/)
- [Pod Security Standards](https://kubernetes.io/docs/concepts/security/pod-security-standards/)
- [trivy Documentation](https://aquasecurity.github.io/trivy/)

---

**Next**: [Day 7: Backup, DR & Authentication](./day7-backup-auth.md)

**Last Updated**: 2025-11-21
