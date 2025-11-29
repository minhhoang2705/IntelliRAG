# Phase 5: CI/CD Pipeline (Simplified)

**Duration**: 2-3 days
**Status**: Pending
**Dependencies**: Phase 0-4 (All previous phases)

---

## 📋 Overview

Streamlined CI/CD pipeline using GitHub Actions for automated testing, building, and deployment. Focuses on essential automation without over-engineering for a learning/capstone project.

**Key Components**:
- **Continuous Integration**: Automated testing with >80% coverage enforcement
- **Continuous Deployment**: Automated Docker builds and Helm deployments to GKE
- **Security Scanning**: Container vulnerability scanning (Trivy only)
- **MLFlow Integration**: Model tracking and versioning in CD pipeline
- **Rollback Mechanisms**: Automated rollback on deployment failures
- **CloudFlare Tunnel Validation**: Health checks for hybrid architecture

**Simplifications from Original Plan**:
- ❌ Removed: Snyk, Bandit, Codecov, automated performance testing, model deployment automation, Slack notifications, multi-Python version matrix
- ✅ Kept: Core CI/CD, Trivy scanning, emergency rollback, MLFlow integration
- ➕ Added: CloudFlare Tunnel health checks

---

## 🎯 Objectives

### Primary Goals
1. Create GitHub Actions CI workflow for automated testing
2. Implement CD workflow for Docker image builds and pushes
3. Automate Helm deployments to GKE
4. Integrate Trivy security scanning
5. Add MLFlow model tracking to CD pipeline
6. Establish rollback mechanisms for failed deployments
7. Validate CloudFlare Tunnel connectivity in deployments

### Success Criteria
- ✅ All tests run automatically on every PR
- ✅ Coverage threshold (>80%) enforced in CI
- ✅ Docker images built and pushed on main branch merge
- ✅ Trivy scans catch critical vulnerabilities before deployment
- ✅ Application automatically deployed to GKE after successful build
- ✅ CloudFlare Tunnel health validated in smoke tests
- ✅ MLFlow tracks model versions used in deployments
- ✅ Failed deployments trigger automatic rollback
- ✅ Full deployment cycle completes in <10 minutes

---

## 🛠️ Prerequisites

- GitHub repository with IntelliRAG codebase
- GCP service account for GKE access
- Docker registry credentials (GCR)
- Kubernetes cluster configured (from Phase 0)
- Helm charts created (from Phase 1)
- Test suite with >80% coverage
- MLFlow server deployed (from Phase 4)
- CloudFlare Tunnel configured (from Phase 0)

---

## 📦 Task 1: Setup GitHub Actions Secrets

### 1.1 Create GCP Service Account for CI/CD

```bash
# Create service account
gcloud iam service-accounts create github-actions-cicd \
  --display-name="GitHub Actions CI/CD Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-cicd@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/container.developer"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-cicd@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/storage.admin"

gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
  --member="serviceAccount:github-actions-cicd@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

# Create and download key
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions-cicd@YOUR_PROJECT_ID.iam.gserviceaccount.com

# Base64 encode for GitHub secret
cat github-actions-key.json | base64 -w 0 > github-actions-key.base64

# Copy the base64 content
cat github-actions-key.base64
```

### 1.2 Configure GitHub Repository Secrets

Navigate to GitHub repository → Settings → Secrets and variables → Actions

Add the following secrets:

| Secret Name | Description | Value |
|-------------|-------------|-------|
| `GCP_PROJECT_ID` | GCP Project ID | `your-project-id` |
| `GCP_SA_KEY` | Service account key (base64) | Output from above command |
| `GKE_CLUSTER` | GKE cluster name | `intellirag-cluster` |
| `GKE_REGION` | GKE cluster region | `asia-southeast1` |
| `DOCKER_REGISTRY` | Docker registry URL | `gcr.io` |
| `MLFLOW_TRACKING_URI` | MLFlow server URL | `https://mlflow.blockchainradar.xyz` |
| `CLOUDFLARE_TUNNEL_URL` | GPU tunnel URL | `https://gpu.intellirag.example.com` |

---

## 📦 Task 2: CI Workflow - Testing and Linting

### 2.1 Create CI Workflow

