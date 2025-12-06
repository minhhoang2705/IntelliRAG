#!/bin/bash
set -e

# IntelliRAG Infrastructure Provisioning Script
# This script initializes Terraform and provisions the GKE cluster

PROJECT_ID="intellirag-aide1-capstone"
REGION="asia-southeast1"
CLUSTER_NAME="intellirag-cluster"

echo "========================================="
echo "IntelliRAG Infrastructure Provisioning"
echo "========================================="
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo "Cluster: $CLUSTER_NAME"
echo ""

# Check if we're in the terraform directory
if [ ! -f "main.tf" ]; then
    echo "Error: This script must be run from the terraform/ directory"
    exit 1
fi

# Step 1: Initialize Terraform
echo "[1/5] Initializing Terraform..."
terraform init
echo "Terraform initialized"

# Step 2: Validate configuration
echo ""
echo "[2/5] Validating Terraform configuration..."
terraform validate
echo "Configuration is valid"

# Step 3: Format Terraform files
echo ""
echo "[3/5] Formatting Terraform files..."
terraform fmt
echo "Files formatted"

# Step 4: Plan infrastructure
echo ""
echo "[4/5] Planning infrastructure changes..."
terraform plan -out=tfplan
echo ""
echo " Plan created: tfplan"
echo ""

# Step 5: Prompt for apply
echo "========================================="
echo "Ready to provision infrastructure!"
echo "========================================="
echo ""
echo "This will create:"
echo "  - VPC network: ${CLUSTER_NAME}-vpc"
echo "  - GKE Autopilot cluster: $CLUSTER_NAME"
echo "  - Service account: ${CLUSTER_NAME}-workload-sa"
echo "  - IAM bindings for Workload Identity"
echo ""
echo "Estimated time: 10-15 minutes"
echo "Estimated cost: ~\$50-150/month"
echo ""
read -p "Do you want to proceed? (yes/no): " -r
echo ""

if [[ $REPLY =~ ^[Yy]es$ ]]; then
    echo "[5/5] Applying infrastructure changes..."
    terraform apply tfplan

    echo ""
    echo "========================================="
    echo " Infrastructure Provisioned Successfully!"
    echo "========================================="
    echo ""

    # Get cluster credentials
    echo "Configuring kubectl access..."
    gcloud container clusters get-credentials $CLUSTER_NAME \
        --region $REGION \
        --project $PROJECT_ID

    echo ""
    echo "Cluster Information:"
    echo "==================="
    kubectl cluster-info
    echo ""

    echo "Nodes:"
    echo "======"
    kubectl get nodes
    echo ""

    echo "Next Steps:"
    echo "==========="
    echo "1. Apply Kubernetes namespaces:"
    echo "   kubectl apply -f ../kubernetes/namespaces.yaml"
    echo ""
    echo "2. Apply service accounts:"
    echo "   kubectl apply -f ../kubernetes/service-accounts.yaml"
    echo ""
    echo "3. Apply RBAC:"
    echo "   kubectl apply -f ../kubernetes/rbac.yaml"
    echo ""
    echo "4. Apply storage class:"
    echo "   kubectl apply -f ../kubernetes/storage-class.yaml"
    echo ""
else
    echo "Provisioning cancelled."
    echo ""
    echo "To review the plan again:"
    echo "  terraform show tfplan"
    echo ""
    echo "To proceed later:"
    echo "  terraform apply tfplan"
    echo ""
fi
