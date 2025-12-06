#!/bin/bash
set -e

# IntelliRAG GCP Project Setup Script
# This script creates the GCP project, enables APIs, and sets up the GCS bucket for Terraform state

PROJECT_ID="intellirag-aide1-capstone"
BILLING_ACCOUNT="013552-2652EA-0DC167"
REGION="asia-southeast1"
STATE_BUCKET="${PROJECT_ID}-terraform-state"

echo "========================================="
echo "IntelliRAG GCP Infrastructure Setup"
echo "========================================="
echo ""
echo "Project ID: $PROJECT_ID"
echo "Region: $REGION"
echo "Billing Account: $BILLING_ACCOUNT"
echo ""

# Step 1: Create GCP project
echo "[1/6] Creating GCP project..."
if gcloud projects describe $PROJECT_ID &>/dev/null; then
    echo "✓ Project $PROJECT_ID already exists"
else
    gcloud projects create $PROJECT_ID \
        --name="IntelliRAG Production" \
        --set-as-default
    echo "✓ Project created successfully"
fi

# Step 2: Link billing account
echo ""
echo "[2/6] Linking billing account..."
gcloud billing projects link $PROJECT_ID \
    --billing-account=$BILLING_ACCOUNT
echo "✓ Billing account linked"

# Step 3: Set default project
echo ""
echo "[3/6] Setting default project..."
gcloud config set project $PROJECT_ID
echo "✓ Default project set to $PROJECT_ID"

# Step 4: Enable required APIs
echo ""
echo "[4/6] Enabling required APIs (this may take 2-3 minutes)..."
gcloud services enable \
    container.googleapis.com \
    compute.googleapis.com \
    storage-api.googleapis.com \
    iam.googleapis.com \
    cloudresourcemanager.googleapis.com \
    --project=$PROJECT_ID

echo "✓ APIs enabled successfully"

# Step 5: Create GCS bucket for Terraform state
echo ""
echo "[5/6] Creating GCS bucket for Terraform state..."
if gsutil ls gs://$STATE_BUCKET &>/dev/null; then
    echo "✓ Bucket gs://$STATE_BUCKET already exists"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$STATE_BUCKET
    echo "✓ Bucket created: gs://$STATE_BUCKET"
fi

# Enable versioning
echo "  - Enabling versioning..."
gsutil versioning set on gs://$STATE_BUCKET

# Set lifecycle policy
echo "  - Setting lifecycle policy..."
cat > /tmp/lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"numNewerVersions": 10}
    }]
  }
}
EOF
gsutil lifecycle set /tmp/lifecycle.json gs://$STATE_BUCKET
rm /tmp/lifecycle.json
echo "✓ Bucket configuration complete"

# Step 6: Verify setup
echo ""
echo "[6/6] Verifying setup..."
echo "  - Checking enabled APIs..."
gcloud services list --enabled --project=$PROJECT_ID | grep -E "(container|compute|storage|iam)" > /dev/null
echo "✓ Required APIs are enabled"

echo ""
echo "========================================="
echo "✓ GCP Setup Complete!"
echo "========================================="
echo ""
echo "Next steps:"
echo "1. cd terraform/"
echo "2. terraform init"
echo "3. terraform plan -out=tfplan"
echo "4. terraform apply tfplan"
echo ""
echo "Project Details:"
echo "  Project ID: $PROJECT_ID"
echo "  Region: $REGION"
echo "  State Bucket: gs://$STATE_BUCKET"
echo ""