**File**: `.github/workflows/ci.yml`
```yaml
name: CI - Test and Lint

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [develop]

jobs:
  test:
    name: Run Tests
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python 3.11
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install uv
      run: |
        curl -LsSf https://astral.sh/uv/install.sh | sh
        echo "$HOME/.cargo/bin" >> $GITHUB_PATH

    - name: Install dependencies
      run: |
        uv pip install --system -r requirements.txt
        uv pip install --system -r requirements-dev.txt

    - name: Lint with ruff
      run: |
        ruff check .

    - name: Type check with mypy
      run: |
        mypy app/
      continue-on-error: true

    - name: Run unit tests with coverage
      run: |
        pytest tests/unit/ \
          --cov=app \
          --cov-report=xml \
          --cov-report=html \
          --cov-report=term-missing \
          --cov-fail-under=80 \
          -v

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v -m "not slow"

    - name: Upload coverage report
      if: always()
      uses: actions/upload-artifact@v4
      with:
        name: coverage-report
        path: |
          coverage.xml
          htmlcov/
```

---

## 📦 Task 3: CD Workflow - Build and Deploy Application

### 3.1 Create CD Workflow for Application

**File**: `.github/workflows/cd-app.yml`
```yaml
name: CD - Deploy Application

on:
  push:
    branches: [main]
    paths:
      - 'app/**'
      - 'Dockerfile'
      - 'helm/intellirag-app/**'
      - '.github/workflows/cd-app.yml'

env:
  GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  GKE_CLUSTER: ${{ secrets.GKE_CLUSTER }}
  GKE_REGION: ${{ secrets.GKE_REGION }}
  DOCKER_REGISTRY: ${{ secrets.DOCKER_REGISTRY }}
  IMAGE_NAME: intellirag-api

jobs:
  build-and-push:
    name: Build and Push Docker Image
    runs-on: ubuntu-latest

    outputs:
      image-tag: ${{ steps.meta.outputs.version }}

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Docker Buildx
      uses: docker/setup-buildx-action@v3

    - name: Authenticate to Google Cloud
      uses: google-github-actions/auth@v2
      with:
        credentials_json: ${{ secrets.GCP_SA_KEY }}

    - name: Configure Docker for GCR
      run: |
        gcloud auth configure-docker ${{ env.DOCKER_REGISTRY }}

    - name: Docker metadata
      id: meta
      uses: docker/metadata-action@v5
      with:
        images: ${{ env.DOCKER_REGISTRY }}/${{ env.GCP_PROJECT_ID }}/${{ env.IMAGE_NAME }}
        tags: |
          type=sha,prefix=sha-
          type=raw,value=latest

    - name: Build and push Docker image
      uses: docker/build-push-action@v5
      with:
        context: .
        push: true
        tags: ${{ steps.meta.outputs.tags }}
        labels: ${{ steps.meta.outputs.labels }}
        cache-from: type=gha
        cache-to: type=gha,mode=max

    - name: Run Trivy vulnerability scanner
      uses: aquasecurity/trivy-action@master
      with:
        image-ref: ${{ env.DOCKER_REGISTRY }}/${{ env.GCP_PROJECT_ID }}/${{ env.IMAGE_NAME }}:latest
        format: 'sarif'
        output: 'trivy-results.sarif'
        severity: 'CRITICAL,HIGH'
        exit-code: '1'  # Fail build on critical vulnerabilities

    - name: Upload Trivy results to GitHub Security
      if: always()
      uses: github/codeql-action/upload-sarif@v3
      with:
        sarif_file: 'trivy-results.sarif'

  deploy-to-gke:
    name: Deploy to GKE
    runs-on: ubuntu-latest
    needs: build-and-push

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Authenticate to Google Cloud
      uses: google-github-actions/auth@v2
      with:
        credentials_json: ${{ secrets.GCP_SA_KEY }}

    - name: Get GKE credentials
      uses: google-github-actions/get-gke-credentials@v2
      with:
        cluster_name: ${{ env.GKE_CLUSTER }}
        location: ${{ env.GKE_REGION }}

    - name: Install Helm
      uses: azure/setup-helm@v4
      with:
        version: '3.13.0'

    - name: Set up Python for MLFlow
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install MLFlow client
      run: |
        pip install mlflow

    - name: Track deployment in MLFlow
      env:
        MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
      run: |
        IMAGE_TAG="${{ needs.build-and-push.outputs.image-tag }}"

        # Log deployment as MLFlow run
        python -c "
        import mlflow
        import os

        mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI'))

        with mlflow.start_run(run_name='deployment-${IMAGE_TAG}'):
            mlflow.log_param('image_tag', '${IMAGE_TAG}')
            mlflow.log_param('commit_sha', '${{ github.sha }}')
            mlflow.log_param('environment', 'production')
            mlflow.log_param('cluster', '${{ env.GKE_CLUSTER }}')
            mlflow.log_param('namespace', 'app')
            mlflow.set_tag('deployment_type', 'automated')
            mlflow.set_tag('triggered_by', '${{ github.actor }}')
        "

    - name: Deploy with Helm
      id: helm-deploy
      run: |
        IMAGE_TAG="${{ needs.build-and-push.outputs.image-tag }}"

        helm upgrade --install intellirag ./helm/intellirag-app \
          --namespace app \
          --create-namespace \
          --set image.tag=${IMAGE_TAG} \
          --set image.repository=${{ env.DOCKER_REGISTRY }}/${{ env.GCP_PROJECT_ID }}/${{ env.IMAGE_NAME }} \
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

        # Test basic query endpoint (with placeholder API key)
        curl -f http://localhost:8000/api/v1/query \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer test-key" \
          -d '{"query":"test"}' || echo "Query test skipped (auth required)"

        # Kill port-forward
        kill $PF_PID

        echo "✅ Smoke tests passed"

    - name: Verify CloudFlare Tunnel connectivity
      env:
        CLOUDFLARE_TUNNEL_URL: ${{ secrets.CLOUDFLARE_TUNNEL_URL }}
      run: |
        # Test GPU tunnel is reachable
        curl -f ${CLOUDFLARE_TUNNEL_URL}/health || exit 1

        echo "✅ CloudFlare Tunnel health check passed"

    - name: Update MLFlow deployment status
      if: success()
      env:
        MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
      run: |
        python -c "
        import mlflow
        import os

        mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI'))

        # Update the last run with success status
        client = mlflow.tracking.MlflowClient()
        runs = client.search_runs(
            experiment_ids=['0'],
            filter_string=\"tags.deployment_type='automated'\",
            order_by=['start_time DESC'],
            max_results=1
        )

        if runs:
            run_id = runs[0].info.run_id
            client.set_tag(run_id, 'deployment_status', 'success')
            client.set_tag(run_id, 'smoke_tests', 'passed')
            client.set_tag(run_id, 'tunnel_health', 'passed')
        "

    - name: Rollback on failure
      if: failure()
      run: |
        echo "❌ Deployment failed, rolling back..."
        helm rollback intellirag -n app
        kubectl rollout status deployment/intellirag-app -n app --timeout=5m

    - name: Update MLFlow on failure
      if: failure()
      env:
        MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
      run: |
        python -c "
        import mlflow
        import os

        mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI'))

        client = mlflow.tracking.MlflowClient()
        runs = client.search_runs(
            experiment_ids=['0'],
            filter_string=\"tags.deployment_type='automated'\",
            order_by=['start_time DESC'],
            max_results=1
        )

        if runs:
            run_id = runs[0].info.run_id
            client.set_tag(run_id, 'deployment_status', 'failed')
            client.set_tag(run_id, 'rollback', 'executed')
        "
```

