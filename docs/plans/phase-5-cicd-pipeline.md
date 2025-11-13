# Phase 5: CI/CD Pipeline

**Duration**: 4-6 days
**Status**: Pending
**Dependencies**: Phase 0-4 (All previous phases)

---

## 📋 Overview

This phase establishes a complete CI/CD pipeline using GitHub Actions for automated testing, building, and deployment. The pipeline enforces code quality standards, runs comprehensive tests, builds Docker images, and deploys to both GKE (application services) and local minikube (model serving).

**Key Components**:
- **Continuous Integration**: Automated testing with >80% coverage enforcement
- **Continuous Deployment**: Automated Docker builds and Helm deployments
- **Multi-Environment Support**: Deploy to staging and production (single env for this project)
- **Rollback Mechanisms**: Automated rollback on deployment failures
- **Security Scanning**: Vulnerability scanning for Docker images
- **Performance Testing**: Automated load testing on each deployment

---

## 🎯 Objectives

### Primary Goals
1. Create GitHub Actions CI workflow for automated testing
2. Implement CD workflow for Docker image builds and pushes
3. Automate Helm deployments to GKE
4. Establish rollback mechanisms for failed deployments
5. Integrate security scanning (Trivy, Snyk)
6. Automate performance testing after deployments
7. Configure deployment notifications (Slack/email)

### Success Criteria
- ✅ All tests run automatically on every PR
- ✅ Coverage threshold (>80%) enforced in CI
- ✅ Docker images built and pushed on main branch merge
- ✅ Application automatically deployed to GKE after successful build
- ✅ Security scans catch critical vulnerabilities before deployment
- ✅ Failed deployments trigger automatic rollback
- ✅ Deployment status notifications sent to team
- ✅ Full deployment cycle completes in <10 minutes

---

## 🛠️ Prerequisites

- GitHub repository with IntelliRAG codebase
- GCP service account for GKE access
- Docker registry credentials (GCR)
- Kubernetes cluster configured (from Phase 0)
- Helm charts created (from Phase 1)
- Test suite with >80% coverage

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
cat github-actions-key.json | base64 > github-actions-key.base64

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
| `GKE_REGION` | GKE cluster region | `us-central1` |
| `DOCKER_REGISTRY` | Docker registry URL | `gcr.io` |
| `SLACK_WEBHOOK_URL` | Slack webhook for notifications | `https://hooks.slack.com/...` |

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
    strategy:
      matrix:
        python-version: ['3.11', '3.12']

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

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
          --cov-report=term-missing \
          --cov-fail-under=80 \
          -v

    - name: Run integration tests
      run: |
        pytest tests/integration/ -v -m "not slow"

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v4
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella

  security-scan:
    name: Security Scan
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Run Snyk to check for vulnerabilities
      uses: snyk/actions/python@master
      env:
        SNYK_TOKEN: ${{ secrets.SNYK_TOKEN }}
      with:
        args: --severity-threshold=high

    - name: Run Bandit security linter
      run: |
        pip install bandit
        bandit -r app/ -f json -o bandit-report.json
      continue-on-error: true

    - name: Upload Bandit report
      uses: actions/upload-artifact@v4
      with:
        name: bandit-report
        path: bandit-report.json
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
          type=semver,pattern={{version}}

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

    - name: Upload Trivy results to GitHub Security
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

    - name: Deploy with Helm
      id: helm-deploy
      run: |
        IMAGE_TAG="${{ needs.build-and-push.outputs.image-tag }}"

        helm upgrade --install intellirag ./helm/intellirag-app \
          --namespace app \
          --create-namespace \
          --set image.tag=${IMAGE_TAG} \
          --values helm/intellirag-app/values-prod.yaml \
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
        sleep 5

        # Test health endpoint
        curl -f http://localhost:8000/health || exit 1

        echo "Smoke tests passed"

    - name: Rollback on failure
      if: failure()
      run: |
        echo "Deployment failed, rolling back..."
        helm rollback intellirag -n app
        kubectl rollout status deployment/intellirag-app -n app --timeout=5m

    - name: Notify Slack
      if: always()
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: |
          Deployment to GKE ${{ job.status }}
          Image: ${{ env.DOCKER_REGISTRY }}/${{ env.GCP_PROJECT_ID }}/${{ env.IMAGE_NAME }}:${{ needs.build-and-push.outputs.image-tag }}
          Commit: ${{ github.sha }}
        webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 📦 Task 4: CD Workflow - Model Deployment

