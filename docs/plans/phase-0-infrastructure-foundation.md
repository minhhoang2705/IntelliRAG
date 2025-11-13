# Phase 0: Infrastructure Foundation

**Duration**: 3-5 days
**Status**: Pending
**Dependencies**: None

---

## 📋 Overview

This phase establishes the foundational infrastructure for IntelliRAG's hybrid deployment architecture. We'll provision a GKE Autopilot cluster for stateless application services and set up a local Kubernetes environment (minikube) with GPU support for model inference.

**Architecture Components**:
- **GKE Autopilot**: Managed Kubernetes cluster for FastAPI application, databases, and orchestration
- **Local Minikube**: Single-node Kubernetes with NVIDIA GPU passthrough for KServe model serving
- **CloudFlare Tunnel**: Secure connectivity between GKE and local GPU server
- **Terraform**: Infrastructure as Code for reproducible GKE provisioning

---

## 🎯 Objectives

### Primary Goals
1. Provision production-grade GKE Autopilot cluster via Terraform
2. Configure local minikube with GPU support for model serving
3. Establish secure CloudFlare Tunnel for GKE ↔ GPU connectivity
4. Create Kubernetes namespaces and RBAC policies
5. Configure persistent storage and networking

### Success Criteria
- ✅ GKE cluster accessible via kubectl
- ✅ Terraform state stored in GCS backend
- ✅ Minikube running with GPU available to pods
- ✅ CloudFlare Tunnel routing traffic to local KServe
- ✅ Namespaces created: `app`, `kserve`, `observability`
- ✅ Service accounts configured with least-privilege IAM

---

## 🛠️ Prerequisites

### GCP Account Setup
```bash
# Verify GCP project exists
gcloud projects list

# Set active project
gcloud config set project YOUR_PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable iam.googleapis.com
gcloud services enable cloudresourcemanager.googleapis.com
```

### Local Machine Requirements
- **OS**: Ubuntu 22.04 LTS
- **Hardware**: NVIDIA RTX 4070Ti (12GB VRAM)
- **RAM**: 32GB minimum
- **Storage**: 500GB+ SSD
- **Network**: Static IP or DDNS

### Tool Installation
```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl

# Install Helm
curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

# Install Terraform
wget -O- https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/hashicorp.list
sudo apt update && sudo apt install terraform

# Install gcloud CLI
curl https://sdk.cloud.google.com | bash
exec -l $SHELL
gcloud init

# Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Install NVIDIA Container Toolkit
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/libnvidia-container/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
sudo apt-get update && sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Verify GPU access
nvidia-smi
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi
```

---

## 📦 Task 1: GKE Cluster Provisioning with Terraform

### 1.1 Create Terraform Directory Structure

```bash
mkdir -p terraform/{modules/{gke,networking,iam},environments/prod}
```

### 1.2 Configure GCS Backend for State Management

**File**: `terraform/backend.tf`
```hcl
terraform {
  backend "gcs" {
    bucket = "intellirag-terraform-state"
    prefix = "gke/prod"
  }
}
```

**Create GCS bucket**:
```bash
# Create bucket for Terraform state
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l us-central1 gs://intellirag-terraform-state

# Enable versioning
gsutil versioning set on gs://intellirag-terraform-state

# Set lifecycle policy to keep 10 versions
cat > lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"numNewerVersions": 10}
    }]
  }
}
EOF
gsutil lifecycle set lifecycle.json gs://intellirag-terraform-state
```

### 1.3 Create Main Terraform Configuration