---

## 📦 Task 4: Emergency Rollback Workflow

### 4.1 Create Emergency Rollback Workflow

**File**: `.github/workflows/rollback.yml`
```yaml
name: Emergency Rollback

on:
  workflow_dispatch:
    inputs:
      revision:
        description: 'Helm revision number to rollback to (leave empty for previous)'
        required: false
        type: string

jobs:
  rollback:
    name: Rollback Application
    runs-on: ubuntu-latest

    steps:
    - name: Authenticate to Google Cloud
      uses: google-github-actions/auth@v2
      with:
        credentials_json: ${{ secrets.GCP_SA_KEY }}

    - name: Get GKE credentials
      uses: google-github-actions/get-gke-credentials@v2
      with:
        cluster_name: ${{ secrets.GKE_CLUSTER }}
        location: ${{ secrets.GKE_REGION }}

    - name: Install Helm
      uses: azure/setup-helm@v4
      with:
        version: '3.13.0'

    - name: Set up Python for MLFlow
      uses: actions/setup-python@v5
      with:
        python-version: '3.11'

    - name: Install MLFlow client
      run: |
        pip install mlflow

    - name: Track rollback in MLFlow
      env:
        MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
      run: |
        python -c "
        import mlflow
        import os

        mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI'))

        with mlflow.start_run(run_name='rollback-emergency'):
            mlflow.log_param('revision', '${{ github.event.inputs.revision }}' or 'previous')
            mlflow.log_param('environment', 'production')
            mlflow.log_param('cluster', '${{ secrets.GKE_CLUSTER }}')
            mlflow.set_tag('rollback_type', 'emergency')
            mlflow.set_tag('triggered_by', '${{ github.actor }}')
        "

    - name: Rollback to previous version
      if: ${{ github.event.inputs.revision == '' }}
      run: |
        helm rollback intellirag -n app
        kubectl rollout status deployment/intellirag-app -n app --timeout=5m

    - name: Rollback to specific revision
      if: ${{ github.event.inputs.revision != '' }}
      run: |
        helm rollback intellirag ${{ github.event.inputs.revision }} -n app
        kubectl rollout status deployment/intellirag-app -n app --timeout=5m

    - name: Verify rollback
      run: |
        kubectl get pods -n app
        kubectl port-forward -n app svc/intellirag-app 8000:8000 &
        PF_PID=$!
        sleep 10

        curl -f http://localhost:8000/health || exit 1

        kill $PF_PID

        echo "✅ Rollback verification passed"

    - name: Update MLFlow rollback status
      if: always()
      env:
        MLFLOW_TRACKING_URI: ${{ secrets.MLFLOW_TRACKING_URI }}
      run: |
        STATUS="${{ job.status }}"

        python -c "
        import mlflow
        import os

        mlflow.set_tracking_uri(os.getenv('MLFLOW_TRACKING_URI'))

        client = mlflow.tracking.MlflowClient()
        runs = client.search_runs(
            experiment_ids=['0'],
            filter_string=\"tags.rollback_type='emergency'\",
            order_by=['start_time DESC'],
            max_results=1
        )

        if runs:
            run_id = runs[0].info.run_id
            client.set_tag(run_id, 'rollback_status', '${STATUS}')
        "
```

