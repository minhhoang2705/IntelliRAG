# CD Workflow Testing Guide

## Overview

This guide provides step-by-step instructions for testing the CD (Continuous Delivery) workflow, including both automatic BUILD phase and manual DEPLOY phase with approval gates.

## Prerequisites

Before testing, ensure:
- ✅ GitHub Actions secrets configured (Task 1)
- ✅ CI workflow passing with >80% coverage (Task 2)
- ✅ CD workflow file created (`.github/workflows/cd-app.yml`)
- ✅ GitHub `production` environment configured with required reviewers
- ✅ GKE cluster running and accessible
- ✅ CloudFlare Tunnel active on local GPU server

## Test 1: Verify Workflow Syntax

First, validate the workflow file syntax:

```bash
# Check workflow syntax with GitHub CLI (if installed)
gh workflow view "CD - Build and Deploy Application"

# Or manually verify YAML syntax
cat .github/workflows/cd-app.yml | python -c "import yaml, sys; yaml.safe_load(sys.stdin)"
```

**Expected**: No syntax errors

## Test 2: Trigger BUILD Phase (Automatic)

### Step 2.1: Create Test Branch

```bash
# Create feature branch
git checkout -b test/cd-workflow-build

# Make a small change to trigger CD
echo "# CD Test - $(date)" >> README.md
git add README.md
git commit -m "test: trigger CD workflow BUILD phase"
git push origin test/cd-workflow-build
```

### Step 2.2: Create and Merge PR

```bash
# Create PR to main branch
gh pr create --base main --head test/cd-workflow-build \
  --title "Test: CD Workflow BUILD Phase" \
  --body "Testing automatic BUILD phase of CD workflow"

# Wait for CI to pass, then merge
gh pr merge --merge
```

### Step 2.3: Monitor BUILD Phase

1. Navigate to: **GitHub repository → Actions tab**
2. Find workflow run: **"CD - Build and Deploy Application"**
3. Watch BUILD job execute

**Expected Outcomes** (BUILD Phase):
- ✅ Workflow triggers automatically on main push
- ✅ BUILD job starts without waiting
- ✅ Docker image builds successfully
- ✅ Image pushed to GCR with tags: `sha-<commit>` and `latest`
- ✅ Trivy security scan completes
- ✅ No CRITICAL vulnerabilities found
- ✅ SARIF results uploaded to GitHub Security tab
- ⏱️ Duration: ~5 minutes

**Expected Outcomes** (DEPLOY Phase):
- ⏸️ DEPLOY job shows "Waiting" status
- 📧 Required reviewer receives GitHub notification
- 🔒 Deployment blocked until manual approval

### Step 2.4: Verify Build Artifacts

```bash
# List GCR images
gcloud container images list --repository=gcr.io/${GCP_PROJECT_ID}

# View image tags
gcloud container images list-tags gcr.io/${GCP_PROJECT_ID}/intellirag-api
```

**Expected**: Image with `sha-<commit>` and `latest` tags visible

### Step 2.5: Review Security Scan

1. Navigate to: **GitHub repository → Security tab**
2. Click: **Code scanning**
3. Find: **Trivy scan results**

**Expected**: Scan results visible, no CRITICAL vulnerabilities

## Test 3: Manual Approval and DEPLOY Phase

### Step 3.1: Access Approval UI

1. Navigate to: **GitHub repository → Actions**
2. Click the **"CD - Build and Deploy Application"** workflow run
3. Locate: **"Review deployments"** button (yellow banner)

**Expected**: Button visible with text "Review deployments"

### Step 3.2: Review Deployment Details

Before approving, verify:
- ✅ CI workflow passed with >80% coverage
- ✅ Trivy scan found no CRITICAL vulnerabilities
- ✅ BUILD job completed successfully
- ✅ Docker image tag matches commit SHA

### Step 3.3: Approve Deployment

1. Click **"Review deployments"**
2. Check: **production** environment
3. Add comment (optional): "Approved - CD test deployment"
4. Click: **"Approve and deploy"**

**Expected**:
- ✅ DEPLOY job status changes from "Waiting" to "In progress"
- ✅ Yellow banner disappears

### Step 3.4: Monitor DEPLOY Phase

Watch the DEPLOY job execute. Expected steps:

```
1. Checkout code ✅
2. Authenticate to GCP ✅
3. Get GKE credentials ✅
4. Install Helm ✅
5. Set up Python + MLFlow ✅
6. Track deployment in MLFlow ✅
7. Deploy with Helm ✅
8. Verify deployment (rollout status) ✅
9. Run smoke tests ✅
   - Health endpoint: http://localhost:8000/health
   - Ready endpoint: http://localhost:8000/ready
   - Query endpoint (auth check)
10. Verify CloudFlare Tunnel ✅
11. Update MLFlow with success status ✅
```