**File**: `terraform/main.tf`
```hcl
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# VPC Network
resource "google_compute_network" "vpc" {
  name                    = "${var.cluster_name}-vpc"
  auto_create_subnetworks = false
  routing_mode            = "REGIONAL"
}

# Subnet for GKE
resource "google_compute_subnetwork" "gke_subnet" {
  name          = "${var.cluster_name}-subnet"
  ip_cidr_range = var.subnet_cidr
  region        = var.region
  network       = google_compute_network.vpc.id

  secondary_ip_range {
    range_name    = "pods"
    ip_cidr_range = var.pods_cidr
  }

  secondary_ip_range {
    range_name    = "services"
    ip_cidr_range = var.services_cidr
  }
}

# GKE Autopilot Cluster
resource "google_container_cluster" "primary" {
  name     = var.cluster_name
  location = var.region

  # Autopilot mode
  enable_autopilot = true

  # Network configuration
  network    = google_compute_network.vpc.name
  subnetwork = google_compute_subnetwork.gke_subnet.name

  # IP allocation for pods and services
  ip_allocation_policy {
    cluster_secondary_range_name  = "pods"
    services_secondary_range_name = "services"
  }

  # Workload Identity
  workload_identity_config {
    workload_pool = "${var.project_id}.svc.id.goog"
  }

  # Maintenance window
  maintenance_policy {
    daily_maintenance_window {
      start_time = "03:00"
    }
  }

  # Release channel
  release_channel {
    channel = "REGULAR"
  }

  # Addons
  addons_config {
    http_load_balancing {
      disabled = false
    }
    horizontal_pod_autoscaling {
      disabled = false
    }
  }

  # Monitoring and logging
  monitoring_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]

    managed_prometheus {
      enabled = true
    }
  }

  logging_config {
    enable_components = ["SYSTEM_COMPONENTS", "WORKLOADS"]
  }
}

# Service Account for Workload Identity
resource "google_service_account" "gke_workload" {
  account_id   = "${var.cluster_name}-workload-sa"
  display_name = "GKE Workload Service Account"
}

# IAM binding for GCS access
resource "google_project_iam_member" "gcs_access" {
  project = var.project_id
  role    = "roles/storage.objectAdmin"
  member  = "serviceAccount:${google_service_account.gke_workload.email}"
}

# IAM binding for Workload Identity
resource "google_service_account_iam_binding" "workload_identity" {
  service_account_id = google_service_account.gke_workload.name
  role               = "roles/iam.workloadIdentityUser"

  members = [
    "serviceAccount:${var.project_id}.svc.id.goog[app/intellirag-app]",
  ]
}
```

### 1.4 Define Variables

**File**: `terraform/variables.tf`
```hcl
variable "project_id" {
  description = "GCP Project ID"
  type        = string
}

variable "region" {
  description = "GCP region for resources"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "intellirag-cluster"
}

variable "subnet_cidr" {
  description = "CIDR range for GKE subnet"
  type        = string
  default     = "10.0.0.0/20"
}

variable "pods_cidr" {
  description = "CIDR range for pods"
  type        = string
  default     = "10.4.0.0/14"
}

variable "services_cidr" {
  description = "CIDR range for services"
  type        = string
  default     = "10.8.0.0/20"
}
```

### 1.5 Define Outputs

**File**: `terraform/outputs.tf`
```hcl
output "cluster_name" {
  description = "GKE cluster name"
  value       = google_container_cluster.primary.name
}

output "cluster_endpoint" {
  description = "GKE cluster endpoint"
  value       = google_container_cluster.primary.endpoint
  sensitive   = true
}

output "cluster_ca_certificate" {
  description = "GKE cluster CA certificate"
  value       = google_container_cluster.primary.master_auth[0].cluster_ca_certificate
  sensitive   = true
}

output "workload_identity_sa_email" {
  description = "Workload Identity service account email"
  value       = google_service_account.gke_workload.email
}

output "vpc_name" {
  description = "VPC network name"
  value       = google_compute_network.vpc.name
}

output "subnet_name" {
  description = "GKE subnet name"
  value       = google_compute_subnetwork.gke_subnet.name
}
```

### 1.6 Create terraform.tfvars

**File**: `terraform/terraform.tfvars`
```hcl
project_id   = "YOUR_PROJECT_ID"
region       = "us-central1"
cluster_name = "intellirag-cluster"
```

### 1.7 Provision Infrastructure

```bash
cd terraform/

# Initialize Terraform
terraform init

# Validate configuration
terraform validate

# Plan infrastructure changes
terraform plan -out=tfplan

# Review plan output carefully
# Expected resources: VPC, subnet, GKE cluster, service accounts

# Apply infrastructure
terraform apply tfplan

# This will take 10-15 minutes to provision GKE Autopilot cluster
```

### 1.8 Configure kubectl Access

```bash
# Get cluster credentials
gcloud container clusters get-credentials intellirag-cluster \
  --region us-central1 \
  --project YOUR_PROJECT_ID

# Verify access
kubectl cluster-info
kubectl get nodes

# Expected output:
# - Cluster endpoint
# - Autopilot-managed nodes in Ready state
```

---

## 📦 Task 2: Local Minikube Setup with GPU

### 2.1 Install Minikube

```bash
# Download minikube binary
curl -LO https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64

# Install to /usr/local/bin
sudo install minikube-linux-amd64 /usr/local/bin/minikube

# Verify installation
minikube version
```