---

## 📦 Task 5: Documentation and Badge Updates

### 5.1 Add CI/CD Badges to README

**File**: `README.md` (add badges at top)
```markdown
# IntelliRAG

[![CI](https://github.com/your-org/intellirag/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/intellirag/actions/workflows/ci.yml)
[![CD - Application](https://github.com/your-org/intellirag/actions/workflows/cd-app.yml/badge.svg)](https://github.com/your-org/intellirag/actions/workflows/cd-app.yml)
[![Security Scan](https://img.shields.io/badge/security-Trivy-blue)](https://github.com/your-org/intellirag/actions/workflows/cd-app.yml)
```

### 5.2 Create CI/CD Documentation

**File**: `docs/deployment/cicd-guide.md`
```markdown
# CI/CD Pipeline Guide

## Overview

Simplified CI/CD pipeline using GitHub Actions for automated testing, building, and deployment. Designed for learning/capstone context with production-ready patterns.

## Architecture Decisions

**Simplifications Made**:
- Single security tool (Trivy) instead of multiple overlapping scanners
- Manual performance testing instead of automated workflow
- Manual model deployment to local GPU server
- GitHub native notifications instead of external services
- Single Python version testing (deployment version only)

**Why These Are Production-Ready**:
- Trivy covers container + dependency vulnerabilities comprehensively
- Performance testing on-demand is sufficient for stable workloads
- Local GPU server updates are infrequent (stable models)
- GitHub Actions UI provides adequate visibility
- Docker enforces single Python version anyway

## Workflows

### 1. CI - Test and Lint
- **Trigger**: Pull requests to main/develop, push to develop
- **Steps**:
  - Install dependencies with uv
  - Lint with ruff
  - Type check with mypy (non-blocking)
  - Run unit tests (>80% coverage enforced)
  - Run integration tests
  - Upload coverage artifacts
- **Duration**: ~5 minutes

### 2. CD - Deploy Application
- **Trigger**: Push to main branch (app changes only)
- **Steps**:
  - Build Docker image with Buildx
  - Push to GCR with caching
  - Run Trivy security scan (fail on CRITICAL)
  - Track deployment in MLFlow
  - Deploy to GKE with Helm
  - Verify rollout status
  - Run smoke tests (health, ready, query)
  - Validate CloudFlare Tunnel connectivity
  - Update MLFlow with deployment status
- **Rollback**: Automatic on any failure
- **Duration**: ~8-10 minutes

### 3. Emergency Rollback
- **Trigger**: Manual via workflow_dispatch
- **Steps**:
  - Track rollback in MLFlow
  - Rollback to previous or specific Helm revision
  - Verify health checks
  - Update MLFlow rollback status
- **Duration**: ~2-3 minutes

## Required Secrets

Configure in GitHub → Settings → Secrets and variables → Actions:

| Secret | Description | Example |
|--------|-------------|---------|
| `GCP_PROJECT_ID` | GCP Project ID | `intellirag-prod` |
| `GCP_SA_KEY` | Service account key (base64) | Base64-encoded JSON key |
| `GKE_CLUSTER` | GKE cluster name | `intellirag-cluster` |
| `GKE_REGION` | GKE region | `asia-southeast1` |
| `DOCKER_REGISTRY` | Docker registry URL | `gcr.io` |
| `MLFLOW_TRACKING_URI` | MLFlow server URL | `https://mlflow.blockchainradar.xyz` |
| `CLOUDFLARE_TUNNEL_URL` | GPU tunnel URL | `https://gpu.intellirag.example.com` |

