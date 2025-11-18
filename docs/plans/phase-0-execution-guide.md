# Phase 0: Infrastructure Foundation - Execution Guide

**Status**: Ready for Execution
**Created**: 2025-11-14
**Project**: intellirag-aide1-capstone
**Region**: asia-southeast1
**Machine Type**: e2-standard-4

---

## 📋 Overview

This guide provides step-by-step instructions for executing Phase 0 of the IntelliRAG production deployment. All Terraform configurations and automation scripts have been created and are ready to use.

---

## 🎯 What Has Been Prepared

### Terraform Infrastructure (GKE)
✅ **Terraform Configuration Files**:
- `terraform/main.tf` - VPC, subnet, GKE Autopilot cluster, service accounts
- `terraform/variables.tf` - Configuration variables
- `terraform/outputs.tf` - Cluster information outputs
- `terraform/backend.tf` - GCS state backend configuration
- `terraform/terraform.tfvars` - Project-specific values

### Kubernetes Resources
✅ **Kubernetes Manifests**:
- `kubernetes/namespaces.yaml` - app, kserve, observability namespaces
- `kubernetes/service-accounts.yaml` - Service accounts with Workload Identity
- `kubernetes/rbac.yaml` - Roles and role bindings
- `kubernetes/storage-class.yaml` - Fast SSD storage class for GKE
- `kubernetes/test-gpu-pod.yaml` - GPU test pod for minikube (future use)

### Automation Scripts
✅ **Setup Scripts** (all executable):
- `terraform/setup-gcp.sh` - GCP project and API setup
- `terraform/provision-infrastructure.sh` - Terraform provisioning
- `terraform/create-storage-buckets.sh` - GCS buckets for models/data
- `terraform/verify-gke.sh` - Comprehensive verification tests

---

## 🚀 Execution Steps

### Prerequisites Checklist

Before starting, ensure you have:

- [ ] GCP account with billing enabled
- [ ] gcloud CLI installed and authenticated (`gcloud auth login`)
- [ ] kubectl installed (v1.28+)
- [ ] Terraform installed (v1.5.0+)
- [ ] Helm installed (v3.0+)
- [ ] Terminal access to the project directory

### Step 1: GCP Project Setup (5 minutes)

**Objective**: Create GCP project, enable APIs, and create Terraform state bucket

```bash
# Navigate to terraform directory
cd terraform/

# Run GCP setup script
./setup-gcp.sh
```

**What this does**:
1. Creates GCP project: `intellirag-aide1-capstone`
2. Links billing account: `013552-2652EA-0DC167`
3. Enables required APIs (container, compute, storage, IAM)
4. Creates GCS bucket: `gs://intellirag-aide1-capstone-terraform-state`
5. Configures bucket versioning and lifecycle policies

**Expected output**:
```
========================================
✓ GCP Setup Complete!
========================================

Project Details:
  Project ID: intellirag-aide1-capstone
  Region: asia-southeast1
  State Bucket: gs://intellirag-aide1-capstone-terraform-state
```

**Verification**:
```bash
# Verify project is set
gcloud config get-value project
# Should output: intellirag-aide1-capstone

# Verify APIs are enabled
gcloud services list --enabled | grep -E "(container|compute|storage)"

# Verify state bucket exists
gsutil ls gs://intellirag-aide1-capstone-terraform-state
```

---

### Step 2: Provision GKE Cluster (15-20 minutes)

**Objective**: Use Terraform to provision GKE Standard cluster with networking

```bash
# Still in terraform/ directory
./provision-infrastructure.sh
```

**What this does**:
1. Initializes Terraform with GCS backend
2. Validates Terraform configuration
3. Creates infrastructure plan
4. Prompts for confirmation
5. Provisions:
   - VPC network: `intellirag-cluster-vpc`
   - Subnet with secondary ranges for pods/services
   - GKE Standard cluster: `intellirag-cluster` (1-3 nodes, e2-standard-4)
   - Service account: `intellirag-cluster-workload-sa`
   - IAM bindings for Workload Identity
6. Configures kubectl access automatically

**During execution**:
- Review the Terraform plan carefully
- When prompted "Do you want to proceed? (yes/no):", type `yes`
- Wait 10-15 minutes for GKE cluster provisioning