### 2.2 Start Minikube with GPU Support

```bash
# Start minikube with Docker driver and GPU passthrough
minikube start \
  --driver=docker \
  --container-runtime=docker \
  --gpus=all \
  --memory=16384 \
  --cpus=8 \
  --disk-size=100g

# Verify GPU is available
minikube ssh -- nvidia-smi

# Expected output: GPU information showing RTX 4070Ti
```

### 2.3 Install NVIDIA Device Plugin

```bash
# Apply NVIDIA device plugin DaemonSet
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml

# Verify GPU resources
kubectl get nodes -o json | jq '.items[].status.capacity'

# Expected output should include:
# "nvidia.com/gpu": "1"
```

### 2.4 Test GPU Access in Pod

**File**: `test-gpu-pod.yaml`
```yaml
apiVersion: v1
kind: Pod
metadata:
  name: gpu-test
spec:
  restartPolicy: Never
  containers:
  - name: cuda-container
    image: nvidia/cuda:12.2.0-base-ubuntu22.04
    command: ["nvidia-smi"]
    resources:
      limits:
        nvidia.com/gpu: 1
```

```bash
# Apply test pod
kubectl apply -f test-gpu-pod.yaml

# Wait for completion
kubectl wait --for=condition=complete pod/gpu-test --timeout=60s

# View logs
kubectl logs gpu-test

# Expected: nvidia-smi output showing RTX 4070Ti

# Cleanup
kubectl delete pod gpu-test
```

---

## 📦 Task 3: CloudFlare Tunnel Setup

### 3.1 Install CloudFlare Tunnel

```bash
# Download and install cloudflared
wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Verify installation
cloudflared --version
```

### 3.2 Authenticate with CloudFlare

```bash
# Login to CloudFlare (opens browser for authentication)
cloudflared tunnel login

# This will download a certificate to ~/.cloudflared/cert.pem
```

### 3.3 Create Tunnel

```bash
# Create named tunnel
cloudflared tunnel create intellirag-gpu

# Output will show tunnel ID and credentials file path
# Example: Created tunnel intellirag-gpu with id 12345678-abcd-1234-abcd-1234567890ab
```

### 3.4 Configure DNS Record

```bash
# Add DNS record pointing to tunnel
cloudflared tunnel route dns intellirag-gpu gpu.intellirag.example.com

# Replace 'intellirag.example.com' with your actual domain
```

### 3.5 Create Tunnel Configuration

**File**: `~/.cloudflared/config.yml`
```yaml
tunnel: intellirag-gpu
credentials-file: /home/YOUR_USERNAME/.cloudflared/TUNNEL_ID.json

ingress:
  # Route to KServe Istio Gateway
  - hostname: gpu.intellirag.example.com
    service: http://localhost:8080
    originRequest:
      connectTimeout: 30s
      noTLSVerify: false

  # Catch-all rule (required)
  - service: http_status:404

# Logging
loglevel: info
```

### 3.6 Test Tunnel Locally

```bash
# Run tunnel in foreground for testing
cloudflared tunnel run intellirag-gpu

# In another terminal, test connectivity
curl -v https://gpu.intellirag.example.com/health
```

### 3.7 Install as Systemd Service

```bash
# Install as system service
sudo cloudflared service install

# Start service
sudo systemctl start cloudflared

# Enable on boot
sudo systemctl enable cloudflared

# Check status
sudo systemctl status cloudflared

# View logs
journalctl -u cloudflared -f
```

---

## 📦 Task 4: Kubernetes Namespaces and RBAC

### 4.1 Create Namespaces

**File**: `kubernetes/namespaces.yaml`
```yaml
---
apiVersion: v1
kind: Namespace
metadata:
  name: app
  labels:
    name: app
    environment: production
---
apiVersion: v1
kind: Namespace
metadata:
  name: kserve
  labels:
    name: kserve
    environment: production
    serving.kserve.io/inferenceservice: enabled
---
apiVersion: v1
kind: Namespace
metadata:
  name: observability
  labels:
    name: observability
    environment: production
```

```bash
# Apply to GKE cluster
kubectl apply -f kubernetes/namespaces.yaml

# Apply to minikube
kubectl apply -f kubernetes/namespaces.yaml --context minikube

# Verify
kubectl get namespaces
```

### 4.2 Create Service Accounts