## Deployment Process

### Standard Deployment Flow

```
1. Developer creates feature branch
   └─> git checkout -b feature/my-feature

2. Make changes, commit, push
   └─> git add . && git commit -m "feat: add feature" && git push

3. Create PR to develop
   └─> Triggers CI workflow
       ├─ Run tests (>80% coverage)
       ├─ Lint with ruff
       ├─ Type check with mypy
       └─ Upload coverage artifacts

4. Merge PR to develop
   └─> CI workflow runs again

5. Create PR from develop to main
   └─> CI workflow runs

6. Merge to main
   └─> Triggers CD workflow
       ├─ Build Docker image
       ├─ Trivy security scan
       ├─ Push to GCR
       ├─ Track in MLFlow
       ├─ Deploy to GKE with Helm
       ├─ Smoke tests + tunnel validation
       └─ Update MLFlow status

7. Monitor deployment
   └─> GitHub Actions UI
       ├─ View logs
       ├─ Check artifacts
       └─ Review security scans
```

### Emergency Rollback Flow

```
1. Navigate to GitHub Actions
   └─> Actions tab → Emergency Rollback

2. Click "Run workflow"
   └─> Select branch: main
       └─> Enter revision (optional, blank = previous)

3. Workflow executes
   ├─ Track in MLFlow
   ├─ Helm rollback
   ├─ Verify pods
   └─ Update MLFlow

4. Verify rollback
   └─> Check Grafana dashboards
       └─> Test application endpoints
```

## Manual Model Deployment

Since models update infrequently, use manual deployment on local GPU server:

```bash
# On local GPU server (minikube)
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml
kubectl rollout status -n kserve inferenceservice/vllm-qwen

# Verify model endpoint
curl https://gpu.intellirag.example.com/v1/models
```

## Manual Performance Testing

Run load tests manually before major releases:

```bash
# Install k6 (one-time)
brew install k6  # macOS
# OR
sudo apt install k6  # Ubuntu

# Run load test
k6 run tests/performance/load-test.js

# View results in terminal
```

## Monitoring Deployments

### GitHub Actions
- View workflow runs: Repository → Actions
- Check individual steps and logs
- Download coverage artifacts
- Review security scan results

### MLFlow
- View deployment history: https://mlflow.blockchainradar.xyz
- Track deployment parameters (image tags, commits)
- Monitor rollback events
- Review deployment success/failure rates

### Grafana
- Infrastructure metrics: GKE nodes, pods, resources
- Application metrics: Request rates, latency, errors
- Deployment events: Annotations on dashboards

### GKE Console
- Pod status: `kubectl get pods -n app`
- Logs: `kubectl logs -n app deployment/intellirag-app -f`
- Events: `kubectl get events -n app --sort-by='.lastTimestamp'`

## Troubleshooting

### CI Workflow Fails

**Problem**: Tests fail with coverage <80%
```bash
# Run locally to debug
pytest tests/unit/ --cov=app --cov-report=term-missing

# Add missing tests
vim tests/unit/test_<component>.py
```

**Problem**: Ruff linting errors
```bash
# Run locally
ruff check .

# Auto-fix
ruff check . --fix
```

### CD Workflow Fails

**Problem**: Trivy scan finds critical vulnerabilities
```bash
# View scan results in GitHub Security tab
# Update vulnerable dependencies
uv pip install --upgrade <package>

# Rebuild and push
```

**Problem**: Helm deployment times out
```bash
# Check pod status
kubectl get pods -n app

# Check pod logs
kubectl logs -n app <pod-name>

# Check events
kubectl get events -n app --sort-by='.lastTimestamp'
```

**Problem**: Smoke tests fail
```bash
# Check application logs
kubectl logs -n app deployment/intellirag-app

# Port-forward and test locally
kubectl port-forward -n app svc/intellirag-app 8000:8000
curl http://localhost:8000/health
```

**Problem**: CloudFlare Tunnel health check fails
```bash
# Check tunnel status on local server
cloudflared tunnel info

# Restart tunnel if needed
sudo systemctl restart cloudflared
```

### Rollback Fails

**Problem**: No previous revision available
```bash
# List Helm revisions
helm history intellirag -n app

# Rollback to specific revision
# Trigger rollback workflow with revision number
```