**Expected output**:
```
========================================
✓ Infrastructure Provisioned Successfully!
========================================

Cluster Information:
===================
Kubernetes control plane is running at https://X.X.X.X
...

Nodes:
======
NAME                                       STATUS   ROLES    AGE   VERSION
gk3-intellirag-cluster-default-pool-...    Ready    <none>   1m    v1.28.x

Next Steps:
===========
1. Apply Kubernetes namespaces:
   kubectl apply -f ../kubernetes/namespaces.yaml
...
```

**Verification**:
```bash
# Check cluster info
kubectl cluster-info

# Verify nodes are ready
kubectl get nodes

# Check system pods
kubectl get pods -n kube-system
```

---

### Step 3: Apply Kubernetes Resources (2 minutes)

**Objective**: Create namespaces, service accounts, RBAC, and storage classes

```bash
# From project root
cd kubernetes/

# Apply namespaces
kubectl apply -f namespaces.yaml

# Apply service accounts
kubectl apply -f service-accounts.yaml

# Apply RBAC
kubectl apply -f rbac.yaml

# Note: Using GKE default StorageClass (standard-rwo)
# No custom StorageClass needed
```

**Expected output for each**:
```
namespace/app created
namespace/kserve created
namespace/observability created

serviceaccount/intellirag-app created
serviceaccount/kserve-sa created
serviceaccount/observability-sa created

role.rbac.authorization.k8s.io/app-role created
rolebinding.rbac.authorization.k8s.io/app-role-binding created
clusterrole.rbac.authorization.k8s.io/kserve-role created
clusterrolebinding.rbac.authorization.k8s.io/kserve-role-binding created

# Using GKE default StorageClass
```

**Verification**:
```bash
# Verify namespaces
kubectl get namespaces

# Verify service accounts
kubectl get sa -A | grep -E "(intellirag|kserve|observability)"

# Verify RBAC
kubectl get roles,rolebindings -n app
kubectl get clusterroles,clusterrolebindings | grep kserve

# Verify default storage class
kubectl get storageclass standard-rwo
```

---

### Step 4: Create GCS Storage Buckets (2 minutes)

**Objective**: Create GCS buckets for model artifacts and data storage

```bash
# From project root
cd terraform/

# Run storage setup script
./create-storage-buckets.sh
```

**What this does**:
1. Creates bucket: `gs://intellirag-models`
2. Creates bucket: `gs://intellirag-data`
3. Sets lifecycle policy (delete old versions after 30 days)
4. Enables uniform bucket-level access
5. Grants `objectAdmin` role to Workload Identity SA

**Expected output**:
```
========================================
✓ Storage Buckets Setup Complete!
========================================

Bucket Information:
===================
Models: gs://intellirag-models
  - Lifecycle: Delete old versions after 30 days
  - Access: objectAdmin for Workload Identity SA

Data: gs://intellirag-data
  - Access: objectAdmin for Workload Identity SA
```

**Verification**:
```bash
# Verify buckets exist
gsutil ls | grep intellirag

# Check bucket configuration
gsutil uniformbucketlevelaccess get gs://intellirag-models
gsutil lifecycle get gs://intellirag-models
```

---

### Step 5: Run Verification Tests (5 minutes)

**Objective**: Validate complete GKE setup with comprehensive tests

```bash
# From terraform/ directory
./verify-gke.sh
```

**What this tests**:
1. **Cluster Connectivity** - kubectl configured and cluster accessible
2. **Namespaces** - app, kserve, observability created
3. **Service Accounts** - All SAs exist with proper annotations
4. **RBAC** - Roles and bindings configured correctly
5. **Storage** - StorageClass and GCS buckets exist
6. **Workload Identity** - Annotation and IAM bindings correct
7. **Pod Scheduling** - Test pod can be scheduled and run
8. **GCS Access** - Pod can access GCS using Workload Identity

**Expected output**:
```
========================================
IntelliRAG GKE Verification
========================================

[1/10] Cluster Connectivity Tests
==================================
Testing: kubectl configured... ✓ PASSED
Testing: Cluster accessible... ✓ PASSED
Testing: System pods running... ✓ PASSED
...
[10/10] Cluster Info
====================
NAME                                       STATUS   ROLES    AGE   VERSION
gk3-intellirag-cluster-default-pool-...    Ready    <none>   15m   v1.28.x

========================================
Verification Results
========================================
Tests Passed: 20
Tests Failed: 0

✓ All tests passed! GKE cluster is ready.
```