**File**: `kubernetes/service-accounts.yaml`
```yaml
---
# Application service account (GKE)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: intellirag-app
  namespace: app
  annotations:
    iam.gke.io/gcp-service-account: intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com
---
# KServe service account (Minikube)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: kserve-sa
  namespace: kserve
---
# Observability service account (GKE)
apiVersion: v1
kind: ServiceAccount
metadata:
  name: observability-sa
  namespace: observability
```

```bash
# Apply to GKE
kubectl apply -f kubernetes/service-accounts.yaml

# Apply KServe SA to minikube
kubectl apply -f kubernetes/service-accounts.yaml --context minikube
```

### 4.3 Create RBAC Roles

**File**: `kubernetes/rbac.yaml`
```yaml
---
# Role for application pods
apiVersion: rbac.authorization.k8s.io/v1
kind: Role
metadata:
  name: app-role
  namespace: app
rules:
  - apiGroups: [""]
    resources: ["configmaps", "secrets"]
    verbs: ["get", "list"]
  - apiGroups: [""]
    resources: ["pods"]
    verbs: ["get", "list"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: RoleBinding
metadata:
  name: app-role-binding
  namespace: app
subjects:
  - kind: ServiceAccount
    name: intellirag-app
    namespace: app
roleRef:
  kind: Role
  name: app-role
  apiGroup: rbac.authorization.k8s.io
---
# Role for KServe
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: kserve-role
rules:
  - apiGroups: ["serving.kserve.io"]
    resources: ["inferenceservices"]
    verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
  - apiGroups: [""]
    resources: ["services", "events"]
    verbs: ["get", "list", "watch", "create", "update", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: kserve-role-binding
subjects:
  - kind: ServiceAccount
    name: kserve-sa
    namespace: kserve
roleRef:
  kind: ClusterRole
  name: kserve-role
  apiGroup: rbac.authorization.k8s.io
```

```bash
# Apply RBAC
kubectl apply -f kubernetes/rbac.yaml

# Apply KServe RBAC to minikube
kubectl apply -f kubernetes/rbac.yaml --context minikube
```

---

## 📦 Task 5: Persistent Storage Configuration

### 5.1 Create GCS Bucket for Model Artifacts

```bash
# Create bucket for models
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l us-central1 gs://intellirag-models

# Create bucket for data
gsutil mb -p YOUR_PROJECT_ID -c STANDARD -l us-central1 gs://intellirag-data

# Set lifecycle policy (delete old versions after 30 days)
cat > model-lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"age": 30, "isLive": false}
    }]
  }
}
EOF
gsutil lifecycle set model-lifecycle.json gs://intellirag-models

# Set uniform bucket-level access
gsutil uniformbucketlevelaccess set on gs://intellirag-models
gsutil uniformbucketlevelaccess set on gs://intellirag-data

# Grant access to Workload Identity service account
gsutil iam ch serviceAccount:intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://intellirag-models
gsutil iam ch serviceAccount:intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com:objectAdmin gs://intellirag-data
```

### 5.2 Create StorageClass for GKE

**File**: `kubernetes/storage-class.yaml`
```yaml
---
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-ssd
  replication-type: regional-pd
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

```bash
# Apply to GKE
kubectl apply -f kubernetes/storage-class.yaml
```

### 5.3 Create PersistentVolume for Minikube

**File**: `kubernetes/minikube-pv.yaml`
```yaml
---
# PV for model cache
apiVersion: v1
kind: PersistentVolume
metadata:
  name: model-cache-pv
spec:
  capacity:
    storage: 50Gi
  accessModes:
    - ReadWriteOnce
  persistentVolumeReclaimPolicy: Retain
  storageClassName: standard
  hostPath:
    path: /mnt/model-cache
    type: DirectoryOrCreate
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: model-cache-pvc
  namespace: kserve
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 50Gi
  storageClassName: standard
```

```bash
# Create host directory in minikube
minikube ssh -- sudo mkdir -p /mnt/model-cache

# Apply PV and PVC
kubectl apply -f kubernetes/minikube-pv.yaml --context minikube
```

---

## 🧪 Verification and Testing

### Test 1: GKE Cluster Connectivity

```bash
# Check cluster health
kubectl get componentstatuses

# List nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system

# Test pod scheduling
kubectl run test-nginx --image=nginx --restart=Never -n app
kubectl wait --for=condition=Ready pod/test-nginx -n app --timeout=60s
kubectl delete pod test-nginx -n app
```

### Test 2: Minikube GPU Access

```bash
# Check GPU device plugin
kubectl get pods -n kube-system | grep nvidia-device-plugin