### 4.1 Create CD Workflow for Model Updates

**File**: `.github/workflows/cd-models.yml`
```yaml
name: CD - Deploy Models to KServe

on:
  workflow_dispatch:
    inputs:
      model_name:
        description: 'Model name (llm or embedding)'
        required: true
        type: choice
        options:
          - llm
          - embedding
      model_version:
        description: 'Model version/tag'
        required: true
        type: string

jobs:
  deploy-model:
    name: Deploy Model to KServe
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Setup SSH for local server
      run: |
        mkdir -p ~/.ssh
        echo "${{ secrets.LOCAL_SERVER_SSH_KEY }}" > ~/.ssh/id_rsa
        chmod 600 ~/.ssh/id_rsa
        ssh-keyscan -H ${{ secrets.LOCAL_SERVER_IP }} >> ~/.ssh/known_hosts

    - name: Deploy to local KServe via webhook
      run: |
        curl -X POST http://${{ secrets.LOCAL_SERVER_IP }}:5001/deploy \
          -H "Content-Type: application/json" \
          -H "Authorization: Bearer ${{ secrets.WEBHOOK_TOKEN }}" \
          -d '{
            "model_name": "${{ github.event.inputs.model_name }}",
            "model_version": "${{ github.event.inputs.model_version }}",
            "action": "deploy"
          }'

    - name: Verify deployment
      run: |
        # Wait for deployment to complete
        sleep 60

        # Test model endpoint
        if [ "${{ github.event.inputs.model_name }}" == "llm" ]; then
          curl -f https://llm.intellirag.example.com/v1/models || exit 1
        else
          curl -f https://embeddings.intellirag.example.com/health || exit 1
        fi

    - name: Notify Slack
      if: always()
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: |
          Model deployment ${{ job.status }}
          Model: ${{ github.event.inputs.model_name }}
          Version: ${{ github.event.inputs.model_version }}
        webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 📦 Task 5: Performance Testing Workflow

### 5.1 Create Performance Test Workflow

**File**: `.github/workflows/performance-test.yml`
```yaml
name: Performance Testing

on:
  workflow_run:
    workflows: ["CD - Deploy Application"]
    types:
      - completed
  workflow_dispatch:

jobs:
  load-test:
    name: Run Load Tests
    runs-on: ubuntu-latest
    if: ${{ github.event.workflow_run.conclusion == 'success' }}

    steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Install k6
      run: |
        sudo gpg -k
        sudo gpg --no-default-keyring --keyring /usr/share/keyrings/k6-archive-keyring.gpg --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
        echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" | sudo tee /etc/apt/sources.list.d/k6.list
        sudo apt-get update
        sudo apt-get install k6

    - name: Run load test
      run: |
        k6 run tests/performance/load-test.js \
          --out json=load-test-results.json

    - name: Parse and evaluate results
      run: |
        python tests/performance/evaluate_results.py \
          load-test-results.json \
          --p95-threshold 2000 \
          --error-rate-threshold 0.01

    - name: Upload results
      uses: actions/upload-artifact@v4
      with:
        name: load-test-results
        path: load-test-results.json

    - name: Comment PR with results
      if: github.event_name == 'pull_request'
      uses: actions/github-script@v7
      with:
        script: |
          const fs = require('fs');
          const results = JSON.parse(fs.readFileSync('load-test-results.json'));

          github.rest.issues.createComment({
            issue_number: context.issue.number,
            owner: context.repo.owner,
            repo: context.repo.repo,
            body: `## Load Test Results\n\n- P95 Latency: ${results.p95}ms\n- Error Rate: ${results.error_rate}%\n- RPS: ${results.rps}`
          });
