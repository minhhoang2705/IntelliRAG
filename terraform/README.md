# IntelliRAG Terraform Infrastructure

Simplified Terraform configuration for GKE cluster provisioning (learning/demo-focused).

## Overview

- **Project**: intellirag-aide1-capstone
- **Region**: asia-southeast1
- **Cluster**: intellirag-cluster (GKE Standard)
- **Network**: Default VPC (no custom networking)

## What This Provisions

- **GKE Standard Cluster** (regional, default VPC)
- **Node Pool** (e2-standard-4, autoscaling 1-3 nodes)
- **Workload Identity** (for secure GCS access)
- **Service Account** (GCS object admin permissions)

## Prerequisites

1. GCP project created and billing enabled
2. Required APIs enabled:
   ```bash
   gcloud services enable container.googleapis.com compute.googleapis.com \
     storage-api.googleapis.com iam.googleapis.com
   ```
3. gcloud CLI authenticated
4. Terraform >= 1.5.6 installed

## Setup

### 1. Create GCS Bucket for State

```bash
gsutil mb -p intellirag-aide1-capstone -c STANDARD \
  -l asia-southeast1 gs://intellirag-aide1-capstone-terraform-state

gsutil versioning set on gs://intellirag-aide1-capstone-terraform-state
```

### 2. Initialize & Apply

```bash
cd terraform/
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

**Provisioning time**: ~10-15 minutes

### 3. Get Cluster Credentials

```bash
gcloud container clusters get-credentials intellirag-cluster \
  --region asia-southeast1 \
  --project intellirag-aide1-capstone

kubectl get nodes
```

## Resources Created

| Resource | Type | Name |
|----------|------|------|
| GKE Cluster | google_container_cluster | intellirag-cluster |
| Node Pool | google_container_node_pool | intellirag-cluster-node-pool |
| Service Account | google_service_account | intellirag-cluster-workload-sa |
| IAM Bindings | google_project_iam_member | GCS access + Workload Identity |

## Configuration

All settings in `terraform.tfvars`:
- Machine type: e2-standard-4 (4 vCPU, 16GB RAM)
- Autoscaling: 1-3 nodes
- Uses default VPC network

## Cost Estimate

**GKE Standard** (asia-southeast1):
- Cluster management: $0.10/hour (~$73/month)
- e2-standard-4 nodes: ~$120/node/month
- **Total**: ~$193-433/month (1-3 nodes)

## Cleanup

```bash
terraform destroy
```

## Next Steps

After cluster is ready:
1. Deploy observability stack (Helmfile)
2. Deploy application services (Helm)
3. Configure KServe for model serving

---

**Last Updated**: 2025-11-16