**If any tests fail**:
- Review the error messages
- Check the troubleshooting section below
- Re-run specific commands to debug

---

## 📊 Infrastructure Summary

After successful completion, you will have:

### GCP Resources
| Resource | Name | Purpose |
|----------|------|---------|
| Project | intellirag-aide1-capstone | GCP project |
| VPC | intellirag-cluster-vpc | Network isolation |
| Subnet | intellirag-cluster-subnet | GKE nodes (10.0.0.0/20) |
| GKE Cluster | intellirag-cluster | Standard cluster (1-3 nodes, e2-standard-4) |
| Service Account | intellirag-cluster-workload-sa | Workload Identity |
| GCS Bucket | intellirag-aide1-capstone-terraform-state | Terraform state |
| GCS Bucket | intellirag-models | Model artifacts |
| GCS Bucket | intellirag-data | Data storage |

### Kubernetes Resources
| Type | Name | Namespace |
|------|------|-----------|
| Namespace | app | - |
| Namespace | kserve | - |
| Namespace | observability | - |
| ServiceAccount | intellirag-app | app |
| ServiceAccount | kserve-sa | kserve |
| ServiceAccount | observability-sa | observability |
| Role | app-role | app |
| ClusterRole | kserve-role | - |

### Network Configuration
| Type | CIDR | Capacity |
|------|------|----------|
| Nodes | 10.0.0.0/20 | 4,094 IPs |
| Pods | 10.4.0.0/14 | 262,144 IPs |
| Services | 10.8.0.0/20 | 4,094 IPs |

---

## 🚨 Troubleshooting

### Issue: API not enabled error

**Error**: `API [container.googleapis.com] not enabled on project`

**Solution**:
```bash
gcloud services enable container.googleapis.com \
  compute.googleapis.com \
  --project=intellirag-aide1-capstone
```

---

### Issue: Terraform backend initialization fails

**Error**: `Failed to get existing workspaces: storage: bucket doesn't exist`

**Solution**:
```bash
# Re-run GCP setup script
cd terraform/
./setup-gcp.sh

# Verify bucket exists
gsutil ls gs://intellirag-aide1-capstone-terraform-state
```

---

### Issue: Quota exceeded

**Error**: `Quota 'CPUS' exceeded. Limit: X in region asia-southeast1`

**Solution**:
1. Go to GCP Console → IAM & Admin → Quotas
2. Filter for "Compute Engine API"
3. Select the exceeded quota
4. Click "EDIT QUOTAS" and request increase
5. Wait for approval (usually 24-48 hours)

**Alternative**: Use a different region with available quota

---

### Issue: Workload Identity test fails

**Error**: Pod cannot access GCS bucket

**Solution**:
```bash
# Verify IAM binding
gcloud iam service-accounts get-iam-policy \
  intellirag-cluster-workload-sa@intellirag-aide1-capstone.iam.gserviceaccount.com

# Re-add binding if missing
gcloud iam service-accounts add-iam-policy-binding \
  intellirag-cluster-workload-sa@intellirag-aide1-capstone.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:intellirag-aide1-capstone.svc.id.goog[app/intellirag-app]"

# Verify service account annotation
kubectl get sa intellirag-app -n app -o yaml | grep iam.gke.io
```

---

### Issue: kubectl cannot connect to cluster

**Error**: `Unable to connect to the server: dial tcp: lookup X on X:53: no such host`

**Solution**:
```bash
# Re-fetch cluster credentials
gcloud container clusters get-credentials intellirag-cluster \
  --region asia-southeast1 \
  --project intellirag-aide1-capstone

# Verify kubeconfig
kubectl config current-context
```

---

## 💰 Cost Tracking

### Monthly Estimates (asia-southeast1)

