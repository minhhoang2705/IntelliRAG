#!/bin/bash
set -e

# Setup GitHub Actions CI/CD Service Account for IntelliRAG
# This script creates a GCP service account with necessary permissions for CI/CD

PROJECT_ID="intellirag-aide1-capstone"
SA_NAME="github-actions-cicd"
SA_DISPLAY_NAME="GitHub Actions CI/CD Service Account"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "=================================================="
echo "GitHub Actions CI/CD Service Account Setup"
echo "=================================================="
echo "Project ID: ${PROJECT_ID}"
echo "Service Account: ${SA_EMAIL}"
echo ""

# Check if service account already exists
if gcloud iam service-accounts describe ${SA_EMAIL} &>/dev/null; then
    echo "✅ Service account already exists: ${SA_EMAIL}"
else
    echo "Creating service account..."
    gcloud iam service-accounts create ${SA_NAME} \
        --display-name="${SA_DISPLAY_NAME}" \
        --project=${PROJECT_ID}

    echo "✅ Service account created: ${SA_EMAIL}"
    echo "⏳ Waiting for service account to propagate..."
    sleep 10
fi

echo ""
echo "Granting IAM permissions..."

# Grant container.developer role (for GKE deployments)
echo "  - roles/container.developer"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/container.developer" \
    --quiet

# Grant storage.admin role (for GCS operations)
echo "  - roles/storage.admin"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/storage.admin" \
    --quiet

# Grant artifactregistry.writer role (for pushing Docker images to GCR)
echo "  - roles/artifactregistry.writer"
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="roles/artifactregistry.writer" \
    --quiet

echo "✅ IAM permissions granted"
echo ""

# Create and download service account key
KEY_FILE="github-actions-key.json"
KEY_FILE_B64="github-actions-key.base64"

if [ -f "${KEY_FILE}" ]; then
    echo "⚠️  Key file already exists: ${KEY_FILE}"
    read -p "Do you want to create a new key? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Skipping key creation."
        exit 0
    fi

    # Backup existing key
    mv ${KEY_FILE} ${KEY_FILE}.backup.$(date +%s)
    echo "Old key backed up."
fi

echo "Creating service account key..."
gcloud iam service-accounts keys create ${KEY_FILE} \
    --iam-account=${SA_EMAIL} \
    --project=${PROJECT_ID}

echo "✅ Service account key created: ${KEY_FILE}"
echo ""

# Base64 encode the key
echo "Encoding key to base64..."
cat ${KEY_FILE} | base64 -w 0 > ${KEY_FILE_B64}

echo "✅ Base64-encoded key created: ${KEY_FILE_B64}"
echo ""

echo "=================================================="
echo "Setup Complete!"
echo "=================================================="
echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Copy the base64-encoded key:"
echo "   cat ${KEY_FILE_B64}"
echo ""
echo "2. Add the following secrets to GitHub repository:"
echo "   Settings → Secrets and variables → Actions → New repository secret"
echo ""
echo "   Secret Name: GCP_SA_KEY"
echo "   Value: <paste base64 content from above>"
echo ""
echo "3. Add other required secrets:"
echo "   - GCP_PROJECT_ID: ${PROJECT_ID}"
echo "   - GKE_CLUSTER: intellirag-cluster"
echo "   - GKE_REGION: asia-southeast1"
echo "   - DOCKER_REGISTRY: gcr.io"
echo "   - MLFLOW_TRACKING_URI: https://mlflow.blockchainradar.xyz"
echo "   - CLOUDFLARE_TUNNEL_URL: https://gpu.intellirag.example.com"
echo ""
echo "⚠️  IMPORTANT: Keep ${KEY_FILE} secure and DO NOT commit to git!"
echo "   Add to .gitignore: github-actions-key.*"
echo ""
