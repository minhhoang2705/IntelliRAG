# Phase 3: AWS Foundation

## Context Links
- [Phase 2: Local Development Setup](./phase-02-local-development-setup.md)
- [AWS Free Tier](https://aws.amazon.com/free/)
- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest)

## Overview

**Priority**: P1 (Critical Path)
**Status**: Pending
**Effort**: 6 hours
**Depends On**: Phase 2

Set up foundational AWS resources that persist across EKS cluster lifecycle. These resources are cheap/free and don't need to be destroyed with the cluster.

## Key Insights

- S3 buckets are essentially free (pay only for storage used)
- Terraform state must be stored before creating EKS
- IAM roles/policies persist and cost nothing
- Secrets Manager: $0.40/secret/month
- These resources are the "permanent" foundation

## Requirements

### Functional
- S3 bucket for Terraform state
- S3 bucket for application documents
- S3 bucket for MLFlow artifacts (optional, can use same bucket)
- IAM roles for EKS cluster
- IAM roles for IRSA (pods accessing S3)
- Secrets Manager for application secrets
- Budget alert at $50 and $100

### Non-Functional
- Minimal monthly cost (<$5)
- Resources survive cluster destroy
- Enable versioning for state bucket
- Encryption at rest

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    AWS Foundation (Persistent)                   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                        S3 Buckets                           │ │
│  │  ┌─────────────────┐  ┌─────────────────┐                   │ │
│  │  │ terraform-state │  │ intellirag-docs │                   │ │
│  │  │ (versioned)     │  │ (app storage)   │                   │ │
│  │  └─────────────────┘  └─────────────────┘                   │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                        IAM Roles                            │ │
│  │  ┌─────────────────┐  ┌─────────────────┐                   │ │
│  │  │ EKS Cluster Role│  │ EKS Node Role   │                   │ │
│  │  └─────────────────┘  └─────────────────┘                   │ │
│  │  ┌─────────────────┐                                        │ │
│  │  │ IRSA Pod Role   │  (S3 access for pods)                  │ │
│  │  └─────────────────┘                                        │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Secrets Manager                          │ │
│  │  - intellirag/api-key                                       │ │
│  │  - intellirag/cloudflare-tunnel                             │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Budget Alerts                            │ │
│  │  - $50 threshold (warning)                                  │ │
│  │  - $100 threshold (critical)                                │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Files to Create
| File | Purpose |
|------|---------|
| `terraform/aws/foundation/main.tf` | Foundation resources |
| `terraform/aws/foundation/s3.tf` | S3 buckets |
| `terraform/aws/foundation/iam.tf` | IAM roles and policies |
| `terraform/aws/foundation/secrets.tf` | Secrets Manager |
| `terraform/aws/foundation/budget.tf` | Budget alerts |
| `terraform/aws/foundation/variables.tf` | Input variables |
| `terraform/aws/foundation/outputs.tf` | Output values |
| `terraform/aws/foundation/backend.tf` | S3 backend config |
| `terraform/aws/foundation/versions.tf` | Provider versions |

### Directory Structure
```
terraform/
├── gcp/                    # Existing GCP (keep for reference)
│   ├── main.tf
│   └── ...
└── aws/
    ├── foundation/         # This phase
    │   ├── main.tf
    │   ├── s3.tf
    │   ├── iam.tf
    │   ├── secrets.tf
    │   ├── budget.tf
    │   ├── variables.tf
    │   ├── outputs.tf
    │   └── versions.tf
    └── eks/                # Phase 4
        └── ...
```

## Implementation Steps

### Step 1: Create Terraform Versions Config

```hcl
# terraform/aws/foundation/versions.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
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
    }
  }
}
```

### Step 2: Create Variables

```hcl
# terraform/aws/foundation/variables.tf
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
  description = "Project name for resource naming"
  type        = string
  default     = "intellirag"
}

variable "budget_limit" {
  description = "Monthly budget limit in USD"
  type        = number
  default     = 100
}

variable "alert_email" {
  description = "Email for budget alerts"
  type        = string
}
```

### Step 3: Create S3 Buckets

```hcl
# terraform/aws/foundation/s3.tf

# Terraform State Bucket
resource "aws_s3_bucket" "terraform_state" {
  bucket = "${var.project_name}-terraform-state-${var.environment}"

  lifecycle {
    prevent_destroy = true
  }
}

resource "aws_s3_bucket_versioning" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state" {
  bucket = aws_s3_bucket.terraform_state.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "terraform_state" {
  bucket                  = aws_s3_bucket.terraform_state.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Application Documents Bucket
resource "aws_s3_bucket" "documents" {
  bucket = "${var.project_name}-documents-${var.environment}"
}

resource "aws_s3_bucket_versioning" "documents" {
  bucket = aws_s3_bucket.documents.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

resource "aws_s3_bucket_public_access_block" "documents" {
  bucket                  = aws_s3_bucket.documents.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Lifecycle policy - delete old versions after 30 days
resource "aws_s3_bucket_lifecycle_configuration" "documents" {
  bucket = aws_s3_bucket.documents.id

  rule {
    id     = "cleanup-old-versions"
    status = "Enabled"

    noncurrent_version_expiration {
      noncurrent_days = 30
    }
  }
}
```

### Step 4: Create IAM Roles