**Expected Outcomes**:
- ✅ All steps complete successfully
- ✅ Helm deployment completes within 10m timeout
- ✅ Smoke tests pass
- ✅ CloudFlare Tunnel health check passes
- ✅ MLFlow updated with deployment metadata
- ⏱️ Duration: ~5 minutes

### Step 3.5: Verify Deployment in GKE

```bash
# Check pod status
kubectl get pods -n app

# Expected: pods in Running state with new image tag
kubectl describe pod -n app <pod-name> | grep Image:

# Check deployment rollout history
kubectl rollout history deployment/intellirag-app -n app

# Check Helm release
helm list -n app
```

**Expected**:
- New revision deployed
- Pods running with new image tag
- Helm release status: deployed

### Step 3.6: Verify MLFlow Tracking

1. Navigate to: https://mlflow.blockchainradar.xyz
2. Find latest run: `deployment-sha-<commit>`
3. Verify parameters logged:
   - `image_tag`: sha-<commit>
   - `commit_sha`: <commit>
   - `environment`: production
   - `cluster`: intellirag-cluster
   - `namespace`: app
4. Verify tags:
   - `deployment_type`: manual
   - `approved_by`: <your-username>
   - `build_automatic`: true
   - `deployment_status`: success
   - `smoke_tests`: passed
   - `tunnel_health`: passed

**Expected**: All parameters and tags logged correctly

## Test 4: Security Scan Failure

Test that CRITICAL vulnerabilities block deployment.

### Step 4.1: Introduce Vulnerable Dependency

```bash
# Create test branch
git checkout -b test/security-scan-failure

# Add vulnerable package
echo "pyyaml==5.1" >> requirements.txt
git add requirements.txt
git commit -m "test: introduce vulnerable dependency"
git push origin test/security-scan-failure

# Create PR to main
gh pr create --base main --head test/security-scan-failure \
  --title "Test: Security Scan Failure" \
  --body "Testing Trivy blocks CRITICAL vulnerabilities"
```

### Step 4.2: Merge and Monitor

```bash
# Merge PR (CI should pass, but CD will fail)
gh pr merge --merge
```

**Expected Outcomes**:
- ✅ CI workflow passes (security not checked in CI)
- ✅ CD BUILD job starts
- ❌ Trivy scan fails with exit code 1
- ❌ BUILD job fails before pushing image
- ✅ SARIF results uploaded to GitHub Security
- 🚫 DEPLOY job never starts (BUILD failed)
- ✅ Pull request shows failed check

### Step 4.3: Verify Security Tab

1. Navigate to: **GitHub Security → Code scanning**
2. Find: **Trivy alerts for pyyaml**

**Expected**: CRITICAL vulnerability alert visible

### Step 4.4: Fix Vulnerability

```bash
# Revert the vulnerable dependency
git revert HEAD
git push origin main
```

**Expected**: New CD run succeeds

## Test 5: Deployment Failure and Rollback

Test automatic rollback on deployment failure.

### Step 5.1: Simulate Deployment Failure

```bash
# Create test branch
git checkout -b test/deployment-failure

# Introduce invalid Helm value (simulate failure)
# Edit helm/intellirag-app/values.yaml - add invalid configuration
# For example, set invalid resource limits

git add helm/intellirag-app/values.yaml
git commit -m "test: simulate deployment failure"
git push origin test/deployment-failure

# Create and merge PR
gh pr create --base main --head test/deployment-failure \
  --title "Test: Deployment Failure Rollback" \
  --body "Testing automatic rollback on deployment failure"

gh pr merge --merge
```

### Step 5.2: Approve Deployment

1. Wait for BUILD to complete
2. Approve deployment in GitHub UI

### Step 5.3: Monitor Rollback

**Expected Outcomes**:
- ✅ DEPLOY job starts
- ❌ Helm deployment fails (invalid config)
- ✅ "Rollback on failure" step executes
- ✅ Previous Helm revision restored
- ✅ MLFlow updated with failure + rollback tags

### Step 5.4: Verify Rollback in GKE

```bash
# Check Helm history
helm history intellirag -n app

# Expected: 2 revisions (failed + rollback)
# Verify pods running with previous version
kubectl get pods -n app
```

### Step 5.5: Fix and Redeploy

```bash
# Revert the invalid config
git revert HEAD
git push origin main

# Approve new deployment
```

**Expected**: Deployment succeeds

