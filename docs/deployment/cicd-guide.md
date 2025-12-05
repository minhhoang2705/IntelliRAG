# CI/CD Pipeline Guide

## Overview

Simplified CI/CD pipeline using GitHub Actions for automated testing, building, and deployment. Designed for learning/capstone context with production-ready patterns.

## Architecture Decisions

**Key Design Choices**:
- **Manual deployment gate**: Build automatic, deploy requires approval (Continuous Delivery not Deployment)
- **Coverage enforcement**: >80% threshold blocks build, not just warns
- **Single security tool**: Trivy only (comprehensive coverage)
- **Manual performance testing**: On-demand instead of automated workflow
- **Manual model deployment**: Local GPU server updates (infrequent, stable)
- **GitHub native notifications**: Built-in Actions UI instead of external services
- **Single Python version**: Deployment version only (3.11)

**Why These Are Production-Ready**:
- Manual deployment approval prevents accidental production releases while maintaining fast feedback
- Coverage gate ensures quality standards before any build artifacts are created
- Trivy covers container + dependency vulnerabilities comprehensively
- Performance testing on-demand is sufficient for stable workloads
- Local GPU server updates are infrequent (stable models benefit from manual oversight)
- GitHub Actions UI provides adequate deployment visibility and audit trail
- Docker enforces single Python version in runtime anyway

## Workflows

### 1. CI - Test and Lint

**File**: `.github/workflows/ci.yml`

- **Trigger**: Pull requests to main/develop, push to develop
- **Steps**:
  - Install dependencies with uv
  - Lint with ruff
  - Type check with mypy (non-blocking)
  - Run unit tests (>80% coverage enforced)
  - Run integration tests
  - Upload coverage artifacts
- **Duration**: ~5 minutes

### 2. CD - Build and Deploy Application

**File**: `.github/workflows/cd-app.yml`

- **Trigger**: Push to main branch (app changes only)
- **Build Phase** (Automatic):
  - Build Docker image with Buildx
  - Push to GCR with caching
  - Run Trivy security scan (fail on CRITICAL)
  - Upload security scan results to GitHub Security tab
- **Deploy Phase** (Manual Approval Required):
  - **Pause for approval** ← Reviewer approves in GitHub UI
  - Track deployment in MLFlow
  - Deploy to GKE with Helm
  - Verify rollout status
  - Run smoke tests (health, ready, query)
  - Validate CloudFlare Tunnel connectivity
  - Update MLFlow with deployment status
- **Rollback**: Automatic on any deployment failure
- **Duration**: Build ~5 minutes, Deploy (after approval) ~5 minutes

### 3. Emergency Rollback

**File**: `.github/workflows/rollback.yml` (to be created in Task 4)

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
       ├─ Run tests (>80% coverage enforced)
       ├─ Lint with ruff
       ├─ Type check with mypy
       └─ Upload coverage artifacts

4. Merge PR to develop
   └─> CI workflow runs again

5. Create PR from develop to main
   └─> CI workflow runs (must pass with >80% coverage)

6. Merge to main
   └─> Triggers CD workflow - BUILD PHASE (Automatic)
       ├─ Build Docker image
       ├─ Trivy security scan (fail on CRITICAL)
       ├─ Push to GCR
       └─ Upload scan results to GitHub Security

7. Review and Approve Deployment
   └─> GitHub Actions → Workflow run → "Review deployments"
       ├─ Check test coverage report (>80%)
       ├─ Check Trivy scan results (no CRITICAL)
       ├─ Verify Docker image tag
       └─ Click "Approve and deploy" button

8. Deploy to GKE (After Approval)
   └─> CD workflow - DEPLOY PHASE (Manual)
       ├─ Track in MLFlow
       ├─ Deploy to GKE with Helm
       ├─ Verify rollout status
       ├─ Run smoke tests + tunnel validation
       └─ Update MLFlow with deployment status

9. Monitor deployment
   └─> GitHub Actions UI / Grafana dashboards
       ├─ View deployment logs
       ├─ Check pod status
       └─ Monitor application metrics
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

## Testing the CI/CD Pipeline

See [CD Testing Guide](./cd-testing-guide.md) for comprehensive testing instructions.