```

**File**: `tests/performance/load-test.js`
```javascript
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

const errorRate = new Rate('errors');
const queryDuration = new Trend('query_duration');

export const options = {
  stages: [
    { duration: '2m', target: 50 },   // Ramp up to 50 users
    { duration: '5m', target: 50 },   // Stay at 50 users
    { duration: '2m', target: 100 },  // Ramp up to 100 users
    { duration: '5m', target: 100 },  // Stay at 100 users
    { duration: '2m', target: 0 },    // Ramp down to 0 users
  ],
  thresholds: {
    'http_req_duration': ['p(95)<2000'],  // 95% of requests < 2s
    'errors': ['rate<0.01'],               // Error rate < 1%
  },
};

const BASE_URL = 'https://api.intellirag.example.com';

export default function () {
  // Test query endpoint
  const queryPayload = JSON.stringify({
    query: 'What is retrieval-augmented generation?',
  });

  const params = {
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${__ENV.API_KEY}`,
    },
  };

  const queryRes = http.post(`${BASE_URL}/api/v1/query`, queryPayload, params);

  check(queryRes, {
    'query status is 200': (r) => r.status === 200,
    'query response has answer': (r) => JSON.parse(r.body).answer !== undefined,
  });

  errorRate.add(queryRes.status !== 200);
  queryDuration.add(queryRes.timings.duration);

  sleep(1);
}
```

---

## 📦 Task 6: Rollback Workflow

### 6.1 Create Emergency Rollback Workflow

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
        sleep 5
        curl -f http://localhost:8000/health

    - name: Notify Slack
      uses: 8398a7/action-slack@v3
      with:
        status: ${{ job.status }}
        text: |
          Emergency rollback ${{ job.status }}
          Revision: ${{ github.event.inputs.revision || 'previous' }}
          Triggered by: ${{ github.actor }}
        webhook_url: ${{ secrets.SLACK_WEBHOOK_URL }}
```

---

## 📦 Task 7: Documentation and Badge Updates

### 7.1 Add CI/CD Badges to README

**File**: `README.md` (add badges at top)
```markdown
# IntelliRAG

[![CI](https://github.com/your-org/intellirag/actions/workflows/ci.yml/badge.svg)](https://github.com/your-org/intellirag/actions/workflows/ci.yml)
[![CD - Application](https://github.com/your-org/intellirag/actions/workflows/cd-app.yml/badge.svg)](https://github.com/your-org/intellirag/actions/workflows/cd-app.yml)
[![codecov](https://codecov.io/gh/your-org/intellirag/branch/main/graph/badge.svg)](https://codecov.io/gh/your-org/intellirag)
[![Security Scan](https://github.com/your-org/intellirag/actions/workflows/security-scan.yml/badge.svg)](https://github.com/your-org/intellirag/actions/workflows/security-scan.yml)
```

### 7.2 Create CI/CD Documentation

**File**: `docs/cicd-guide.md`
```markdown
# CI/CD Pipeline Guide

## Overview

Our CI/CD pipeline uses GitHub Actions to automate testing, building, and deployment.

## Workflows

### 1. CI - Test and Lint
- **Trigger**: Pull requests to main/develop, push to develop
- **Steps**: Install deps → Lint → Type check → Unit tests → Integration tests → Security scan
- **Coverage**: >80% required

### 2. CD - Deploy Application
- **Trigger**: Push to main branch
- **Steps**: Build Docker image → Push to GCR → Security scan → Deploy to GKE → Smoke tests
- **Rollback**: Automatic on failure

### 3. CD - Deploy Models
- **Trigger**: Manual via workflow_dispatch
- **Steps**: Trigger webhook → Deploy to KServe → Verify endpoint

### 4. Performance Testing
- **Trigger**: After successful CD deployment
- **Steps**: Run k6 load tests → Evaluate against thresholds → Comment results

### 5. Emergency Rollback
- **Trigger**: Manual via workflow_dispatch
- **Steps**: Rollback to previous or specific Helm revision

## Required Secrets

Configure in GitHub → Settings → Secrets:

| Secret | Description |
|--------|-------------|
| `GCP_PROJECT_ID` | GCP Project ID |
| `GCP_SA_KEY` | Service account key (base64) |
| `GKE_CLUSTER` | GKE cluster name |
| `GKE_REGION` | GKE region |
| `SLACK_WEBHOOK_URL` | Slack notifications |
| `LOCAL_SERVER_SSH_KEY` | SSH key for local server |
| `LOCAL_SERVER_IP` | Local server IP |
| `WEBHOOK_TOKEN` | Model deployment webhook token |

## Deployment Process

1. **Developer pushes to develop branch**
   - CI workflow runs tests
   - PR created for main branch

2. **PR merged to main**
   - CD workflow builds Docker image
   - Image pushed to GCR with security scan
   - Helm deploys to GKE
   - Smoke tests verify deployment

3. **Model updates (manual)**
   - Trigger "CD - Deploy Models" workflow
   - Select model (llm/embedding) and version
   - Webhook deploys to local KServe

4. **Emergency rollback**
   - Trigger "Emergency Rollback" workflow
   - Specify revision or use previous
   - Automatic verification

## Monitoring Deployments

- **GitHub Actions**: View workflow runs in Actions tab
- **Slack**: Receive notifications on #deployments channel
- **Grafana**: Monitor deployment metrics
- **Datadog/Sentry**: Track errors and performance
```

---

## 🧪 Testing and Verification

### Test 1: CI Workflow

```bash
# Create feature branch
git checkout -b feature/test-ci

# Make a change
echo "# Test" >> README.md
git add README.md
git commit -m "test: trigger CI workflow"

# Push and create PR
git push origin feature/test-ci

# Expected:
# - CI workflow runs automatically
# - All tests pass
# - Coverage report generated
# - Security scan completes
```

### Test 2: CD Workflow

```bash
# Merge PR to main
git checkout main
git merge feature/test-ci
git push origin main

# Expected:
# - CD workflow triggers
# - Docker image built and pushed
# - Security scan passes
# - Helm deployment successful
# - Smoke tests pass
# - Slack notification sent
```

### Test 3: Rollback

```bash
# Trigger emergency rollback via GitHub UI
# Actions → Emergency Rollback → Run workflow

# Expected:
# - Previous Helm revision restored
# - Pods restarted with old version
# - Health checks pass
# - Slack notification sent
```

---

## ✅ Deliverables Checklist

- [ ] GitHub Actions workflows created (CI, CD, performance, rollback)
- [ ] GCP service account for CI/CD configured
- [ ] GitHub repository secrets configured
- [ ] CI workflow running on all PRs
- [ ] Test coverage >80% enforced
- [ ] Security scanning integrated (Trivy, Snyk)
- [ ] Docker images built and pushed automatically
- [ ] Helm deployments automated
- [ ] Smoke tests verify deployments
- [ ] Automatic rollback on failures
- [ ] Performance tests run after deployments
- [ ] Slack notifications configured
- [ ] CI/CD badges added to README
- [ ] CI/CD documentation complete
- [ ] Emergency rollback workflow tested

---

## 📝 Summary

Phase 5 completes the IntelliRAG production deployment with a fully automated CI/CD pipeline. Every code change is automatically tested, built, scanned for vulnerabilities, and deployed to production with zero manual intervention. The pipeline enforces quality standards, provides rapid feedback, and enables safe, frequent deployments.

**Key Achievements**:
- **Automated Quality Gates**: Coverage, linting, security scans
- **Zero-Downtime Deployments**: Rolling updates with automatic health checks
- **Fast Feedback**: Complete pipeline in <10 minutes
- **Safety**: Automatic rollback on failures
- **Visibility**: Notifications and deployment tracking

---

**Phase Status**: Pending
**Last Updated**: 2025-11-13