```hcl
# terraform/aws/foundation/iam.tf

# EKS Cluster Role
resource "aws_iam_role" "eks_cluster" {
  name = "${var.project_name}-eks-cluster-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "eks.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_cluster_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"
  role       = aws_iam_role.eks_cluster.name
}

# EKS Node Role
resource "aws_iam_role" "eks_node" {
  name = "${var.project_name}-eks-node-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ec2.amazonaws.com"
      }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "eks_worker_node_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_cni_policy" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy"
  role       = aws_iam_role.eks_node.name
}

resource "aws_iam_role_policy_attachment" "eks_container_registry" {
  policy_arn = "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
  role       = aws_iam_role.eks_node.name
}

# S3 Access Policy for Pods (IRSA will use this)
resource "aws_iam_policy" "s3_access" {
  name        = "${var.project_name}-s3-access"
  description = "Allow pods to access S3 buckets"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.documents.arn,
          "${aws_s3_bucket.documents.arn}/*"
        ]
      }
    ]
  })
}

# Note: IRSA role will be created in EKS phase after OIDC provider exists
```

### Step 5: Create Secrets Manager Resources

```hcl
# terraform/aws/foundation/secrets.tf

resource "aws_secretsmanager_secret" "api_key" {
  name                    = "${var.project_name}/api-key"
  description             = "IntelliRAG API authentication key"
  recovery_window_in_days = 0  # Immediate deletion for dev
}

resource "aws_secretsmanager_secret" "cloudflare_tunnel" {
  name                    = "${var.project_name}/cloudflare-tunnel"
  description             = "CloudFlare Tunnel URL for GPU server"
  recovery_window_in_days = 0
}

# Note: Secret values are set manually or via CI/CD
# aws secretsmanager put-secret-value --secret-id intellirag/api-key --secret-string "your-key"
```

### Step 6: Create Budget Alerts

```hcl
# terraform/aws/foundation/budget.tf

resource "aws_budgets_budget" "monthly" {
  name         = "${var.project_name}-monthly-budget"
  budget_type  = "COST"
  limit_amount = var.budget_limit
  limit_unit   = "USD"
  time_unit    = "MONTHLY"

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 50
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 80
    threshold_type             = "PERCENTAGE"
    notification_type          = "ACTUAL"
    subscriber_email_addresses = [var.alert_email]
  }

  notification {
    comparison_operator        = "GREATER_THAN"
    threshold                  = 100
    threshold_type             = "PERCENTAGE"
    notification_type          = "FORECASTED"
    subscriber_email_addresses = [var.alert_email]
  }
}
```

### Step 7: Create Outputs

```hcl
# terraform/aws/foundation/outputs.tf

output "terraform_state_bucket" {
  description = "S3 bucket for Terraform state"
  value       = aws_s3_bucket.terraform_state.id
}

output "documents_bucket" {
  description = "S3 bucket for application documents"
  value       = aws_s3_bucket.documents.id
}

output "documents_bucket_arn" {
  description = "ARN of documents bucket"
  value       = aws_s3_bucket.documents.arn
}

output "eks_cluster_role_arn" {
  description = "ARN of EKS cluster IAM role"
  value       = aws_iam_role.eks_cluster.arn
}

output "eks_node_role_arn" {
  description = "ARN of EKS node IAM role"
  value       = aws_iam_role.eks_node.arn
}

output "s3_access_policy_arn" {
  description = "ARN of S3 access policy for IRSA"
  value       = aws_iam_policy.s3_access.arn
}

output "region" {
  description = "AWS region"
  value       = var.region
}
```

### Step 8: Bootstrap Process

```bash
# scripts/aws-foundation-bootstrap.sh
#!/bin/bash
set -e

cd terraform/aws/foundation

# First run: no backend, state stored locally
echo "Step 1: Initial apply (local state)..."
terraform init
terraform apply -var="alert_email=your@email.com"

# Get state bucket name
STATE_BUCKET=$(terraform output -raw terraform_state_bucket)

# Create backend config
cat > backend.tf <<EOF
terraform {
  backend "s3" {
    bucket = "${STATE_BUCKET}"
    key    = "foundation/terraform.tfstate"
    region = "us-east-1"
  }
}
EOF

# Migrate state to S3
echo "Step 2: Migrating state to S3..."
terraform init -migrate-state

echo "Foundation setup complete!"
echo "State bucket: ${STATE_BUCKET}"
```

## Todo List

- [ ] Create AWS account (if needed)
- [ ] Configure AWS CLI: `aws configure`
- [ ] Create terraform/aws/foundation directory structure
- [ ] Create versions.tf
- [ ] Create variables.tf
- [ ] Create s3.tf
- [ ] Create iam.tf
- [ ] Create secrets.tf
- [ ] Create budget.tf
- [ ] Create outputs.tf
- [ ] Create bootstrap script
- [ ] Run bootstrap: `./scripts/aws-foundation-bootstrap.sh`
- [ ] Verify S3 buckets created
- [ ] Verify IAM roles created
- [ ] Set secret values in Secrets Manager
- [ ] Test budget alert (optional)

## Success Criteria

- [ ] Terraform state stored in S3
- [ ] Documents bucket created with encryption
- [ ] IAM roles for EKS ready
- [ ] S3 access policy created
- [ ] Secrets Manager secrets created
- [ ] Budget alerts configured
- [ ] Monthly cost <$5

## Cost Breakdown

| Resource | Monthly Cost |
|----------|--------------|
| S3 (5GB storage) | ~$0.12 |
| Secrets Manager (2 secrets) | ~$0.80 |
| Budget alerts | Free |
| IAM roles/policies | Free |
| **Total** | **~$1/month** |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Accidental bucket deletion | `prevent_destroy = true` |
| State corruption | S3 versioning enabled |
| Over-budget | Multiple alert thresholds |

## Security Considerations

- All S3 buckets block public access
- Encryption at rest enabled
- IAM follows least privilege
- Secrets never in Terraform state

## Next Steps

After completing this phase:
1. Verify all outputs accessible
2. Note bucket names for Phase 4
3. Proceed to Phase 4: EKS Infrastructure
