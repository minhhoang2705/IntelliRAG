#!/bin/bash
set -e

# IntelliRAG Storage Buckets Setup Script
# This script creates GCS buckets for models and data storage

PROJECT_ID="intellirag-aide1-capstone"
REGION="asia-southeast1"
MODELS_BUCKET="intellirag-aide1-capstone-models"
DATA_BUCKET="intellirag-aide1-capstone-data"
WORKLOAD_SA="intellirag-cluster-workload-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "========================================="
echo "IntelliRAG Storage Buckets Setup"
echo "========================================="
echo ""
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Create models bucket
echo "[1/4] Creating models bucket..."
if gsutil ls gs://$MODELS_BUCKET &>/dev/null; then
    echo "✓ Bucket gs://$MODELS_BUCKET already exists"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$MODELS_BUCKET
    echo "✓ Bucket created: gs://$MODELS_BUCKET"
fi

# Step 2: Create data bucket
echo ""
echo "[2/4] Creating data bucket..."
if gsutil ls gs://$DATA_BUCKET &>/dev/null; then
    echo "✓ Bucket gs://$DATA_BUCKET already exists"
else
    gsutil mb -p $PROJECT_ID -c STANDARD -l $REGION gs://$DATA_BUCKET
    echo "✓ Bucket created: gs://$DATA_BUCKET"
fi

# Step 3: Configure bucket policies
echo ""
echo "[3/4] Configuring bucket policies..."

# Set lifecycle policy for models
cat > /tmp/model-lifecycle.json <<EOF
{
  "lifecycle": {
    "rule": [{
      "action": {"type": "Delete"},
      "condition": {"age": 30, "isLive": false}
    }]
  }
}
EOF
gsutil lifecycle set /tmp/model-lifecycle.json gs://$MODELS_BUCKET
rm /tmp/model-lifecycle.json
echo "  ✓ Lifecycle policy set for models bucket"

# Set uniform bucket-level access
gsutil uniformbucketlevelaccess set on gs://$MODELS_BUCKET
gsutil uniformbucketlevelaccess set on gs://$DATA_BUCKET
echo "  ✓ Uniform bucket-level access enabled"

# Step 4: Grant access to Workload Identity service account
echo ""
echo "[4/4] Granting access to Workload Identity service account..."

# Check if service account exists
if gcloud iam service-accounts describe $WORKLOAD_SA &>/dev/null; then
    gsutil iam ch serviceAccount:${WORKLOAD_SA}:objectAdmin gs://$MODELS_BUCKET
    gsutil iam ch serviceAccount:${WORKLOAD_SA}:objectAdmin gs://$DATA_BUCKET
    echo "✓ Access granted to $WORKLOAD_SA"
else
    echo "⚠ Warning: Workload Identity service account not found yet"
    echo "  Service account: $WORKLOAD_SA"
    echo "  Run this script again after provisioning infrastructure with Terraform"
fi

echo ""
echo "========================================="
echo "✓ Storage Buckets Setup Complete!"
echo "========================================="
echo ""
echo "Bucket Information:"
echo "==================="
echo "Models: gs://$MODELS_BUCKET"
echo "  - Lifecycle: Delete old versions after 30 days"
echo "  - Access: objectAdmin for Workload Identity SA"
echo ""
echo "Data: gs://$DATA_BUCKET"
echo "  - Access: objectAdmin for Workload Identity SA"
echo ""
echo "Next Steps:"
echo "==========="
echo "1. Upload model artifacts:"
echo "   gsutil cp -r /path/to/models/* gs://$MODELS_BUCKET/"
echo ""
echo "2. Verify bucket access from GKE pod:"
echo "   See terraform/README.md for Workload Identity testing"
echo ""
