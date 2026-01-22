# Phase 5: CI/CD Pipeline Update

## Context Links
- [Current CD Workflow](../../.github/workflows/cd-app.yml)
- [Phase 4: EKS Infrastructure](./phase-04-terraform-eks-infrastructure.md)
- [GitHub Container Registry](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)

## Overview

**Priority**: P1 (Critical Path)
**Status**: Pending
**Effort**: 4 hours
**Depends On**: Phase 4

Update CI/CD pipeline to use GitHub Container Registry (ghcr.io) and deploy to EKS instead of GKE.

## Key Insights

- ghcr.io is free for public repos, generous free tier for private
- Already using GitHub Actions - native integration
- No AWS credentials needed for registry (uses GitHub token)
- EKS deployment uses aws-actions instead of google-github-actions
- Keep same workflow structure: build -> deploy (manual approval)

## Requirements

### Functional
- Build Docker image and push to ghcr.io
- Deploy to EKS with Helm
- Manual approval for production deploy
- Smoke tests after deployment
- CloudFlare Tunnel connectivity check

### Non-Functional
- Build time <10 minutes
- Zero registry costs
- Rollback on failure

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    GitHub Actions Workflow                       │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                     Build Job                               │ │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐                 │ │
│  │  │Checkout │───►│ Build   │───►│ Push to │                 │ │
│  │  │  Code   │    │ Image   │    │ ghcr.io │                 │ │
│  │  └─────────┘    └─────────┘    └─────────┘                 │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │              Manual Approval Gate                           │ │
│  └─────────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                    Deploy Job                               │ │
│  │  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐ │ │
│  │  │ AWS     │───►│  Helm   │───►│ Verify  │───►│ Smoke   │ │ │
│  │  │ Auth    │    │ Deploy  │    │ Rollout │    │ Tests   │ │ │
│  │  └─────────┘    └─────────┘    └─────────┘    └─────────┘ │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

## Related Code Files

### Files to Create
| File | Purpose |
|------|---------|
| `.github/workflows/cd-aws.yml` | New AWS deployment workflow |

### Files to Modify
| File | Changes |
|------|---------|
| `.github/workflows/cd-app.yml` | Rename to cd-gcp.yml (archive) |

### GitHub Secrets to Add
| Secret | Description |
|--------|-------------|
| `AWS_ACCESS_KEY_ID` | AWS IAM user access key |
| `AWS_SECRET_ACCESS_KEY` | AWS IAM user secret key |
| `AWS_REGION` | AWS region (us-east-1) |
| `EKS_CLUSTER_NAME` | EKS cluster name (intellirag) |

### GitHub Secrets to Remove (After Migration)
| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | No longer needed |
| `GCP_SA_KEY` | No longer needed |
| `GKE_CLUSTER` | No longer needed |
| `GKE_REGION` | No longer needed |
| `DOCKER_REGISTRY` | Replaced by ghcr.io |

## Implementation Steps

### Step 1: Create New AWS CD Workflow

```yaml
# .github/workflows/cd-aws.yml
name: CD - Build and Deploy to AWS

on:
  push:
    branches: [main]
    paths:
      - 'app/**'
      - 'Dockerfile'
      - 'helm/intellirag-app/**'
      - '.github/workflows/cd-aws.yml'

env:
  REGISTRY: ghcr.io
  IMAGE_NAME: ${{ github.repository }}/intellirag-api
  AWS_REGION: us-east-1
  EKS_CLUSTER: intellirag

jobs:
  # ============================================
  # BUILD JOB - Push to GitHub Container Registry
  # ============================================
  build-and-push:
    name: Build and Push Docker Image
    runs-on: ubuntu-latest
    permissions:
      contents: read
      packages: write

    outputs:
      image-tag: ${{ steps.meta.outputs.version }}
      image-digest: ${{ steps.build.outputs.digest }}

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Free disk space
      uses: jlumbroso/free-disk-space@main
      with:
        tool-cache: false
        android: true
        dotnet: true
        haskell: true
        large-packages: true
        docker-images: true
        swap-storage: true

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Log in to GitHub Container Registry
      uses: docker/login-action@v3
      with:
        registry: ${{ env.REGISTRY }}
        username: ${{ github.actor }}
        password: ${{ secrets.GITHUB_TOKEN }}

    - name: Extract metadata for Docker
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}
        tags: |
          type=sha,prefix=sha-
          type=raw,value=latest

    - name: Build and push Docker image
      id: build
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

  # ============================================
  # DEPLOY JOB - Deploy to EKS
  # ============================================
  deploy-to-eks:
    name: Deploy to EKS (Manual Approval Required)
    runs-on: ubuntu-latest
    needs: build-and-push
    environment: production  # Manual approval gate
    permissions:
      contents: read
      packages: read

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Configure AWS credentials
      uses: aws-actions/configure-aws-credentials@v4
      with:
        aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
        aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        aws-region: ${{ env.AWS_REGION }}

    - name: Update kubeconfig for EKS
      run: |
        aws eks update-kubeconfig --region ${{ env.AWS_REGION }} --name ${{ env.EKS_CLUSTER }}

    - name: Install Helm
      uses: azure/setup-helm@v4
      with:
        version: '3.13.0'

    - name: Create image pull secret
      run: |
        kubectl create secret docker-registry ghcr-secret \
          --namespace app \
          --docker-server=${{ env.REGISTRY }} \
          --docker-username=${{ github.actor }} \
          --docker-password=${{ secrets.GITHUB_TOKEN }} \
          --dry-run=client -o yaml | kubectl apply -f -

    - name: Deploy with Helm
      id: helm-deploy
      run: |
        IMAGE_TAG="${{ needs.build-and-push.outputs.image-tag }}"

        helm upgrade --install intellirag ./helm/intellirag-app \
          --namespace app \
          --create-namespace \
          --set image.repository=${{ env.REGISTRY }}/${{ env.IMAGE_NAME }} \
          --set image.tag=${IMAGE_TAG} \
          --set imagePullSecrets[0].name=ghcr-secret \
          --wait \
          --timeout 10m

        echo "deployment-status=success" >> $GITHUB_OUTPUT

    - name: Verify deployment
      run: |
        kubectl rollout status deployment/intellirag-app -n app --timeout=5m
        kubectl get pods -n app

    - name: Run smoke tests
      run: |
        # Port-forward to service
        kubectl port-forward -n app svc/intellirag-app 8000:8000 &
        PF_PID=$!
        sleep 10

        # Test health endpoint
        curl -f http://localhost:8000/health || exit 1

        # Test ready endpoint
        curl -f http://localhost:8000/ready || exit 1

        # Kill port-forward
        kill $PF_PID

        echo "Smoke tests passed"

    - name: Verify CloudFlare Tunnel connectivity
      env:
        CLOUDFLARE_TUNNEL_URL: ${{ secrets.CLOUDFLARE_TUNNEL_URL }}
      run: |
        curl -f ${CLOUDFLARE_TUNNEL_URL}/health || exit 1
        echo "CloudFlare Tunnel health check passed"

    - name: Rollback on failure
      if: failure()
      run: |
        echo "Deployment failed, rolling back..."
        helm rollback intellirag -n app
        kubectl rollout status deployment/intellirag-app -n app --timeout=5m
```