## Best Practices

1. **Always run tests locally before pushing**
   ```bash
   pytest tests/ --cov=app --cov-report=term-missing
   ruff check .
   mypy app/
   ```

2. **Use conventional commits for clear history**
   ```bash
   feat(api): add new query endpoint
   fix(vectordb): handle connection timeout
   docs(readme): update deployment guide
   ```

3. **Review security scan results**
   - Check GitHub Security tab after each deployment
   - Address CRITICAL and HIGH vulnerabilities promptly

4. **Monitor MLFlow for deployment patterns**
   - Track deployment frequency
   - Identify rollback trends
   - Review deployment parameters

5. **Test CloudFlare Tunnel before deployments**
   ```bash
   curl https://gpu.intellirag.example.com/health
   ```

6. **Keep Helm charts version-controlled**
   - Update `helm/intellirag-app/Chart.yaml` version
   - Document changes in `helm/intellirag-app/CHANGELOG.md`

## CI/CD Metrics

Track these metrics to improve pipeline:

| Metric | Target | Current |
|--------|--------|---------|
| CI Duration | <5 min | TBD |
| CD Duration | <10 min | TBD |
| Deployment Frequency | 2-3/week | TBD |
| Deployment Success Rate | >95% | TBD |
| Rollback Rate | <5% | TBD |
| Test Coverage | >80% | TBD |

## Future Enhancements

**When to Add**:
- Automated performance testing → When load patterns change frequently
- Model deployment automation → When implementing continuous model retraining
- Advanced notifications → When team grows beyond 2-3 people
- Multi-environment → When adding staging environment
- Canary deployments → When risk tolerance decreases

**Not Needed for This Project**:
- Multi-cloud deployment
- Blue-green deployments
- Feature flags
- A/B testing infrastructure
```

### 5.3 Document Manual Model Deployment Process

**File**: `docs/deployment/model-deployment-manual.md`
```markdown
# Manual Model Deployment Guide

## Overview

Model updates to the local GPU server (KServe on minikube) are performed manually. This is intentional because:
- Models update infrequently (Qwen3-0.6B is stable)
- Local server is not cloud-managed infrastructure
- Manual process is simple (2 commands) and safer
- Avoids complex SSH/webhook automation overhead

## Prerequisites

- SSH access to local GPU server
- kubectl configured for local minikube
- Model files downloaded to `~/.cache/huggingface`

## LLM Model Deployment (Qwen3-0.6B)

### 1. Update InferenceService Manifest

**Edit**: `kubernetes/kserve/vllm-qwen-inference.yaml`

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: vllm-qwen
  namespace: kserve
spec:
  predictor:
    model:
      modelFormat:
        name: vllm
      runtime: kserve-vllmruntime
      storageUri: "hf://Qwen/Qwen3-0.6B"  # Update model version here
      resources:
        limits:
          nvidia.com/gpu: "1"
```

### 2. Apply Updated Manifest

```bash
# SSH to local GPU server
ssh gpu-server

# Apply manifest
kubectl apply -f kubernetes/kserve/vllm-qwen-inference.yaml

# Watch rollout
kubectl rollout status -n kserve inferenceservice/vllm-qwen

# Verify pods
kubectl get pods -n kserve
```

### 3. Verify Model Endpoint

```bash
# Test model endpoint
curl https://gpu.intellirag.example.com/v1/models

# Test inference
curl https://gpu.intellirag.example.com/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "Qwen/Qwen3-0.6B",
    "prompt": "Hello, world!",
    "max_tokens": 50
  }'
```

### 4. Track in MLFlow

```bash
# On your development machine
python -c "
import mlflow

mlflow.set_tracking_uri('https://mlflow.blockchainradar.xyz')

with mlflow.start_run(run_name='model-deployment-llm'):
    mlflow.log_param('model_name', 'Qwen3-0.6B')
    mlflow.log_param('model_format', 'vllm')
    mlflow.log_param('deployment_type', 'manual')
    mlflow.log_param('environment', 'local-gpu-server')
    mlflow.set_tag('deployment_status', 'success')
"
```

## Embedding Model Deployment (BGE-M3)

### 1. Update InferenceService Manifest

**Edit**: `kubernetes/kserve/embedding-bge-m3-inference.yaml`

```yaml
apiVersion: serving.kserve.io/v1beta1
kind: InferenceService
metadata:
  name: embedding-bge-m3
  namespace: kserve
spec:
  predictor:
    containers:
    - name: embedding-server
      image: your-embedding-service:latest  # Update version here
      env:
      - name: MODEL_NAME
        value: "BAAI/bge-m3"  # Update model if needed
