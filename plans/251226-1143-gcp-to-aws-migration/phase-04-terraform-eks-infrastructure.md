# Phase 4: Terraform EKS Infrastructure

## Context Links
- [Phase 3: AWS Foundation](./phase-03-aws-foundation.md)
- [Terraform EKS Module](https://registry.terraform.io/modules/terraform-aws-modules/eks/aws/latest)
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)

## Overview

**Priority**: P1 (Critical Path)
**Status**: Pending
**Effort**: 8 hours
**Depends On**: Phase 3

Create ephemeral EKS infrastructure with spot instances. Designed for provision/destroy pattern to minimize costs during development.

## Key Insights

- EKS control plane: $0.10/hr ($73/month if 24/7)
- t3.xlarge spot: ~$0.05/hr (70% savings vs on-demand)
- Single node sufficient for full stack + observability
- Cluster provision time: ~15 minutes
- Cluster destroy time: ~10 minutes
- Use official Terraform EKS module for reliability

## Requirements

### Functional
- EKS cluster with single managed node group
- Spot instances for cost savings
- IRSA (IAM Roles for Service Accounts) enabled
- NGINX Ingress Controller
- Kubernetes namespaces: app, observability
- OIDC provider for IRSA

### Non-Functional
- Provision in <20 minutes
- Destroy cleanly in <15 minutes
- Support t3.xlarge (4 vCPU, 16GB)
- Spot instance with on-demand fallback

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         AWS VPC                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Public Subnets                           │ │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │ │
│  │  │  us-east-1a │  │  us-east-1b │  │  us-east-1c │         │ │
│  │  │  10.0.1.0/24│  │  10.0.2.0/24│  │  10.0.3.0/24│         │ │
│  │  └─────────────┘  └─────────────┘  └─────────────┘         │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│  ┌───────────────────────────┼─────────────────────────────────┐ │
│  │                    EKS Cluster                              │ │
│  │                           │                                 │ │
│  │  ┌────────────────────────▼────────────────────────┐       │ │
│  │  │              Node Group (Spot)                  │       │ │
│  │  │  ┌────────────────────────────────────────────┐ │       │ │
│  │  │  │           t3.xlarge (single)               │ │       │ │
│  │  │  │  ┌─────────┐  ┌─────────┐  ┌─────────┐    │ │       │ │
│  │  │  │  │ FastAPI │  │ Qdrant  │  │  Obs    │    │ │       │ │
│  │  │  │  │ (2 pods)│  │ (1 pod) │  │ Stack   │    │ │       │ │
│  │  │  │  └─────────┘  └─────────┘  └─────────┘    │ │       │ │
│  │  │  └────────────────────────────────────────────┘ │       │ │
│  │  └─────────────────────────────────────────────────┘       │ │
│  │                                                             │ │
│  │  OIDC Provider ─────► IRSA ─────► S3 Access                │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Files to Create
| File | Purpose |
|------|---------|
| `terraform/aws/eks/main.tf` | EKS cluster and node group |
| `terraform/aws/eks/vpc.tf` | VPC and subnets |
| `terraform/aws/eks/irsa.tf` | IRSA configuration |
| `terraform/aws/eks/variables.tf` | Input variables |
| `terraform/aws/eks/outputs.tf` | Output values |
| `terraform/aws/eks/backend.tf` | S3 backend config |
| `terraform/aws/eks/versions.tf` | Provider versions |
| `scripts/eks-provision.sh` | One-command provision |
| `scripts/eks-destroy.sh` | One-command destroy |
| `scripts/eks-kubeconfig.sh` | Get kubeconfig |

### Directory Structure
```
terraform/aws/
├── foundation/     # Phase 3 (persistent)
└── eks/            # This phase (ephemeral)
    ├── main.tf
    ├── vpc.tf
    ├── irsa.tf
    ├── variables.tf
    ├── outputs.tf
    ├── backend.tf
    └── versions.tf
```

## Implementation Steps

### Step 1: Create Terraform Versions Config

```hcl
# terraform/aws/eks/versions.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    kubernetes = {
      source  = "hashicorp/kubernetes"
      version = "~> 2.23"
    }
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Project     = "IntelliRAG"
      Environment = var.environment
      ManagedBy   = "Terraform"
      Ephemeral   = "true"
    }
  }
}

provider "kubernetes" {
  host                   = module.eks.cluster_endpoint
  cluster_ca_certificate = base64decode(module.eks.cluster_certificate_authority_data)

  exec {
    api_version = "client.authentication.k8s.io/v1beta1"
    command     = "aws"
    args        = ["eks", "get-token", "--cluster-name", module.eks.cluster_name]
  }
}
```