**GKE Standard**:
- Cluster management: Free (Standard tier)
- Compute resources:
  - Scenario 1 (Current - 1 node, e2-standard-4):
    - 1 × e2-standard-4 = $97.82/month
    - Storage (50GB SSD): $8.50/month
  - Scenario 2 (Peak - 3 nodes, e2-standard-4):
    - 3 × e2-standard-4 = $293.46/month
    - Storage (150GB SSD): $25.50/month
- **Subtotal**: ~$106-319/month (1-3 nodes)

**GCS Storage**:
- Data bucket (50GB): ~$1.30/month
- Model artifacts (10GB): ~$0.26/month
- Terraform state: ~$0.02/month
- **Subtotal**: ~$1.58/month

**Networking**:
- Egress (10-30GB): ~$1-4/month
- **Subtotal**: ~$2/month

**Total GKE Monthly Cost**: ~$109-322/month (depending on node count)

**Expected Load**: 150 requests/minute (~2.5 req/sec)
**Recommended**: Start with 1 node, scale to 2-3 nodes as needed

**Cost Optimization Tips**:
1. Use node auto-scaling (scale down to 1 node during low traffic)
2. Set up budget alerts in GCP Console ($100, $150, $200 thresholds)
3. Review GCS lifecycle policies to auto-delete old data
4. Monitor resource usage with Grafana (Phase 1)
5. Consider Spot/Preemptible nodes for dev workloads (60-91% discount)

---

## ✅ Phase 0 Completion Checklist

Before moving to Phase 1, verify:

- [ ] GCP project `intellirag-aide1-capstone` created and billing enabled
- [ ] All required APIs enabled
- [ ] GKE Standard cluster `intellirag-cluster` running
- [ ] kubectl configured and can access cluster
- [ ] All 3 namespaces created (app, kserve, observability)
- [ ] Service accounts created with Workload Identity annotations
- [ ] RBAC roles and bindings applied
- [ ] Default StorageClass `standard-rwo` available
- [ ] GCS buckets created (terraform-state, models, data)
- [ ] Workload Identity SA has access to GCS buckets
- [ ] All verification tests pass (20/20)
- [ ] Terraform state stored in GCS backend

---

## 📈 Next Steps

### Phase 1: Application Deployment

With Phase 0 complete, you can now proceed to Phase 1:

1. **Deploy Observability Stack** (Prometheus, Grafana, Jaeger, Loki)
   - Already have helmfiles in `kubernetes/observability/`
   - Update and deploy using `helmfile apply`

2. **Build Application Docker Image**
   - Create Dockerfile for FastAPI application
   - Build and push to GCR: `gcr.io/intellirag-aide1/intellirag-api`

3. **Create Helm Charts**
   - Application deployment, service, configmap
   - Configure health checks and resource limits

4. **Deploy to GKE**
   - Install with Helm to `app` namespace
   - Verify pods are running and healthy

5. **Configure Ingress**
   - Set up NGINX Ingress Controller
   - Configure TLS certificates

**Documentation**: See `docs/plans/phase-1-application-deployment.md`

---

## 🔍 Validation Commands

Quick reference for validating the setup:

```bash
# Cluster status
kubectl cluster-info
kubectl get nodes
kubectl top nodes

# Namespaces
kubectl get namespaces

# Service accounts
kubectl get sa -A | grep -E "(intellirag|kserve|observability)"

# RBAC
kubectl get roles,rolebindings -A | grep -E "(app|kserve)"
kubectl get clusterroles,clusterrolebindings | grep kserve

# Storage
kubectl get storageclass
gsutil ls | grep intellirag

# Workload Identity
kubectl describe sa intellirag-app -n app
gcloud iam service-accounts get-iam-policy \
  intellirag-cluster-workload-sa@intellirag-aide1-capstone.iam.gserviceaccount.com
```

---

## 📚 Additional Resources

- **Terraform Documentation**: `terraform/README.md`
- **Phase 0 Plan**: `docs/plans/phase-0-infrastructure-foundation.md`
- **GKE Autopilot Docs**: https://cloud.google.com/kubernetes-engine/docs/concepts/autopilot-overview
- **Workload Identity Guide**: https://cloud.google.com/kubernetes-engine/docs/how-to/workload-identity

---

**Status**: ✅ Ready for Execution
**Estimated Total Time**: 30-40 minutes
**Last Updated**: 2025-11-14
**Author**: IntelliRAG Team