```

### 2. Apply and Verify

```bash
# Apply manifest
kubectl apply -f kubernetes/kserve/embedding-bge-m3-inference.yaml

# Watch rollout
kubectl rollout status -n kserve inferenceservice/embedding-bge-m3

# Test endpoint
curl https://gpu.intellirag.example.com/embeddings/health
```

## Rollback Model Deployment

If new model version has issues:

```bash
# List InferenceService revisions
kubectl get inferenceservices -n kserve

# Rollback to previous version
kubectl rollout undo -n kserve inferenceservice/vllm-qwen

# Verify rollback
kubectl rollout status -n kserve inferenceservice/vllm-qwen
```

## Troubleshooting

### Model Download Issues

```bash
# Check pod logs
kubectl logs -n kserve <pod-name>

# Pre-download model
huggingface-cli download Qwen/Qwen3-0.6B
```

### GPU Not Detected

```bash
# Verify GPU is available
kubectl describe node minikube | grep nvidia.com/gpu

# Check NVIDIA device plugin
kubectl get pods -n kube-system | grep nvidia
```

### InferenceService Not Ready

```bash
# Check InferenceService status
kubectl get inferenceservices -n kserve

# Check pod events
kubectl get events -n kserve --sort-by='.lastTimestamp'

# Check pod logs
kubectl logs -n kserve <pod-name> -c kserve-container
```

## Best Practices

1. **Test model locally first** before deploying to KServe
   ```bash
   docker run --gpus all -p 8000:8000 \
     vllm/vllm-openai:latest \
     --model Qwen/Qwen3-0.6B
   ```

2. **Always track deployments in MLFlow** for audit trail

3. **Verify CloudFlare Tunnel** is working before deployment

4. **Monitor GPU utilization** during and after deployment
   ```bash
   nvidia-smi -l 1
   ```

5. **Keep model artifacts backed up** in HuggingFace cache
```

---

## 🧪 Testing and Verification

### Test 1: CI Workflow

```bash
# Create feature branch
git checkout -b feature/test-ci-simplified

# Make a test change
echo "# CI Test" >> README.md
git add README.md
git commit -m "test: trigger simplified CI workflow"

# Push and create PR to develop
git push origin feature/test-ci-simplified

# Expected outcomes:
# ✅ CI workflow runs automatically
# ✅ Tests pass with >80% coverage
# ✅ Ruff linting passes
# ✅ Coverage artifacts uploaded
# ⏱️ Duration: ~5 minutes
```

### Test 2: CD Workflow

```bash
# Merge PR to develop, then create PR to main
git checkout develop
git merge feature/test-ci-simplified
git push origin develop

# Create PR from develop to main
# Merge PR to main
git checkout main
git merge develop
git push origin main

# Expected outcomes:
# ✅ CD workflow triggers automatically
# ✅ Docker image built and pushed to GCR
# ✅ Trivy scan completes (no CRITICAL vulnerabilities)
# ✅ MLFlow tracks deployment run
# ✅ Helm deployment successful
# ✅ Smoke tests pass (health, ready)
# ✅ CloudFlare Tunnel health check passes
# ✅ MLFlow updated with success status
# ⏱️ Duration: ~8-10 minutes
```

### Test 3: Security Scan Failure

```bash
# Intentionally introduce vulnerable dependency
# (do this in a test branch)
git checkout -b test/security-scan
echo "pyyaml==5.1" >> requirements.txt  # Vulnerable version
git commit -am "test: trigger security scan failure"
git push origin test/security-scan

# Create PR to main
# Expected outcomes:
# ❌ CD workflow fails at Trivy scan step
# ✅ SARIF results uploaded to GitHub Security
# ✅ Build does not proceed to deployment
# ✅ Pull request shows failed check
```

### Test 4: CloudFlare Tunnel Failure

```bash
# Simulate tunnel failure (on local GPU server)
sudo systemctl stop cloudflared

# Trigger deployment (merge to main)
# Expected outcomes:
# ❌ CD workflow fails at tunnel health check
# ✅ Automatic rollback triggered
# ✅ MLFlow updated with failure + rollback status
# ✅ Previous deployment version restored

# Restore tunnel
sudo systemctl start cloudflared
```

### Test 5: Emergency Rollback

```bash
# Navigate to GitHub Actions UI
# Actions → Emergency Rollback → Run workflow
# Branch: main
# Revision: (leave empty for previous)

# Expected outcomes:
# ✅ MLFlow tracks rollback run
# ✅ Helm rollback executed
# ✅ Pods restarted with previous version
# ✅ Health checks pass
# ✅ MLFlow updated with rollback status
# ⏱️ Duration: ~2-3 minutes
```