### Step 2: Create Backend Config

```hcl
# terraform/aws/eks/backend.tf
terraform {
  backend "s3" {
    bucket = "intellirag-terraform-state-dev"  # From Phase 3
    key    = "eks/terraform.tfstate"
    region = "us-east-1"
  }
}
```

### Step 3: Create Variables

```hcl
# terraform/aws/eks/variables.tf
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "dev"
}

variable "project_name" {
  description = "Project name"
  type        = string
  default     = "intellirag"
}

variable "cluster_version" {
  description = "EKS cluster version"
  type        = string
  default     = "1.28"
}

variable "instance_types" {
  description = "Instance types for node group"
  type        = list(string)
  default     = ["t3.xlarge", "t3a.xlarge"]  # Spot fallback options
}

variable "node_desired_size" {
  description = "Desired number of nodes"
  type        = number
  default     = 1
}

variable "node_min_size" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "node_max_size" {
  description = "Maximum number of nodes"
  type        = number
  default     = 2
}

# Reference from foundation
variable "documents_bucket_arn" {
  description = "ARN of documents S3 bucket"
  type        = string
}

variable "s3_access_policy_arn" {
  description = "ARN of S3 access IAM policy"
  type        = string
}
```

### Step 4: Create VPC

```hcl
# terraform/aws/eks/vpc.tf
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "~> 5.0"

  name = "${var.project_name}-vpc"
  cidr = "10.0.0.0/16"

  azs             = ["${var.region}a", "${var.region}b"]
  public_subnets  = ["10.0.1.0/24", "10.0.2.0/24"]

  # No NAT gateway - use public subnets only (cost saving)
  enable_nat_gateway = false

  # Required for EKS
  enable_dns_hostnames = true
  enable_dns_support   = true

  # Tags required for EKS
  public_subnet_tags = {
    "kubernetes.io/role/elb"                    = 1
    "kubernetes.io/cluster/${var.project_name}" = "owned"
  }

  tags = {
    "kubernetes.io/cluster/${var.project_name}" = "owned"
  }
}
```

### Step 5: Create EKS Cluster

```hcl
# terraform/aws/eks/main.tf
module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 19.0"

  cluster_name    = var.project_name
  cluster_version = var.cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.public_subnets

  # Public access for development (simplifies setup)
  cluster_endpoint_public_access = true

  # Enable IRSA
  enable_irsa = true

  # Managed node group with spot instances
  eks_managed_node_groups = {
    spot = {
      name = "${var.project_name}-spot"

      instance_types = var.instance_types
      capacity_type  = "SPOT"

      min_size     = var.node_min_size
      max_size     = var.node_max_size
      desired_size = var.node_desired_size

      # Use public subnets (no NAT needed)
      subnet_ids = module.vpc.public_subnets

      # Disk size
      disk_size = 50

      labels = {
        Environment = var.environment
        NodeType    = "spot"
      }

      tags = {
        "k8s.io/cluster-autoscaler/enabled"             = "true"
        "k8s.io/cluster-autoscaler/${var.project_name}" = "owned"
      }
    }
  }

  # Cluster addons
  cluster_addons = {
    coredns = {
      most_recent = true
    }
    kube-proxy = {
      most_recent = true
    }
    vpc-cni = {
      most_recent = true
    }
  }

  tags = {
    Environment = var.environment
    Terraform   = "true"
  }
}

# Create namespaces
resource "kubernetes_namespace" "app" {
  metadata {
    name = "app"
    labels = {
      name = "app"
    }
  }

  depends_on = [module.eks]
}

resource "kubernetes_namespace" "observability" {
  metadata {
    name = "observability"
    labels = {
      name = "observability"
    }
  }

  depends_on = [module.eks]
}
```

### Step 6: Create IRSA Configuration

```hcl
# terraform/aws/eks/irsa.tf

# IRSA role for IntelliRAG app (S3 access)
module "irsa_intellirag" {
  source  = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"
  version = "~> 5.0"

  role_name = "${var.project_name}-irsa-role"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["app:intellirag-app"]
    }
  }

  role_policy_arns = {
    s3_access = var.s3_access_policy_arn
  }
}

# Output the role ARN for Helm values
output "irsa_role_arn" {
  description = "IRSA role ARN for IntelliRAG app"
  value       = module.irsa_intellirag.iam_role_arn
}
```

### Step 7: Create Outputs