## Test 6: CloudFlare Tunnel Failure

Test tunnel health check validation.

### Step 6.1: Stop CloudFlare Tunnel

On local GPU server:
```bash
# Stop tunnel
sudo systemctl stop cloudflared

# Verify tunnel down
curl https://gpu.intellirag.example.com/health
# Expected: Connection refused or timeout
```

### Step 6.2: Trigger Deployment

```bash
# Make change and push to main
echo "# Tunnel test - $(date)" >> README.md
git add README.md
git commit -m "test: CloudFlare tunnel health check"
git push origin main

# Approve deployment when BUILD completes
```

### Step 6.3: Monitor Failure

**Expected Outcomes**:
- ✅ BUILD completes successfully
- ✅ Deployment starts after approval
- ✅ Helm deployment succeeds
- ✅ Smoke tests pass
- ❌ CloudFlare Tunnel health check fails
- ✅ Automatic rollback triggered
- ✅ MLFlow updated with failure status

### Step 6.4: Restore Tunnel

```bash
# On local GPU server
sudo systemctl start cloudflared

# Verify tunnel up
curl https://gpu.intellirag.example.com/health

# Redeploy
git commit --allow-empty -m "test: retry with tunnel restored"
git push origin main
```

**Expected**: Deployment succeeds with tunnel validation passing

## Test 7: Rejection Flow

Test deployment rejection by reviewer.

### Step 7.1: Trigger Deployment

```bash
# Create change
echo "# Rejection test - $(date)" >> README.md
git add README.md
git commit -m "test: deployment rejection"
git push origin main
```

### Step 7.2: Reject Deployment

1. Wait for BUILD to complete
2. Click **"Review deployments"**
3. Add comment: "Rejected - testing rejection flow"
4. Click: **"Reject"**

**Expected Outcomes**:
- 🚫 DEPLOY job status: "Cancelled"
- ✅ Workflow run marked as cancelled
- ✅ No deployment to GKE
- ✅ No MLFlow run created

## Post-Test Cleanup

After all tests complete:

```bash
# Delete test branches
git branch -D test/cd-workflow-build test/security-scan-failure \
  test/deployment-failure test/deployment-rejection

# Delete remote branches
git push origin --delete test/cd-workflow-build test/security-scan-failure \
  test/deployment-failure test/deployment-rejection

# Verify GKE deployment is stable
kubectl get pods -n app
helm list -n app

# Verify CloudFlare Tunnel is running
curl https://gpu.intellirag.example.com/health
```

## Success Criteria

All tests should demonstrate:
- ✅ BUILD phase runs automatically on main push
- ✅ Trivy blocks CRITICAL vulnerabilities
- ✅ DEPLOY phase requires manual approval
- ✅ Approval UI works correctly
- ✅ Smoke tests validate deployment health
- ✅ CloudFlare Tunnel health validated
- ✅ MLFlow tracks all deployments with metadata
- ✅ Automatic rollback on deployment failure
- ✅ Rejection prevents deployment

## Troubleshooting

### Workflow Not Triggering

**Problem**: CD workflow doesn't start after push to main

**Solution**:
```bash
# Verify workflow file path
ls -la .github/workflows/cd-app.yml

# Check workflow is enabled in GitHub
# Settings → Actions → Workflows

# Verify push modified monitored paths
git log --name-only -1
```

### Approval Button Not Visible

**Problem**: "Review deployments" button doesn't appear

**Solution**:
- Verify `production` environment exists in Settings → Environments
- Verify environment has required reviewers configured
- Verify you are one of the required reviewers
- Check workflow uses `environment: production` in DEPLOY job

### Trivy Scan Hangs

**Problem**: Trivy scan times out or takes too long

**Solution**:
```bash
# Reduce scan scope in workflow
# Add timeout to Trivy action:
timeout: '10m'
```

### MLFlow Connection Fails

**Problem**: MLFlow tracking fails in workflow

**Solution**:
- Verify `MLFLOW_TRACKING_URI` secret is correct
- Test MLFlow from local machine:
  ```bash
  curl https://mlflow.blockchainradar.xyz
  ```
- Check MLFlow server is running:
  ```bash
  kubectl get pods -n observability | grep mlflow
  ```

## Next Steps

After successful testing:
1. Proceed to Task 4: Emergency Rollback Workflow
2. Proceed to Task 5: Documentation and Badge Updates
3. Test complete deployment cycle with real feature

## References

- [CI/CD Guide](./cicd-guide.md)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [Helm Documentation](https://helm.sh/docs/)
- [Trivy Documentation](https://aquasecurity.github.io/trivy/)