# Verify GPU resource
kubectl describe node | grep -A 5 "Allocatable" | grep nvidia.com/gpu

# Run GPU test
kubectl apply -f test-gpu-pod.yaml --context minikube
kubectl logs gpu-test --context minikube
```

### Test 3: CloudFlare Tunnel

```bash
# Check tunnel status
cloudflared tunnel info intellirag-gpu

# Test from external network
curl -v https://gpu.intellirag.example.com/health

# Expected: 404 (no service running yet on port 8080)
# Connection successful indicates tunnel is working
```

### Test 4: Workload Identity (GKE)

```bash
# Create test pod with Workload Identity
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: Pod
metadata:
  name: workload-identity-test
  namespace: app
spec:
  serviceAccountName: intellirag-app
  containers:
  - name: gcloud
    image: google/cloud-sdk:slim
    command: ["sleep", "3600"]
EOF

# Exec into pod
kubectl exec -it workload-identity-test -n app -- /bin/bash

# Inside pod, test GCS access
gcloud auth list
gsutil ls gs://intellirag-models

# Expected: Service account intellirag-cluster-workload-sa@PROJECT_ID.iam.gserviceaccount.com
# and successful bucket listing

# Exit and cleanup
exit
kubectl delete pod workload-identity-test -n app
```

---

## 🚨 Troubleshooting

### Issue 1: Terraform Apply Fails with Quota Error

**Error**: "Quota 'IN_USE_ADDRESSES' exceeded"

**Solution**:
```bash
# Check current quotas
gcloud compute project-info describe --project=YOUR_PROJECT_ID

# Request quota increase in GCP Console:
# IAM & Admin → Quotas → Filter: "Compute Engine API" → Request increase
```

### Issue 2: Minikube GPU Not Available

**Error**: `nvidia.com/gpu: 0` in node capacity

**Solution**:
```bash
# Verify NVIDIA drivers
nvidia-smi

# Verify Docker can access GPU
docker run --rm --gpus all nvidia/cuda:12.2.0-base-ubuntu22.04 nvidia-smi

# Restart minikube
minikube delete
minikube start --driver=docker --gpus=all

# Reapply device plugin
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/v0.14.0/nvidia-device-plugin.yml
```

### Issue 3: CloudFlare Tunnel Not Connecting

**Error**: "tunnel connection error"

**Solution**:
```bash
# Check cloudflared service
sudo systemctl status cloudflared

# View logs
journalctl -u cloudflared -n 50 --no-pager

# Verify configuration
cat ~/.cloudflared/config.yml

# Test tunnel manually
sudo systemctl stop cloudflared
cloudflared tunnel run intellirag-gpu

# If working, restart service
sudo systemctl start cloudflared
```

### Issue 4: GKE Workload Identity Not Working

**Error**: Pod cannot access GCS

**Solution**:
```bash
# Verify IAM binding
gcloud iam service-accounts get-iam-policy \
  intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Re-add Workload Identity binding
gcloud iam service-accounts add-iam-policy-binding \
  intellirag-cluster-workload-sa@YOUR_PROJECT_ID.iam.gserviceaccount.com \
  --role roles/iam.workloadIdentityUser \
  --member "serviceAccount:YOUR_PROJECT_ID.svc.id.goog[app/intellirag-app]"

# Verify pod annotation
kubectl get sa intellirag-app -n app -o yaml | grep iam.gke.io
```

---

## ✅ Deliverables Checklist

- [ ] Terraform configuration committed to repository
- [ ] GKE cluster provisioned and accessible
- [ ] Terraform state stored in GCS backend
- [ ] Minikube running with GPU support
- [ ] NVIDIA device plugin installed and verified
- [ ] CloudFlare Tunnel active and routing traffic
- [ ] Kubernetes namespaces created (app, kserve, observability)
- [ ] Service accounts configured with Workload Identity
- [ ] RBAC roles and bindings applied
- [ ] GCS buckets created for models and data
- [ ] StorageClass configured for GKE
- [ ] PersistentVolume configured for minikube
- [ ] All verification tests passing
- [ ] Documentation updated with cluster details

---

## 📝 Next Steps

After completing Phase 0, proceed to:
- **[Phase 1: Application Deployment](./phase-1-application-deployment.md)** - Deploy FastAPI services to GKE

---

**Phase Status**: Pending
**Last Updated**: 2025-11-13