```hcl
# terraform/aws/eks/outputs.tf
output "cluster_name" {
  description = "EKS cluster name"
  value       = module.eks.cluster_name
}

output "cluster_endpoint" {
  description = "EKS cluster endpoint"
  value       = module.eks.cluster_endpoint
}

output "cluster_certificate_authority_data" {
  description = "EKS cluster CA data"
  value       = module.eks.cluster_certificate_authority_data
  sensitive   = true
}

output "oidc_provider_arn" {
  description = "OIDC provider ARN"
  value       = module.eks.oidc_provider_arn
}

output "configure_kubectl" {
  description = "Command to configure kubectl"
  value       = "aws eks update-kubeconfig --region ${var.region} --name ${module.eks.cluster_name}"
}
```

### Step 8: Create Provision Script

```bash
#!/bin/bash
# scripts/eks-provision.sh
set -e

echo "=== IntelliRAG EKS Provision ==="
START_TIME=$(date +%s)

# Get foundation outputs
cd terraform/aws/foundation
DOCUMENTS_BUCKET_ARN=$(terraform output -raw documents_bucket_arn)
S3_POLICY_ARN=$(terraform output -raw s3_access_policy_arn)

# Provision EKS
cd ../eks
echo "Initializing Terraform..."
terraform init

echo "Provisioning EKS cluster (this takes ~15 minutes)..."
terraform apply -auto-approve \
  -var="documents_bucket_arn=${DOCUMENTS_BUCKET_ARN}" \
  -var="s3_access_policy_arn=${S3_POLICY_ARN}"

# Configure kubectl
echo "Configuring kubectl..."
aws eks update-kubeconfig --region us-east-1 --name intellirag

# Verify cluster
echo "Verifying cluster..."
kubectl get nodes
kubectl get namespaces

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "=== EKS provisioned in ${DURATION} seconds ==="
```

### Step 9: Create Destroy Script

```bash
#!/bin/bash
# scripts/eks-destroy.sh
set -e

echo "=== IntelliRAG EKS Destroy ==="
echo "WARNING: This will destroy the EKS cluster!"
read -p "Are you sure? (yes/no): " confirm

if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 1
fi

START_TIME=$(date +%s)

cd terraform/aws/eks

# Get foundation outputs for destroy
cd ../foundation
DOCUMENTS_BUCKET_ARN=$(terraform output -raw documents_bucket_arn)
S3_POLICY_ARN=$(terraform output -raw s3_access_policy_arn)
cd ../eks

echo "Destroying EKS cluster..."
terraform destroy -auto-approve \
  -var="documents_bucket_arn=${DOCUMENTS_BUCKET_ARN}" \
  -var="s3_access_policy_arn=${S3_POLICY_ARN}"

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))
echo "=== EKS destroyed in ${DURATION} seconds ==="
```

### Step 10: Create Kubeconfig Script

```bash
#!/bin/bash
# scripts/eks-kubeconfig.sh
# Get kubeconfig for existing cluster

aws eks update-kubeconfig --region us-east-1 --name intellirag
kubectl get nodes
```

## Todo List

- [ ] Create terraform/aws/eks directory
- [ ] Create versions.tf
- [ ] Create backend.tf (reference foundation state bucket)
- [ ] Create variables.tf
- [ ] Create vpc.tf
- [ ] Create main.tf (EKS module)
- [ ] Create irsa.tf
- [ ] Create outputs.tf
- [ ] Create scripts/eks-provision.sh
- [ ] Create scripts/eks-destroy.sh
- [ ] Create scripts/eks-kubeconfig.sh
- [ ] Make scripts executable
- [ ] Run provision script
- [ ] Verify kubectl access
- [ ] Test IRSA role (create test pod with S3 access)
- [ ] Document provision/destroy times

## Success Criteria

- [ ] EKS cluster provisions in <20 minutes
- [ ] kubectl connects to cluster
- [ ] Single spot node running
- [ ] Namespaces created (app, observability)
- [ ] IRSA role configured
- [ ] Cluster destroys cleanly in <15 minutes
- [ ] Spot instance running (verify in EC2 console)

## Cost Analysis

| Resource | Hourly Cost | 80 hrs/month |
|----------|-------------|--------------|
| EKS Control Plane | $0.10 | $8 |
| t3.xlarge Spot | ~$0.05 | $4 |
| **Total** | **~$0.15** | **~$12** |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Spot termination | On-demand fallback in instance_types |
| VPC conflicts | Isolated VPC with unique CIDR |
| Long provision time | Use smaller cluster version |
| State corruption | S3 versioned backend |

## Security Considerations

- Public endpoint for simplicity (add IP whitelist for production)
- IRSA for pod-level IAM (no node-level credentials)
- No secrets in Terraform state

## Next Steps

After completing this phase:
1. Install NGINX Ingress Controller
2. Proceed to Phase 5: CI/CD Pipeline Update
3. Deploy application with Helm