### Step 2: Update Helm Values for ghcr.io

```yaml
# Update helm/intellirag-app/values.yaml
image:
  repository: ghcr.io/minhhoang2705/intellirag/intellirag-api  # Update this
  pullPolicy: Always
  tag: "latest"

imagePullSecrets:
  - name: ghcr-secret  # Add this
```

### Step 3: Create AWS IAM User for CI/CD

```bash
# scripts/setup-cicd-iam.sh
#!/bin/bash
# Create IAM user for GitHub Actions

aws iam create-user --user-name intellirag-cicd

# Create policy for EKS access
cat > /tmp/cicd-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "eks:DescribeCluster",
        "eks:ListClusters"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name intellirag-cicd-policy \
  --policy-document file:///tmp/cicd-policy.json

aws iam attach-user-policy \
  --user-name intellirag-cicd \
  --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/intellirag-cicd-policy

# Create access key
aws iam create-access-key --user-name intellirag-cicd

echo "Add the access key to GitHub secrets:"
echo "AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY"
```

### Step 4: Add RBAC for CI/CD User

```yaml
# kubernetes/cicd-rbac.yaml
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: cicd-deployer
rules:
- apiGroups: ["", "apps", "extensions"]
  resources: ["deployments", "services", "pods", "configmaps", "secrets", "namespaces"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["get", "list", "watch", "create", "update", "patch", "delete"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: cicd-deployer-binding
subjects:
- kind: User
  name: intellirag-cicd
  apiGroup: rbac.authorization.k8s.io
roleRef:
  kind: ClusterRole
  name: cicd-deployer
  apiGroup: rbac.authorization.k8s.io
```

### Step 5: Archive GCP Workflow

```bash
# Rename existing workflow
mv .github/workflows/cd-app.yml .github/workflows/cd-gcp-archived.yml.bak
```

## Todo List

- [ ] Create `.github/workflows/cd-aws.yml`
- [ ] Create IAM user for CI/CD: `./scripts/setup-cicd-iam.sh`
- [ ] Add GitHub secrets: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY
- [ ] Apply RBAC for CI/CD user
- [ ] Update Helm values for ghcr.io
- [ ] Archive GCP workflow
- [ ] Test build job (push to ghcr.io)
- [ ] Test deploy job (manual approval)
- [ ] Verify smoke tests pass
- [ ] Verify CloudFlare Tunnel check

## Success Criteria

- [ ] Docker image builds and pushes to ghcr.io
- [ ] Image visible in GitHub Packages
- [ ] Deploy job waits for manual approval
- [ ] Helm deploys to EKS successfully
- [ ] Smoke tests pass
- [ ] CloudFlare Tunnel connectivity verified
- [ ] Rollback works on failure

## GitHub Secrets Summary

### New Secrets (AWS)
| Secret | Value | Source |
|--------|-------|--------|
| `AWS_ACCESS_KEY_ID` | AKIA... | IAM user |
| `AWS_SECRET_ACCESS_KEY` | ... | IAM user |
| `AWS_REGION` | us-east-1 | Fixed |
| `EKS_CLUSTER_NAME` | intellirag | Fixed |

### Keep (Unchanged)
| Secret | Purpose |
|--------|---------|
| `CLOUDFLARE_TUNNEL_URL` | GPU server health check |
| `MLFLOW_TRACKING_URI` | MLFlow tracking (optional) |

### Remove After Migration
| Secret | Reason |
|--------|--------|
| `GCP_PROJECT_ID` | No longer using GCP |
| `GCP_SA_KEY` | No longer using GCP |
| `GKE_CLUSTER` | Replaced by EKS |
| `GKE_REGION` | Replaced by AWS_REGION |
| `DOCKER_REGISTRY` | Replaced by ghcr.io |

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| ghcr.io rate limits | Use caching, batch builds |
| AWS credential exposure | Rotate keys regularly |
| Deployment failure | Automatic rollback |

## Security Considerations

- GitHub token scoped to packages:write
- AWS credentials with minimal EKS permissions
- RBAC limits CI/CD user capabilities
- No long-lived credentials in cluster

## Next Steps

After completing this phase:
1. Run full CI/CD pipeline
2. Verify deployment succeeds
3. Proceed to Phase 6: Helm Charts AWS Adaptation