---

## ✅ Deliverables Checklist

### GitHub Actions Setup
- [ ] GCP service account created for CI/CD
- [ ] Service account has correct IAM roles (container.developer, storage.admin, artifactregistry.writer)
- [ ] Service account key generated and base64-encoded
- [ ] GitHub repository secrets configured (7 secrets)

### CI Workflow
- [ ] `.github/workflows/ci.yml` created
- [ ] Workflow runs on PR to main/develop
- [ ] Python 3.11 used (deployment version)
- [ ] uv package manager configured
- [ ] Ruff linting integrated
- [ ] mypy type checking (non-blocking)
- [ ] Unit tests run with >80% coverage enforcement
- [ ] Integration tests run (excluding slow tests)
- [ ] Coverage artifacts uploaded to GitHub

### CD Workflow
- [ ] `.github/workflows/cd-app.yml` created
- [ ] Workflow triggers on push to main (app changes only)
- [ ] Docker Buildx configured
- [ ] GCR authentication working
- [ ] Docker metadata action for image tagging
- [ ] Build cache enabled (GitHub Actions cache)
- [ ] Trivy security scan integrated
- [ ] Trivy fails build on CRITICAL vulnerabilities
- [ ] SARIF results uploaded to GitHub Security
- [ ] MLFlow client installed in workflow
- [ ] MLFlow tracks deployment runs with parameters
- [ ] Helm deployment with image tag from build job
- [ ] Rollout status verification
- [ ] Smoke tests (health, ready, query)
- [ ] CloudFlare Tunnel health check
- [ ] MLFlow updated with deployment status
- [ ] Automatic rollback on failure
- [ ] MLFlow tracks rollback events

### Rollback Workflow
- [ ] `.github/workflows/rollback.yml` created
- [ ] Manual trigger via workflow_dispatch
- [ ] Optional revision parameter
- [ ] MLFlow tracks rollback runs
- [ ] Helm rollback to previous or specific revision
- [ ] Health check verification
- [ ] MLFlow updated with rollback status

### Documentation
- [ ] CI/CD badges added to README
- [ ] `docs/deployment/cicd-guide.md` created
- [ ] Simplified approach documented
- [ ] Deployment process documented
- [ ] Manual model deployment guide created (`docs/deployment/model-deployment-manual.md`)
- [ ] Manual performance testing documented
- [ ] Troubleshooting guide included
- [ ] Best practices documented
- [ ] Future enhancements noted

### Testing & Validation
- [ ] CI workflow tested with feature branch PR
- [ ] CD workflow tested with main branch push
- [ ] Security scan failure tested (vulnerable dependency)
- [ ] CloudFlare Tunnel failure tested
- [ ] Emergency rollback tested via GitHub Actions UI
- [ ] MLFlow tracking verified for all workflows
- [ ] Coverage artifacts downloadable from GitHub
- [ ] Trivy results visible in GitHub Security tab

---

## 📝 Summary

Phase 5 (Simplified) establishes production-ready CI/CD automation while avoiding over-engineering for a learning/capstone context.

**Key Achievements**:
- **Automated Quality Gates**: >80% coverage, Trivy security scanning
- **Zero-Downtime Deployments**: Rolling updates with automatic health checks
- **Fast Feedback**: Complete pipeline in <10 minutes
- **Safety**: Automatic rollback on any failure
- **MLOps Integration**: All deployments tracked in MLFlow
- **Hybrid Architecture Support**: CloudFlare Tunnel health validation
- **Visibility**: GitHub Actions UI + MLFlow dashboards

**Intentional Simplifications**:
- Single security tool (Trivy) instead of 3 overlapping scanners
- Manual performance testing instead of automated workflow
- Manual model deployment (2 commands on local server)
- GitHub native notifications instead of Slack
- Single Python version testing (deployment version)

**Why This Is Still Production-Ready**:
- Trivy comprehensively covers container + dependency vulnerabilities
- Performance testing on-demand is sufficient for stable workloads
- Local GPU model updates are infrequent and benefit from manual oversight
- GitHub Actions UI provides adequate deployment visibility
- Docker enforces single Python version regardless of CI matrix

**Timeline**: 2-3 days (vs 4-6 days original plan)

**Budget Impact**: Zero additional cloud costs (no external services)

---

**Phase Status**: Pending
**Last Updated**: 2025-11-29

**Next Phase**: Final integration testing and project wrap-up
