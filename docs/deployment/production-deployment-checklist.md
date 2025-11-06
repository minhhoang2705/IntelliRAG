# Production Deployment Checklist

**Last Updated**: 2025-11-06  
**Project**: IntelliRAG Production RAG System  
**Purpose**: Pre-deployment validation checklist for production readiness

---

## Table of Contents

1. [Pre-Deployment Validation](#1-pre-deployment-validation)
2. [Infrastructure Readiness](#2-infrastructure-readiness)
3. [Security Checklist](#3-security-checklist)
4. [Configuration Validation](#4-configuration-validation)
5. [Observability Validation](#5-observability-validation)
6. [Performance Benchmarks](#6-performance-benchmarks)
7. [Deployment Execution](#7-deployment-execution)
8. [Post-Deployment Validation](#8-post-deployment-validation)
9. [Rollback Procedures](#9-rollback-procedures)

---

## 1. Pre-Deployment Validation

### 1.1 Code Quality

- [ ] **All Tests Passing**
  - Unit tests: >80% coverage achieved
  - Integration tests: All scenarios passing
  - No flaky tests detected
  - Test execution time <5 minutes

- [ ] **Code Review Completed**
  - All PRs reviewed and approved
  - No outstanding review comments
  - Security review completed
  - Architecture review completed

- [ ] **Linting and Static Analysis**
  - Ruff linter: No errors
  - mypy type checking: No errors
  - Bandit security scan: No high-severity issues
  - Dependency vulnerabilities checked (no critical CVEs)

- [ ] **Documentation Updated**
  - API documentation current
  - Architecture diagrams updated
  - Deployment guides reviewed
  - Runbooks completed

### 1.2 Version Control

- [ ] **Git Repository Clean**
  - All changes committed
  - No uncommitted files
  - Git tags created for release
  - Changelog updated

- [ ] **Branch Strategy**
  - Production branch up-to-date
  - Release branch created
  - Hotfix procedures documented

---

## 2. Infrastructure Readiness

### 2.1 Kubernetes Cluster

- [ ] **GKE Cluster Provisioned**
  - Cluster version: 1.25+
  - Node pools configured
  - GPU node pool ready (for model serving)
  - Autoscaling enabled
  - Resource quotas defined

- [ ] **Namespaces Created**
  - `intellirag` namespace
  - `kserve` namespace
  - `observability` namespace
  - Resource quotas applied
  - Network policies configured

- [ ] **Storage Provisioned**
  - Persistent volumes created
  - Storage classes configured
  - Backup strategy in place
  - GCS buckets created

### 2.2 Kubernetes Manifests

- [ ] **Application Deployments**
  - FastAPI deployment manifest validated
  - Qdrant StatefulSet manifest validated
  - Resource limits appropriate for production
  - Health check probes configured
  - Service manifests created

- [ ] **Model Serving (KServe)**
  - BGE-M3 embedding InferenceService ready
  - vLLM Qwen InferenceService ready
  - GPU resources allocated
  - Autoscaling policies configured

- [ ] **Observability Stack**
  - Prometheus deployment ready
  - Grafana deployment ready
  - Jaeger deployment ready
  - Loki deployment ready
  - All Helmfiles validated

### 2.3 Networking

- [ ] **NGINX Ingress Controller**
  - Installed and configured
  - TLS certificates provisioned (Let's Encrypt)
  - Rate limiting configured
  - Authentication middleware enabled
  - CORS policy configured

- [ ] **DNS Configuration**
  - Domain names registered
  - DNS records created:
    - `api.intellirag.com` → Ingress
    - `grafana.intellirag.com` → Grafana
    - `jaeger.intellirag.com` → Jaeger
  - SSL certificates valid

- [ ] **Load Balancing**
  - Load balancer provisioned
  - Health checks configured
  - Session affinity configured (if needed)

---

## 3. Security Checklist

### 3.1 Secrets Management

- [ ] **GCP Secret Manager**
  - Project configured
  - Secrets created and populated:
    - GCP service account credentials
    - API keys
    - Database credentials
    - TLS certificates
  - Access controls configured (IAM)
  - Audit logging enabled

- [ ] **Kubernetes Secrets**
  - External Secrets Operator installed
  - Secrets synced from GCP
  - Secrets encrypted at rest
  - No secrets in git repository (verified)

### 3.2 Access Control

- [ ] **RBAC Configuration**
  - ServiceAccounts created per namespace
  - Roles and RoleBindings configured
  - Cluster roles defined
  - Principle of least privilege applied

- [ ] **IAM Policies**
  - GCP service accounts with minimal permissions
  - Workload Identity configured
  - Pod Security Policies enabled
  - Network Policies configured

### 3.3 Authentication & Authorization

- [ ] **API Authentication**
  - API key authentication implemented
  - Rate limiting per API key
  - Token expiration configured
  - Admin API endpoints protected

- [ ] **Internal Communication**
  - TLS for inter-service communication (if using service mesh)
  - Certificate rotation automated

### 3.4 Security Scanning

- [ ] **Container Security**
  - Base images scanned for vulnerabilities
  - No critical CVEs in dependencies
  - Images signed and verified
  - Container runtime security configured

- [ ] **Code Security**
  - Static analysis completed (Bandit)
  - Dependency scanning completed (Safety)
  - No hardcoded credentials
  - Security headers configured

---

## 4. Configuration Validation

### 4.1 Environment-Specific Configs

- [ ] **Production Configuration**
  - `config/prod.yaml` validated
  - API endpoints correct
  - Resource limits appropriate
  - Logging level set to INFO
  - Debug mode disabled

- [ ] **Feature Flags**
  - Production features enabled
  - Beta features disabled
  - Feature flag configuration documented

### 4.2 External Service Configuration

- [ ] **GCS Configuration**
  - Bucket names correct
  - Permissions validated
  - Lifecycle policies configured
  - Versioning enabled

- [ ] **Qdrant Configuration**
  - Connection string correct
  - Collection names validated
  - Persistence configured
  - Backup strategy in place

- [ ] **Model Serving Configuration**
  - Model paths validated
  - GPU allocation correct
  - Autoscaling thresholds appropriate
  - Timeout values configured

---

## 5. Observability Validation

### 5.1 Metrics Collection

- [ ] **Prometheus**
  - Deployed and running
  - Scraping all targets successfully
  - All 19+ custom metrics appearing
  - Service discovery working
  - Retention policy configured (15 days)

- [ ] **Grafana Dashboards**
  - All 5 dashboards loaded:
    1. Infrastructure
    2. Ingestion Pipeline
    3. IntelliRAG Overview
    4. LLM Metrics
    5. Query Performance
  - Queries returning data
  - Variables configured correctly
  - Refresh intervals appropriate

### 5.2 Distributed Tracing

- [ ] **Jaeger**
  - Deployed and running
  - Receiving traces from all services
  - Trace sampling rate configured
  - Retention policy configured (7 days)
  - Query performance acceptable

- [ ] **Trace Validation**
  - End-to-end traces visible
  - Span relationships correct
  - Trace IDs propagating
  - Error traces captured

### 5.3 Centralized Logging

- [ ] **Loki**
  - Deployed and running
  - Promtail collecting logs from all pods
  - Logs queryable in Grafana
  - Retention policy configured (30 days)
  - Log aggregation working

- [ ] **Log Validation**
  - Structured JSON logs appearing
  - Correlation IDs present
  - Log levels appropriate
  - No sensitive data in logs

### 5.4 Alerting

- [ ] **Alert Rules Configured**
  - High error rate alerts
  - High latency alerts
  - Resource exhaustion alerts
  - Service down alerts
  - Data drift alerts (when implemented)

- [ ] **Notification Channels**
  - Slack webhook configured
  - Email notifications configured
  - PagerDuty integration (if applicable)
  - Alert routing rules defined
  - Test alerts sent and received

---

## 6. Performance Benchmarks

### 6.1 Load Testing

- [ ] **Sustained Load Test**
  - 100 concurrent users for 30 minutes
  - P95 latency <500ms
  - P99 latency <1000ms
  - Error rate <0.1%
  - No memory leaks detected

- [ ] **Spike Test**
  - Sudden increase to 500 users
  - System handles spike gracefully
  - Autoscaling triggered correctly
  - Recovery time acceptable

- [ ] **Soak Test**
  - 50 users for 4 hours
  - No degradation over time
  - Memory usage stable
  - No resource exhaustion

### 6.2 Performance Metrics

- [ ] **Query Latency**
  - P50: <200ms
  - P95: <500ms
  - P99: <1000ms
  - Embeddings: <100ms

- [ ] **Throughput**
  - LLM: 793+ TPS (vLLM)
  - API: 100+ requests/second
  - Concurrent users: 100+

- [ ] **Resource Utilization**
  - CPU: <70% average
  - Memory: <80% average
  - GPU: 95%+ utilization (vLLM)
  - Disk I/O: Acceptable

---

## 7. Deployment Execution

### 7.1 Pre-Deployment Steps

- [ ] **Backup Current State**
  - Database backup completed
  - Configuration backup completed
  - Git tag created for rollback

- [ ] **Maintenance Window**
  - Maintenance window scheduled
  - Users notified
  - Support team on standby

- [ ] **Deployment Plan Review**
  - Deployment steps documented
  - Rollback procedures reviewed
  - Team briefing completed

### 7.2 Deployment Steps

**Execute in this order:**

1. **Deploy Infrastructure**
   - [ ] Apply Terraform changes (if any)
   - [ ] Create/update namespaces
   - [ ] Apply network policies

2. **Deploy Data Layer**
   - [ ] Deploy Qdrant StatefulSet
   - [ ] Verify Qdrant is healthy
   - [ ] Restore data if needed

3. **Deploy Model Serving**
   - [ ] Deploy BGE-M3 InferenceService
   - [ ] Deploy vLLM Qwen InferenceService
   - [ ] Verify models are loaded

4. **Deploy Application**
   - [ ] Deploy FastAPI application
   - [ ] Verify health checks passing
   - [ ] Verify pods are running

5. **Deploy Observability**
   - [ ] Deploy Prometheus
   - [ ] Deploy Grafana
   - [ ] Deploy Jaeger
   - [ ] Deploy Loki
   - [ ] Verify metrics collection

6. **Configure Networking**
   - [ ] Apply Ingress configuration
   - [ ] Verify TLS certificates
   - [ ] Verify rate limiting

### 7.3 Deployment Validation

- [ ] **Service Health**
  - All pods running
  - All health checks passing
  - No crash loops
  - Resource usage normal

- [ ] **API Endpoints**
  - `/health` returns 200
  - `/ready` returns 200
  - `/metrics` accessible
  - API endpoints respond correctly

---

## 8. Post-Deployment Validation

### 8.1 Smoke Tests

- [ ] **Basic Functionality**
  - Upload document via API
  - Trigger ingestion
  - Check job status
  - Query document
  - Receive response

- [ ] **Error Scenarios**
  - Invalid file upload rejected
  - Rate limiting works
  - Authentication required
  - Proper error messages

### 8.2 Integration Tests

- [ ] **End-to-End Flows**
  - Complete ingestion pipeline
  - Complete query/RAG pipeline
  - Observability data flowing
  - Alerts can fire

### 8.3 Monitoring Validation

- [ ] **Dashboards**
  - All Grafana dashboards showing data
  - No errors in queries
  - Metrics trending as expected

- [ ] **Logs**
  - Application logs appearing in Loki
  - No error spikes
  - Log volume normal

- [ ] **Traces**
  - Traces appearing in Jaeger
  - End-to-end traces complete
  - Latency acceptable

### 8.4 User Acceptance

- [ ] **Beta Users**
  - Beta users can access system
  - Functionality meets requirements
  - Performance acceptable
  - Feedback collected

---

## 9. Rollback Procedures

### 9.1 Rollback Triggers

**Initiate rollback if:**
- Critical bug discovered
- Error rate >1%
- P99 latency >5 seconds
- Data loss or corruption detected
- Security vulnerability discovered

### 9.2 Rollback Steps

**Execute in reverse order:**

1. **Switch Traffic**
   - [ ] Update Ingress to previous version
   - [ ] Verify traffic redirected

2. **Rollback Application**
   - [ ] Apply previous deployment manifest
   - [ ] Verify pods are running
   - [ ] Verify health checks passing

3. **Rollback Data Layer (if needed)**
   - [ ] Restore database from backup
   - [ ] Verify data integrity

4. **Rollback Configuration**
   - [ ] Revert ConfigMaps
   - [ ] Revert Secrets (if changed)

5. **Verify Rollback**
   - [ ] Run smoke tests
   - [ ] Verify metrics
   - [ ] Verify logs
   - [ ] User validation

### 9.3 Post-Rollback

- [ ] **Incident Report**
  - Document what went wrong
  - Root cause analysis
  - Action items to prevent recurrence

- [ ] **User Communication**
  - Notify users of rollback
  - Provide timeline for fix

---

## Sign-Off

### Deployment Team Approval

- [ ] **DevOps Lead**: _________________ Date: _______
- [ ] **Backend Lead**: _________________ Date: _______
- [ ] **QA Lead**: _____________________ Date: _______
- [ ] **Security Lead**: ________________ Date: _______
- [ ] **Product Owner**: _______________ Date: _______

### Post-Deployment Sign-Off

- [ ] **Deployment Successful**: Yes / No
- [ ] **All Smoke Tests Passed**: Yes / No
- [ ] **Monitoring Validated**: Yes / No
- [ ] **Ready for Production Traffic**: Yes / No

**Deployment Date**: _______________  
**Deployment Time**: _______________  
**Deployment Engineer**: _______________

---

## Appendix: Quick Reference

### Emergency Contacts

- **On-Call Engineer**: [Contact Info]
- **DevOps Lead**: [Contact Info]
- **Security Team**: [Contact Info]
- **Infrastructure Team**: [Contact Info]

### Key URLs

- Production API: `https://api.intellirag.com`
- Grafana: `https://grafana.intellirag.com`
- Jaeger: `https://jaeger.intellirag.com`
- Kubernetes Dashboard: [URL]

### Common Commands

```bash
# Check pod status
kubectl get pods -n intellirag

# View logs
kubectl logs -f deployment/fastapi -n intellirag

# Port forward to service
kubectl port-forward svc/fastapi 8000:8000 -n intellirag

# Restart deployment
kubectl rollout restart deployment/fastapi -n intellirag

# Rollback deployment
kubectl rollout undo deployment/fastapi -n intellirag
```

---

**Related Documents:**
- [PROJECT-STATUS.md](../PROJECT-STATUS.md) - Overall project status
- [Infrastructure Readiness](../evaluation/infrastructure-readiness.md) - Infrastructure assessment
- [Runbook](./runbook.md) - Operational procedures (to be created)
- [Troubleshooting Guide](./troubleshooting.md) - Common issues (to be created)

**Last Updated**: 2025-11-06  
**Maintained By**: IntelliRAG Development Team

